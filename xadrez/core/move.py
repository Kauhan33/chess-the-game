"""Jogada de xadrez e o relatório que o motor devolve depois de tentar executá-la."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .types import GameResult, MoveError, PieceType, Square

if TYPE_CHECKING:
    from .pieces import Piece


@dataclass(frozen=True, slots=True)
class Move:
    origin: Square
    target: Square
    promotion: PieceType | None = None
    is_castling: bool = False
    is_en_passant: bool = False
    is_double_push: bool = False

    @property
    def uci(self) -> str:
        suffix = self.promotion.symbol.lower() if self.promotion else ""
        return f"{self.origin.name}{self.target.name}{suffix}"

    @property
    def captured_square(self) -> Square:
        """Casa da peça capturada. No en passant o peão capturado está ao lado da origem, não no alvo."""
        if self.is_en_passant:
            return Square(self.target.file, self.origin.rank)
        return self.target


@dataclass
class MoveOutcome:
    """Resposta de `GameEngine.play`.

    `piece` é a peça que saiu da origem: na promoção, é o peão, e `promoted_to` diz o novo tipo.
    """

    ok: bool
    error: MoveError | None = None
    move: Move | None = None
    piece: Piece | None = None
    captured: Piece | None = None
    captured_square: Square | None = None
    rook_path: tuple[Square, Square] | None = None
    promoted_to: PieceType | None = None
    gives_check: bool = False
    result: GameResult | None = None
    san: str = ""
