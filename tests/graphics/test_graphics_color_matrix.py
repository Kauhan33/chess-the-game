"""CT-32: matriz de cores, em que o estado da casa vira cor, com prioridade."""
import numpy as np
import pytest

from xadrez.graphics import CellState, ColorMatrix
from xadrez.graphics.color_matrix import DEFAULT_DARK_SQUARE, DEFAULT_LIGHT_SQUARE

ct32 = pytest.mark.ct("CT-32")


@ct32
def test_matriz_vazia_e_o_tabuleiro_quadriculado_com_a1_escura():
    rgb = ColorMatrix().rgb()
    assert rgb.shape == (8, 8, 3)
    assert rgb.dtype == np.uint8
    assert tuple(rgb[0, 0]) == DEFAULT_DARK_SQUARE
    assert tuple(rgb[1, 0]) == DEFAULT_LIGHT_SQUARE
    assert tuple(rgb[7, 7]) == DEFAULT_DARK_SQUARE


@ct32
def test_cores_base_vem_do_construtor():
    rgb = ColorMatrix(light_square=(1, 2, 3), dark_square=(4, 5, 6)).rgb()
    assert tuple(rgb[1, 0]) == (1, 2, 3)
    assert tuple(rgb[0, 0]) == (4, 5, 6)


@pytest.mark.parametrize("state", [state for state in CellState if state != CellState.NONE])
@ct32
def test_cada_estado_muda_a_cor_so_da_sua_casa(state):
    matrix = ColorMatrix()
    plain = matrix.rgb(0.0)
    matrix.set(3, 4, state)
    colored = matrix.rgb(0.0)
    changed = np.argwhere((plain != colored).any(axis=2))
    assert changed.tolist() == [[3, 4]]


@ct32
def test_estados_diferentes_dao_cores_diferentes():
    colors = set()
    for state in CellState:
        matrix = ColorMatrix()
        matrix.set(0, 1, state)
        colors.add(tuple(matrix.rgb(0.25)[0, 1]))
    assert len(colors) == len(CellState)


@ct32
def test_prioridade_maior_vence_e_menor_nao_sobrescreve():
    matrix = ColorMatrix()
    matrix.set(2, 2, CellState.PATH)
    matrix.set(2, 2, CellState.SELECTED)
    assert matrix.state_at(2, 2) == CellState.SELECTED
    matrix.set(2, 2, CellState.THREAT)
    assert matrix.state_at(2, 2) == CellState.SELECTED
    matrix.set(2, 2, CellState.CURSOR)
    assert matrix.state_at(2, 2) == CellState.CURSOR


@ct32
def test_none_limpa_a_casa_e_clear_limpa_tudo():
    matrix = ColorMatrix()
    matrix.set_many([(0, 0), (1, 1)], CellState.PATH)
    assert matrix.state_at(1, 1) == CellState.PATH
    matrix.set(0, 0, CellState.NONE)
    assert matrix.state_at(0, 0) == CellState.NONE
    matrix.clear()
    assert not matrix.states.any()


@ct32
def test_casa_invalida_e_ignorada_sem_excecao():
    matrix = ColorMatrix()
    matrix.set(-1, 0, CellState.CHECK)
    matrix.set(0, 8, CellState.CHECK)
    assert not matrix.states.any()
    assert matrix.state_at(9, 9) == CellState.NONE


@pytest.mark.parametrize("state", [CellState.CHECK, CellState.THREAT])
@ct32
def test_estados_de_atencao_pulsam_e_o_pulso_e_funcao_pura_do_tempo(state):
    matrix = ColorMatrix()
    matrix.set(4, 4, state)
    samples = {tuple(matrix.rgb(t)[4, 4]) for t in np.linspace(0.0, 1.0, 12)}
    assert len(samples) > 3
    assert tuple(matrix.rgb(0.37)[4, 4]) == tuple(matrix.rgb(0.37)[4, 4])


@pytest.mark.parametrize("state", [CellState.PATH, CellState.SELECTED, CellState.CURSOR, CellState.LAST_MOVE])
@ct32
def test_estados_estaveis_nao_pulsam(state):
    matrix = ColorMatrix()
    matrix.set(4, 4, state)
    samples = {tuple(matrix.rgb(t)[4, 4]) for t in np.linspace(0.0, 1.0, 12)}
    assert len(samples) == 1


@ct32
def test_paleta_pode_ser_trocada():
    matrix = ColorMatrix(palette={CellState.PATH: (0, 0, 255)})
    matrix.set(0, 0, CellState.PATH)
    red, _, blue = matrix.rgb()[0, 0]
    assert blue > red
