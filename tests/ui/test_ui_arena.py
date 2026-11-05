"""Menu da versão 1.1: abas, formulário por adversário e tudo cabendo na janela (RF01, RF17, RF18, RF19, RF24)."""
import itertools

import pygame
import pytest
from ui_helpers import resize, start_cpu_game, start_game

from xadrez.core import Color, Difficulty, TimeControl
from xadrez.ui import App, GameMode, MatchOptions, MenuScene
from xadrez.ui.autoplay import Autoplayer
from xadrez.ui.match import OPPONENT_CPU, OPPONENT_LOCAL, OPPONENT_NET, TIME_CONTROLS, time_control_label
from xadrez.ui.menu_scene import TAB_HISTORY, TAB_PLAY

SIZES = [(1280, 720), (1024, 640), (1920, 1080), (800, 600)]
KIND_INDEX = {OPPONENT_LOCAL: 0, OPPONENT_CPU: 1, OPPONENT_NET: 2}


def show_form(player, menu, kind):
    player.click_segment(menu.opponent_selector, KIND_INDEX[kind])


def test_menu_comeca_em_2_jogadores_no_modo_treinamento_com_o_foco_no_nome(app):
    menu = app.scene
    assert menu.tab_bar.value == TAB_PLAY
    assert menu.opponent_kind == OPPONENT_LOCAL
    assert menu.mode_selector.value is GameMode.TRAINING
    assert menu.focus.focused is menu.white_input


def test_formulario_de_2_jogadores_mostra_nomes_e_camera(app):
    menu = app.scene
    widgets = menu.focus.widgets
    for widget in (menu.white_input, menu.black_input, menu.time_selector, menu.camera_selector, menu.start_button):
        assert widget in widgets
    for widget in (menu.difficulty_selector, menu.color_selector, menu.create_room_button, menu.join_room_button):
        assert widget not in widgets


def test_formulario_contra_a_cpu_mostra_nivel_e_cor(app, player):
    menu = app.scene
    show_form(player, menu, OPPONENT_CPU)
    widgets = menu.focus.widgets
    for widget in (menu.difficulty_selector, menu.color_selector, menu.time_selector, menu.start_button):
        assert widget in widgets
    for widget in (menu.white_input, menu.black_input, menu.camera_selector, menu.create_room_button):
        assert widget not in widgets
    assert [label for label, _ in menu.difficulty_selector.options] == ["Easy", "Medium", "Hard", "Hardcore"]
    assert menu.difficulty_selector.value is Difficulty.EASY, "quem nunca jogou começa pelo mais fácil"
    assert [label for label, _ in menu.color_selector.options] == ["Brancas", "Pretas", "Sorteio"]


def test_cada_nivel_tem_uma_frase_explicando(app, player):
    menu = app.scene
    show_form(player, menu, OPPONENT_CPU)
    notes = []
    for index in range(4):
        player.click_segment(menu.difficulty_selector, index)
        notes.append(" ".join(line for lines, *_ in menu._notes for line in lines))
    assert len(set(notes)) == 4
    assert Difficulty.HARDCORE.description.split()[0] in notes[3]


def test_modo_tem_uma_frase_explicando(app, player):
    menu = app.scene
    before = " ".join(line for lines, *_ in menu._notes for line in lines)
    player.click_segment(menu.mode_selector, 1)
    after = " ".join(line for lines, *_ in menu._notes for line in lines)
    assert before != after
    assert menu.options().mode is GameMode.MATCH


def test_formulario_de_rede_mostra_criar_sala_e_entrar_com_codigo(app, player):
    menu = app.scene
    show_form(player, menu, OPPONENT_NET)
    widgets = menu.focus.widgets
    for widget in (menu.white_input, menu.time_selector, menu.create_room_button, menu.join_room_button):
        assert widget in widgets
    assert menu.black_input not in widgets
    assert menu.camera_selector not in widgets
    assert menu.start_button not in widgets
    assert menu.white_input.label == "Seu nome"


def test_trocar_de_formulario_e_voltar_mantem_o_que_foi_digitado(app, player):
    menu = app.scene
    player.type_text("Alfa")
    show_form(player, menu, OPPONENT_CPU)
    show_form(player, menu, OPPONENT_LOCAL)
    assert menu.white_input.text == "Alfa"
    assert menu.white_input.label == "Brancas"


def test_tempos_pedidos_com_incremento(app):
    menu = app.scene
    assert [label for label, _ in menu.time_selector.options] == [
        "Sem limite", "Blitz 3+2", "Blitz 5", "Rápida 10+0", "Clássica 30", "Clássica 15+10",
    ]
    assert menu.time_selector.value == TimeControl.RAPID_10


def test_tempo_com_incremento_chega_ao_motor_e_ao_hud(app, player):
    menu = app.scene
    while menu.time_selector.value != TimeControl.BLITZ_3_2:
        menu.time_selector.step(1)
    player.click_widget(menu.start_button)
    scene = app.scene
    assert scene.engine.time_control == TimeControl.BLITZ_3_2
    player.settle()
    player.play("e2e4")
    assert scene.engine.clock.remaining(Color.WHITE) > 180.0, "o incremento entrou"


@pytest.mark.parametrize("time_control, label", [(control, name) for name, control in TIME_CONTROLS])
def test_nome_de_cada_tempo(time_control, label):
    assert time_control_label(time_control) == label


def test_tempo_fora_da_lista_tambem_tem_nome():
    assert time_control_label(TimeControl(0.5, 1)) == "0,5+1"


def test_menu_lembra_nivel_cor_modo_e_adversario():
    application = App(seed=3)
    pygame.event.clear()
    options = MatchOptions("Alfa", "Bravo", TimeControl.BLITZ_3_2, False, GameMode.MATCH, OPPONENT_CPU, Difficulty.HARD, None)
    menu = MenuScene(application, options)
    assert menu.options() == options
    assert menu.focus.focused is menu.start_button, "sem campo de nome, o teclado começa em iniciar"


def test_voltar_ao_menu_depois_da_cpu_lembra_o_formulario(app):
    scene, player = start_cpu_game(app, Difficulty.HARD, human_color=Color.BLACK)
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[-1])
    player.click_widget(scene.modals[-1].buttons[0])
    menu = app.scene
    assert menu.opponent_kind == OPPONENT_CPU
    assert menu.difficulty_selector.value is Difficulty.HARD
    assert menu.color_selector.value is Color.BLACK


def test_aba_de_historico_troca_os_controles_e_volta(app, player):
    menu = app.scene
    player.click_segment(menu.tab_bar, 1)
    assert menu.tab_bar.value == TAB_HISTORY
    assert menu.opponent_selector not in menu.focus.widgets
    assert menu.quit_button in menu.focus.widgets
    player.click_segment(menu.tab_bar, 0)
    assert menu.opponent_selector in menu.focus.widgets


def test_teclado_percorre_o_formulario_na_ordem_visual(app, player):
    menu = app.scene
    order = [menu.focus.focused]
    for _ in range(len(menu.focus.widgets) - 1):
        player.press(pygame.K_TAB)
        order.append(menu.focus.focused)
    assert set(order) == set(menu.focus.widgets)
    tops = [widget.rect.top for widget in menu.focus.widgets]
    assert tops == sorted(tops), "Tab segue a ordem em que os controles aparecem"


def test_seta_escolhe_a_opcao_no_controle_segmentado(app, player):
    menu = app.scene
    menu.focus.focus(menu.opponent_selector)
    player.press(pygame.K_RIGHT)
    assert menu.opponent_kind == OPPONENT_CPU
    assert menu.focus.focused is menu.opponent_selector
    player.press(pygame.K_LEFT)
    assert menu.opponent_kind == OPPONENT_LOCAL


def test_passar_o_mouse_no_controle_segmentado(app, player):
    menu = app.scene
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=menu.opponent_selector.segment_rect(2).center, rel=(0, 0), buttons=(0, 0, 0)))
    player.frames(1)
    assert menu.opponent_selector._hovered_segment == 2


@pytest.mark.parametrize("size, kind", list(itertools.product(SIZES, KIND_INDEX)))
def test_tudo_cabe_na_janela_sem_sobrepor(size, kind):
    application = App(size, seed=3)
    pygame.event.clear()
    player = Autoplayer(application)
    menu = application.scene
    show_form(player, menu, kind)
    player.frames(1)
    window = pygame.Rect(0, 0, *size)
    widgets = menu.focus.widgets
    for widget in widgets:
        assert window.contains(widget.rect), f"{widget} em {widget.rect} fora de {size}"
    for first, second in itertools.combinations(widgets, 2):
        assert not first.rect.colliderect(second.rect), f"{first.rect} sobre {second.rect}"


@pytest.mark.parametrize("size", [(1, 1), (40, 40), (320, 200), (640, 360), (3000, 200), (90, 640)])
@pytest.mark.parametrize("kind", KIND_INDEX)
def test_janela_minuscula_nao_derruba_nenhum_formulario(app, player, size, kind):
    menu = app.scene
    menu.opponent_selector.select(KIND_INDEX[kind])
    resize(player, size)
    player.frames(2)
    resize(player, (1280, 720))
    assert app.scene is menu


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("local", [True, False])
def test_botoes_do_hud_cabem_e_a_planilha_continua_legivel(size, local):
    application = App(size, seed=3)
    pygame.event.clear()
    scene, _ = start_game(application) if local else start_cpu_game(application, Difficulty.EASY)
    window = pygame.Rect(0, 0, *size)
    for button in scene.hud.buttons:
        assert window.contains(button.rect), f"{button.label} em {button.rect}"
    for first, second in itertools.combinations(scene.hud.buttons, 2):
        assert not first.rect.colliderect(second.rect)
    theme = application.theme
    rows = (scene.hud.sheet.rect.height - theme.px(25)) // theme.px(23)
    assert rows >= 8, f"só {rows} linhas de lances"
    scene.shutdown()


def test_desistir_ocupa_a_linha_inteira_quando_sobra_sozinho(app):
    scene, _ = start_game(app)
    resign = scene.hud.buttons[-1]
    assert resign.label == "Desistir"
    assert resign.rect.width > scene.hud.buttons[0].rect.width


def test_botao_desativado_nao_responde(app, player):
    menu = app.scene
    menu.quit_button.is_enabled = False
    player.click_widget(menu.quit_button)
    assert app.running is True
    player.frames(1)
