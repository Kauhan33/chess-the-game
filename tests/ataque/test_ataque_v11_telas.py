"""Telas com nomes longos em várias janelas: nada fora da janela, nada por cima de nada e nenhum rótulo cortado.

CT-131: login, menu, histórico e sala: todos os controles dentro da janela e sem se sobrepor.
CT-132: HUD com 3 e 4 fileiras de botões, sobreposições e telas de fim, em cada janela.
CT-133: texto com nome longo cabe na faixa, nos botões e na tela de fim, sem perder o que explica a ação.
CT-134: o motivo gravado no histórico descreve o que aconteceu do ponto de vista de quem lê.
"""
from __future__ import annotations

import pygame
import pytest
from test_ataque_v11_apoio import *  # noqa: F403

from xadrez.core import Color, Difficulty, EndReason, TimeControl
from xadrez.data import HistoryStore, MatchRecord
from xadrez.ui import LoginScene, MenuScene
from xadrez.ui import theme as tokens
from xadrez.ui.hud import PANEL_WIDTH
from xadrez.ui.match import MatchOptions, OPPONENT_CPU

LONG = "W" * 16
LONG2 = "M" * 16
TINY = (640, 360)
SIZES = [(800, 600), (1024, 640), (1280, 720), (1366, 768), (1920, 1080), (640, 480), TINY]


def rect_in_window(rect, size):
    return rect.left >= 0 and rect.top >= 0 and rect.right <= size[0] and rect.bottom <= size[1]


def assert_inside(items, size):
    for name, rect in items:
        assert rect.width > 0 and rect.height > 0, f"{name}: tamanho zero em {size}"
        assert rect_in_window(rect, size), f"{name} {rect} sai da janela {size}"


def assert_no_overlap(items, size):
    for index, (name, rect) in enumerate(items):
        for other_name, other in items[index + 1:]:
            assert not rect.colliderect(other), f"{name} {rect} cobre {other_name} {other} em {size}"


def widgets_of(scene):
    return [(f"{type(widget).__name__}:{getattr(widget, 'label', '')}", widget.rect) for widget in scene.focus.widgets]


def seed_history(name):
    store = HistoryStore(name)
    for index in range(50):
        store.add(MatchRecord(f"2026-01-{index % 28 + 1:02d}T10:00:00", LONG, "rede", None, "Pretas", "derrota", "Xeque-mate", 100 + index,
                              3599.0, "Clássica 15+10", "Treinamento", '[White "a"]\n\n1. e4 *\n', "8/8/8/8/8/8/8/8 w - - 0 1"))


@pytest.fixture(params=SIZES, ids=lambda size: f"{size[0]}x{size[1]}")
def size(request):
    return request.param


@pytest.fixture(params=[size for size in SIZES if size != TINY], ids=lambda size: f"{size[0]}x{size[1]}")
def form_size(request):
    """Os formulários cabem daqui para cima. Abaixo disso, ver `test_formularios_na_menor_janela`."""
    return request.param


@pytest.mark.ct("CT-131")
def test_login_nos_dois_modos_e_com_erro_longo(form_size):
    size = form_size
    application = make_app(size=size, require_login=True)
    scene = application.scene
    for creating in (0, 1):
        scene.mode_selector.select(creating)
        application.step(0.0)
        assert_inside(widgets_of(scene), size)
        assert_no_overlap(widgets_of(scene), size)
        scene._show_error("O nome precisa ter de 3 a 16 caracteres e não pode ser repetido, nem ter caracteres estranhos.")
        application.step(0.0)
        assert_inside(widgets_of(scene), size)
        assert_no_overlap(widgets_of(scene), size)


@pytest.mark.ct("CT-131")
@pytest.mark.parametrize("account", [None, LONG])
@pytest.mark.parametrize("opponent", [0, 1, 2])
def test_menu_em_cada_opcao(form_size, account, opponent):
    size = form_size
    application = make_app(size=size, require_login=True)
    application.account = account
    application.scene.next_scene = application.menu_scene(MatchOptions(LONG, LONG2, TimeControl.CLASSIC_15_10))
    application.step(0.0)
    menu = application.scene
    menu.opponent_selector.select(opponent)
    application.step(0.0)
    assert_inside(widgets_of(menu), size)
    assert_no_overlap(widgets_of(menu), size)


@pytest.mark.ct("CT-131")
def test_historico_cheio_e_folha_aberta(size):
    application = make_app(size=size, require_login=True)
    application.account = LONG
    seed_history(LONG)
    application.scene.next_scene = application.menu_scene()
    application.step(0.0)
    menu = application.scene
    menu.tab_bar.select(1)
    application.step(0.0)
    assert_inside(widgets_of(menu), size)
    assert_no_overlap(widgets_of(menu), size)
    menu.history.open_record(0)
    menu._refresh_history_focus()
    application.step(0.0)
    sheet = [("copiar", menu.history.copy_button.rect), ("fechar", menu.history.close_button.rect)]
    assert_inside(sheet, size)
    assert_no_overlap(sheet, size)
    assert rect_in_window(menu.history._sheet, size), f"a folha sai da janela: {menu.history._sheet}"


@pytest.mark.ct("CT-131")
def test_sala_criar_e_entrar_com_erro(network, size):
    application = make_app(network, size=size)
    options = MatchOptions(LONG, LONG2, TimeControl.CLASSIC_15_10)
    application.scene.next_scene = application.lobby_scene(options, "host")
    application.step(0.0)
    lobby = application.scene
    assert_inside(widgets_of(lobby), size)
    assert_no_overlap(widgets_of(lobby), size)
    lobby._fail("Não foi possível abrir a porta 50507: ela está ocupada ou bloqueada. Feche o outro jogo ou sala e tente de novo.")
    application.step(0.0)
    assert_inside(widgets_of(lobby), size)
    assert_no_overlap(widgets_of(lobby), size)
    lobby.cancel()
    application.step(0.0)
    application.scene.next_scene = application.lobby_scene(options, "guest")
    application.step(0.0)
    guest = application.scene
    guest.error = "Não foi possível conectar à sala. Confira o código, a rede e o firewall de quem criou a sala."
    guest._layout_form()
    application.step(0.0)
    assert_inside(widgets_of(guest), size)
    assert_no_overlap(widgets_of(guest), size)


@pytest.mark.ct("CT-131")
@pytest.mark.xfail(strict=True, reason="QA11-17, aceito: abaixo de 640x480 o formulário não cabe. Basta não derrubar: ver os dois testes abaixo")
@pytest.mark.parametrize("form", ["login_criar", "menu_local", "menu_cpu", "menu_rede"])
def test_formularios_na_menor_janela(form):
    application = make_app(size=TINY, require_login=True)
    if form == "login_criar":
        application.scene.mode_selector.select(1)
        application.scene._show_error("O nome precisa ter de 3 a 16 caracteres e não pode ser repetido, nem ter caracteres estranhos.")
    else:
        application.scene.next_scene = application.menu_scene(MatchOptions(LONG, LONG2, TimeControl.CLASSIC_15_10))
        application.step(0.0)
        application.scene.opponent_selector.select(("menu_local", "menu_cpu", "menu_rede").index(form))
    application.step(0.0)
    assert_inside(widgets_of(application.scene), TINY)
    assert_no_overlap(widgets_of(application.scene), TINY)


def open_form(form, size):
    application = make_app(size=size, require_login=True)
    if form == "login_criar":
        application.scene.mode_selector.select(1)
        application.scene._show_error("O nome precisa ter de 3 a 16 caracteres e não pode ser repetido, nem ter caracteres estranhos.")
    else:
        application.scene.next_scene = application.menu_scene(MatchOptions(LONG, LONG2, TimeControl.CLASSIC_15_10))
        application.step(0.0)
        application.scene.opponent_selector.select(("menu_local", "menu_cpu", "menu_rede").index(form))
    application.step(0.0)
    return application


@pytest.mark.ct("CT-131")
@pytest.mark.parametrize("form", ["login_criar", "menu_local", "menu_cpu", "menu_rede"])
def test_formularios_cabem_a_partir_de_640x480(form):
    size = (640, 480)
    application = open_form(form, size)
    assert_inside(widgets_of(application.scene), size)
    assert_no_overlap(widgets_of(application.scene), size)


@pytest.mark.ct("CT-131")
@pytest.mark.parametrize("size", [TINY, (320, 200), (1, 1)])
@pytest.mark.parametrize("form", ["login_criar", "menu_local", "menu_cpu", "menu_rede"])
def test_formularios_em_janela_pequena_nao_derrubam(form, size):
    application = open_form(form, size)
    Autoplayer(application).frames(2)
    application.scene.draw(application.screen)


def hud_items(scene):
    hud = scene.hud
    items = [(f"botão {button.label}", button.rect) for button in hud.buttons]
    items += [(f"placa {color.label}", card.rect) for color, card in hud.cards.items()]
    if hud.sheet.rect.height > 0:
        items.append(("planilha", hud.sheet.rect))
    return items


@pytest.mark.ct("CT-132")
@pytest.mark.parametrize("kind", ["local", "cpu"])
def test_hud_com_fileiras_de_botoes(size, kind):
    application = make_app(size=size)
    if kind == "cpu":
        scene, player = open_game(application, opponent_kind=OPPONENT_CPU, difficulty=Difficulty.EASY, names=(LONG, LONG2), human_color=Color.BLACK)
    else:
        scene, player = open_game(application, names=(LONG, LONG2))
    player.frames(1)
    items = hud_items(scene)
    assert_inside(items, size)
    assert_no_overlap(items, size)
    scene.shutdown()


@pytest.mark.ct("CT-132")
def test_hud_em_rede_seis_botoes(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    for size in ((800, 600), (640, 360)):
        for application in table.apps:
            pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
            application.step(FRAME)
        for scene in (table.host, table.guest):
            assert_inside(hud_items(scene), size)
            assert_no_overlap(hud_items(scene), size)


@pytest.mark.ct("CT-132")
def test_sobreposicoes_cabem_na_janela(size):
    application = make_app(size=size)
    scene, player = open_game(application, names=(LONG, LONG2))
    player.press(pygame.K_p)
    pause = scene.modals[-1]
    assert rect_in_window(pause._panel, size), f"pausa {pause._panel}"
    assert_inside([(button.label, button.rect) for button in pause.buttons], size)
    player.press(pygame.K_p)
    player.press(pygame.K_h)
    help_overlay = scene.modals[-1]
    assert rect_in_window(help_overlay._panel, size), f"ajuda {help_overlay._panel}"
    player.press(pygame.K_h)
    scene._confirm_resign()
    player.frames(1)
    assert rect_in_window(scene.modals[-1]._panel, size)


@pytest.mark.ct("CT-132")
def test_tela_de_fim_em_cada_janela(size):
    application = make_app(size=size)
    scene, player = open_game(application, names=(LONG, LONG2))
    scene._resign()
    player.seconds(1.2)
    over = application.scene
    assert isinstance(over, GameOverScene)
    items = widgets_of(over)
    assert_inside(items, size)
    assert_no_overlap(items, size)
    assert rect_in_window(over._result_rect, size)
    assert rect_in_window(over._series_rect, size)


@pytest.mark.ct("CT-133")
def test_faixa_de_avisos_com_nome_longo_cabe_no_tabuleiro(size):
    application = make_app(size=size)
    scene, player = open_game(application, names=(LONG, LONG2))
    player.frames(1)
    rendered = scene.notices._rendered
    assert rendered.get_width() <= scene.hud.viewport.width


@pytest.mark.ct("CT-133")
def test_botao_de_aceitar_revanche_mantem_a_acao_a_vista(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    # Quem está na tela tem o nome longo do outro lado.
    table.host.net.link.peer_name = LONG
    table.host._resign()
    table.run_until_both_over()
    table.guest.rematch()
    drive(table.apps, lambda: table.host.link.peer_wants_rematch)
    over = table.host
    over._refresh_rematch_button()
    theme = table.host_app.theme
    button = over.rematch_button
    available = button.rect.width - theme.px(16)
    fitted = theme.text_fit(button.label, tokens.ROLE_LABEL, theme.px(button.font_size), tokens.INK, available)
    full_width = theme.font(tokens.ROLE_LABEL, max(round(theme.px(button.font_size) * 0.66), tokens.MIN_FONT_SIZE)).size(button.label)[0]
    assert fitted.get_width() <= available
    assert full_width <= available, "o rótulo não cabe nem no menor tamanho: sai com reticências"


@pytest.mark.ct("CT-133")
def test_painel_lateral_nao_passa_da_metade_da_janela(size):
    application = make_app(size=size)
    scene, _ = open_game(application, names=(LONG, LONG2))
    assert scene.hud.panel.width <= max(application.theme.px(PANEL_WIDTH), 1)
    assert scene.hud.panel.width <= round(size[0] * 0.5)


@pytest.mark.ct("CT-134")
def test_quem_abandona_nao_le_que_o_adversario_desconectou(host_app, guest_app):
    host_app.account = "Ana"
    host_app.scene.next_scene = host_app.menu_scene()
    host_app.step(0.0)
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    table.host._leave_room()
    record = HistoryStore("Ana").records()[0]
    assert record.outcome == "derrota"
    assert "Adversário" not in record.reason


@pytest.mark.ct("CT-134")
def test_quem_ganha_por_abandono_le_o_motivo_certo(host_app, guest_app):
    guest_app.account = "Bia"
    guest_app.scene.next_scene = guest_app.menu_scene()
    guest_app.step(0.0)
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    guest = table.guest
    table.host._leave_room()
    drive([guest_app], lambda: guest.engine.result is not None)
    record = HistoryStore("Bia").records()[0]
    assert record.outcome == "vitoria"
    assert record.reason == EndReason.ABANDONMENT.label
