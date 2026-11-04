"""As seis peças do xadrez, modeladas em low-poly a partir de primitivas próprias.

Medidas em unidades de mundo (uma casa = 1). Base no plano y = 0, eixo em y. As peças de
revolução nascem de perfis (raio, y). O cavalo é uma silhueta facetada sobre base torneada.
A estética é de faces planas: poucos segmentos, com as arestas à mostra.
"""
from __future__ import annotations

import math

import numpy as np

from xadrez.graphics.matrix import compose, rotation_x, rotation_y, rotation_z, translation
from xadrez.graphics.mesh import Mesh, box, lathe, merge, triangulate_polygon
from xadrez.graphics.vector import Vector2D

PIECE_KINDS = ("pawn", "knight", "bishop", "rook", "queen", "king")

IVORY = (240, 228, 200)
EBONY = (54, 44, 44)

# O cavalo foi modelado olhando para -z, o lado das pretas: é a orientação das brancas.
FACING_WHITE = 0.0
FACING_BLACK = math.pi

_BODY_SEGMENTS = 10
_PAWN_SEGMENTS = 8
_FINIAL_SEGMENTS = 6
_CONTACT_SHADE_HEIGHT = 0.22
_CONTACT_SHADE_FLOOR = 0.70
_DEEP_SHADE = 0.24
_MITRE_SLOPE = math.radians(21)
_MITRE_SLIT_TILT = math.radians(32)
# De frente ou de costas, a cabeça do cavalo é só uma coluna. Girada sobre a base, ela
# continua olhando para o lado do adversário e mostra o perfil para quem está jogando.
_KNIGHT_PROFILE_TURN = math.radians(50)


def _with_contact_shade(mesh: Mesh) -> Mesh:
    """Oclusão de contato: escurece as faces perto da mesa, onde chega menos luz rebatida."""
    closeness = np.clip(mesh.face_centers[:, 1] / _CONTACT_SHADE_HEIGHT, 0.0, 1.0)
    mesh.face_shades = mesh.face_shades * (_CONTACT_SHADE_FLOOR + (1.0 - _CONTACT_SHADE_FLOOR) * closeness)
    return mesh


def _build_pawn() -> Mesh:
    profile = [
        (0.30, 0.00), (0.31, 0.05), (0.205, 0.10), (0.125, 0.19), (0.105, 0.31), (0.175, 0.375), (0.10, 0.435),
        (0.175, 0.55), (0.14, 0.675), (0.0, 0.75),
    ]
    return lathe(profile, _PAWN_SEGMENTS)


def _build_rook() -> Mesh:
    profile = [
        (0.33, 0.00), (0.34, 0.06), (0.25, 0.14), (0.185, 0.30), (0.185, 0.60),
        (0.26, 0.67), (0.26, 0.76), (0.165, 0.76), (0.165, 0.71), (0.0, 0.71),
    ]
    return merge(lathe(profile, _BODY_SEGMENTS), *_rook_merlons(count=6, center_radius=0.215, base_y=0.76))


def _rook_merlons(count: int, center_radius: float, base_y: float) -> list[Mesh]:
    """Ameias: caixas giradas em volta do topo, com o vão entre elas marcando a silhueta."""
    merlon = box(0.145, 0.15, 0.095)
    return [
        merlon.transformed(compose(rotation_y(2.0 * math.pi * i / count + math.pi / count),
                                   translation(0.0, base_y, center_radius)))
        for i in range(count)
    ]


def _build_bishop() -> Mesh:
    profile = [
        (0.31, 0.00), (0.32, 0.055), (0.23, 0.12), (0.115, 0.34), (0.095, 0.53), (0.175, 0.59), (0.10, 0.65),
        (0.178, 0.79), (0.12, 0.94), (0.045, 1.02), (0.06, 1.06), (0.0, 1.125),
    ]
    return merge(lathe(profile, _BODY_SEGMENTS), _mitre_slit(0.0), _mitre_slit(math.pi))


def _mitre_slit(side_angle: float) -> Mesh:
    """Corte diagonal da mitra: lâmina escura e fina, rente à superfície inclinada.

    Fica dos dois lados para ser vista tanto pelas brancas quanto pelas pretas.
    """
    slit = box(0.024, 0.19, 0.03)
    slit.face_shades = np.full(len(slit.faces), _DEEP_SHADE)
    return slit.transformed(compose(
        rotation_y(side_angle),
        translation(0.0, 0.845, 0.145),
        rotation_x(-_MITRE_SLOPE),
        rotation_z(_MITRE_SLIT_TILT),
        translation(0.0, -0.095, 0.0),
    ))


def _build_queen() -> Mesh:
    profile = [
        (0.33, 0.00), (0.34, 0.06), (0.24, 0.14), (0.125, 0.38), (0.105, 0.66),
        (0.20, 0.73), (0.115, 0.80), (0.215, 1.02), (0.13, 1.02), (0.0, 1.06),
    ]
    finial = lathe([(0.05, 1.05), (0.072, 1.11), (0.05, 1.17), (0.0, 1.20)], _FINIAL_SEGMENTS)
    return merge(lathe(profile, _BODY_SEGMENTS), finial, *_crown_points(count=8, radius=0.20, base_y=1.0))


def _crown_points(count: int, radius: float, base_y: float) -> list[Mesh]:
    """Pontas da coroa: pirâmides de base triangular, inclinadas para fora em volta do aro."""
    point = lathe([(0.055, 0.0), (0.0, 0.17)], 3)
    tilt = math.radians(14)
    return [
        point.transformed(compose(rotation_y(2.0 * math.pi * i / count),
                                  translation(radius, base_y, 0.0),
                                  rotation_z(-tilt)))
        for i in range(count)
    ]


def _build_king() -> Mesh:
    profile = [
        (0.34, 0.00), (0.35, 0.06), (0.25, 0.14), (0.13, 0.40), (0.11, 0.72),
        (0.21, 0.79), (0.125, 0.86), (0.215, 1.08), (0.15, 1.14), (0.0, 1.19),
    ]
    upright = box(0.082, 0.38, 0.082).transformed(translation(0.0, 1.16, 0.0))
    arm = box(0.27, 0.082, 0.082).transformed(translation(0.0, 1.31, 0.0))
    return merge(lathe(profile, _BODY_SEGMENTS), upright, arm)


# Cabeça de cavalo de perfil: x positivo é o focinho, y é a altura. Sentido anti-horário.
_KNIGHT_SILHOUETTE = (
    (-0.25, 0.14), (0.25, 0.14), (0.27, 0.28), (0.19, 0.41), (0.12, 0.50), (0.20, 0.52), (0.33, 0.53),
    (0.42, 0.60), (0.41, 0.70), (0.27, 0.83), (0.17, 0.94), (0.04, 1.01), (-0.10, 0.97),
    (-0.23, 0.83), (-0.30, 0.62), (-0.32, 0.42), (-0.28, 0.25),
)
_KNIGHT_MANE_EDGES = range(11, 15)
_KNIGHT_INSET = 0.050
_KNIGHT_BOTTOM_WIDTH = 0.20
_KNIGHT_TOP_WIDTH = 0.095
_KNIGHT_MAX_MITER = 2.2


def _inset_polygon(polygon: np.ndarray, amount: float) -> np.ndarray:
    """Encolhe o polígono: anda `amount` para dentro na bissetriz das arestas vizinhas.

    Em polígono anti-horário, o interior fica à esquerda da aresta e = (x, y), de normal
    (-y, x). No vértice, o passo é a soma das normais vizinhas dividida pelo cosseno do
    meio-ângulo, para que a distância a cada aresta seja exatamente `amount`.
    """
    count = len(polygon)
    result = []
    for i in range(count):
        current = Vector2D(*polygon[i])
        incoming = (current - Vector2D(*polygon[i - 1])).normalized()
        outgoing = (Vector2D(*polygon[(i + 1) % count]) - current).normalized()
        left_in, left_out = Vector2D(-incoming.y, incoming.x), Vector2D(-outgoing.y, outgoing.x)
        bisector = (left_in + left_out).normalized()
        miter = min(1.0 / max(bisector.dot(left_out), 1e-3), _KNIGHT_MAX_MITER)
        step = bisector * (amount * miter)
        result.append((current.x + step.x, current.y + step.y))
    return np.array(result)


def _knight_width(heights: np.ndarray) -> np.ndarray:
    """Pescoço grosso embaixo e cabeça fina em cima."""
    fraction = np.clip((heights - 0.14) / 0.87, 0.0, 1.0)
    return _KNIGHT_BOTTOM_WIDTH + (_KNIGHT_TOP_WIDTH - _KNIGHT_BOTTOM_WIDTH) * fraction


def _build_knight_head() -> Mesh:
    """Silhueta com seção em losango: uma crista no meio e bochechas planas dos dois lados.

    Uma extrusão plana, vista por trás, seria só um retângulo. A crista forma a crina e dá
    facetas visíveis de qualquer ângulo. Três cópias da silhueta (bochecha, crista, bochecha)
    são ligadas por faixas de quadriláteros, e as bochechas fecham com triângulos.
    """
    ridge = np.array(_KNIGHT_SILHOUETTE)
    cheek = _inset_polygon(ridge, _KNIGHT_INSET)
    count = len(ridge)
    half_width = _knight_width(cheek[:, 1])
    vertices = np.vstack((
        np.c_[ridge, np.zeros(count)],
        np.c_[cheek, half_width],
        np.c_[cheek, -half_width],
    ))
    front, back = count, 2 * count
    faces: list[tuple[int, ...]] = []
    shades: list[float] = []
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, front + j, front + i))
        faces.append((j, i, back + i, back + j))
        shades.extend([0.74 if i in _KNIGHT_MANE_EDGES else 1.0] * 2)
    for a, b, c in triangulate_polygon(cheek):
        faces.append((front + a, front + b, front + c))
        faces.append((back + c, back + b, back + a))
        shades.extend([1.0, 1.0])
    return Mesh(vertices, faces, shades)


def _knight_ear(side: float) -> Mesh:
    ear = lathe([(0.052, 0.0), (0.0, 0.135)], 4)
    return ear.transformed(compose(translation(0.075, 0.955, side * 0.05), rotation_y(math.pi / 4.0)))


def _knight_eye(side: float) -> Mesh:
    """Olho: placa escura rente à bochecha, que marca a cabeça quando vista de perfil."""
    eye = box(0.062, 0.05, 0.012)
    eye.face_shades = np.full(len(eye.faces), _DEEP_SHADE)
    width = float(_knight_width(np.array([0.76]))[0])
    return eye.transformed(translation(0.17, 0.745, side * width))


def _build_knight() -> Mesh:
    base_profile = [(0.32, 0.00), (0.33, 0.055), (0.285, 0.105), (0.25, 0.16), (0.0, 0.18)]
    # A silhueta é modelada olhando para +x. Ry(90 graus) leva +x até -z, o lado das pretas.
    head = merge(_build_knight_head(), _knight_ear(1.0), _knight_ear(-1.0), _knight_eye(1.0), _knight_eye(-1.0))
    return merge(lathe(base_profile, _BODY_SEGMENTS),
                 head.transformed(rotation_y(math.pi / 2.0 + _KNIGHT_PROFILE_TURN)))


_BUILDERS = {
    "pawn": _build_pawn,
    "knight": _build_knight,
    "bishop": _build_bishop,
    "rook": _build_rook,
    "queen": _build_queen,
    "king": _build_king,
}


def build_piece_meshes() -> dict[str, Mesh]:
    return {kind: _with_contact_shade(_BUILDERS[kind]()) for kind in PIECE_KINDS}
