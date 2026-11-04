"""Tela cheia (F11), botão de sair do menu e clique duplo, que a banca provavelmente vai experimentar."""
import pygame

from ui_helpers import start_game
from xadrez.ui.autoplay import Autoplayer, post_click, post_key
from xadrez.ui.hud import clock_font_size

FRAME_SECONDS = 1.0 / 60.0


def test_f11_entra_e_sai_da_tela_cheia_voltando_ao_tamanho_de_antes(app):
    before = app.size
    post_key(pygame.K_F11)
    app.step(FRAME_SECONDS)
    assert app.screen.get_flags() & pygame.FULLSCREEN
    assert app.scene.next_scene is None
    post_key(pygame.K_F11)
    app.step(FRAME_SECONDS)
    assert app.size == before
    assert not app.screen.get_flags() & pygame.FULLSCREEN


def test_f11_durante_a_partida_mantem_o_jogo_e_o_clique(app):
    scene, player = start_game(app)
    post_key(pygame.K_F11)
    player.frames(1)
    player.click_square((4, 1))
    assert scene.selection == (4, 1)
    post_key(pygame.K_F11)
    player.frames(1)
    player.click_square((4, 3))
    player.settle()
    assert scene.engine.history == ["e4"]


def test_botao_sair_do_menu_encerra_o_jogo(app):
    menu = app.scene
    Autoplayer(app).click_widget(menu.quit_button)
    assert app.running is False


def test_clique_duplo_em_retomar_nao_atinge_o_tabuleiro(app):
    scene, player = start_game(app)
    player.click_square((4, 1))
    player.press(pygame.K_p)
    pixel = scene.modals[-1].buttons[0].rect.center
    post_click(pixel)
    player.frames(1)
    assert not scene.modals
    post_click(pixel)
    player.frames(1)
    assert scene.selection == (4, 1), "o 2º clique do clique duplo não pode cair no tabuleiro"


def test_clique_depois_do_tempo_do_clique_duplo_vale_normalmente(app):
    scene, player = start_game(app)
    player.press(pygame.K_p)
    pixel = scene.modals[-1].buttons[0].rect.center
    post_click(pixel)
    player.frames(1)
    player.seconds(0.3)
    post_click(pixel)
    player.frames(1)
    assert scene.notices.kind == "warning" or scene.selection is not None, "o clique deveria ter chegado ao tabuleiro"


def test_giro_desligado_fica_nas_opcoes_que_a_revanche_usa(app):
    scene, player = start_game(app, auto_rotate=True)
    player.press(pygame.K_t)
    assert scene.options.auto_rotate is False


def test_relogio_com_hora_usa_fonte_menor():
    assert clock_font_size("09:57") > clock_font_size("1:02:05")
