"""Redimensionar: o clique segue certo e nenhum tamanho derruba o jogo (RNF07, RF16)."""
import pygame
import pytest
from ui_helpers import cell, click, finish_with_mate, resize, start_game

from xadrez.ui import GameOverScene, GameScene, MenuScene

ORDINARY_SIZES = [(1024, 640), (1920, 1080), (800, 600), (1600, 700)]
EXTREME_SIZES = [(1, 1), (2, 2), (40, 40), (120, 90), (320, 200), (4000, 300), (300, 2000), (640, 90), (90, 640)]


@pytest.mark.ct("CT-49")
@pytest.mark.parametrize("size", ORDINARY_SIZES)
def test_redimensionar_mantem_o_clique_correto(app, size):
    scene, player = start_game(app)
    resize(player, size)
    assert app.screen.get_size() == size
    assert scene.view.camera.viewport[2] < size[0]
    assert scene.view.camera.viewport[3] == size[1]
    click(player, "e2")
    assert scene.selection == cell("e2")
    click(player, "e4")
    player.settle()
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-49")
def test_varios_redimensionamentos_seguidos_com_partida_em_andamento(app):
    scene, player = start_game(app)
    player.play("e2e4")
    for size in ORDINARY_SIZES:
        resize(player, size)
    click(player, "e7")
    assert scene.selection == cell("e7")


@pytest.mark.ct("CT-49")
def test_botoes_do_painel_acompanham_o_redimensionamento(app):
    scene, player = start_game(app)
    resize(player, (1600, 900))
    pause_button = scene.hud.buttons[0]
    assert pause_button.rect.right <= 1600
    assert pause_button.rect.bottom <= 900
    player.click_widget(pause_button)
    assert scene.modals


@pytest.mark.ct("CT-49")
def test_sobreposicao_acompanha_o_redimensionamento(app):
    scene, player = start_game(app)
    player.press(pygame.K_p)
    resize(player, (800, 600))
    overlay = scene.modals[-1]
    assert overlay.buttons[0].rect.centerx == pytest.approx(400, abs=2)
    player.click_widget(overlay.buttons[0])
    assert scene.modals == []


def test_tamanho_mudado_sem_evento_tambem_e_seguido(app):
    scene, player = start_game(app)
    pygame.display.set_mode((1000, 700), pygame.RESIZABLE)
    player.frames(1)
    assert app.size == (1000, 700)
    assert scene.view.camera.viewport[3] == 700
    click(player, "e2")
    assert scene.selection == cell("e2")


@pytest.mark.parametrize("size", EXTREME_SIZES)
def test_tamanho_extremo_no_menu_nao_derruba(app, player, size):
    resize(player, size)
    player.frames(3)
    assert isinstance(app.scene, MenuScene)
    player.press(pygame.K_F1)
    player.frames(2)
    resize(player, (1280, 720))
    player.frames(2)


@pytest.mark.parametrize("size", EXTREME_SIZES)
def test_tamanho_extremo_na_partida_nao_derruba(app, size):
    scene, player = start_game(app)
    player.press(pygame.K_F3)
    player.press(pygame.K_F4)
    resize(player, size)
    player.frames(3)
    player.press(pygame.K_F4)
    player.press(pygame.K_F4)
    player.press(pygame.K_p)
    player.frames(2)
    player.press(pygame.K_p)
    player.press(pygame.K_h)
    player.frames(2)
    player.press(pygame.K_h)
    player.frames(2)
    resize(player, (1280, 720))
    click(player, "e2")
    assert scene.selection == cell("e2")


@pytest.mark.parametrize("size", EXTREME_SIZES)
def test_tamanho_extremo_no_dialogo_de_promocao_nao_derruba(app, size):
    scene, player = start_game(app, "4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", auto_rotate=False)
    click(player, "b7")
    click(player, "b8")
    resize(player, size)
    player.frames(2)
    assert scene.modals


@pytest.mark.parametrize("size", EXTREME_SIZES)
def test_tamanho_extremo_na_tela_final_nao_derruba(app, size):
    _, player = start_game(app)
    finish_with_mate(player)
    assert isinstance(app.scene, GameOverScene)
    resize(player, size)
    player.seconds(0.3)
    assert isinstance(app.scene, GameOverScene)


def test_animacao_em_andamento_sobrevive_ao_redimensionamento(app):
    scene, player = start_game(app)
    click(player, "e2")
    click(player, "e4")
    resize(player, (700, 500))
    player.settle()
    assert scene.engine.history == ["e4"]
    assert isinstance(app.scene, GameScene)
