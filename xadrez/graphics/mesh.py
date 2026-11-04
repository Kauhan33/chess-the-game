"""Malhas poligonais e os construtores de primitivas.

Toda face é guardada como quadrilátero (M, 4). Um triângulo repete o último índice.
A forma fixa permite processar a cena inteira em arrays, sem laço por face no Python.
A ordem dos vértices é anti-horária vista de fora, o que faz a normal apontar para fora.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

_MIN_NORMAL_LENGTH = 1e-12


def compute_face_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Normal por produto vetorial das diagonais: n = (v2 - v0) x (v3 - v1).

    Funciona igual para quadrilátero e para triângulo degenerado (v3 = v2). Faces sem
    área (malha com escala 0 em animação) ficam com normal nula.
    """
    first_diagonal = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    second_diagonal = vertices[faces[:, 3]] - vertices[faces[:, 1]]
    normals = np.cross(first_diagonal, second_diagonal)
    lengths = np.sqrt((normals * normals).sum(axis=1, keepdims=True))
    return normals / np.maximum(lengths, _MIN_NORMAL_LENGTH)


def compute_face_centers(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    corner_sum = vertices[faces].sum(axis=1)
    is_triangle = faces[:, 2] == faces[:, 3]
    corner_sum[is_triangle] -= vertices[faces[is_triangle, 3]]
    return corner_sum / np.where(is_triangle, 3.0, 4.0)[:, None]


def _pad_faces(faces: Sequence[Sequence[int]]) -> np.ndarray:
    padded = [tuple(face) + (face[-1],) * (4 - len(face)) for face in faces]
    return np.array(padded, dtype=np.int32).reshape(-1, 4)


def _build_face_neighbors(faces: np.ndarray) -> np.ndarray:
    """Face do outro lado de cada aresta. Em malha fechada, a aresta (a, b) de uma face é a

    aresta (b, a) da vizinha. Posição sem vizinha aponta para a própria face, de modo que
    "alguma vizinha está virada para trás" (silhueta) nunca dispara por falta de vizinha.
    """
    neighbors = np.tile(np.arange(len(faces), dtype=np.int32)[:, None], (1, 4))
    edge_owner: dict[tuple[int, int], tuple[int, int]] = {}
    for face_index, face in enumerate(faces.tolist()):
        for corner in range(4):
            a, b = face[corner], face[(corner + 1) % 4]
            if a == b:
                continue
            partner = edge_owner.pop((b, a), None)
            if partner is None:
                edge_owner[(a, b)] = (face_index, corner)
                continue
            neighbors[face_index, corner] = partner[0]
            neighbors[partner] = face_index
    return neighbors


class Mesh:
    """Malha de faces planas. `face_shades` guarda oclusão pré-calculada por face (1 = sem)."""

    def __init__(self, vertices, faces, face_shades=None):
        self.vertices = np.asarray(vertices, dtype=float).reshape(-1, 3)
        self.faces = _pad_faces(faces) if not isinstance(faces, np.ndarray) else faces.astype(np.int32)
        self.face_normals = compute_face_normals(self.vertices, self.faces)
        self.face_centers = compute_face_centers(self.vertices, self.faces)
        count = len(self.faces)
        self.face_shades = np.ones(count) if face_shades is None else np.asarray(face_shades, dtype=float)
        self._face_neighbors: np.ndarray | None = None

    @property
    def face_neighbors(self) -> np.ndarray:
        if self._face_neighbors is None:
            self._face_neighbors = _build_face_neighbors(self.faces)
        return self._face_neighbors

    @property
    def height(self) -> float:
        return float(self.vertices[:, 1].max())

    @property
    def radius(self) -> float:
        """Maior distância ao eixo y: usada para enquadrar a peça em ícones."""
        return float(np.hypot(self.vertices[:, 0], self.vertices[:, 2]).max())

    def transformed(self, matrix: np.ndarray) -> Mesh:
        points = self.vertices @ matrix[:3, :3].T + matrix[:3, 3]
        return Mesh(points, self.faces, self.face_shades)


def _cap_faces(ring: Sequence[int], is_facing_up: bool) -> list[tuple[int, ...]]:
    """Fecha um anel com leque de quadriláteros: menos polígonos que um leque de triângulos."""
    ordered = list(ring) if is_facing_up else list(reversed(ring))
    faces = []
    for i in range(1, len(ordered) - 1, 2):
        faces.append((ordered[0], *ordered[i : i + 3]))
    return faces


def lathe(profile: Sequence[tuple[float, float]], segments: int) -> Mesh:
    """Superfície de revolução: gira o perfil (raio, y) em torno do eixo y.

    Cada ponto do perfil vira um anel p(a) = (r cos a, y, -r sen a). O seno negativo faz
    as faces, na ordem (anel, a), (anel, a + 1), (próximo anel, a + 1), (próximo anel, a),
    terem normal para fora. Raio zero no início ou no fim fecha em ponta. Raio positivo
    fecha com uma tampa plana. O perfil deve ir de baixo para cima.
    """
    angles = np.arange(segments) * (2.0 * math.pi / segments)
    vertices: list[tuple[float, float, float]] = []
    rings: list[list[int]] = []
    for radius, y in profile:
        if radius <= 0.0:
            vertices.append((0.0, y, 0.0))
            rings.append([len(vertices) - 1] * segments)
            continue
        start = len(vertices)
        vertices.extend((radius * math.cos(a), y, -radius * math.sin(a)) for a in angles)
        rings.append(list(range(start, start + segments)))
    faces = _lathe_side_faces(rings, segments)
    if profile[0][0] > 0.0:
        faces.extend(_cap_faces(rings[0], is_facing_up=False))
    if profile[-1][0] > 0.0:
        faces.extend(_cap_faces(rings[-1], is_facing_up=True))
    return Mesh(vertices, faces)


def _lathe_side_faces(rings: list[list[int]], segments: int) -> list[tuple[int, ...]]:
    faces = []
    for lower, upper in zip(rings, rings[1:]):
        for j in range(segments):
            next_j = (j + 1) % segments
            corners = (lower[j], lower[next_j], upper[next_j], upper[j])
            distinct = tuple(dict.fromkeys(corners))
            if len(distinct) >= 3:
                faces.append(distinct)
    return faces


def signed_area(polygon: np.ndarray) -> float:
    """Fórmula do cadarço: positiva quando o polígono é anti-horário."""
    x, y = polygon[:, 0], polygon[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def triangulate_polygon(polygon: np.ndarray) -> list[tuple[int, int, int]]:
    """Corte de orelhas: remove repetidamente um vértice convexo sem outro vértice dentro.

    `polygon` deve ser simples e anti-horário. Devolve índices do polígono original.
    """
    remaining = list(range(len(polygon)))
    triangles = []
    while len(remaining) > 3:
        ear = _find_ear(polygon, remaining)
        triangles.append((remaining[ear - 1], remaining[ear], remaining[(ear + 1) % len(remaining)]))
        remaining.pop(ear)
    triangles.append(tuple(remaining))
    return triangles


def _find_ear(polygon: np.ndarray, remaining: list[int]) -> int:
    count = len(remaining)
    for i in range(count):
        a, b, c = (polygon[remaining[i - 1]], polygon[remaining[i]], polygon[remaining[(i + 1) % count]])
        others = [polygon[v] for v in remaining if v not in (remaining[i - 1], remaining[i], remaining[(i + 1) % count])]
        if _cross_2d(b - a, c - b) > 0.0 and not any(_point_in_triangle(p, a, b, c) for p in others):
            return i
    raise ValueError("Polígono inválido: não foi possível triangular.")


def _cross_2d(u: np.ndarray, v: np.ndarray) -> float:
    return float(u[0] * v[1] - u[1] * v[0])


def _point_in_triangle(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
    """O ponto está dentro se fica à esquerda das três arestas orientadas."""
    return _cross_2d(b - a, p - a) >= 0.0 and _cross_2d(c - b, p - b) >= 0.0 and _cross_2d(a - c, p - c) >= 0.0


def extrude(polygon_2d, depth: float) -> Mesh:
    """Extruda um polígono (x, y) ao longo de z, centrado em z = 0."""
    polygon = np.asarray(polygon_2d, dtype=float)
    if signed_area(polygon) < 0.0:
        polygon = polygon[::-1]
    count = len(polygon)
    half = depth / 2.0
    front = np.c_[polygon, np.full(count, half)]
    back = np.c_[polygon, np.full(count, -half)]
    faces: list[tuple[int, ...]] = [
        (i, i + count, (i + 1) % count + count, (i + 1) % count) for i in range(count)
    ]
    for a, b, c in triangulate_polygon(polygon):
        faces.append((a, b, c))
        faces.append((c + count, b + count, a + count))
    return Mesh(np.vstack((front, back)), faces)


def box(width: float, height: float, depth: float) -> Mesh:
    """Caixa centrada em x e z, com a base em y = 0."""
    half_w, half_d = width / 2.0, depth / 2.0
    vertices = [
        (-half_w, 0.0, -half_d), (half_w, 0.0, -half_d), (half_w, 0.0, half_d), (-half_w, 0.0, half_d),
        (-half_w, height, -half_d), (half_w, height, -half_d), (half_w, height, half_d), (-half_w, height, half_d),
    ]
    faces = [
        (0, 1, 2, 3), (7, 6, 5, 4),
        (3, 2, 6, 7), (1, 0, 4, 5),
        (2, 1, 5, 6), (0, 3, 7, 4),
    ]
    return Mesh(vertices, faces)


def merge(*meshes: Mesh) -> Mesh:
    """Junta malhas em uma só: basta somar o deslocamento nos índices das faces."""
    offsets = np.cumsum([0] + [len(mesh.vertices) for mesh in meshes[:-1]])
    vertices = np.vstack([mesh.vertices for mesh in meshes])
    faces = np.vstack([mesh.faces + offset for mesh, offset in zip(meshes, offsets)])
    shades = np.concatenate([mesh.face_shades for mesh in meshes])
    return Mesh(vertices, faces, shades)
