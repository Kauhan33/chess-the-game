"""Tipos básicos do motor: cores, tipos de peça, casas e enums do estado da partida."""
from __future__ import annotations

import operator
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

BOARD_SIZE = 8
FILE_NAMES = "abcdefgh"


class Color(Enum):
    WHITE = "white"
    BLACK = "black"

    @property
    def opposite(self) -> Color:
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    @property
    def label(self) -> str:
        return "Brancas" if self is Color.WHITE else "Pretas"


class PieceType(Enum):
    """Tipo de peça. Cada membro carrega os pontos de material e a letra usada em FEN e SAN."""

    PAWN = ("pawn", 1, "P")
    KNIGHT = ("knight", 3, "N")
    BISHOP = ("bishop", 3, "B")
    ROOK = ("rook", 5, "R")
    QUEEN = ("queen", 9, "Q")
    KING = ("king", 0, "K")

    def __new__(cls, value: str, points: int, symbol: str) -> PieceType:
        member = object.__new__(cls)
        member._value_ = value
        member.points = points
        member.symbol = symbol
        return member


class Square(NamedTuple):
    """Casa do tabuleiro: file 0..7 são as colunas a..h; rank 0..7 são as fileiras 1..8."""

    file: int
    rank: int

    @classmethod
    def from_name(cls, name: str) -> Square:
        """Converte um nome como "e4". Nome malformado é erro de quem programou: levanta ValueError."""
        is_well_formed = (
            isinstance(name, str) and len(name) == 2 and name[0] in FILE_NAMES and name[1] in "12345678"
        )
        if not is_well_formed:
            raise ValueError(f"Nome de casa inválido: {name!r}")
        return cls(FILE_NAMES.index(name[0]), int(name[1]) - 1)

    @property
    def name(self) -> str:
        return f"{FILE_NAMES[self.file]}{self.rank + 1}"

    @property
    def is_dark(self) -> bool:
        return (self.file + self.rank) % 2 == 0

    def is_valid(self) -> bool:
        return 0 <= self.file < BOARD_SIZE and 0 <= self.rank < BOARD_SIZE


# Instâncias únicas de cada casa: geradas uma vez só, são reaproveitadas nas tabelas de peças e
# na varredura do tabuleiro, um caminho executado milhares de vezes por segundo.
SQUARE_GRID = tuple(tuple(Square(file, rank) for rank in range(BOARD_SIZE)) for file in range(BOARD_SIZE))
ALL_SQUARES = tuple(square for column in SQUARE_GRID for square in column)


def coerce_square(value: object) -> Square | None:
    """Normaliza a entrada do jogador; devolve None para o que não for uma casa do tabuleiro.

    Aceita qualquer par de inteiros porque a interface pode entregar `(file, rank)` em tupla simples
    ou com inteiros do numpy. `operator.index` aceita esses inteiros e recusa float e texto.
    """
    try:
        file, rank = value
        square = Square(operator.index(file), operator.index(rank))
    except (TypeError, ValueError):
        return None
    return square if square.is_valid() else None


class GameState(Enum):
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    FINISHED = "finished"


class EndReason(Enum):
    CHECKMATE = "Xeque-mate"
    STALEMATE = "Afogamento"
    INSUFFICIENT_MATERIAL = "Material insuficiente"
    FIFTY_MOVES = "Regra dos 50 lances"
    THREEFOLD_REPETITION = "Tripla repetição"
    TIMEOUT = "Tempo esgotado"
    RESIGNATION = "Desistência"
    AGREEMENT = "Empate por acordo"
    ABANDONMENT = "Adversário desconectou"

    @property
    def label(self) -> str:
        return self.value


class MoveError(Enum):
    GAME_NOT_ACTIVE = "A partida não está ativa."
    NO_PIECE = "Não há peça nessa casa."
    NOT_YOUR_TURN = "Essa peça é do adversário."
    ILLEGAL_MOVE = "Essa peça não pode fazer esse movimento."
    LEAVES_KING_IN_CHECK = "Essa jogada deixa o seu rei em xeque."
    PROMOTION_REQUIRED = "Escolha a peça para a promoção do peão."

    @property
    def message(self) -> str:
        return self.value


@dataclass(frozen=True)
class GameResult:
    """Resultado da partida. `winner` é None quando há empate."""

    winner: Color | None
    reason: EndReason

    @property
    def is_draw(self) -> bool:
        return self.winner is None
