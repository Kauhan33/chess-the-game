"""Revanche com as cores trocadas e volta ao menu (RF13)."""
import math

import pygame
import pytest
from ui_helpers import ENDING_SECONDS, cell, click, finish_with_mate, start_game

from xadrez.core import Color
from xadrez.ui import GameOverScene, GameScene, MenuScene


def _reach_victory(app):
    _, player = start_game(app)
    finish_with_mate(player)
    assert isinstance(app.scene, GameOverScene)
    return app.scene, player


@pytest.mark.ct("CT-47")
def test_revanche_troca_as_cores_e_mantem_o_placar(app):
    end, player = _reach_victory(app)
    engine = end.engine
    assert engine.players[Color.WHITE].name == "Jogador 1"
    assert engine.players[Color.WHITE].match_points == 1.0
    player.click_widget(end.rematch_button)
    scene = app.scene
    assert isinstance(scene, GameScene)
    assert scene.engine is engine
    assert engine.players[Color.WHITE].name == "Jogador 2"
    assert engine.players[Color.BLACK].name == "Jogador 1"
    assert engine.players[Color.BLACK].match_points == 1.0
    assert engine.players[Color.WHITE].match_points == 0.0
    assert engine.history == []


@pytest.mark.ct("CT-47")
def test_revanche_comeca_jogavel_e_com_a_camera_de_quem_joga(app):
    end, player = _reach_victory(app)
    player.click_widget(end.rematch_button)
    scene = app.scene
    player.settle()
    assert scene.view.camera.yaw % (2 * math.pi) == pytest.approx(0.0, abs=1e-6)
    assert scene.view.camera.distance == pytest.approx(16.5)
    assert scene.view.particles.alive_count == 0
    assert cell("e8") not in scene.view._hidden_squares()
    click(player, "e2")
    assert scene.selection == cell("e2")


@pytest.mark.ct("CT-47")
def test_revanche_do_meio_da_serie_soma_nova_vitoria(app):
    end, player = _reach_victory(app)
    player.click_widget(end.rematch_button)
    finish_with_mate(player)
    final = app.scene
    assert isinstance(final, GameOverScene)
    assert final.engine.players[Color.WHITE].name == "Jogador 2"
    assert final.engine.players[Color.WHITE].match_points == 1.0
    assert final.engine.players[Color.BLACK].match_points == 1.0


@pytest.mark.ct("CT-47")
def test_menu_volta_ao_inicio_e_comeca_serie_nova(app):
    end, player = _reach_victory(app)
    player.click_widget(end.menu_button)
    menu = app.scene
    assert isinstance(menu, MenuScene)
    player.click_widget(menu.start_button)
    scene = app.scene
    assert isinstance(scene, GameScene)
    assert scene.engine is not end.engine
    assert scene.engine.players[Color.WHITE].match_points == 0.0
    assert scene.engine.players[Color.WHITE].name == "Jogador 1"


def test_tela_de_fim_navegavel_pelo_teclado(app):
    end, player = _reach_victory(app)
    assert end.rematch_button.is_focused
    player.press(pygame.K_DOWN)
    assert end.menu_button.is_focused
    player.press(pygame.K_UP)
    player.press(pygame.K_RETURN)
    assert isinstance(app.scene, GameScene)


def test_ficar_na_tela_final_nao_soma_pontos(app):
    end, player = _reach_victory(app)
    player.seconds(ENDING_SECONDS)
    assert end.engine.players[Color.WHITE].match_points == 1.0
