"""Formas do HUD: placas de cantos cortados, brilho e o chão de nogueira do painel."""
from __future__ import annotations

import numpy as np
import pygame

from xadrez.graphics.backdrop import render_backdrop

_SUPERSAMPLE = 2
_PANEL_BRIGHTNESS = 150
_SHADOW_BLUR_DIVISOR = 6
_GLOW_FALLOFF = 2.6


def chamfered_points(width: float, height: float, cut: float, inset: float = 0.0) -> list[tuple[float, float]]:
    left, top, right, bottom = inset, inset, width - inset, height - inset
    return [
        (left + cut, top), (right - cut, top), (right, top + cut), (right, bottom - cut),
        (right - cut, bottom), (left + cut, bottom), (left, bottom - cut), (left, top + cut),
    ]


def _usable_size(size: tuple[int, int]) -> tuple[int, int]:
    return max(int(size[0]), 1), max(int(size[1]), 1)


def _usable_cut(size: tuple[int, int], cut: int) -> int:
    return min(cut, size[0] // 2, size[1] // 2)


def _vertical_gradient(size: tuple[int, int], top: tuple, bottom: tuple) -> pygame.Surface:
    width, height = size
    fractions = np.linspace(0.0, 1.0, height)[None, :, None]
    colors = np.array(top, dtype=float) + (np.array(bottom, dtype=float) - np.array(top, dtype=float)) * fractions
    pixels = np.broadcast_to(colors, (width, height, 3)).astype(np.uint8)
    return pygame.surfarray.make_surface(pixels)


def render_plate(size: tuple[int, int], top: tuple, bottom: tuple, border: tuple | None, cut: int) -> pygame.Surface:
    """Placa em degradê vertical. A máscara é superamostrada para os cortes saírem sem serrilhado."""
    size = _usable_size(size)
    cut = _usable_cut(size, cut)
    plate = pygame.Surface(size, pygame.SRCALPHA)
    plate.blit(_vertical_gradient(size, top, bottom), (0, 0))
    mask = pygame.Surface((size[0] * _SUPERSAMPLE, size[1] * _SUPERSAMPLE), pygame.SRCALPHA)
    mask.fill((255, 255, 255, 0))
    pygame.draw.polygon(mask, (255, 255, 255, 255), chamfered_points(*mask.get_size(), cut * _SUPERSAMPLE))
    plate.blit(pygame.transform.smoothscale(mask, size), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    if border is not None:
        plate.blit(render_outline(size, border, cut, 1), (0, 0))
    return plate


def render_outline(size: tuple[int, int], color: tuple, cut: int, thickness: int) -> pygame.Surface:
    size = _usable_size(size)
    cut = _usable_cut(size, cut)
    canvas = pygame.Surface((size[0] * _SUPERSAMPLE, size[1] * _SUPERSAMPLE), pygame.SRCALPHA)
    canvas.fill((*color, 0))
    inset = thickness * _SUPERSAMPLE / 2.0
    points = chamfered_points(*canvas.get_size(), cut * _SUPERSAMPLE, inset)
    pygame.draw.polygon(canvas, (*color, 255), points, thickness * _SUPERSAMPLE)
    return pygame.transform.smoothscale(canvas, size)


def render_glow(size: tuple[int, int], color: tuple, peak_alpha: int) -> pygame.Surface:
    """Brilho elíptico gaussiano: é a luz do abajur caindo em volta da placa de quem joga."""
    width, height = _usable_size(size)
    x = np.linspace(-1.0, 1.0, width)[:, None]
    y = np.linspace(-1.0, 1.0, height)[None, :]
    glow = pygame.Surface((width, height), pygame.SRCALPHA)
    glow.fill((*color, 0))
    alpha = pygame.surfarray.pixels_alpha(glow)
    alpha[:] = (peak_alpha * np.exp(-(x * x + y * y) * _GLOW_FALLOFF)).astype(np.uint8)
    del alpha
    return glow


def render_soft_shadow(size: tuple[int, int], margin: int, peak_alpha: int) -> pygame.Surface:
    """Sombra borrada: desenha um retângulo, reduz e amplia de volta."""
    width, height = _usable_size(size)
    full = (width + 2 * margin, height + 2 * margin)
    sharp = pygame.Surface(full, pygame.SRCALPHA)
    sharp.fill((0, 0, 0, 0))
    pygame.draw.rect(sharp, (0, 0, 0, peak_alpha), (margin, margin, width, height))
    small_size = (max(full[0] // _SHADOW_BLUR_DIVISOR, 1), max(full[1] // _SHADOW_BLUR_DIVISOR, 1))
    return pygame.transform.smoothscale(pygame.transform.smoothscale(sharp, small_size), full)


def render_panel_ground(size: tuple[int, int]) -> pygame.Surface:
    """Chão do painel: a mesma nogueira do fundo 3D, mais escura, com o filete de latão do tabuleiro na divisa."""
    width, height = _usable_size(size)
    ground = render_backdrop(width, height)
    ground.fill((_PANEL_BRIGHTNESS,) * 3, special_flags=pygame.BLEND_RGB_MULT)
    return ground


def draw_inlay_line(surface: pygame.Surface, x: int, height: int, thickness: int, shadow: tuple, brass: tuple) -> None:
    """Filete vertical: sombra, latão e sombra, como a marchetaria em volta das casas."""
    pygame.draw.rect(surface, shadow, (x, 0, thickness + 2, height))
    pygame.draw.rect(surface, brass, (x + 1, 0, thickness, height))


def draw_warning_triangle(surface: pygame.Surface, center: tuple[int, int], radius: int, color: tuple, mark: tuple) -> None:
    x, y = center
    pygame.draw.polygon(surface, color, [(x, y - radius), (x + radius, y + radius - 1), (x - radius, y + radius - 1)])
    stem = max(radius // 4, 1)
    pygame.draw.rect(surface, mark, (x - stem // 2, y - radius // 3, max(stem, 1), radius // 1))
    pygame.draw.rect(surface, mark, (x - stem // 2, y + radius - stem - 2, max(stem, 1), max(stem, 1)))


def draw_arrow(surface: pygame.Surface, center: tuple[int, int], radius: int, points_right: bool, color: tuple) -> None:
    x, y = center
    tip = radius if points_right else -radius
    polygon = [(x + tip, y), (x - tip // 2, y - radius), (x - tip // 2, y + radius)]
    pygame.draw.polygon(surface, color, polygon)
    pygame.draw.aalines(surface, color, True, polygon)
