"""Seleção por mouse, matriz de cores, marcadores de forma e cursor (RF08, RF09, RNF03)."""
import math

import pygame
import pytest
from ui_helpers import cell, click, hover, move_mouse_off_board, start_game, state_at

from xadrez.core import Color, TimeControl
from xadrez.graphics import MARKER_DOT, MARKER_RING, CellState, ColorMatrix, square_to_world
from xadrez.ui.autoplay import click_point, post_click, post_mouse_move


QUEEN_BEHIND_KING = "4k3/8/8/8/8/Q7/4K3/8 w - - 0 1"


def _markers_at(scene, name):
    return [marker[2] for marker in scene.view.markers if marker[:2] == cell(name)]


@pytest.mark.ct("CT-41")
def test_clique_seleciona_e_preenche_a_matriz_de_cores(app):
    scene, player = start_game(app)
    fen = scene.engine.board.to_fen()
    click(player, "e2")
    assert scene.selection == cell("e2")
    assert state_at(scene, "e2") == CellState.SELECTED
    assert state_at(scene, "e3") == CellState.PATH
    assert state_at(scene, "e4") == CellState.PATH
    assert state_at(scene, "e5") == CellState.NONE
    assert scene.engine.board.to_fen() == fen


@pytest.mark.ct("CT-41")
def test_caminho_e_captura_tem_forma_alem_de_cor(app):
    scene, player = start_game(app)
    player.play_all("e2e4 d7d5")
    click(player, "e4")
    assert state_at(scene, "d5") == CellState.CAPTURE
    assert state_at(scene, "e5") == CellState.PATH
    assert MARKER_RING in _markers_at(scene, "d5")
    assert MARKER_DOT in _markers_at(scene, "e5")


@pytest.mark.ct("CT-41")
def test_clique_no_alvo_joga_e_marca_o_ultimo_lance(app):
    scene, player = start_game(app)
    player.play("e2e4")
    assert scene.engine.history == ["e4"]
    assert scene.selection is None
    assert state_at(scene, "e2") == CellState.LAST_MOVE
    assert state_at(scene, "e4") == CellState.LAST_MOVE


def test_en_passant_marca_a_casa_vazia_como_captura(app):
    scene, player = start_game(app, "4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1", auto_rotate=False)
    player.play("e2e4")
    click(player, "d4")
    assert state_at(scene, "e3") == CellState.CAPTURE
    assert MARKER_RING in _markers_at(scene, "e3")
    assert scene.engine.board.piece_at(cell("e3")) is None


def test_promocao_nao_repete_o_destino(app):
    scene, player = start_game(app, "4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", auto_rotate=False)
    click(player, "b7")
    assert list(scene.targets) == [cell("b8")]


def test_clique_em_outra_peca_propria_troca_a_selecao(app):
    scene, player = start_game(app)
    click(player, "e2")
    click(player, "g1")
    assert scene.selection == cell("g1")
    assert state_at(scene, "e2") != CellState.SELECTED
    assert state_at(scene, "f3") == CellState.PATH


def test_clique_na_peca_selecionada_tira_a_selecao(app):
    scene, player = start_game(app)
    click(player, "e2")
    click(player, "e2")
    assert scene.selection is None
    assert state_at(scene, "e3") == CellState.NONE


def test_clique_fora_do_tabuleiro_limpa_a_selecao_sem_aviso(app):
    scene, player = start_game(app)
    click(player, "e2")
    post_click((3, 3))
    player.frames(1)
    assert scene.selection is None
    assert scene.notices.kind != "warning"


def test_peca_selecionada_e_levantada(app):
    scene, player = start_game(app)
    click(player, "e2")
    assert scene.view.lifted_square == cell("e2")
    click(player, "e2")
    assert scene.view.lifted_square is None


def test_peca_sem_jogada_e_selecionada_com_aviso(app):
    scene, player = start_game(app)
    click(player, "a1")
    assert scene.selection == cell("a1")
    assert scene.targets == {}
    assert "não tem jogada" in scene.notices.text


def test_hover_marca_o_cursor_no_mesmo_quadro(app):
    scene, player = start_game(app)
    hover(player, "d4")
    assert scene.cursor == cell("d4")
    assert state_at(scene, "d4") == CellState.CURSOR
    move_mouse_off_board(player)
    assert scene.cursor is None
    assert state_at(scene, "d4") == CellState.NONE


def test_hover_nao_apaga_a_casa_selecionada(app):
    scene, player = start_game(app)
    click(player, "e2")
    assert scene.cursor == cell("e2")
    assert state_at(scene, "e2") == CellState.SELECTED


def test_picking_so_e_refeito_quando_mouse_ou_camera_mudam(app, monkeypatch):
    scene, player = start_game(app)
    hover(player, "d4")
    calls = []
    original = scene.view.pick
    monkeypatch.setattr(scene.view, "pick", lambda position: calls.append(position) or original(position))
    player.frames(30)
    assert calls == []
    hover(player, "d5")
    assert len(calls) >= 1


def test_clique_na_cabeca_da_peca_escolhe_a_peca_e_nao_a_casa_de_tras(app):
    scene, player = start_game(app)
    x, _, z = square_to_world(*cell("e1"))
    pixels, _ = scene.view.camera.project([(x, scene.view.piece_height_at(cell("e1")) * 0.95, z)])
    head = (round(float(pixels[0, 0])), round(float(pixels[0, 1])))
    assert scene.view.camera.pick_square(*head) != cell("e1")
    post_click(head)
    player.frames(1)
    assert scene.selection == cell("e1")


def _floor_pixel_near_tall_piece(scene, x_offset):
    """Chão de e3 visto das Brancas, passando perto do rei em e2. Com deslocamento, o raio passa ao lado da cintura."""
    x, _, z = square_to_world(*cell("e3"))
    pixels, _ = scene.view.camera.project([(x + x_offset, 0.0, z + 0.3)])
    return round(float(pixels[0, 0])), round(float(pixels[0, 1]))


def test_destino_visivel_ao_lado_de_peca_alta_recebe_o_clique(app):
    scene, player = start_game(app, QUEEN_BEHIND_KING, auto_rotate=False)
    click(player, "a3")
    floor = _floor_pixel_near_tall_piece(scene, x_offset=0.3)
    assert scene.view.pick(floor) == cell("e3")
    post_click(floor)
    player.frames(1)
    player.settle()
    assert scene.engine.board.piece_at(cell("e3")).kind.value == "queen"


def test_pixel_que_mostra_a_peca_aciona_a_peca_mesmo_com_destino_atras(app):
    scene, player = start_game(app, QUEEN_BEHIND_KING, auto_rotate=False)
    click(player, "a3")
    assert scene.view.pick(_floor_pixel_near_tall_piece(scene, x_offset=0.0)) == cell("e2")


def test_durante_o_voo_o_clique_fica_bloqueado_e_o_relogio_espera_o_pouso(app):
    scene, player = start_game(app)
    click(player, "e2")
    click(player, "e4")
    assert scene.view.is_flying
    clock_before = scene.engine.clock.remaining(Color.BLACK)
    click(player, "e7")
    assert scene.selection is None
    assert scene.notices.kind != "warning"
    hover(player, "d5")
    assert scene.cursor == cell("d5")
    assert scene.engine.clock.remaining(Color.BLACK) == clock_before
    player.settle()
    player.frames(2)
    assert scene.engine.clock.remaining(Color.BLACK) < clock_before


def test_durante_o_giro_da_camera_o_clique_continua_funcionando(app):
    scene, player = start_game(app)
    player.play("e2e4")
    scene.view.camera.orbit_to(0.0, duration=5.0)
    player.frames(60)
    assert scene.view.camera.is_moving
    click(player, "e7")
    assert scene.selection == cell("e7")


def test_camera_gira_para_quem_joga_depois_do_pouso(app):
    scene, player = start_game(app)
    player.play("e2e4")
    assert scene.view.camera.yaw % (2 * math.pi) == pytest.approx(math.pi)
    player.play("e7e5")
    assert scene.view.camera.yaw % (2 * math.pi) == pytest.approx(0.0, abs=1e-6)


def test_roque_anima_tambem_a_torre(app):
    scene, player = start_game(app, "4k3/8/8/8/8/8/8/4K2R w K - 0 1", auto_rotate=False)
    click(player, "e1")
    assert state_at(scene, "g1") == CellState.PATH
    click(player, "g1")
    assert len(scene.view._flights) == 2
    player.settle()
    assert scene.engine.board.piece_at(cell("f1")).kind.value == "rook"


def test_captura_anima_a_peca_capturada_e_solta_particulas(app):
    scene, player = start_game(app, auto_rotate=False)
    player.play_all("e2e4 d7d5")
    click(player, "e4")
    click(player, "d5")
    assert scene.view._waiting_capture is not None
    player.frames(20)
    assert scene.view._waiting_capture is None
    assert scene.view.particles.alive_count > 0
    player.settle()
    assert scene.engine.players[Color.WHITE].captured


def test_matriz_de_cores_usa_a_paleta_do_tema(app):
    scene, _ = start_game(app)
    assert isinstance(scene.view.matrix, ColorMatrix)
    scene.view.matrix.set(0, 0, CellState.SELECTED)
    assert tuple(scene.view.matrix.rgb()[0, 0]) != tuple(ColorMatrix().rgb()[0, 0])


def test_hover_por_mouse_volta_depois_do_teclado(app):
    scene, player = start_game(app, time_control=TimeControl.UNLIMITED)
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e2")
    post_mouse_move(click_point(scene.view, cell("d4")))
    player.frames(1)
    assert scene.cursor == cell("d4")
