"""Matriz de cores do tabuleiro (RF09, RF10).

`states` é a matriz 8x8 de estados. `rgb` a transforma na matriz 8x8x3 de cores que o
renderizador desenha, com a mistura base (1 - a) + destaque a por casa, em uma única
operação de arrays.
"""
from __future__ import annotations

import math
from enum import IntEnum
from typing import Iterable

import numpy as np

BOARD_SIZE = 8
DEFAULT_LIGHT_SQUARE = (214, 186, 142)
DEFAULT_DARK_SQUARE = (104, 66, 42)
_PULSE_HERTZ = 1.1


class CellState(IntEnum):
    """Estado de uma casa. Quanto maior o valor, maior a prioridade."""

    NONE = 0
    LAST_MOVE = 1
    PATH = 2
    CAPTURE = 3
    THREAT = 4
    CHECK = 5
    SELECTED = 6
    CURSOR = 7


DEFAULT_PALETTE = {
    CellState.LAST_MOVE: (196, 170, 74),
    CellState.PATH: (82, 186, 112),
    CellState.CAPTURE: (222, 74, 58),
    CellState.THREAT: (240, 136, 40),
    CellState.CHECK: (232, 40, 44),
    CellState.SELECTED: (246, 208, 82),
    CellState.CURSOR: (86, 176, 240),
}

# Força da mistura com a cor do estado. CHECK e THREAT oscilam entre mínimo e máximo.
_BLEND_STRENGTH = {
    CellState.NONE: (0.0, 0.0),
    CellState.LAST_MOVE: (0.42, 0.42),
    CellState.PATH: (0.55, 0.55),
    CellState.CAPTURE: (0.68, 0.68),
    CellState.THREAT: (0.34, 0.74),
    CellState.CHECK: (0.48, 0.92),
    CellState.SELECTED: (0.78, 0.78),
    CellState.CURSOR: (0.72, 0.72),
}


def _is_on_board(file: int, rank: int) -> bool:
    return 0 <= file < BOARD_SIZE and 0 <= rank < BOARD_SIZE


class ColorMatrix:
    """Estados por casa, indexados por [file, rank], e a conversão deles em cores."""

    def __init__(self, light_square=DEFAULT_LIGHT_SQUARE, dark_square=DEFAULT_DARK_SQUARE, palette=None):
        self.states = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.uint8)
        files, ranks = np.indices((BOARD_SIZE, BOARD_SIZE))
        is_dark = (files + ranks) % 2 == 0
        self._base = np.where(is_dark[..., None], np.array(dark_square, float), np.array(light_square, float))
        colors = {**DEFAULT_PALETTE, **(palette or {})}
        self._highlight = np.array([colors.get(state, (0, 0, 0)) for state in CellState], dtype=float)
        self._blend_low = np.array([_BLEND_STRENGTH[state][0] for state in CellState])
        self._blend_high = np.array([_BLEND_STRENGTH[state][1] for state in CellState])

    def clear(self) -> None:
        self.states.fill(CellState.NONE)

    def set(self, file: int, rank: int, state: CellState) -> None:
        """Marca a casa. Estado de prioridade menor não sobrescreve; NONE sempre limpa."""
        if not _is_on_board(file, rank):
            return
        if state == CellState.NONE or state > self.states[file, rank]:
            self.states[file, rank] = state

    def set_many(self, squares: Iterable[tuple[int, int]], state: CellState) -> None:
        for file, rank in squares:
            self.set(file, rank, state)

    def state_at(self, file: int, rank: int) -> CellState:
        if not _is_on_board(file, rank):
            return CellState.NONE
        return CellState(int(self.states[file, rank]))

    def rgb(self, time: float = 0.0) -> np.ndarray:
        """Matriz (8, 8, 3) de cores no instante `time`. É função pura do tempo e dos estados.

        O pulso 0,5 + 0,5 sen(2 pi f t) varia de 0 a 1 e leva a força da mistura do mínimo
        ao máximo. Estados de força constante têm mínimo igual ao máximo e não piscam.
        """
        pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * _PULSE_HERTZ * time)
        strength = self._blend_low + (self._blend_high - self._blend_low) * pulse
        blend = strength[self.states][..., None]
        return np.rint(self._base * (1.0 - blend) + self._highlight[self.states] * blend).astype(np.uint8)
