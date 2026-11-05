"""Virar o tabuleiro: meia volta da câmera, com o clique e as setas certos do outro lado (RF23, CT-97)."""
import math

import pygame
import pytest
from ui_helpers import cell, click, hud_button, start_cpu_game, start_game

from xadrez.core import Color, Difficulty
from xadrez.ui import GameOverScene


def side(scene):
    return scene.view.camera.yaw % (2.0 * math.pi)


def assert_facing(scene, yaw):
    assert math.isclose(side(scene), yaw, abs_tol=1e-6) or math.isclose(side(scene), yaw + 2.0 * math.pi, abs_tol=1e-6)


@pytest.mark.ct("CT-97")
def test_tecla_vira_e_o_clique_continua_certo(app):
    scene, player = start_game(app, auto_rotate=False)
    player.press(pygame.K_f)
    assert scene.view.camera.is_moving
    player.settle()
    assert_facing(scene, math.pi)
    click(player, "e2")
    assert scene.selection == cell("e2")
    click(player, "e4")
    player.settle()
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-97")
def test_botao_vira_e_outro_toque_volta(app):
    scene, player = start_game(app, auto_rotate=False)
    button = hud_button(scene, "Virar")
    player.click_widget(button)
    player.settle()
    assert_facing(scene, math.pi)
    player.click_widget(button)
    player.settle()
    assert_facing(scene, 0.0)


@pytest.mark.ct("CT-97")
@pytest.mark.parametrize("name", ["a2", "e2", "h1", "d8", "g7", "d4", "b6"])
def test_clique_em_varias_casas_com_o_tabuleiro_virado(app, name):
    from xadrez.ui.autoplay import click_point

    scene, player = start_game(app, auto_rotate=False)
    player.press(pygame.K_f)
    player.settle()
    assert scene.view.pick(click_point(scene.view, cell(name))) == cell(name)


@pytest.mark.ct("CT-97")
def test_setas_seguem_o_lado_de_quem_olha(app):
    scene, player = start_game(app, auto_rotate=False)
    player.press(pygame.K_f)
    player.settle()
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e2")
    player.press(pygame.K_UP)
    assert scene.cursor == cell("e1"), "com o tabuleiro virado, para cima é a fileira menor"
    player.press(pygame.K_RIGHT)
    assert scene.cursor == cell("d1")


@pytest.mark.ct("CT-97")
def test_virar_duas_vezes_no_meio_do_giro_termina_em_um_lado_exato(app):
    scene, player = start_game(app, auto_rotate=False)
    player.press(pygame.K_f)
    player.frames(10)
    player.press(pygame.K_f)
    player.settle()
    assert_facing(scene, 0.0)
    player.press(pygame.K_f)
    player.frames(10)
    player.press(pygame.K_f)
    player.frames(5)
    player.press(pygame.K_f)
    player.settle()
    assert_facing(scene, math.pi)


@pytest.mark.ct("CT-97")
def test_virar_durante_a_volta_a_vista_padrao_termina_do_outro_lado(app):
    scene, player = start_game(app, auto_rotate=False)
    scene.view.camera.orbit_by(0.8, -0.3)
    player.press(pygame.K_v)
    player.frames(3)
    assert scene.view.is_camera_moving
    player.press(pygame.K_f)
    player.settle()
    assert_facing(scene, math.pi)
    assert scene.view.camera.pitch == pytest.approx(math.radians(52))


@pytest.mark.ct("CT-97")
def test_vista_padrao_desfaz_a_virada(app):
    scene, player = start_game(app, auto_rotate=False)
    player.press(pygame.K_f)
    player.settle()
    player.press(pygame.K_v)
    player.settle()
    assert_facing(scene, 0.0)


@pytest.mark.ct("CT-97")
def test_contra_a_cpu_a_virada_fica_ate_pedir_a_vista_padrao(app):
    scene, player = start_cpu_game(app, Difficulty.EASY, human_color=Color.WHITE)
    player.press(pygame.K_f)
    player.settle()
    assert_facing(scene, math.pi)
    player.press(pygame.K_v)
    player.settle()
    assert_facing(scene, 0.0)


def test_virar_durante_o_fim_nao_quebra(app):
    scene, player = start_game(app)
    player.play_all("e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7")
    player.press(pygame.K_f)
    player.seconds(3.0)
    assert isinstance(app.scene, GameOverScene)


def test_giro_por_turno_continua_mandando_em_2_jogadores(app):
    scene, player = start_game(app, auto_rotate=True)
    player.press(pygame.K_f)
    player.settle()
    assert_facing(scene, math.pi)
    player.play("e2e4")
    assert_facing(scene, math.pi)  # É a vez das Pretas: a câmera fica nesse lado.
