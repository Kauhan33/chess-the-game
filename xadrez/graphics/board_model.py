"""Geometria do tabuleiro: moldura, filete de latão, casas e veios da madeira."""
from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np

from xadrez.graphics.matrix import BOARD_SIZE, rotation_y, square_to_world, transform_points
from xadrez.graphics.mesh import Mesh

WALNUT_FRAME = (70, 42, 27)
WALNUT_DARK = (38, 23, 16)
WALNUT_EDGE = (98, 62, 38)
BRASS = (190, 150, 84)
FELT_PAD = (14, 9, 7)

_GRAIN_SEED = 8
_GRAIN_PER_SQUARE = 3
_GRAIN_WIDTH_RANGE = (0.004, 0.011)
_GRAIN_SHADE_RANGE = (0.90, 0.96)
_LAMP_CENTER = (-0.8, 0.8)
_LAMP_FALLOFF = 0.0052
_SIDE_SHADES = (1.0, 0.92, 1.0, 0.92)


def _square_ring(inner: float, outer: float, inner_y: float, outer_y: float) -> Mesh:
    """Anel quadrado em quatro trapézios. Cada lado é o mesmo trapézio girado 90 graus."""
    corners = np.array([
        (-outer, outer_y, outer), (outer, outer_y, outer), (inner, inner_y, inner), (-inner, inner_y, inner),
    ])
    vertices = np.vstack([transform_points(rotation_y(side * math.pi / 2.0), corners) for side in range(4)])
    faces = np.arange(16, dtype=np.int32).reshape(4, 4)
    return Mesh(vertices, faces, _SIDE_SHADES)


def build_frame_parts() -> list[tuple[Mesh, tuple[int, int, int]]]:
    """Moldura de fora para dentro: é a ordem de desenho, pois nada ali se cobre."""
    half = BOARD_SIZE / 2.0
    return [
        (_square_ring(4.62, 4.74, -0.34, -0.34), FELT_PAD),
        (_square_ring(4.62, 4.62, -0.07, -0.34), WALNUT_DARK),
        (_square_ring(4.53, 4.62, 0.0, -0.07), WALNUT_EDGE),
        (_square_ring(half + 0.09, 4.53, 0.0, 0.0), WALNUT_FRAME),
        (_square_ring(half + 0.035, half + 0.09, 0.0, 0.0), BRASS),
        (_square_ring(half, half + 0.035, 0.0, 0.0), WALNUT_DARK),
    ]


class BoardGeometry(NamedTuple):
    """Casas e veios no mundo, com o quanto a luz do abajur alcança cada casa."""

    square_corners: np.ndarray  # (8, 8, 4, 3), indexado por [file, rank]
    grain_corners: np.ndarray  # (G, 4, 3)
    grain_square: np.ndarray  # (G, 2): [file, rank] da casa de cada veio
    grain_shades: np.ndarray  # (G,)
    square_light: np.ndarray  # (8, 8)


def _square_corners() -> np.ndarray:
    corners = np.zeros((BOARD_SIZE, BOARD_SIZE, 4, 3))
    half = 0.5
    # Ordem anti-horária vista de cima, para a normal apontar para +y.
    offsets = np.array([(-half, 0.0, half), (half, 0.0, half), (half, 0.0, -half), (-half, 0.0, -half)])
    for file in range(BOARD_SIZE):
        for rank in range(BOARD_SIZE):
            corners[file, rank] = np.array(square_to_world(file, rank)) + offsets
    return corners


def _grain_lines() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Veios finos em cada casa. A direção alterna, como em marchetaria real."""
    rng = np.random.default_rng(_GRAIN_SEED)
    corners, owners, shades = [], [], []
    for file in range(BOARD_SIZE):
        for rank in range(BOARD_SIZE):
            is_along_x = (file + rank) % 2 == 0
            center = np.array(square_to_world(file, rank))
            for _ in range(_GRAIN_PER_SQUARE):
                corners.append(center + _grain_quad(rng, is_along_x))
                owners.append((file, rank))
                shades.append(rng.uniform(*_GRAIN_SHADE_RANGE))
    return np.array(corners), np.array(owners), np.array(shades)


def _grain_quad(rng: np.random.Generator, is_along_x: bool) -> np.ndarray:
    across = rng.uniform(-0.44, 0.44)
    width = rng.uniform(*_GRAIN_WIDTH_RANGE)
    start, end = sorted(rng.uniform(-0.49, 0.49, 2))
    if end - start < 0.35:
        start, end = -0.49, 0.49
    drift = rng.uniform(-0.02, 0.02)
    u = np.array((start, end, end, start))
    v = np.array((across + width, across + width + drift, across - width + drift, across - width))
    if is_along_x:
        return np.c_[u, np.zeros(4), v]
    return np.c_[v, np.zeros(4), u[::-1]]


def _square_light() -> np.ndarray:
    """Queda suave de luz a partir do ponto mais iluminado: 1 - k d^2."""
    files, ranks = np.indices((BOARD_SIZE, BOARD_SIZE))
    x, z = files - 3.5, 3.5 - ranks
    squared = (x - _LAMP_CENTER[0]) ** 2 + (z - _LAMP_CENTER[1]) ** 2
    return 1.04 - _LAMP_FALLOFF * squared


def build_board_geometry() -> BoardGeometry:
    grain_corners, grain_square, grain_shades = _grain_lines()
    return BoardGeometry(_square_corners(), grain_corners, grain_square, grain_shades, _square_light())
