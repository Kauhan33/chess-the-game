"""Fundo procedural: mesa de nogueira escura sob um foco de luz quente.

É uma imagem de tela, calculada uma vez por tamanho de viewport, porque os gradientes
suaves saem caros por polígono e, sem textura perspectiva, a mesa não depende da câmera.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pygame

_SEED = 21
_CACHED_SIZES = 8
_WALNUT_DARK = np.array((30.0, 18.0, 12.0))
_WALNUT_LIGHT = np.array((84.0, 52.0, 33.0))
_LAMP_TINT = np.array((1.0, 0.88, 0.72))
_POOL_CENTER = (0.5, 0.5)
_POOL_RADIUS = (0.68, 0.82)
_POOL_FLOOR = 0.22
_POOL_GAIN = 0.92


def _smooth_noise(rng: np.random.Generator, width: int, height: int, cells_x: int, cells_y: int) -> np.ndarray:
    """Ruído de valor: grade aleatória grossa, interpolada com smoothstep em (altura, largura)."""
    grid = rng.random((cells_y + 2, cells_x + 2))
    x = np.linspace(0.0, cells_x, width, endpoint=False)
    y = np.linspace(0.0, cells_y, height, endpoint=False)
    xi, yi = x.astype(int), y.astype(int)
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * (3.0 - 2.0 * fx), fy * fy * (3.0 - 2.0 * fy)
    top = grid[yi][:, xi] * (1.0 - fx) + grid[yi][:, xi + 1] * fx
    bottom = grid[yi + 1][:, xi] * (1.0 - fx) + grid[yi + 1][:, xi + 1] * fx
    return top * (1.0 - fy)[:, None] + bottom * fy[:, None]


def _walnut_pattern(rng: np.random.Generator, width: int, height: int) -> np.ndarray:
    """Veios: faixas finas e esticadas na direção da madeira, somadas em três escalas."""
    broad = _smooth_noise(rng, width, height, 3, 9)
    medium = _smooth_noise(rng, width, height, 5, 46)
    fine = _smooth_noise(rng, width, height, 8, 170)
    pores = _smooth_noise(rng, width, height, 40, 340)
    streaks = 0.5 + 0.5 * np.sin(2.0 * np.pi * (5.0 * broad + 2.0 * medium))
    return np.clip(0.08 + 0.34 * streaks + 0.34 * fine + 0.24 * pores, 0.0, 1.0)


def _lamp_pool(width: int, height: int) -> np.ndarray:
    """Foco de luz: gaussiana elíptica, somada a um mínimo para o canto não ficar preto."""
    x = (np.linspace(0.0, 1.0, width) - _POOL_CENTER[0]) / _POOL_RADIUS[0]
    y = (np.linspace(0.0, 1.0, height) - _POOL_CENTER[1]) / _POOL_RADIUS[1]
    return _POOL_FLOOR + _POOL_GAIN * np.exp(-(x[None, :] ** 2 + y[:, None] ** 2) * 2.2)


@lru_cache(maxsize=_CACHED_SIZES)
def render_backdrop(width: int, height: int) -> pygame.Surface:
    """Gerar a madeira custa cerca de 126 ms em 960x720. A superfície é compartilhada: copie antes de alterá-la."""
    rng = np.random.default_rng(_SEED)
    pattern = _walnut_pattern(rng, width, height)[..., None]
    wood = _WALNUT_DARK + (_WALNUT_LIGHT - _WALNUT_DARK) * pattern
    lit = wood * _lamp_pool(width, height)[..., None] * _LAMP_TINT
    # Ruído de 1 nível quebra as faixas que um gradiente escuro mostra em 8 bits.
    dither = rng.uniform(-0.6, 0.6, (height, width, 1))
    pixels = np.clip(lit + dither, 0.0, 255.0).astype(np.uint8)
    return pygame.surfarray.make_surface(pixels.swapaxes(0, 1))
