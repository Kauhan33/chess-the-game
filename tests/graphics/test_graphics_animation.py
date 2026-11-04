"""CT-35: animação, com interpolação, easing e composição de transformações."""
import math

import numpy as np
import pytest

from xadrez.graphics import (
    CaptureAnimation,
    KingFallAnimation,
    PieceAnimation,
    SpawnAnimation,
    Tween,
    ease_in_out_cubic,
    ease_out_back,
    ease_out_bounce,
    linear,
    square_to_world,
    transform_points,
)

ct35 = pytest.mark.ct("CT-35")
EASINGS = (linear, ease_in_out_cubic, ease_out_back, ease_out_bounce)


def origin_of(matrix):
    return transform_points(matrix, [[0.0, 0.0, 0.0]])[0]


@pytest.mark.parametrize("easing", EASINGS)
@ct35
def test_easing_comeca_em_zero_e_termina_em_um(easing):
    assert easing(0.0) == pytest.approx(0.0, abs=1e-9)
    assert easing(1.0) == pytest.approx(1.0, abs=1e-9)


@ct35
def test_ease_in_out_cubico_e_simetrico_e_monotono():
    assert ease_in_out_cubic(0.5) == pytest.approx(0.5)
    assert ease_in_out_cubic(0.25) == pytest.approx(1.0 - ease_in_out_cubic(0.75))
    samples = [ease_in_out_cubic(t) for t in np.linspace(0.0, 1.0, 50)]
    assert samples == sorted(samples)


@ct35
def test_ease_out_back_passa_do_alvo_e_volta():
    samples = [ease_out_back(t) for t in np.linspace(0.0, 1.0, 50)]
    assert max(samples) > 1.0
    assert samples[-1] == pytest.approx(1.0)


@ct35
def test_ease_out_bounce_quica_nos_quatro_arcos():
    samples = [ease_out_bounce(t) for t in np.linspace(0.0, 1.0, 200)]
    drops = sum(1 for a, b in zip(samples, samples[1:]) if b < a - 1e-9 and a >= b)
    assert drops > 0
    assert all(0.0 <= value <= 1.0 + 1e-9 for value in samples)


@ct35
def test_tween_interpola_com_o_easing_e_para_no_fim():
    tween = Tween(10.0, 20.0, 2.0)
    assert tween.value == 10.0
    tween.update(1.0)
    assert tween.value == pytest.approx(15.0)
    assert not tween.is_done
    tween.update(5.0)
    assert tween.value == 20.0
    assert tween.is_done


@ct35
def test_tween_aceita_vetor_e_ignora_tempo_negativo():
    tween = Tween(np.zeros(3), np.ones(3), 1.0)
    tween.update(-1.0)
    assert tween.value == pytest.approx(np.zeros(3))
    tween.update(0.25)
    assert tween.value == pytest.approx(np.full(3, 0.25))


@ct35
def test_tween_de_duracao_zero_termina_na_hora():
    tween = Tween(1.0, 2.0, 0.0)
    assert tween.is_done
    assert tween.value == 2.0


@ct35
def test_peca_viaja_em_arco_e_pousa_exatamente_no_alvo():
    animation = PieceAnimation((4, 1), (4, 3), duration=1.0, arc_height=0.6)
    assert origin_of(animation.model_matrix()) == pytest.approx(square_to_world(4, 1))
    animation.update(0.5)
    x, y, z = origin_of(animation.model_matrix())
    middle = np.mean([square_to_world(4, 1), square_to_world(4, 3)], axis=0)
    assert (x, z) == pytest.approx((middle[0], middle[2]))
    assert y == pytest.approx(0.6)
    animation.update(0.6)
    assert animation.is_done
    assert origin_of(animation.model_matrix()) == pytest.approx(square_to_world(4, 3))
    assert transform_points(animation.model_matrix(), [[0.0, 1.0, 0.0]])[0][1] == pytest.approx(1.0)


@ct35
def test_peca_inclina_e_estica_no_meio_do_voo():
    animation = PieceAnimation((0, 0), (0, 2), duration=1.0, arc_height=0.0)
    animation.update(0.5)
    top = transform_points(animation.model_matrix(), [[0.0, 1.0, 0.0]])[0]
    base = origin_of(animation.model_matrix())
    # A peça anda para -z (rank crescente), e o topo aponta para o mesmo lado.
    assert top[2] < base[2]
    assert np.linalg.norm(top - base) > 1.0


@ct35
def test_arco_padrao_cresce_com_a_distancia():
    near = PieceAnimation((0, 0), (0, 1)).arc_height
    far = PieceAnimation((0, 0), (0, 5)).arc_height
    assert far > near > 0.0


@ct35
def test_orientacao_gira_a_peca_em_torno_do_proprio_eixo():
    animation = PieceAnimation((3, 3), (3, 3), duration=0.5, facing=math.pi)
    nose = transform_points(animation.model_matrix(), [[0.0, 0.0, -1.0]])[0]
    assert nose == pytest.approx(np.array(square_to_world(3, 3)) + (0.0, 0.0, 1.0))


@ct35
def test_captura_encolhe_girando():
    animation = CaptureAnimation((2, 2), duration=1.0)
    assert origin_of(animation.model_matrix()) == pytest.approx(square_to_world(2, 2))
    size_start = np.linalg.norm(animation.model_matrix()[:3, 0])
    animation.update(0.5)
    size_middle = np.linalg.norm(animation.model_matrix()[:3, 0])
    axis_middle = animation.model_matrix()[:3, 0] / size_middle
    animation.update(0.6)
    assert animation.is_done
    assert size_start > size_middle > np.linalg.norm(animation.model_matrix()[:3, 0])
    assert axis_middle == pytest.approx(np.array((math.cos(CaptureAnimation.SPIN_ANGLE / 2.0), 0.0, -math.sin(CaptureAnimation.SPIN_ANGLE / 2.0))))
    assert np.isfinite(animation.model_matrix()).all()


@ct35
def test_promocao_cresce_e_passa_um_pouco_do_tamanho():
    animation = SpawnAnimation((5, 7), duration=1.0, facing=math.pi)
    assert np.linalg.norm(animation.model_matrix()[:3, 1]) < 0.01
    sizes = []
    for _ in range(20):
        animation.update(0.05)
        sizes.append(np.linalg.norm(animation.model_matrix()[:3, 1]))
    assert max(sizes) > 1.0
    assert sizes[-1] == pytest.approx(1.0)
    assert origin_of(animation.model_matrix()) == pytest.approx(square_to_world(5, 7))


@pytest.mark.parametrize("direction", [(1.0, 0.0), (0.0, -1.0), (-1.0, 1.0)])
@ct35
def test_rei_tomba_em_torno_da_borda_que_nao_sai_do_lugar(direction):
    animation = KingFallAnimation((4, 0), direction=direction, duration=1.0, base_radius=0.3)
    pivot = np.array(animation.pivot)
    world_pivot = np.array(square_to_world(4, 0)) + pivot
    assert transform_points(animation.model_matrix(), [pivot])[0] == pytest.approx(world_pivot)
    animation.update(1.0)
    assert animation.is_done
    assert transform_points(animation.model_matrix(), [pivot])[0] == pytest.approx(world_pivot)
    top = transform_points(animation.model_matrix(), [[0.0, 1.0, 0.0]])[0]
    horizontal = (top - np.array(square_to_world(4, 0)))[[0, 2]]
    unit = np.array(direction) / np.linalg.norm(direction)
    # O topo caiu para o lado pedido e ficou perto do chão: na altura do raio da base, menos a queda.
    assert horizontal @ unit > 0.8
    assert top[1] < 0.3


@ct35
def test_rei_tombando_passa_por_angulos_intermediarios():
    animation = KingFallAnimation((4, 0), duration=1.0)
    upright_axis = animation.model_matrix()[:3, 1].copy()
    animation.update(0.2)
    leaning_axis = animation.model_matrix()[:3, 1]
    assert upright_axis == pytest.approx((0.0, 1.0, 0.0))
    assert 0.0 < leaning_axis[1] < 1.0
    assert leaning_axis[0] > 0.0
