"""Opções de uma partida e formatação dos números que o jogador lê na tela."""
from __future__ import annotations

import math
from dataclasses import dataclass

from xadrez.core import GameEngine, TimeControl

DEFAULT_WHITE_NAME = "Jogador 1"
DEFAULT_BLACK_NAME = "Jogador 2"
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_MINUTE = 60


@dataclass(frozen=True)
class MatchOptions:
    """O que o menu decide. Sobrevive à revanche e volta ao menu para não redigitar os nomes."""

    white_name: str = DEFAULT_WHITE_NAME
    black_name: str = DEFAULT_BLACK_NAME
    time_control: TimeControl = TimeControl.RAPID_10
    auto_rotate: bool = True

    def create_engine(self, fen: str | None = None) -> GameEngine:
        return GameEngine(self.white_name, self.black_name, self.time_control, fen)


def format_clock(seconds: float) -> str:
    """Relógio de jogo: 09:57, ou 1:02:33 acima de uma hora. Fração arredonda para cima, como em um relógio de torneio."""
    total = max(0, math.ceil(seconds - 1e-9))
    hours, remainder = divmod(total, _SECONDS_PER_HOUR)
    minutes, secs = divmod(remainder, _SECONDS_PER_MINUTE)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_points(points: float) -> str:
    """Placar da série em português: 1, 0,5 e 1,5."""
    return f"{points:g}".replace(".", ",")
