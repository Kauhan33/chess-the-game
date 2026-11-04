"""Jogador: nome, cor e as duas pontuações, a de material e a da série."""
from __future__ import annotations

from dataclasses import dataclass, field

from .types import Color, PieceType


@dataclass
class Player:
    name: str
    color: Color
    match_points: float = 0.0
    captured: list[PieceType] = field(default_factory=list)

    @property
    def material_score(self) -> int:
        return sum(kind.points for kind in self.captured)
