"""CT-34: malhas, com normais para fora e faces válidas."""
import math

import numpy as np
import pytest

from xadrez.graphics import IVORY, PIECE_KINDS, DirectionalLight, Mesh, box, build_piece_meshes, extrude, lathe, merge
from xadrez.graphics import rotation_y, transform_points
from xadrez.graphics.board_model import build_board_geometry, build_frame_parts
from xadrez.graphics.mesh import signed_area, triangulate_polygon

ct34 = pytest.mark.ct("CT-34")

MESHES = build_piece_meshes()
MAX_FACES_PER_PIECE = 160


def signed_volume(mesh: Mesh) -> float:
    """Teorema da divergência: positivo em malha fechada com normais para fora."""
    corners = mesh.vertices[mesh.faces]
    a, b, c, d = corners[:, 0], corners[:, 1], corners[:, 2], corners[:, 3]
    first = (a * np.cross(b, c)).sum()
    second = (a * np.cross(c, d)).sum()
    return float(first + second) / 6.0


def edge_balance(mesh: Mesh) -> dict:
    """Soma +1 para cada aresta (a, b) e -1 para (b, a). Malha fechada zera todas."""
    balance: dict = {}
    for face in mesh.faces.tolist():
        for corner in range(4):
            a, b = face[corner], face[(corner + 1) % 4]
            if a == b:
                continue
            key = (min(a, b), max(a, b))
            balance[key] = balance.get(key, 0) + (1 if a < b else -1)
    return balance


def assert_valid_faces(mesh: Mesh) -> None:
    assert mesh.faces.min() >= 0
    assert mesh.faces.max() < len(mesh.vertices)
    assert np.isfinite(mesh.face_normals).all()
    lengths = np.linalg.norm(mesh.face_normals, axis=1)
    assert lengths == pytest.approx(np.ones_like(lengths))
    for face in mesh.faces.tolist():
        assert len(set(face)) >= 3


@pytest.mark.parametrize("kind", PIECE_KINDS)
@ct34
def test_pecas_tem_faces_validas_e_volume_positivo(kind):
    mesh = MESHES[kind]
    assert_valid_faces(mesh)
    assert signed_volume(mesh) > 0.0


@pytest.mark.parametrize("kind", PIECE_KINDS)
@ct34
def test_pecas_sao_low_poly_de_verdade(kind):
    assert len(MESHES[kind].faces) <= MAX_FACES_PER_PIECE


@pytest.mark.parametrize("kind", PIECE_KINDS)
@ct34
def test_pecas_sao_fechadas_sem_arestas_soltas(kind):
    assert not [edge for edge, count in edge_balance(MESHES[kind]).items() if count != 0]


@pytest.mark.parametrize("kind", PIECE_KINDS)
@ct34
def test_pecas_apoiam_na_mesa_e_cabem_na_casa(kind):
    mesh = MESHES[kind]
    assert mesh.vertices[:, 1].min() == pytest.approx(0.0)
    assert mesh.radius < 0.5


@ct34
def test_alturas_seguem_a_hierarquia_do_xadrez():
    height = {kind: MESHES[kind].height for kind in PIECE_KINDS}
    assert height["pawn"] < height["rook"] < height["knight"] < height["bishop"] < height["queen"] < height["king"]


@ct34
def test_cavalo_olha_para_menos_z_com_o_perfil_virado_para_o_jogador():
    knight = MESHES["knight"]
    head = knight.vertices[knight.vertices[:, 1] > 0.5]
    snout = head[np.hypot(head[:, 0], head[:, 2]).argmax()]
    # O focinho é o vértice mais afastado do eixo: fica à frente (-z) e para o lado (-x).
    assert snout[2] < -0.2
    assert snout[0] < -0.2


@ct34
def test_lathe_tem_normais_para_fora_do_eixo():
    mesh = lathe([(1.0, 0.0), (1.0, 1.0)], 8)
    side = np.abs(mesh.face_normals[:, 1]) < 0.5
    radial = mesh.face_centers[side][:, [0, 2]]
    outward = (mesh.face_normals[side][:, [0, 2]] * radial).sum(axis=1)
    assert (outward > 0.0).all()
    assert not [edge for edge, count in edge_balance(mesh).items() if count != 0]


@ct34
def test_lathe_fecha_em_ponta_e_usa_tampas_de_poucos_quadrilateros():
    cone = lathe([(1.0, 0.0), (0.0, 1.0)], 6)
    assert signed_volume(cone) == pytest.approx(math.pi / 3.0, rel=0.2)
    assert cone.vertices[:, 1].max() == 1.0
    cylinder = lathe([(1.0, 0.0), (1.0, 1.0)], 12)
    side_faces, cap_faces = 12, 5
    assert len(cylinder.faces) == side_faces + 2 * cap_faces


@ct34
def test_box_tem_seis_faces_para_fora_e_base_no_zero():
    mesh = box(2.0, 3.0, 4.0)
    center = np.array((0.0, 1.5, 0.0))
    assert ((mesh.face_normals * (mesh.face_centers - center)).sum(axis=1) > 0.0).all()
    assert len(mesh.faces) == 6
    assert signed_volume(mesh) == pytest.approx(24.0)
    assert mesh.vertices[:, 1].min() == 0.0


@ct34
def test_extrude_aceita_as_duas_voltas_e_fecha_a_malha():
    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for polygon in (square, square[::-1]):
        mesh = extrude(polygon, 2.0)
        assert signed_volume(mesh) == pytest.approx(2.0)
        assert not [edge for edge, count in edge_balance(mesh).items() if count != 0]


@ct34
def test_triangulacao_de_poligono_concavo_preserva_a_area():
    arrow = np.array([(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (1.0, 0.8), (0.0, 2.0)])
    triangles = triangulate_polygon(arrow)
    assert len(triangles) == len(arrow) - 2
    total = sum(signed_area(arrow[list(triangle)]) for triangle in triangles)
    assert total == pytest.approx(signed_area(arrow))
    assert signed_area(arrow) > 0.0


@ct34
def test_triangulacao_recusa_poligono_invalido():
    with pytest.raises(ValueError):
        triangulate_polygon(np.array([(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]))


@ct34
def test_merge_soma_os_deslocamentos_dos_indices():
    first, second = box(1, 1, 1), box(1, 1, 1).transformed(rotation_y(0.5))
    merged = merge(first, second)
    assert len(merged.vertices) == 16
    assert len(merged.faces) == 12
    assert merged.faces[6:].min() == 8
    assert signed_volume(merged) == pytest.approx(2.0)
    assert not [edge for edge, count in edge_balance(merged).items() if count != 0]


@ct34
def test_vizinhas_compartilham_aresta_em_sentido_oposto():
    mesh = box(1, 1, 1)
    neighbors = mesh.face_neighbors
    assert neighbors.shape == (6, 4)
    for face_index, face in enumerate(mesh.faces.tolist()):
        for corner in range(4):
            a, b = face[corner], face[(corner + 1) % 4]
            neighbor_face = mesh.faces[neighbors[face_index, corner]].tolist()
            pairs = [(neighbor_face[i], neighbor_face[(i + 1) % 4]) for i in range(4)]
            assert (b, a) in pairs


@ct34
def test_aresta_sem_vizinha_aponta_para_a_propria_face():
    single = Mesh([(0, 0, 0), (1, 0, 0), (1, 0, -1)], [(0, 1, 2)])
    assert single.face_neighbors.tolist() == [[0, 0, 0, 0]]


@ct34
def test_triangulo_guarda_centro_de_tres_vertices():
    triangle = Mesh([(0, 0, 0), (3, 0, 0), (0, 0, -3)], [(0, 1, 2)])
    assert triangle.faces.tolist() == [[0, 1, 2, 2]]
    assert triangle.face_centers[0] == pytest.approx((1, 0, -1))
    assert triangle.face_normals[0] == pytest.approx((0, 1, 0))


@ct34
def test_moldura_e_casas_tem_normais_para_cima_ou_para_fora():
    for mesh, _ in build_frame_parts():
        horizontal = mesh.face_centers[:, [0, 2]]
        normals = mesh.face_normals
        assert (normals[:, 1] > -1e-9).all()
        assert ((normals[:, [0, 2]] * horizontal).sum(axis=1) > -1e-9).all()
    corners = build_board_geometry().square_corners
    for file, rank in ((0, 0), (3, 5), (7, 7)):
        face = corners[file, rank]
        normal = np.cross(face[2] - face[0], face[3] - face[1])
        assert normal[1] > 0.0


@ct34
def test_veios_ficam_dentro_da_propria_casa():
    geometry = build_board_geometry()
    for corners, (file, rank) in zip(geometry.grain_corners, geometry.grain_square):
        assert (corners[:, 0] >= file - 4.0).all() and (corners[:, 0] <= file - 3.0).all()
        assert (corners[:, 2] >= 3.0 - rank).all() and (corners[:, 2] <= 4.0 - rank).all()


@ct34
def test_lambert_escurece_com_o_angulo_e_nunca_passa_de_255():
    light = DirectionalLight(direction=(0.0, -1.0, 0.0), ambient=0.2, diffuse=0.8, color=(1.0, 1.0, 1.0))
    normals = np.array([(0.0, 1.0, 0.0), (0.0, math.cos(1.0), math.sin(1.0)), (0.0, -1.0, 0.0)])
    colors = light.shade(normals, (200.0, 200.0, 200.0))
    assert colors[0, 0] > colors[1, 0] > colors[2, 0]
    assert colors[2, 0] > 0.0
    assert light.shade(normals, (9000.0, 9000.0, 9000.0)).max() <= 255.0


@ct34
def test_transform_points_em_malha_preserva_forma_e_ivory_e_rgb_valido():
    moved = transform_points(rotation_y(1.0), MESHES["pawn"].vertices)
    assert moved.shape == MESHES["pawn"].vertices.shape
    assert all(0 <= channel <= 255 for channel in IVORY)
