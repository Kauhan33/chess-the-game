"""Formato das mensagens: uma linha de JSON. Tudo que chega passa por aqui, porque a rede não é confiável (RNF08)."""
from __future__ import annotations

import json
import re
from typing import Callable

from xadrez.core import Color, EndReason, GameResult, PieceType, Square

PROTOCOL_VERSION = 3
MAX_LINE_BYTES = 4096
MAX_NAME_CHARS = 16
MAX_CLOCK_MS = 7 * 24 * 60 * 60 * 1000
DEFAULT_NAME = "Jogador"
REFUSED_VERSION = "version"
REFUSED_ROOM_FULL = "room_full"
# O modo de jogo vale para os dois lados. A sala escolhe, e quem entra segue.
MODE_TRAINING = "training"
MODE_MATCH = "match"

_MAX_MINUTES = 24 * 60
_MAX_INCREMENT_SECONDS = 60 * 60
_MAX_VERSION = 65_535
_MAX_PLIES = 65_535
_UCI_PATTERN = re.compile(r"[a-h][1-8][a-h][1-8][qrbn]?")
_PROMOTIONS = {"q": PieceType.QUEEN, "r": PieceType.ROOK, "b": PieceType.BISHOP, "n": PieceType.KNIGHT}
_COLORS = {color.value for color in Color}
_REASONS = {reason.name.lower(): reason for reason in EndReason}
_REASONS_WITH_WINNER = frozenset({EndReason.CHECKMATE, EndReason.RESIGNATION, EndReason.ABANDONMENT})
_REASONS_WITHOUT_WINNER = frozenset({
    EndReason.STALEMATE,
    EndReason.INSUFFICIENT_MATERIAL,
    EndReason.FIFTY_MOVES,
    EndReason.THREEFOLD_REPETITION,
    EndReason.AGREEMENT,
})


class ProtocolError(Exception):
    """A mensagem não segue o protocolo. A sessão encerra a conexão em vez de tentar entender."""


def is_valid_name(value: object) -> bool:
    # `isprintable` recusa controle, surrogate solto e o que engana a leitura, como inversão de direção de texto.
    return isinstance(value, str) and 0 < len(value) <= MAX_NAME_CHARS and value.isprintable() and bool(value.strip())


def is_valid_uci(value: object) -> bool:
    return isinstance(value, str) and _UCI_PATTERN.fullmatch(value) is not None


def _is_int_up_to(limit: int) -> Callable[[object], bool]:
    # `type` em vez de `isinstance`: em Python, True também é um int, e o protocolo não aceita booleano como número.
    return lambda value: type(value) is int and 0 <= value <= limit


def _is_number_up_to(limit: int) -> Callable[[object], bool]:
    # A comparação também descarta o infinito, que o JSON produz a partir de um texto como 1e999.
    return lambda value: type(value) in (int, float) and 0 <= value <= limit


def _is_bool(value: object) -> bool:
    return type(value) is bool


def _is_refusal(value: object) -> bool:
    return value in (REFUSED_VERSION, REFUSED_ROOM_FULL)


def _is_color(value: object) -> bool:
    return isinstance(value, str) and value in _COLORS


def _is_mode(value: object) -> bool:
    return value in (MODE_TRAINING, MODE_MATCH)


def _is_winner(value: object) -> bool:
    return value is None or _is_color(value)


def _is_reason(value: object) -> bool:
    return isinstance(value, str) and value in _REASONS


_SCHEMAS: dict[str, dict[str, Callable[[object], bool]]] = {
    "hello": {"version": _is_int_up_to(_MAX_VERSION), "name": is_valid_name},
    "start": {
        "white": is_valid_name,
        "black": is_valid_name,
        "your_color": _is_color,
        "minutes": _is_number_up_to(_MAX_MINUTES),
        "increment": _is_number_up_to(_MAX_INCREMENT_SECONDS),
        "mode": _is_mode,
    },
    "refused": {"code": _is_refusal},
    "move": {"uci": is_valid_uci, "clock_ms": _is_int_up_to(MAX_CLOCK_MS)},
    "draw_answer": {"accept": _is_bool},
    "result": {"winner": _is_winner, "reason": _is_reason, "plies": _is_int_up_to(_MAX_PLIES)},
    "resign": {},
    "draw_offer": {},
    "rematch": {},
    "bye": {},
    "ping": {},
}


def encode_message(message: dict[str, object]) -> bytes:
    """Valida também o que sai: um bug deste lado não pode virar uma mensagem que o outro lado recusaria."""
    _require_valid(message)
    line = json.dumps(message, separators=(",", ":"), allow_nan=False).encode("ascii") + b"\n"
    if len(line) > MAX_LINE_BYTES:
        raise ProtocolError("Mensagem grande demais.")
    return line


def decode_message(line: bytes) -> dict[str, object]:
    """Devolve a mensagem com todos os campos conferidos, ou levanta `ProtocolError`."""
    try:
        message = json.loads(line.decode("utf-8"), parse_constant=_refuse_constant)
    except (ValueError, RecursionError) as error:
        # RecursionError: uma linha pequena com milhares de "[" estoura a pilha do decodificador de JSON.
        raise ProtocolError("A mensagem não é um JSON válido.") from error
    _require_valid(message)
    return message


def _refuse_constant(constant: str) -> None:
    raise ValueError(f"Constante fora do JSON padrão: {constant}")


def _require_valid(message: object) -> None:
    if not isinstance(message, dict):
        raise ProtocolError("A mensagem precisa ser um objeto JSON.")
    kind = message.get("type")
    schema = _SCHEMAS.get(kind) if isinstance(kind, str) else None
    if schema is None:
        raise ProtocolError("Tipo de mensagem desconhecido.")
    if message.keys() != {"type", *schema}:
        raise ProtocolError(f"Campos errados na mensagem {kind}.")
    if not all(is_valid(message[field]) for field, is_valid in schema.items()):
        raise ProtocolError(f"Valor inválido na mensagem {kind}.")
    if kind == "result" and not _is_coherent_result(message):
        raise ProtocolError("Vencedor e motivo não combinam na mensagem result.")


def _is_coherent_result(message: dict[str, object]) -> bool:
    """Mate, por exemplo, sempre tem vencedor, e afogamento nunca. Só o tempo esgotado aceita os dois."""
    reason = _REASONS[message["reason"]]
    if message["winner"] is None:
        return reason not in _REASONS_WITH_WINNER
    return reason not in _REASONS_WITHOUT_WINNER


class LineSplitter:
    """Separa as linhas do fluxo TCP. Nunca guarda mais que `MAX_LINE_BYTES` à espera do fim da linha."""

    def __init__(self) -> None:
        self._partial = bytearray()

    def feed(self, chunk: bytes) -> list[bytes]:
        self._partial += chunk
        *lines, rest = self._partial.split(b"\n")
        if len(rest) > MAX_LINE_BYTES or any(len(line) > MAX_LINE_BYTES for line in lines):
            self._partial.clear()
            raise ProtocolError(f"Linha com mais de {MAX_LINE_BYTES} bytes.")
        self._partial = rest
        return [bytes(line) for line in lines]


def sanitize_name(name: object) -> str:
    """Prepara o nome local para envio: o que o jogador digitou não pode fazer o outro lado recusar a conexão."""
    text = name if isinstance(name, str) else ""
    printable = "".join(char for char in text if char.isprintable())
    return printable.strip()[:MAX_NAME_CHARS].strip() or DEFAULT_NAME


def clock_to_wire(clock_ms: object) -> int:
    """Relógio em milissegundos, dentro da faixa do protocolo. Sem limite de tempo (`math.inf`), vale 0."""
    try:
        return min(max(int(clock_ms), 0), MAX_CLOCK_MS)
    except (TypeError, ValueError, OverflowError):
        return 0


def result_fields(result: GameResult, plies: int) -> dict[str, object]:
    """Campos da mensagem `result`. `plies` diz em que lance a partida parou, para os dois lados terminarem iguais."""
    winner = None if result.winner is None else result.winner.value
    return {"winner": winner, "reason": result.reason.name.lower(), "plies": plies}


def parse_result(message: dict[str, object]) -> GameResult:
    """Traduz uma mensagem `result` já conferida por `decode_message`."""
    winner = message["winner"]
    return GameResult(None if winner is None else Color(winner), _REASONS[message["reason"]])


def parse_uci(uci: str) -> tuple[Square, Square, PieceType | None]:
    """Traduz uma jogada de `MoveReceived` para os argumentos de `GameEngine.play`."""
    if not is_valid_uci(uci):
        raise ValueError(f"Jogada em formato inválido: {uci!r}")
    return Square.from_name(uci[:2]), Square.from_name(uci[2:4]), _PROMOTIONS.get(uci[4:])
