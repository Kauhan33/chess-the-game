"""Câmera orbital: coordenadas de mundo para tela e de tela de volta para o mundo."""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from xadrez.graphics.animation import Tween, ease_in_out_cubic
from xadrez.graphics.matrix import look_at, perspective, square_to_world, transform_points, viewport, world_to_square
from xadrez.graphics.mesh import Mesh
from xadrez.graphics.vector import Vector3D

NEAR_PLANE = 0.5
FAR_PLANE = 80.0
MIN_PITCH = math.radians(18)
MAX_PITCH = math.radians(85)
MIN_DISTANCE = 9.0
MAX_DISTANCE = 32.0
_WORLD_UP = (0.0, 1.0, 0.0)
_RAY_PARALLEL_LIMIT = 1e-9
_MIN_W = 1e-6
# Com a câmera mirando o centro exato, o tabuleiro fica baixo na tela, porque a borda
# próxima cresce em perspectiva. Mirar um pouco à frente centraliza o conjunto na imagem.
_DEFAULT_AIM_LEAD = 0.5
# Abaixo desta proporção (viewport estreito), o campo de visão vertical abre para o
# tabuleiro não ser cortado nas laterais.
_MIN_FULL_FOV_ASPECT = 1.35
# Folga do cilindro envolvente, para cobrir a peça selecionada, que fica levantada, e o tremor.
_PIECE_BOUNDS_MARGIN = 0.16

# Peça que pode ser clicada: file, rank, malha e matriz de modelo.
PickablePiece = tuple[int, int, Mesh, np.ndarray]


class Camera:
    """Orbita em torno do centro do tabuleiro. yaw 0 fica do lado das brancas."""

    def __init__(self, viewport=(0, 0, 1280, 720), yaw: float = 0.0, pitch: float = math.radians(52),
                 distance: float = 16.5, fov_y: float = math.radians(30), target=None):
        self._viewport = tuple(viewport)
        self._yaw = yaw
        self._pitch = float(np.clip(pitch, MIN_PITCH, MAX_PITCH))
        self._distance = distance
        self.fov_y = fov_y
        self._fixed_target = None if target is None else np.asarray(target, dtype=float)
        self._yaw_tween: Tween | None = None
        self.revision = 0
        self._matrices: dict[str, np.ndarray] = {}

    @property
    def viewport(self) -> tuple[int, int, int, int]:
        return self._viewport

    @property
    def yaw(self) -> float:
        return self._yaw

    @property
    def pitch(self) -> float:
        return self._pitch

    @property
    def distance(self) -> float:
        return self._distance

    @property
    def is_moving(self) -> bool:
        return self._yaw_tween is not None

    def set_viewport(self, x: int, y: int, w: int, h: int) -> None:
        self._viewport = (x, y, max(w, 1), max(h, 1))
        self._invalidate()

    def orbit_to(self, yaw: float, duration: float = 0.8) -> None:
        """Anima o giro até `yaw` pelo menor arco."""
        shortest = (yaw - self._yaw + math.pi) % (2.0 * math.pi) - math.pi
        self._yaw_tween = Tween(self._yaw, self._yaw + shortest, duration, ease_in_out_cubic)

    def orbit_by(self, dyaw: float, dpitch: float = 0.0) -> None:
        self._yaw_tween = None
        self._yaw += dyaw
        self._pitch = float(np.clip(self._pitch + dpitch, MIN_PITCH, MAX_PITCH))
        self._invalidate()

    def zoom_by(self, factor: float) -> None:
        self._distance = float(np.clip(self._distance * factor, MIN_DISTANCE, MAX_DISTANCE))
        self._invalidate()

    def update(self, dt: float) -> None:
        if self._yaw_tween is None:
            return
        self._yaw_tween.update(dt)
        self._yaw = self._yaw_tween.value
        if self._yaw_tween.is_done:
            self._yaw_tween = None
        self._invalidate()

    def _invalidate(self) -> None:
        self.revision += 1
        self._matrices.clear()

    def _cached(self, name: str, build) -> np.ndarray:
        matrix = self._matrices.get(name)
        if matrix is None:
            matrix = self._matrices[name] = build()
        return matrix

    @property
    def target(self) -> np.ndarray:
        if self._fixed_target is not None:
            return self._fixed_target
        return np.array((math.sin(self._yaw), 0.0, math.cos(self._yaw))) * _DEFAULT_AIM_LEAD

    @property
    def eye(self) -> np.ndarray:
        """Coordenadas esféricas em torno do alvo: yaw gira em torno de y, pitch eleva."""
        horizontal = self._distance * math.cos(self._pitch)
        return self.target + np.array(
            (horizontal * math.sin(self._yaw), self._distance * math.sin(self._pitch), horizontal * math.cos(self._yaw))
        )

    @property
    def view_matrix(self) -> np.ndarray:
        return self._cached("view", lambda: look_at(self.eye, self.target, _WORLD_UP))

    @property
    def projection_matrix(self) -> np.ndarray:
        return self._cached("projection", self._build_projection)

    def _build_projection(self) -> np.ndarray:
        aspect = self._viewport[2] / self._viewport[3]
        tan_half_fov = math.tan(self.fov_y / 2.0)
        if aspect < _MIN_FULL_FOV_ASPECT:
            tan_half_fov *= _MIN_FULL_FOV_ASPECT / aspect
        return perspective(2.0 * math.atan(tan_half_fov), aspect, NEAR_PLANE, FAR_PLANE)

    @property
    def view_projection_matrix(self) -> np.ndarray:
        return self._cached("view_projection", lambda: self.projection_matrix @ self.view_matrix)

    @property
    def viewport_matrix(self) -> np.ndarray:
        return self._cached("viewport", lambda: viewport(*self._viewport))

    @property
    def inverse_view_projection(self) -> np.ndarray:
        return self._cached("inverse", lambda: np.linalg.inv(self.view_projection_matrix))

    @property
    def focal_pixels(self) -> float:
        """Pixels de tela por unidade de mundo a uma unidade de distância da câmera."""
        return self.projection_matrix[1, 1] * self._viewport[3] / 2.0

    def project(self, points) -> tuple[np.ndarray, np.ndarray]:
        """Mundo -> Recorte -> NDC -> Tela. Devolve pixels (N, 2) e profundidade (N,).

        A profundidade é w = -z de visão: a distância ao longo do eixo da câmera.
        Valores abaixo de NEAR_PLANE estão atrás do plano near e o pixel não vale nada.
        """
        points = np.asarray(points, dtype=float)
        matrix = self.view_projection_matrix
        clip_xy = points @ matrix[:2, :3].T + matrix[:2, 3]
        w = points @ matrix[3, :3] + matrix[3, 3]
        ndc = clip_xy / np.where(np.abs(w) < _MIN_W, _MIN_W, w)[:, None]
        to_screen = self.viewport_matrix
        pixels = ndc * (to_screen[0, 0], to_screen[1, 1]) + (to_screen[0, 3], to_screen[1, 3])
        return pixels, w

    def _unproject(self, ndc_x: float, ndc_y: float, ndc_z: float) -> Vector3D:
        homogeneous = self.inverse_view_projection @ np.array((ndc_x, ndc_y, ndc_z, 1.0))
        return Vector3D.from_array(homogeneous[:3] / homogeneous[3])

    def screen_ray(self, sx: float, sy: float) -> tuple[Vector3D, Vector3D]:
        """Raio de mundo que passa pelo pixel: caminho inverso do pipeline.

        Tela -> NDC desfaz o viewport. Desprojetar (x_ndc, y_ndc, -1) e (x_ndc, y_ndc, +1)
        com a inversa da view-projection dá os pontos do pixel nos planos near e far.
        A direção do raio é far - near.
        """
        x, y, w, h = self._viewport
        ndc_x = 2.0 * (sx - x) / w - 1.0
        ndc_y = 1.0 - 2.0 * (sy - y) / h
        near_point = self._unproject(ndc_x, ndc_y, -1.0)
        far_point = self._unproject(ndc_x, ndc_y, 1.0)
        return near_point, (far_point - near_point).normalized()

    def pick_plane(self, sx: float, sy: float, plane_y: float = 0.0) -> tuple[float, float] | None:
        """Interseção raio-plano: de o.y + t d.y = plane_y vem t = (plane_y - o.y) / d.y."""
        origin, direction = self.screen_ray(sx, sy)
        if abs(direction.y) < _RAY_PARALLEL_LIMIT:
            return None
        t = (plane_y - origin.y) / direction.y
        if t < 0.0:
            return None
        hit = origin + direction * t
        return hit.x, hit.z

    def _contains_pixel(self, sx: float, sy: float) -> bool:
        x, y, w, h = self._viewport
        return x <= sx < x + w and y <= sy < y + h

    def pick_square(self, sx: float, sy: float) -> tuple[int, int] | None:
        """Casa sob o pixel, ou None se o clique caiu fora do viewport ou do tabuleiro."""
        if not self._contains_pixel(sx, sy):
            return None
        hit = self.pick_plane(sx, sy)
        return None if hit is None else world_to_square(*hit)

    def pick_piece(self, sx: float, sy: float, pieces: Iterable[PickablePiece]) -> tuple[int, int] | None:
        """Casa da peça que aparece sob o pixel, ou do tabuleiro, se nenhuma aparecer.

        Vista em ângulo, a cabeça de uma peça cobre a casa de trás, e a peça da frente cobre parte
        da de trás. Para acionar o que o jogador vê, cada malha é projetada e o pixel é testado
        contra as faces dela: é a silhueta. O teste segue a ordem inversa da pintura, da peça mais
        próxima do olho para a mais distante. Um cilindro envolvente descarta antes o que está
        longe do raio, porque projetar 32 malhas a cada movimento do mouse seria desperdício.
        """
        if not self._contains_pixel(sx, sy):
            return None
        origin, direction = self.screen_ray(sx, sy)
        candidates = [piece for piece in pieces if _ray_touches_bounds(origin, direction, piece)]
        candidates.sort(key=self._squared_distance_to_eye)
        for file, rank, mesh, model_matrix in candidates:
            screen_points, _ = self.project(transform_points(model_matrix, mesh.vertices))
            if _pixel_inside_any_face(sx, sy, screen_points[mesh.faces]):
                return file, rank
        return self.pick_square(sx, sy)

    def _squared_distance_to_eye(self, piece: PickablePiece) -> float:
        offset = piece[3][:3, 3] - self.eye
        return float(offset @ offset)


def _ray_touches_bounds(origin: Vector3D, direction: Vector3D, piece: PickablePiece) -> bool:
    """O raio passa pelo cilindro vertical que envolve a peça?

    Em (x, z), o cilindro é o círculo |p - c|^2 = r^2. Trocar p por o + t d dá a
    equação de segundo grau a t^2 + 2 b t + c = 0. Depois confere se y está na altura.
    """
    file, rank, mesh, _ = piece
    center_x, _, center_z = square_to_world(file, rank)
    offset_x, offset_z = origin.x - center_x, origin.z - center_z
    radius = mesh.radius + _PIECE_BOUNDS_MARGIN
    a = direction.x**2 + direction.z**2
    b = offset_x * direction.x + offset_z * direction.z
    c = offset_x**2 + offset_z**2 - radius**2
    discriminant = b * b - a * c
    if a < _RAY_PARALLEL_LIMIT or discriminant < 0.0 or direction.y >= 0.0:
        return False
    # O raio desce: entre a entrada e a saída do cilindro, ele toca a faixa 0 <= y <= altura?
    highest = origin.y + direction.y * (-b - math.sqrt(discriminant)) / a
    lowest = origin.y + direction.y * (-b + math.sqrt(discriminant)) / a
    return highest >= 0.0 and lowest <= mesh.height + _PIECE_BOUNDS_MARGIN


def _pixel_inside_any_face(sx: float, sy: float, quads: np.ndarray) -> bool:
    """Teste do ponto em polígono convexo, para (F, 4, 2) faces projetadas de uma vez.

    O produto vetorial 2D de cada aresta com o vetor até o pixel diz de que lado ele está. Dentro
    da face, os quatro têm o mesmo sinal, seja qual for o sentido em que ela aparece. A aresta
    nula do triângulo (último vértice repetido) dá zero e não atrapalha.
    """
    edges = np.roll(quads, -1, axis=1) - quads
    to_pixel = np.array((sx, sy)) - quads
    sides = edges[..., 0] * to_pixel[..., 1] - edges[..., 1] * to_pixel[..., 0]
    return bool(((sides >= 0.0).all(axis=1) | (sides <= 0.0).all(axis=1)).any())
