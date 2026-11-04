"""Menu inicial: identificação dos jogadores, modo de jogo e navegação por teclado (RF01)."""
import pygame
import pytest

from xadrez.core import Color, TimeControl
from xadrez.ui import GameScene, MatchOptions, MenuScene
from xadrez.ui.overlays import HelpOverlay


def _time_index(menu, time_control):
    return next(i for i, (_, value) in enumerate(menu.time_selector.options) if value == time_control)


@pytest.mark.ct("CT-40")
def test_menu_inicia_partida_com_nomes_e_tempo_escolhidos_pelo_mouse(app, player):
    menu = app.scene
    player.click_widget(menu.white_input)
    player.type_text("Alfa")
    player.click_widget(menu.black_input)
    player.type_text("Bravo")
    arrow_on_right = (menu.time_selector.rect.right - 5, menu.time_selector.rect.centery)
    while menu.time_selector.value != TimeControl.BLITZ_5:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=arrow_on_right, button=1))
        player.frames(1)
    player.click_widget(menu.start_button)
    scene = app.scene
    assert isinstance(scene, GameScene)
    assert scene.engine.players[Color.WHITE].name == "Alfa"
    assert scene.engine.players[Color.BLACK].name == "Bravo"
    assert scene.engine.time_control == TimeControl.BLITZ_5


@pytest.mark.ct("CT-40")
def test_menu_funciona_so_pelo_teclado(app, player):
    menu = app.scene
    player.type_text("Lado Claro")
    player.press(pygame.K_RETURN)
    assert menu.focus.focused is menu.black_input
    player.type_text("Lado Escuro")
    player.press(pygame.K_TAB)
    assert menu.focus.focused is menu.time_selector
    while menu.time_selector.value != TimeControl.CLASSIC_30:
        player.press(pygame.K_RIGHT)
    player.press(pygame.K_DOWN)
    assert menu.focus.focused is menu.camera_selector
    player.press(pygame.K_LEFT)
    assert menu.camera_selector.value is False
    player.press(pygame.K_RETURN)
    assert menu.focus.focused is menu.start_button
    player.press(pygame.K_RETURN)
    scene = app.scene
    assert isinstance(scene, GameScene)
    assert scene.engine.players[Color.WHITE].name == "Lado Claro"
    assert scene.engine.players[Color.BLACK].name == "Lado Escuro"
    assert scene.engine.time_control == TimeControl.CLASSIC_30
    assert scene.auto_rotate is False


def test_nome_vazio_vira_o_padrao(app, player):
    menu = app.scene
    player.click_widget(menu.start_button)
    assert app.scene.engine.players[Color.WHITE].name == "Jogador 1"
    assert app.scene.engine.players[Color.BLACK].name == "Jogador 2"


def test_so_espacos_tambem_vira_o_padrao(app, player):
    player.type_text("    ")
    assert app.scene.white_input.value == "Jogador 1"


def test_nome_aceita_acentos_e_corta_em_16_caracteres(app, player):
    menu = app.scene
    player.type_text("Peão Promoção")
    assert menu.white_input.value == "Peão Promoção"
    player.type_text(" até o último")
    assert len(menu.white_input.text) == 16


def test_nome_recusa_caractere_de_controle_e_glifo_que_a_fonte_nao_tem(app, player):
    menu = app.scene
    player.type_text("a\x00b\n")
    assert menu.white_input.text == "ab"
    menu.white_input.text = ""
    player.type_text("\U0001F600")
    assert menu.white_input.text == ""


def test_backspace_apaga_e_espaco_entra_no_nome(app, player):
    menu = app.scene
    player.type_text("Alfa")
    player.press(pygame.K_BACKSPACE)
    assert menu.white_input.text == "Alf"
    player.type_text(" ")
    player.press(pygame.K_SPACE)
    assert menu.white_input.text == "Alf "


def test_setas_do_seletor_dao_a_volta_nas_opcoes(app, player):
    selector = app.scene.camera_selector
    total = len(selector.options)
    start = selector.index
    app.scene.focus.focus(selector)
    for _ in range(total):
        player.press(pygame.K_SPACE)
    assert selector.index == start


def test_clique_na_esquerda_do_seletor_volta_uma_opcao(app, player):
    selector = app.scene.time_selector
    start = selector.index
    position = (selector.rect.x + 4, selector.rect.centery)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=1))
    player.frames(1)
    assert selector.index == (start - 1) % len(selector.options)


def test_shift_tab_volta_o_foco(app, player):
    menu = app.scene
    player.press(pygame.K_TAB)
    assert menu.focus.focused is menu.black_input
    player.press(pygame.K_TAB, pygame.KMOD_SHIFT)
    assert menu.focus.focused is menu.white_input


def test_ajuda_abre_pelo_botao_e_pelo_f1_e_fecha(app, player):
    menu = app.scene
    player.click_widget(menu.help_button)
    assert isinstance(menu.modal, HelpOverlay)
    player.press(pygame.K_ESCAPE)
    assert menu.modal is None
    player.press(pygame.K_F1)
    assert isinstance(menu.modal, HelpOverlay)
    player.press(pygame.K_RETURN)
    assert menu.modal is None


def test_digitar_com_a_ajuda_aberta_nao_escreve_no_nome(app, player):
    menu = app.scene
    player.press(pygame.K_F1)
    player.type_text("Alfa")
    assert menu.white_input.text == ""


def test_peca_3d_gira_sozinha_no_menu(app, player):
    camera = app.scene.camera
    before = camera.yaw
    player.seconds(0.5)
    assert camera.yaw != pytest.approx(before)


def test_menu_lembra_as_opcoes_da_partida_anterior(app):
    options = MatchOptions("Alfa", "Bravo", TimeControl.CLASSIC_30, auto_rotate=False)
    menu = MenuScene(app, options)
    assert menu.options() == options


def test_nome_padrao_volta_como_campo_vazio(app):
    menu = MenuScene(app, MatchOptions())
    assert menu.white_input.text == ""
