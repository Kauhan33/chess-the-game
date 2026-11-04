"""Easing, interpolação e animações de peça.

Cada animação expõe `model_matrix()`, a composição de translação, rotação e escala do
instante atual. A Interface entrega essa matriz a `Renderer3D.add_mesh`.
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np

from xadrez.graphics.matrix import compose, rotation_y, rotation_z, scaling, square_to_world, translation
from xadrez.graphics.vector import Vector2D

Square = tuple[int, int]
Easing = Callable[[float], float]

_BACK_OVERSHOOT = 1.70158
_BOUNCE_SCALE = 7.5625
_BOUNCE_DIVISOR = 2.75
_MIN_VISIBLE_SCALE = 1e-3


def linear(t: float) -> float:
    return t


def ease_in_out_cubic(t: float) -> float:
    """Acelera e desacelera: 4t^3 na primeira metade, espelhada na segunda."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def ease_out_back(t: float) -> float:
    """Passa do alvo e volta: 1 + (c + 1)(t - 1)^3 + c (t - 1)^2."""
    shifted = t - 1.0
    return 1.0 + (_BACK_OVERSHOOT + 1.0) * shifted**3 + _BACK_OVERSHOOT * shifted**2


def ease_out_bounce(t: float) -> float:
    """Quatro arcos de parábola de altura decrescente, como uma bola quicando."""
    if t < 1.0 / _BOUNCE_DIVISOR:
        return _BOUNCE_SCALE * t * t
    if t < 2.0 / _BOUNCE_DIVISOR:
        t -= 1.5 / _BOUNCE_DIVISOR
        return _BOUNCE_SCALE * t * t + 0.75
    if t < 2.5 / _BOUNCE_DIVISOR:
        t -= 2.25 / _BOUNCE_DIVISOR
        return _BOUNCE_SCALE * t * t + 0.9375
    t -= 2.625 / _BOUNCE_DIVISOR
    return _BOUNCE_SCALE * t * t + 0.984375


class Tween:
    """Interpola de `start` a `end`: valor = start + (end - start) e(t), com t em [0, 1]."""

    def __init__(self, start, end, duration: float, easing: Easing = linear):
        self.start = start
        self.end = end
        self.duration = float(duration)
        self.easing = easing
        self.elapsed = 0.0

    def update(self, dt: float) -> None:
        self.elapsed = min(self.elapsed + max(dt, 0.0), max(self.duration, 0.0))

    @property
    def progress(self) -> float:
        if self.duration <= 0.0:
            return 1.0
        return self.elapsed / self.duration

    @property
    def value(self):
        return self.start + (self.end - self.start) * self.easing(self.progress)

    @property
    def is_done(self) -> bool:
        return self.progress >= 1.0


def _heading_of(direction: Vector2D) -> float:
    """Ângulo que `rotation_y` usa para levar o eixo +x até (direction.x, 0, direction.y)."""
    return math.atan2(-direction.y, direction.x)


def _tilt_toward(direction: Vector2D, angle: float) -> np.ndarray:
    """Inclina o topo para `direction`: gira em torno de y, tomba em torno de z e desfaz o giro.

    R = Ry(h) Rz(-a) Ry(-h). Levar a direção ao eixo x, tombar e voltar é a forma mais
    simples de rotacionar em torno de um eixo horizontal qualquer.
    """
    heading = _heading_of(direction)
    return compose(rotation_y(heading), rotation_z(-angle), rotation_y(-heading))


class _TimedAnimation:
    """Base de duração e progresso. Cada subclasse transforma o progresso em matriz."""

    def __init__(self, duration: float, easing: Easing):
        self._tween = Tween(0.0, 1.0, duration, easing)

    def update(self, dt: float) -> None:
        self._tween.update(dt)

    @property
    def progress(self) -> float:
        return self._tween.progress

    @property
    def eased(self) -> float:
        return self._tween.value

    @property
    def is_done(self) -> bool:
        return self._tween.is_done

    def model_matrix(self) -> np.ndarray:
        raise NotImplementedError


class PieceAnimation(_TimedAnimation):
    """Peça viajando em arco entre duas casas.

    Altura em parábola, y = 4 h t (1 - t), que vale 0 nas pontas e h no meio. No voo a
    peça se inclina para a frente e estica um pouco, de volta ao normal ao pousar:
    M = T(posição) @ R(inclinação) @ Ry(orientação) @ S(esticada).
    """

    BASE_ARC = 0.28
    ARC_PER_SQUARE = 0.09
    MAX_TILT = math.radians(13)
    MAX_STRETCH = 0.07

    def __init__(self, origin: Square, target: Square, duration: float = 0.38,
                 arc_height: float | None = None, facing: float = 0.0):
        super().__init__(duration, ease_in_out_cubic)
        self._start = Vector2D(*self._ground_point(origin))
        self._end = Vector2D(*self._ground_point(target))
        travel = self._end - self._start
        self._direction = travel.normalized()
        self.arc_height = self.BASE_ARC + self.ARC_PER_SQUARE * travel.length() if arc_height is None else arc_height
        self.facing = facing

    @staticmethod
    def _ground_point(square: Square) -> tuple[float, float]:
        x, _, z = square_to_world(*square)
        return x, z

    @property
    def position(self) -> tuple[float, float, float]:
        t = self.eased
        ground = self._start.lerp(self._end, t)
        return ground.x, 4.0 * self.arc_height * t * (1.0 - t), ground.y

    def model_matrix(self) -> np.ndarray:
        flight = math.sin(math.pi * self.progress)
        vertical = 1.0 + self.MAX_STRETCH * flight
        horizontal = 1.0 / math.sqrt(vertical)
        return compose(
            translation(*self.position),
            _tilt_toward(self._direction, self.MAX_TILT * flight),
            rotation_y(self.facing),
            scaling(horizontal, vertical, horizontal),
        )


class CaptureAnimation(_TimedAnimation):
    """Peça capturada encolhe girando e sobe um pouco: M = T @ Ry(giro) @ S(1 - e)."""

    SPIN_ANGLE = 3.0 * math.pi
    LIFT = 0.35

    def __init__(self, square: Square, duration: float = 0.45, facing: float = 0.0):
        super().__init__(duration, ease_in_out_cubic)
        self._ground = square_to_world(*square)
        self.facing = facing

    def model_matrix(self) -> np.ndarray:
        t = self.eased
        x, _, z = self._ground
        return compose(
            translation(x, self.LIFT * t, z),
            rotation_y(self.facing + self.SPIN_ANGLE * t),
            scaling(max(1.0 - t, _MIN_VISIBLE_SCALE)),
        )


class SpawnAnimation(_TimedAnimation):
    """Peça promovida nasce crescendo, com `ease_out_back` para passar um pouco do tamanho."""

    def __init__(self, square: Square, duration: float = 0.45, facing: float = 0.0):
        super().__init__(duration, ease_out_back)
        self._ground = square_to_world(*square)
        self.facing = facing

    def model_matrix(self) -> np.ndarray:
        return compose(
            translation(*self._ground),
            rotation_y(self.facing),
            scaling(max(self.eased, _MIN_VISIBLE_SCALE)),
        )


class KingFallAnimation(_TimedAnimation):
    """Rei derrotado tomba girando em torno da borda da base.

    Girar em torno de um ponto p que não é a origem é conjugar a rotação:
    M = T(p) @ R @ T(-p). O ponto p vai para a origem, gira e volta, então ele não sai
    do lugar: é a borda da base servindo de dobradiça.
    """

    # Passa de 90 graus porque a coroa é mais estreita que a base: é o ângulo em que ela toca a mesa.
    FINAL_ANGLE = math.radians(96)

    def __init__(self, square: Square, direction: tuple[float, float] = (1.0, 0.0), duration: float = 0.95,
                 base_radius: float = 0.34, facing: float = 0.0):
        super().__init__(duration, ease_out_bounce)
        self._ground = square_to_world(*square)
        self._direction = Vector2D(*direction).normalized()
        self._base_radius = base_radius
        self.facing = facing

    @property
    def pivot(self) -> tuple[float, float, float]:
        """Ponto da borda da base, em relação ao centro da peça, que fica fixo na queda."""
        return self._direction.x * self._base_radius, 0.0, self._direction.y * self._base_radius

    def model_matrix(self) -> np.ndarray:
        pivot_x, pivot_y, pivot_z = self.pivot
        return compose(
            translation(*self._ground),
            translation(pivot_x, pivot_y, pivot_z),
            _tilt_toward(self._direction, self.FINAL_ANGLE * self.eased),
            translation(-pivot_x, -pivot_y, -pivot_z),
            rotation_y(self.facing),
        )
