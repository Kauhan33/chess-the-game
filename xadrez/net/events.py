"""Eventos que `poll()` entrega à interface. `PeerLeft` e `NetworkError` sempre encerram a sessão."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from xadrez.core import Color, GameResult


@dataclass(frozen=True)
class PeerJoined:
    name: str


@dataclass(frozen=True)
class GameStart:
    """Início de uma partida, a primeira ou uma revanche. `minutes=0` significa sem limite de tempo."""

    white: str
    black: str
    your_color: Color
    minutes: float
    increment: float


@dataclass(frozen=True)
class MoveReceived:
    """Jogada com o formato já conferido. A legalidade quem confere é o `GameEngine` da interface."""

    uci: str
    clock_ms: int


@dataclass(frozen=True)
class PeerResigned:
    pass


@dataclass(frozen=True)
class DrawOffered:
    pass


@dataclass(frozen=True)
class DrawAnswered:
    accept: bool


@dataclass(frozen=True)
class GameDecided:
    """A sala decidiu o fim da partida, depois de `plies` meios-lances. Só quem entrou na sala recebe."""

    result: GameResult
    plies: int


@dataclass(frozen=True)
class RematchRequested:
    pass


@dataclass(frozen=True)
class PeerLeft:
    reason: str


@dataclass(frozen=True)
class NetworkError:
    message: str


NetEvent = Union[
    PeerJoined,
    GameStart,
    MoveReceived,
    PeerResigned,
    DrawOffered,
    DrawAnswered,
    GameDecided,
    RematchRequested,
    PeerLeft,
    NetworkError,
]
