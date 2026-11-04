"""CT-30: matrizes e vetores."""
import math

import numpy as np
import pytest

from xadrez.graphics import (
    Vector2D,
    Vector3D,
    compose,
    identity,
    look_at,
    perspective,
    piece_matrix,
    planar_shadow,
    rotation_x,
    rotation_y,
    rotation_z,
    scaling,
    square_to_world,
    transform_points,
    translation,
    viewport,
    world_to_square,
)

ct30 = pytest.mark.ct("CT-30")


def point_of(matrix, x, y, z):
    return transform_points(matrix, [[x, y, z]])[0]


@ct30
def test_translacao_soma_o_deslocamento_ao_ponto():
    assert point_of(translation(1, 2, 3), 4, 5, 6) == pytest.approx((5, 7, 9))


@ct30
def test_translacao_nao_afeta_direcao_com_w_zero():
    direction = np.array((1.0, 0.0, 0.0, 0.0))
    assert translation(5, 5, 5) @ direction == pytest.approx(direction)


@ct30
def test_escala_uniforme_e_por_eixo():
    assert point_of(scaling(2), 1, 2, 3) == pytest.approx((2, 4, 6))
    assert point_of(scaling(2, 3, 4), 1, 1, 1) == pytest.approx((2, 3, 4))


@pytest.mark.parametrize(
    "rotation, start, expected",
    [
        (rotation_x, (0, 1, 0), (0, 0, 1)),
        (rotation_y, (0, 0, 1), (1, 0, 0)),
        (rotation_z, (1, 0, 0), (0, 1, 0)),
    ],
)
@ct30
def test_rotacao_de_90_graus_segue_a_mao_direita(rotation, start, expected):
    assert point_of(rotation(math.pi / 2), *start) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("rotation", [rotation_x, rotation_y, rotation_z])
@ct30
def test_rotacao_e_ortonormal_e_preserva_distancias(rotation):
    matrix = rotation(0.73)[:3, :3]
    assert matrix @ matrix.T == pytest.approx(np.eye(3))
    assert np.linalg.det(matrix) == pytest.approx(1.0)


@ct30
def test_composicao_aplica_o_ultimo_argumento_primeiro():
    # Girar e depois transladar é diferente de transladar e depois girar.
    rotate_then_move = compose(translation(1, 0, 0), rotation_z(math.pi / 2))
    move_then_rotate = compose(rotation_z(math.pi / 2), translation(1, 0, 0))
    assert point_of(rotate_then_move, 1, 0, 0) == pytest.approx((1, 1, 0))
    assert point_of(move_then_rotate, 1, 0, 0) == pytest.approx((0, 2, 0))


@ct30
def test_composicao_sem_argumentos_e_a_identidade():
    assert compose() == pytest.approx(identity())


@ct30
def test_look_at_leva_o_olho_para_a_origem_e_o_alvo_para_z_negativo():
    eye, target = (0.0, 5.0, 5.0), (0.0, 0.0, 0.0)
    view = look_at(eye, target, (0, 1, 0))
    assert point_of(view, *eye) == pytest.approx((0, 0, 0), abs=1e-12)
    x, y, z = point_of(view, *target)
    assert x == pytest.approx(0.0, abs=1e-12)
    assert y == pytest.approx(0.0, abs=1e-12)
    assert z == pytest.approx(-math.hypot(5.0, 5.0))


@ct30
def test_look_at_com_up_paralelo_nao_produz_matriz_degenerada():
    view = look_at((0, 5, 0), (0, 0, 0), (0, 1, 0))
    assert abs(np.linalg.det(view)) == pytest.approx(1.0)


@ct30
def test_perspectiva_mapeia_near_e_far_para_as_faces_do_cubo():
    projection = perspective(math.radians(60), 1.5, 1.0, 100.0)
    assert point_of(projection, 0, 0, -1.0)[2] == pytest.approx(-1.0)
    assert point_of(projection, 0, 0, -100.0)[2] == pytest.approx(1.0)


@ct30
def test_perspectiva_encolhe_com_a_distancia():
    projection = perspective(math.radians(60), 1.0, 1.0, 100.0)
    near_x = point_of(projection, 1, 0, -2.0)[0]
    far_x = point_of(projection, 1, 0, -4.0)[0]
    assert near_x == pytest.approx(2 * far_x)


@ct30
def test_viewport_inverte_y_e_respeita_o_deslocamento():
    matrix = viewport(100, 50, 800, 600)
    assert point_of(matrix, -1, 1, 0)[:2] == pytest.approx((100, 50))
    assert point_of(matrix, 1, -1, 0)[:2] == pytest.approx((900, 650))


@ct30
def test_sombra_planar_achata_no_plano_na_direcao_da_luz():
    light = (0.5, -1.0, -0.25)
    shadow = planar_shadow(light)
    assert point_of(shadow, 1.0, 2.0, 1.0) == pytest.approx((2.0, 0.0, 0.5))


@ct30
def test_sombra_planar_em_plano_deslocado_e_ponto_no_plano_fica_parado():
    light = (0.5, -1.0, 0.0)
    shadow = planar_shadow(light, plane_y=1.0)
    assert point_of(shadow, 3.0, 1.0, 2.0) == pytest.approx((3.0, 1.0, 2.0))
    assert point_of(shadow, 3.0, 2.0, 2.0) == pytest.approx((3.5, 1.0, 2.0))


@ct30
def test_sombra_planar_recusa_luz_horizontal():
    with pytest.raises(ValueError):
        planar_shadow((1.0, 0.0, 0.0))


@ct30
def test_transform_points_divide_por_w_quando_a_matriz_nao_e_afim():
    matrix = np.eye(4)
    matrix[3, 3] = 2.0
    assert point_of(matrix, 2, 4, 6) == pytest.approx((1, 2, 3))


@ct30
def test_casa_e_mundo_seguem_a_convencao_do_design():
    assert square_to_world(0, 0) == (-3.5, 0.0, 3.5)
    assert square_to_world(7, 7) == (3.5, 0.0, -3.5)
    for file in range(8):
        for rank in range(8):
            x, _, z = square_to_world(file, rank)
            assert world_to_square(x, z) == (file, rank)
    assert world_to_square(4.1, 0.0) is None
    assert world_to_square(0.0, -4.1) is None


@ct30
def test_matriz_de_peca_leva_o_centro_para_a_casa_e_e_somente_leitura():
    matrix = piece_matrix(4, 3, math.pi)
    assert point_of(matrix, 0, 0, 0) == pytest.approx(square_to_world(4, 3))
    assert point_of(matrix, 0, 0, -1) == pytest.approx(np.array(square_to_world(4, 3)) + (0, 0, 1))
    assert not matrix.flags.writeable


@ct30
def test_vector2d_operacoes():
    v = Vector2D(3, 4)
    assert v.length() == 5
    assert v + Vector2D(1, 1) == Vector2D(4, 5)
    assert v - Vector2D(1, 1) == Vector2D(2, 3)
    assert 2 * v == Vector2D(6, 8)
    assert v / 2 == Vector2D(1.5, 2)
    assert -v == Vector2D(-3, -4)
    assert v.dot(Vector2D(1, 0)) == 3
    assert v.normalized().length() == pytest.approx(1.0)
    assert Vector2D().normalized() == Vector2D()
    assert Vector2D(1, 0).rotated(math.pi / 2) == Vector2D(0, 1)
    assert Vector2D(0, 0).lerp(Vector2D(2, 4), 0.5) == Vector2D(1, 2)
    assert Vector2D(1, -1).reflect(Vector2D(0, 2)) == Vector2D(1, 1)
    assert "Vector2D" in repr(v)
    assert v != "outra coisa"


@ct30
def test_vector3d_operacoes():
    v = Vector3D(1, 2, 2)
    assert v.length() == 3
    assert v + Vector3D(1, 1, 1) == Vector3D(2, 3, 3)
    assert v - Vector3D(1, 1, 1) == Vector3D(0, 1, 1)
    assert 2 * v == Vector3D(2, 4, 4)
    assert v / 2 == Vector3D(0.5, 1, 1)
    assert -v == Vector3D(-1, -2, -2)
    assert Vector3D(1, 0, 0).cross(Vector3D(0, 1, 0)) == Vector3D(0, 0, 1)
    assert v.dot(Vector3D(1, 0, 0)) == 1
    assert v.normalized().length() == pytest.approx(1.0)
    assert Vector3D().normalized() == Vector3D()
    assert Vector3D(0, 0, 0).lerp(Vector3D(2, 4, 6), 0.5) == Vector3D(1, 2, 3)
    assert Vector3D(1, -1, 0).reflect(Vector3D(0, 1, 0)) == Vector3D(1, 1, 0)
    assert Vector3D(1, 0, 0).rotated(Vector3D(0, 0, 2), math.pi / 2) == Vector3D(0, 1, 0)
    assert Vector3D.from_array(v.as_array()) == v
    assert "Vector3D" in repr(v)
    assert v != "outra coisa"
