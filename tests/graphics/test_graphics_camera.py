"""CT-31: câmera, com ida e volta mundo, tela e casa em vários ângulos."""
import math

import numpy as np
import pytest

from xadrez.graphics import Camera, build_piece_meshes, piece_matrix, square_to_world
from xadrez.graphics.camera import MAX_DISTANCE, MAX_PITCH, MIN_DISTANCE, MIN_PITCH

ct31 = pytest.mark.ct("CT-31")

KING = build_piece_meshes()["king"]


def _king_at(file, rank):
    return file, rank, KING, piece_matrix(file, rank, 0.0)


YAWS = (0.0, 0.7, math.pi / 2, 2.1, math.pi, 4.4)
PITCHES = (math.radians(28), math.radians(52), math.radians(78))
VIEWPORTS = ((0, 0, 1280, 720), (320, 48, 900, 640), (17, 203, 640, 480))


@pytest.mark.parametrize("viewport_rect", VIEWPORTS)
@pytest.mark.parametrize("pitch", PITCHES)
@pytest.mark.parametrize("yaw", YAWS)
@ct31
def test_ida_e_volta_nas_64_casas(yaw, pitch, viewport_rect):
    # Distância folgada: com a câmera muito alta e girada, os cantos sairiam do viewport.
    camera = Camera(viewport_rect, yaw=yaw, pitch=pitch, distance=24.0)
    for file in range(8):
        for rank in range(8):
            pixels, depth = camera.project([square_to_world(file, rank)])
            assert depth[0] > 0.0
            assert camera.pick_square(*pixels[0]) == (file, rank)


@pytest.mark.parametrize("yaw", (0.0, math.pi))
@pytest.mark.parametrize("viewport_rect", VIEWPORTS)
@ct31
def test_ida_e_volta_com_a_camera_padrao(yaw, viewport_rect):
    camera = Camera(viewport_rect, yaw=yaw)
    for file in range(8):
        for rank in range(8):
            pixels, _ = camera.project([square_to_world(file, rank)])
            assert camera.pick_square(*pixels[0]) == (file, rank)


@pytest.mark.parametrize("yaw", YAWS)
@ct31
def test_pick_plane_devolve_o_mesmo_ponto_de_mundo(yaw):
    camera = Camera((320, 48, 900, 640), yaw=yaw)
    point = (1.23, 0.0, -2.34)
    pixels, _ = camera.project([point])
    x, z = camera.pick_plane(*pixels[0])
    assert (x, z) == pytest.approx((point[0], point[2]), abs=1e-6)


@ct31
def test_a1_fica_no_canto_inferior_esquerdo_para_as_brancas():
    camera = Camera()
    a1, _ = camera.project([square_to_world(0, 0)])
    h8, _ = camera.project([square_to_world(7, 7)])
    assert a1[0, 0] < h8[0, 0]
    assert a1[0, 1] > h8[0, 1]


@ct31
def test_vista_das_pretas_inverte_o_tabuleiro():
    camera = Camera(yaw=math.pi)
    a1, _ = camera.project([square_to_world(0, 0)])
    h8, _ = camera.project([square_to_world(7, 7)])
    assert a1[0, 0] > h8[0, 0]
    assert a1[0, 1] < h8[0, 1]


@pytest.mark.parametrize("viewport_rect", VIEWPORTS)
@ct31
def test_tabuleiro_e_pecas_cabem_no_viewport_na_camera_padrao(viewport_rect):
    camera = Camera(viewport_rect)
    corners = [(-4.6, 0, 4.6), (4.6, 0, 4.6), (-4.6, 0, -4.6), (4.6, 0, -4.6), (0.5, 1.5, -3.5)]
    pixels, _ = camera.project(corners)
    x, y, w, h = viewport_rect
    assert (pixels[:, 0] >= x).all() and (pixels[:, 0] <= x + w).all()
    assert (pixels[:, 1] >= y).all() and (pixels[:, 1] <= y + h).all()


@ct31
def test_clique_fora_do_viewport_ou_do_tabuleiro_nao_escolhe_casa():
    camera = Camera((320, 48, 900, 640))
    assert camera.pick_square(10, 300) is None
    assert camera.pick_square(321, 49) is None
    assert camera.pick_piece(10, 300, []) is None


@ct31
def test_raio_para_cima_nao_toca_o_plano():
    camera = Camera()
    origin, direction = camera.screen_ray(640, 360)
    assert direction.y < 0.0
    assert camera.pick_plane(640, 360, plane_y=origin.y + 50.0) is None


@ct31
def test_clicar_na_cabeca_da_peca_escolhe_a_casa_dela():
    camera = Camera()
    x, _, z = square_to_world(4, 1)
    head = (x, 1.0, z)
    pixels, _ = camera.project([head])
    assert camera.pick_square(*pixels[0]) != (4, 1)
    assert camera.pick_piece(*pixels[0], [_king_at(4, 1)]) == (4, 1)


@ct31
def test_clique_escolhe_a_peca_da_frente_quando_duas_se_cobrem():
    camera = Camera()
    x, _, z = square_to_world(4, 1)
    pixels, _ = camera.project([(x, 0.9, z)])
    pieces = [_king_at(4, 3), _king_at(4, 1), _king_at(4, 2)]
    assert camera.pick_piece(*pixels[0], pieces) == (4, 1)


@ct31
def test_clique_escolhe_a_peca_da_frente_mesmo_com_a_de_tras_antes_na_lista():
    """Vista das pretas, a ordem da lista é a contrária à da profundidade: quem decide é a distância ao olho."""
    camera = Camera()
    x, _, z = square_to_world(4, 1)
    pixels, _ = camera.project([(x, 1.5, z)])
    assert camera.pick_piece(*pixels[0], [_king_at(4, 2)]) == (4, 2), "sozinha, a de trás também aparece neste pixel"
    assert camera.pick_piece(*pixels[0], [_king_at(4, 2), _king_at(4, 1)]) == (4, 1)


@ct31
def test_clique_que_erra_as_pecas_cai_na_casa_do_tabuleiro():
    camera = Camera()
    pixels, _ = camera.project([square_to_world(4, 4)])
    assert camera.pick_piece(*pixels[0], [_king_at(0, 0)]) == (4, 4)


@ct31
def test_clique_ao_lado_da_cintura_da_peca_cai_na_casa_de_tras():
    """O chão visível ao lado da cintura está dentro do cilindro envolvente, mas fora da silhueta."""
    camera = Camera()
    x, _, z = square_to_world(4, 2)
    pixels, _ = camera.project([(x + 0.3, 0.0, z + 0.3)])
    assert camera.pick_piece(*pixels[0], [_king_at(4, 1)]) == (4, 2)


@ct31
def test_clique_na_silhueta_acerta_em_qualquer_angulo():
    camera = Camera()
    x, _, z = square_to_world(4, 1)
    for yaw in (0.0, 0.8, math.pi, -2.2):
        camera.orbit_by(yaw - camera.yaw)
        pixels, _ = camera.project([(x, 0.8, z)])
        assert camera.pick_piece(*pixels[0], [_king_at(4, 1)]) == (4, 1)


@ct31
def test_orbit_to_toma_o_menor_arco_e_termina_no_alvo():
    camera = Camera(yaw=math.radians(350))
    camera.orbit_to(math.radians(10), duration=1.0)
    assert camera.is_moving
    camera.update(0.5)
    assert math.radians(350) < camera.yaw < math.radians(370)
    camera.update(0.6)
    assert not camera.is_moving
    assert math.cos(camera.yaw) == pytest.approx(math.cos(math.radians(10)))
    assert math.sin(camera.yaw) == pytest.approx(math.sin(math.radians(10)))


@ct31
def test_orbit_by_respeita_os_limites_e_cancela_a_animacao():
    camera = Camera()
    camera.orbit_to(1.0, duration=1.0)
    camera.orbit_by(0.1, 10.0)
    assert not camera.is_moving
    assert camera.pitch == MAX_PITCH
    camera.orbit_by(0.0, -10.0)
    assert camera.pitch == MIN_PITCH


@ct31
def test_zoom_respeita_os_limites():
    camera = Camera()
    camera.zoom_by(1000.0)
    assert camera.distance == MAX_DISTANCE
    camera.zoom_by(0.0001)
    assert camera.distance == MIN_DISTANCE


@ct31
def test_mudar_a_camera_invalida_as_matrizes_em_cache():
    camera = Camera()
    before = camera.view_matrix.copy()
    revision = camera.revision
    camera.orbit_by(0.5)
    assert camera.revision > revision
    assert not np.allclose(before, camera.view_matrix)
    camera.update(0.1)
    assert camera.revision == revision + 1


@ct31
def test_viewport_estreito_abre_o_campo_de_visao_e_redimensionar_nao_quebra():
    camera = Camera()
    wide_focal = camera.projection_matrix[1, 1]
    camera.set_viewport(0, 0, 500, 700)
    assert camera.projection_matrix[1, 1] < wide_focal
    camera.set_viewport(0, 0, 0, 0)
    assert camera.viewport == (0, 0, 1, 1)
    assert np.isfinite(camera.view_projection_matrix).all()
