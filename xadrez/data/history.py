"""Histórico de partidas de cada conta: as 50 mais recentes, com o PGN e o FEN final."""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .accounts import username_key
from .paths import data_dir
from .storage import DataError, quarantine, read_json, write_json_atomic

MAX_RECORDS = 50
OPPONENT_KINDS = frozenset({"local", "cpu", "rede"})
OUTCOME_WIN = "vitoria"
OUTCOME_LOSS = "derrota"
OUTCOME_DRAW = "empate"
OUTCOMES = frozenset({OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_DRAW})

_FORMAT_VERSION = 1
_FILE_PREFIX = "history-"
_FILE_HASH_CHARS = 32
_TEXT_FIELDS = ("played_at", "opponent", "color", "reason", "time_control", "mode", "pgn", "final_fen")


@dataclass(frozen=True)
class MatchRecord:
    """Uma partida encerrada. Valor inválido levanta `ValueError`: gravado, ele faria o arquivo inteiro ser posto de lado."""

    played_at: str
    opponent: str
    opponent_kind: str
    difficulty: str | None
    color: str
    outcome: str
    reason: str
    moves: int
    seconds: float
    time_control: str
    mode: str
    pgn: str
    final_fen: str

    def __post_init__(self) -> None:
        if not all(isinstance(getattr(self, name), str) for name in _TEXT_FIELDS):
            raise ValueError(f"Os campos {', '.join(_TEXT_FIELDS)} precisam ser texto.")
        if self.opponent_kind not in OPPONENT_KINDS:
            raise ValueError(f"Tipo de adversário desconhecido: {self.opponent_kind!r}")
        if self.outcome not in OUTCOMES:
            raise ValueError(f"Resultado desconhecido: {self.outcome!r}")
        if self.difficulty is not None and not isinstance(self.difficulty, str):
            raise ValueError("A dificuldade precisa ser texto ou None.")
        if type(self.moves) is not int or self.moves < 0:
            raise ValueError("O número de lances precisa ser um inteiro não negativo.")
        if type(self.seconds) not in (int, float) or not 0 <= self.seconds < math.inf:
            raise ValueError("A duração precisa ser um número finito não negativo.")


@dataclass(frozen=True)
class HistoryStats:
    """Contagem sobre as partidas guardadas, não sobre todas as já jogadas pela conta."""

    played: int
    wins: int
    losses: int
    draws: int


class HistoryStore:
    def __init__(self, username: str, directory: Path | None = None) -> None:
        self._path = (data_dir() if directory is None else Path(directory)) / _history_file_name(username)

    def add(self, record: MatchRecord) -> None:
        """Guarda a partida como a mais recente. Levanta `DataError` se não conseguir ler nem gravar."""
        records = [record, *self._load()][:MAX_RECORDS]
        write_json_atomic(self._path, {"version": _FORMAT_VERSION, "records": [asdict(item) for item in records]})

    def records(self) -> list[MatchRecord]:
        """Mais recente primeiro. Sem acesso ao arquivo, a lista vem vazia: histórico nunca impede de jogar."""
        try:
            return self._load()
        except DataError:
            return []

    def stats(self) -> HistoryStats:
        outcomes = [record.outcome for record in self.records()]
        return HistoryStats(
            played=len(outcomes),
            wins=outcomes.count(OUTCOME_WIN),
            losses=outcomes.count(OUTCOME_LOSS),
            draws=outcomes.count(OUTCOME_DRAW),
        )

    def _load(self) -> list[MatchRecord]:
        payload = read_json(self._path)
        if payload is None:
            return []
        try:
            return _parse_records(payload)
        except (KeyError, TypeError, ValueError):
            quarantine(self._path)
            return []


def _history_file_name(username: str) -> str:
    """O nome vem de um hash: nada digitado chega ao caminho, então `../../x`, `CON` ou `a/b` não têm efeito."""
    digest = hashlib.sha256(username_key(username).encode("utf-8", "surrogatepass")).hexdigest()
    return f"{_FILE_PREFIX}{digest[:_FILE_HASH_CHARS]}.json"


def _parse_records(payload: object) -> list[MatchRecord]:
    if payload["version"] != _FORMAT_VERSION:
        raise ValueError("versão desconhecida")
    return [_parse_record(entry) for entry in payload["records"]][:MAX_RECORDS]


def _parse_record(entry: dict[str, object]) -> MatchRecord:
    return MatchRecord(**{field.name: entry[field.name] for field in fields(MatchRecord)})
