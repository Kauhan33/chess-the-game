"""Matrizes 4x4 de transformação em coordenadas homogêneas.

Convenção de vetor coluna, p' = M @ p. Em `compose(A, B, C)` o produto é A @ B @ C,
logo C é aplicada primeiro ao ponto. Coordenada homogênea é o que permite escrever
translação (que não é linear em 3D) e projeção perspectiva como produto de matrizes.
"""
from __future__ import annotations

import math
from functools import lru_cache, reduce

import numpy as np

from xadrez.graphics.vector import Vector3D

BOARD_SIZE = 8
_BOARD_HALF = BOARD_SIZE / 2
_SQUARE_CENTER_OFFSET = _BOARD_HALF - 0.5
_MIN_LIGHT_SLOPE = 1e-6
_MIN_W = 1e-9


def identity() -> np.ndarray:
    return np.eye(4)


def translation(x: float, y: float, z: float) -> np.ndarray:
    matrix = np.eye(4)
    matrix[:3, 3] = (x, y, z)
    return matrix


def scaling(sx: float, sy: float | None = None, sz: float | None = None) -> np.ndarray:
    """Escala em relação à origem. Só com `sx`, a escala é uniforme."""
    sy = sx if sy is None else sy
    sz = sx if sz is None else sz
    return np.diag((float(sx), float(sy), float(sz), 1.0))


def rotation_x(angle: float) -> np.ndarray:
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return np.array(
        [[1.0, 0.0, 0.0, 0.0], [0.0, cos_a, -sin_a, 0.0], [0.0, sin_a, cos_a, 0.0], [0.0, 0.0, 0.0, 1.0]]
    )


def rotation_y(angle: float) -> np.ndarray:
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return np.array(
        [[cos_a, 0.0, sin_a, 0.0], [0.0, 1.0, 0.0, 0.0], [-sin_a, 0.0, cos_a, 0.0], [0.0, 0.0, 0.0, 1.0]]
    )


def rotation_z(angle: float) -> np.ndarray:
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return np.array(
        [[cos_a, -sin_a, 0.0, 0.0], [sin_a, cos_a, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    )


def compose(*matrices: np.ndarray) -> np.ndarray:
    """Produto na ordem dada: o último argumento é aplicado primeiro ao ponto."""
    return reduce(np.matmul, matrices) if matrices else np.eye(4)


def look_at(eye, target, up) -> np.ndarray:
    """Matriz de visão: leva o mundo para a base da câmera, que olha para -z.

    A base ortonormal sai de produtos vetoriais:
        f = normalizar(alvo - olho)
        r = normalizar(f x up)
        u = r x f
    Como a base é ortonormal, a inversa da rotação é a transposta (linhas r, u, -f).
    A última coluna é R @ (-olho), ou seja, primeiro leva o olho à origem e depois gira.
    """
    eye_v = Vector3D.from_array(eye)
    forward = (Vector3D.from_array(target) - eye_v).normalized()
    right = forward.cross(Vector3D.from_array(up)).normalized()
    if right.length() == 0.0:
        right = forward.cross(Vector3D(0.0, 0.0, -1.0)).normalized()
    true_up = right.cross(forward)
    return np.array(
        [
            [right.x, right.y, right.z, -right.dot(eye_v)],
            [true_up.x, true_up.y, true_up.z, -true_up.dot(eye_v)],
            [-forward.x, -forward.y, -forward.z, forward.dot(eye_v)],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def perspective(fov_y: float, aspect: float, near: float, far: float) -> np.ndarray:
    """Projeção perspectiva: mapeia o tronco de visão para o cubo NDC [-1, 1].

    Com f = 1 / tan(fov_y / 2), um ponto de visão (x, y, z) vira, após dividir por w:
        x_ndc = f x / (aspect (-z))     y_ndc = f y / (-z)
    A última linha faz w = -z. É essa divisão que deixa o que está longe menor.
    As duas constantes de z mapeiam z = -near para -1 e z = -far para +1.
    """
    focal = 1.0 / math.tan(fov_y / 2.0)
    depth_range = near - far
    return np.array(
        [
            [focal / aspect, 0.0, 0.0, 0.0],
            [0.0, focal, 0.0, 0.0],
            [0.0, 0.0, (far + near) / depth_range, 2.0 * far * near / depth_range],
            [0.0, 0.0, -1.0, 0.0],
        ]
    )


def viewport(x: float, y: float, w: float, h: float) -> np.ndarray:
    """De NDC para pixels: sx = x + (ndc_x + 1) w / 2 e sy = y + (1 - ndc_y) h / 2.

    O sinal de y inverte porque, na tela, y cresce para baixo.
    """
    half_w, half_h = w / 2.0, h / 2.0
    return np.array(
        [
            [half_w, 0.0, 0.0, x + half_w],
            [0.0, -half_h, 0.0, y + half_h],
            [0.0, 0.0, 0.5, 0.5],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def planar_shadow(light_dir, plane_y: float = 0.0) -> np.ndarray:
    """Achata os pontos no plano y = plane_y na direção da luz.

    O ponto p viaja pelo raio p + t d até o plano. De p.y + t d.y = plane_y vem
    t = (plane_y - p.y) / d.y, portanto:
        x' = x - (d.x / d.y)(y - plane_y)
        y' = plane_y
        z' = z - (d.z / d.y)(y - plane_y)
    Tudo isso é linear em (x, y, z, 1), logo cabe em uma matriz. A última linha é
    (0, 0, 0, 1) porque a luz direcional é um ponto no infinito: não há divisão por w.
    """
    dx, dy, dz = light_dir
    if abs(dy) < _MIN_LIGHT_SLOPE:
        raise ValueError("A luz precisa ter componente vertical para projetar sombra no plano.")
    slope_x, slope_z = dx / dy, dz / dy
    return np.array(
        [
            [1.0, -slope_x, 0.0, slope_x * plane_y],
            [0.0, 0.0, 0.0, plane_y],
            [0.0, -slope_z, 1.0, slope_z * plane_y],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def transform_points(matrix: np.ndarray, points) -> np.ndarray:
    """Aplica M a pontos (N, 3) e divide por w. Evita montar (N, 4) quando M é afim."""
    points = np.asarray(points, dtype=float)
    transformed = points @ matrix[:3, :3].T + matrix[:3, 3]
    bottom_row = matrix[3]
    if bottom_row[0] == bottom_row[1] == bottom_row[2] == 0.0 and bottom_row[3] == 1.0:
        return transformed
    w = points @ bottom_row[:3] + bottom_row[3]
    safe_w = np.where(np.abs(w) < _MIN_W, _MIN_W, w)
    return transformed / safe_w[:, None]


def square_to_world(file: int, rank: int) -> tuple[float, float, float]:
    """Centro da casa no mundo: x = file - 3.5 e z = 3.5 - rank (brancas em z positivo)."""
    return (file - _SQUARE_CENTER_OFFSET, 0.0, _SQUARE_CENTER_OFFSET - rank)


def world_to_square(x: float, z: float) -> tuple[int, int] | None:
    """Casa que contém o ponto (x, z), ou None se o ponto está fora do tabuleiro."""
    file = math.floor(x + _BOARD_HALF)
    rank = math.floor(_BOARD_HALF - z)
    if 0 <= file < BOARD_SIZE and 0 <= rank < BOARD_SIZE:
        return file, rank
    return None


@lru_cache(maxsize=256)
def piece_matrix(file: int, rank: int, facing: float = 0.0) -> np.ndarray:
    """Matriz-modelo de uma peça parada: girada em torno de si e levada até a casa.

    São poucas combinações, repetidas a cada quadro, então a matriz fica em cache.
    Por isso ela é somente leitura.
    """
    matrix = compose(translation(*square_to_world(file, rank)), rotation_y(facing))
    matrix.flags.writeable = False
    return matrix
