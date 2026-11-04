"""Uma partida inteira, do menu à vitória, só por eventos reais (RF07, RF14)."""
import pygame
import pytest
from ui_helpers import ENDING_SECONDS, FULL_GAME, SCHOLARS_MATE, cell, click, hover, start_game, state_at

from xadrez.core import Color, EndReason, GameState
from xadrez.graphics import CellState
from xadrez.ui import GameOverScene, GameScene, MenuScene


@pytest.mark.ct("CT-46")
def test_partida_completa_por_eventos_ate_a_tela_de_vitoria(app, player):
    assert isinstance(app.scene, MenuScene)
    player.type_text("Jogador 1")
    player.click_widget(app.scene.start_button)
    scene = app.scene
    assert isinstance(scene, GameScene)
    player.settle()
    player.play_all(FULL_GAME)
    assert scene.engine.state is GameState.FINISHED
    assert isinstance(app.scene, GameScene)
    player.seconds(ENDING_SECONDS)
    end = app.scene
    assert isinstance(end, GameOverScene)
    assert end.result.winner is Color.WHITE
    assert end.result.reason is EndReason.CHECKMATE
    assert len(end.engine.history) == 33
    assert end.engine.history[-1] == "Rd8#"
    assert end.engine.history[22] == "O-O-O"
    assert end.engine.players[Color.WHITE].match_points == 1.0


@pytest.mark.ct("CT-46")
def test_partida_inteira_tambem_funciona_com_a_camera_fixa(app):
    scene, player = start_game(app, auto_rotate=False)
    player.play_all(SCHOLARS_MATE)
    assert scene.view.camera.yaw == pytest.approx(0.0)
    player.seconds(ENDING_SECONDS)
    assert isinstance(app.scene, GameOverScene)
    assert scene.engine.result.winner is Color.WHITE


def test_mate_tomba_o_rei_e_solta_fogos_antes_da_tela_final(app):
    scene, player = start_game(app)
    player.play_all(SCHOLARS_MATE)
    assert scene.view._fallen_king is not None
    assert scene.view._fallen_king.square == cell("e8")
    assert state_at(scene, "e8") == CellState.CHECK
    assert state_at(scene, "f7") == CellState.CHECK
    assert scene.notices.text == "Xeque-mate! Jogador 1 venceu."
    player.seconds(1.0)
    assert scene.view.particles.alive_count > 0
    assert isinstance(app.scene, GameScene)
    player.seconds(1.6)
    assert isinstance(app.scene, GameOverScene)


def test_rei_tombado_continua_no_chao_na_tela_final(app):
    scene, player = start_game(app)
    player.play_all(SCHOLARS_MATE)
    player.seconds(ENDING_SECONDS + 2.0)
    assert scene.view._fallen_king.animation.is_done
    assert cell("e8") in scene.view._hidden_squares()


def test_tabuleiro_nao_aceita_clique_depois_do_mate(app):
    scene, player = start_game(app)
    player.play_all(SCHOLARS_MATE)
    click(player, "e1")
    assert scene.selection is None


def test_cursor_some_no_fim_de_jogo(app):
    scene, player = start_game(app)
    player.play_all(SCHOLARS_MATE)
    hover(player, "a4")
    click(player, "a4")
    player.press(pygame.K_UP)
    assert scene.cursor is None
    assert state_at(scene, "a4") == CellState.NONE
