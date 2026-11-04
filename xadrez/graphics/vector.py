"""Vetores 2D e 3D.

São usados onde a leitura da matemática importa mais que a velocidade: montar a
câmera, gerar o raio de clique, orientar animações e desenhar marcadores. As contas
em massa (malhas e partículas) ficam em arrays numpy, porque um laço de objetos
Python custaria caro demais a cada quadro.
"""
from __future__ import annotations

import math

import numpy as np

_EPSILON = 1e-12


class Vector2D:
    """Vetor no plano: direção sobre o tabuleiro ou deslocamento em tela."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2D:
        return Vector2D(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> Vector2D:
        return Vector2D(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vector2D:
        return Vector2D(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2D):
            return NotImplemented
        return math.isclose(self.x, other.x, abs_tol=1e-9) and math.isclose(self.y, other.y, abs_tol=1e-9)

    def __repr__(self) -> str:
        return f"Vector2D({self.x:g}, {self.y:g})"

    def dot(self, other: Vector2D) -> float:
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> Vector2D:
        size = self.length()
        return Vector2D() if size < _EPSILON else self / size

    def rotated(self, angle: float) -> Vector2D:
        """Rotação anti-horária: x' = x cos a - y sen a; y' = x sen a + y cos a."""
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return Vector2D(self.x * cos_a - self.y * sin_a, self.x * sin_a + self.y * cos_a)

    def lerp(self, other: Vector2D, t: float) -> Vector2D:
        return self + (other - self) * t

    def reflect(self, normal: Vector2D) -> Vector2D:
        """Reflexão especular: v' = v - 2(v.n)n, com n unitário."""
        unit = normal.normalized()
        return self - unit * (2.0 * self.dot(unit))


class Vector3D:
    """Vetor no espaço: ponto ou direção em coordenadas de mundo."""

    __slots__ = ("x", "y", "z")

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    @classmethod
    def from_array(cls, values) -> Vector3D:
        return cls(values[0], values[1], values[2])

    def as_array(self) -> np.ndarray:
        return np.array((self.x, self.y, self.z), dtype=float)

    def __add__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3D:
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> Vector3D:
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> Vector3D:
        return Vector3D(-self.x, -self.y, -self.z)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3D):
            return NotImplemented
        return all(
            math.isclose(a, b, abs_tol=1e-9)
            for a, b in zip((self.x, self.y, self.z), (other.x, other.y, other.z))
        )

    def __repr__(self) -> str:
        return f"Vector3D({self.x:g}, {self.y:g}, {self.z:g})"

    def dot(self, other: Vector3D) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3D) -> Vector3D:
        """Produto vetorial: perpendicular aos dois, pela regra da mão direita."""
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def normalized(self) -> Vector3D:
        size = self.length()
        return Vector3D() if size < _EPSILON else self / size

    def rotated(self, axis: Vector3D, angle: float) -> Vector3D:
        """Fórmula de Rodrigues: v' = v cos a + (k x v) sen a + k (k.v)(1 - cos a), com k unitário."""
        unit = axis.normalized()
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return self * cos_a + unit.cross(self) * sin_a + unit * (unit.dot(self) * (1.0 - cos_a))

    def lerp(self, other: Vector3D, t: float) -> Vector3D:
        return self + (other - self) * t

    def reflect(self, normal: Vector3D) -> Vector3D:
        """Reflexão especular: v' = v - 2(v.n)n, com n unitário."""
        unit = normal.normalized()
        return self - unit * (2.0 * self.dot(unit))
