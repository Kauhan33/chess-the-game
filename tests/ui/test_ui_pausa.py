"""Pausa e as ações dela: retomar, reiniciar, propor empate, desistir e voltar ao menu (RF12, RF13)."""
import pygame
import pytest
from ui_helpers import cell, click, start_game

from xadrez.core import Color, EndReason, GameState
from xadrez.ui import GameOverScene, GameScene, MenuScene
from xadrez.ui.autoplay import click_point, post_click

RESUME, RESTART, DRAW, RESIGN, MENU = range(5)
ACCEPT, DECLINE = range(2)


def _open_pause(scene, player):
    player.press(pygame.K_p)
    assert scene.engine.state is GameState.PAUSED


def _click_entry(scene, player, index):
    player.click_widget(scene.modals[-1].buttons[index])


@pytest.mark.ct("CT-45")
def test_pausa_congela_o_relogio_e_bloqueia_o_tabuleiro(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    remaining = scene.engine.clock.remaining(Color.WHITE)
    fen = scene.engine.board.to_fen()
    player.frames(90)
    assert scene.engine.clock.remaining(Color.WHITE) == remaining
    post_click(click_point(scene.view, cell("e2")))
    player.frames(1)
    assert scene.selection is None
    assert scene.engine.board.to_fen() == fen


@pytest.mark.ct("CT-45")
def test_pausa_bloqueia_teclado_de_jogo_e_atalhos(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    camera_yaw = scene.view.camera.yaw
    for key in (pygame.K_UP, pygame.K_t, pygame.K_v, pygame.K_r):
        player.press(key)
    assert scene.cursor is None
    assert scene.auto_rotate is True
    assert scene.view.camera.yaw == camera_yaw
    assert len(scene.modals) == 1


@pytest.mark.ct("CT-45")
def test_hud_nao_recebe_clique_com_a_pausa_aberta(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    rotation_button = scene.hud.buttons[1]
    player.click_widget(rotation_button)
    assert scene.auto_rotate is True


@pytest.mark.ct("CT-45")
def test_retomar_devolve_relogio_e_tabuleiro(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    _click_entry(scene, player, RESUME)
    assert scene.engine.state is GameState.IN_PROGRESS
    remaining = scene.engine.clock.remaining(Color.WHITE)
    player.frames(10)
    assert scene.engine.clock.remaining(Color.WHITE) < remaining
    click(player, "e2")
    assert scene.selection == cell("e2")


@pytest.mark.ct("CT-45")
def test_p_e_esc_tambem_retomam(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    player.press(pygame.K_p)
    assert scene.engine.state is GameState.IN_PROGRESS
    _open_pause(scene, player)
    player.press(pygame.K_ESCAPE)
    assert scene.engine.state is GameState.IN_PROGRESS


def test_botao_pausar_do_painel(app):
    scene, player = start_game(app)
    player.click_widget(scene.hud.buttons[0])
    assert scene.engine.state is GameState.PAUSED


def test_pausa_navegavel_pelo_teclado(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    overlay = scene.modals[-1]
    player.press(pygame.K_DOWN)
    assert overlay.buttons[RESTART].is_focused
    player.press(pygame.K_RETURN)
    assert len(scene.modals) == 2


def test_confirmacao_comeca_com_o_foco_na_opcao_segura(app):
    scene, player = start_game(app)
    player.play("e2e4")
    _open_pause(scene, player)
    _click_entry(scene, player, RESIGN)
    player.press(pygame.K_RETURN)
    assert scene.engine.result is None
    assert len(scene.modals) == 1


def test_animacao_em_andamento_congela_na_pausa(app):
    scene, player = start_game(app)
    click(player, "e2")
    click(player, "e4")
    assert scene.view.is_flying
    _open_pause(scene, player)
    player.frames(60)
    assert scene.view.is_flying
    player.press(pygame.K_p)
    player.settle()
    assert not scene.view.is_flying


def test_reiniciar_com_confirmacao_mantem_o_placar_e_as_cores(app):
    scene, player = start_game(app)
    scene.engine.players[Color.WHITE].match_points = 1.0
    player.play_all("e2e4 e7e5")
    _open_pause(scene, player)
    _click_entry(scene, player, RESTART)
    assert scene.engine.history == ["e4", "e5"]
    _click_entry(scene, player, ACCEPT)
    assert scene.engine.history == []
    assert scene.engine.state is GameState.IN_PROGRESS
    assert scene.engine.players[Color.WHITE].name == "Jogador 1"
    assert scene.engine.players[Color.WHITE].match_points == 1.0
    assert scene.modals == []


def test_reiniciar_durante_o_voo_limpa_a_animacao(app):
    scene, player = start_game(app)
    click(player, "e2")
    click(player, "e4")
    player.press(pygame.K_r)
    _click_entry(scene, player, ACCEPT)
    assert not scene.view.is_flying
    player.settle()
    click(player, "e2")
    assert scene.selection == cell("e2")


def test_voltar_da_confirmacao_nao_reinicia_e_mantem_a_pausa(app):
    scene, player = start_game(app)
    player.play("e2e4")
    _open_pause(scene, player)
    _click_entry(scene, player, RESTART)
    _click_entry(scene, player, DECLINE)
    assert len(scene.modals) == 1
    assert scene.engine.state is GameState.PAUSED
    assert scene.engine.history == ["e4"]


def test_empate_por_acordo_passa_pela_confirmacao_do_outro_jogador(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    _click_entry(scene, player, DRAW)
    overlay = scene.modals[-1]
    assert "Jogador 1 propõe" in overlay.lines[0]
    assert "Jogador 2" in overlay.lines[1]
    assert scene.engine.result is None
    _click_entry(scene, player, ACCEPT)
    assert scene.engine.result.reason is EndReason.AGREEMENT
    player.seconds(1.5)
    assert isinstance(app.scene, GameOverScene)
    assert scene.engine.players[Color.WHITE].match_points == 0.5
    assert scene.engine.players[Color.BLACK].match_points == 0.5


def test_empate_recusado_volta_ao_jogo_com_aviso(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    _click_entry(scene, player, DRAW)
    _click_entry(scene, player, DECLINE)
    assert scene.modals == []
    assert scene.engine.state is GameState.IN_PROGRESS
    assert "Jogador 2 recusou" in scene.notices.text
    assert scene.engine.result is None


def test_esc_na_proposta_de_empate_recusa(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    _click_entry(scene, player, DRAW)
    player.press(pygame.K_ESCAPE)
    assert scene.modals == []
    assert scene.engine.result is None


def test_desistir_pede_confirmacao_e_da_a_vitoria_ao_outro(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    _click_entry(scene, player, RESIGN)
    assert "Jogador 1" in scene.modals[-1].lines[0]
    assert scene.engine.result is None
    _click_entry(scene, player, ACCEPT)
    assert scene.engine.result.winner is Color.BLACK
    assert scene.engine.result.reason is EndReason.RESIGNATION
    assert scene.modals == []
    player.seconds(1.5)
    assert isinstance(app.scene, GameOverScene)


def test_voltar_ao_menu_pede_confirmacao(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    _click_entry(scene, player, MENU)
    assert isinstance(app.scene, GameScene)
    _click_entry(scene, player, ACCEPT)
    assert isinstance(app.scene, MenuScene)


def test_nao_ha_pausa_depois_do_fim(app):
    scene, player = start_game(app)
    _open_pause(scene, player)
    _click_entry(scene, player, RESIGN)
    _click_entry(scene, player, ACCEPT)
    player.press(pygame.K_p)
    assert scene.modals == []
    player.press(pygame.K_h)
    assert scene.modals == []
    player.press(pygame.K_r)
    assert scene.modals == []
