"""Jogo pelo teclado: cursor relativo à visão, confirmação, cancelamento e atalhos (RF08, RF16)."""
import math

import pygame
import pytest
from ui_helpers import cell, click, move_mouse_off_board, start_game, state_at

from xadrez.core import Color, GameState
from xadrez.graphics import CellState
from xadrez.ui.overlays import ChoiceOverlay, HelpOverlay


@pytest.mark.ct("CT-42")
def test_teclado_seleciona_e_executa_a_jogada(app):
    scene, player = start_game(app)
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e2")
    player.press(pygame.K_RETURN)
    assert scene.selection == cell("e2")
    player.press(pygame.K_UP)
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e4")
    player.press(pygame.K_SPACE)
    player.settle()
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-42")
def test_setas_seguem_a_visao_com_a_camera_do_lado_das_pretas(app):
    scene, player = start_game(app)
    player.play("e2e4")
    assert scene.view.camera.yaw % (2 * math.pi) == pytest.approx(math.pi)
    move_mouse_off_board(player)
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e7")
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e6")
    player.press(pygame.K_RIGHT)
    assert scene.cursor == cell("d6")
    player.press(pygame.K_DOWN)
    assert scene.cursor == cell("d7")
    player.press(pygame.K_LEFT)
    assert scene.cursor == cell("e7")


@pytest.mark.ct("CT-42")
def test_setas_com_a_camera_de_lado_seguem_o_quarto_de_volta_mais_proximo(app):
    scene, player = start_game(app)
    player.press(pygame.K_UP)
    scene.view.camera.orbit_by(math.pi / 2)
    player.press(pygame.K_UP)
    assert scene.cursor == cell("d2")
    scene.view.camera.orbit_by(math.pi)
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e2")


def test_cursor_nao_sai_do_tabuleiro(app):
    scene, player = start_game(app)
    player.press(pygame.K_UP)
    for _ in range(10):
        player.press(pygame.K_DOWN)
    assert scene.cursor == cell("e1")
    for _ in range(10):
        player.press(pygame.K_LEFT)
    assert scene.cursor == cell("a1")


def test_enter_sem_cursor_so_mostra_o_cursor(app):
    scene, player = start_game(app)
    player.press(pygame.K_RETURN)
    assert scene.cursor == cell("e2")
    assert scene.selection is None


def test_teclado_nao_e_atropelado_pelo_mouse_parado_quando_a_camera_gira(app):
    scene, player = start_game(app)
    click(player, "e2")
    click(player, "e4")
    player.press(pygame.K_UP)
    cursor = scene.cursor
    player.settle()
    assert scene.cursor == cursor


def test_esc_limpa_a_selecao_e_depois_abre_a_pausa(app):
    scene, player = start_game(app)
    click(player, "e2")
    player.press(pygame.K_ESCAPE)
    assert scene.selection is None
    assert state_at(scene, "e3") == CellState.NONE
    assert scene.engine.state is GameState.IN_PROGRESS
    player.press(pygame.K_ESCAPE)
    assert scene.engine.state is GameState.PAUSED


def test_t_liga_e_desliga_o_giro_por_turno(app):
    scene, player = start_game(app)
    assert scene.auto_rotate is True
    player.press(pygame.K_t)
    assert scene.auto_rotate is False
    assert "desligado" in scene.notices.text
    player.play("e2e4")
    assert scene.view.camera.yaw == pytest.approx(0.0)
    player.press(pygame.K_t)
    assert scene.auto_rotate is True
    player.settle()
    assert scene.view.camera.yaw % (2 * math.pi) == pytest.approx(math.pi)


def test_botao_de_giro_mostra_o_estado(app):
    scene, player = start_game(app)
    button = scene.hud.buttons[1]
    assert button.label == "Giro ligado"
    player.click_widget(button)
    assert button.label == "Giro desligado"
    assert scene.auto_rotate is False


def test_botao_direito_arrastando_orbita_a_camera(app):
    scene, player = start_game(app)
    yaw, pitch = scene.view.camera.yaw, scene.view.camera.pitch
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(400, 400), button=3))
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(430, 390), rel=(30, -10), buttons=(0, 0, 1)))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(430, 390), button=3))
    player.frames(1)
    assert scene.view.camera.yaw != pytest.approx(yaw)
    assert scene.view.camera.pitch != pytest.approx(pitch)
    yaw_after = scene.view.camera.yaw
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(450, 390), rel=(20, 0), buttons=(0, 0, 0)))
    player.frames(1)
    assert scene.view.camera.yaw == pytest.approx(yaw_after)


def test_arrastar_a_partir_do_painel_nao_orbita(app):
    scene, player = start_game(app)
    yaw = scene.view.camera.yaw
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(app.size[0] - 5, 300), button=3))
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(app.size[0] - 50, 300), rel=(-45, 0), buttons=(0, 0, 1)))
    player.frames(1)
    assert scene.view.camera.yaw == pytest.approx(yaw)


def test_roda_do_mouse_da_zoom(app):
    scene, player = start_game(app)
    distance = scene.view.camera.distance
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=2, flipped=False))
    player.frames(1)
    assert scene.view.camera.distance < distance


def test_v_volta_a_vista_padrao(app):
    scene, player = start_game(app)
    camera = scene.view.camera
    camera.orbit_by(1.0, -0.3)
    camera.zoom_by(0.7)
    player.press(pygame.K_v)
    assert scene.view.is_camera_moving
    player.settle()
    assert camera.yaw % (2 * math.pi) == pytest.approx(0.0, abs=1e-6)
    assert camera.pitch == pytest.approx(math.radians(52))
    assert camera.distance == pytest.approx(16.5)


def test_h_abre_a_ajuda_e_congela_o_relogio(app):
    scene, player = start_game(app)
    player.press(pygame.K_h)
    assert isinstance(scene.modals[-1], HelpOverlay)
    remaining = scene.engine.clock.remaining(Color.WHITE)
    player.frames(30)
    assert scene.engine.clock.remaining(Color.WHITE) == remaining
    player.press(pygame.K_h)
    assert scene.modals == []
    assert scene.engine.state is GameState.IN_PROGRESS


def test_botao_fechar_da_ajuda(app):
    scene, player = start_game(app)
    player.press(pygame.K_F1)
    player.click_widget(scene.modals[-1]._close_button)
    assert scene.modals == []


def test_r_pede_confirmacao_antes_de_reiniciar(app):
    scene, player = start_game(app)
    player.play("e2e4")
    player.press(pygame.K_r)
    assert isinstance(scene.modals[-1], ChoiceOverlay)
    assert scene.engine.history == ["e4"]
    player.press(pygame.K_ESCAPE)
    assert scene.modals == []
    assert scene.engine.history == ["e4"]
    assert scene.engine.turn is Color.BLACK


def test_f3_e_f4_abrem_os_paineis_de_bancada(app):
    scene, player = start_game(app)
    board_width = scene.view.camera.viewport[2]
    player.press(pygame.K_F3)
    player.press(pygame.K_F4)
    click(player, "e2")
    assert scene.performance_panel.is_visible
    assert scene.didactic_panel.is_visible
    assert scene.view.camera.viewport[2] < board_width
    click(player, "e2")
    assert scene.selection is None
    player.press(pygame.K_F4)
    assert scene.view.camera.viewport[2] == board_width


def test_f4_funciona_com_a_pausa_aberta(app):
    scene, player = start_game(app)
    player.press(pygame.K_p)
    player.press(pygame.K_F4)
    assert scene.didactic_panel.is_visible
    assert scene.engine.state is GameState.PAUSED
