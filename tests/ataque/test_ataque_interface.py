"""Roteiros maliciosos contra a interface, por eventos reais e `App.step`, sem janela.

CT-58: corridas entre relógio, voo, pausa, promoção e fim de jogo: tudo termina em um estado coerente.
CT-59: clique: o pixel que mostra uma peça aciona essa peça, e clicar de novo nela desmarca (QA-02, QA-03).
CT-60: clique duplo e dois eventos no mesmo quadro não confirmam nem repetem ações (QA-04, QA-07, QA-08).
CT-61: nomes: nenhum caractere derruba o jogo, e a fonte desenha o que o campo aceita (QA-01, QA-06, QA-09).
CT-62: janelas e números extremos: redimensionar, zoom, F4 e dt absurdo (QA-12, QA-13, QA-16).
CT-63: telas de fim: revanche e menu mantêm nomes e opções, sem pular a vitória (QA-05, QA-10, QA-11, QA-17, QA-18).
CT-64: vazamento: revanches em série e partida longa não acumulam memória nem caches.
"""
from __future__ import annotations

import gc
import math
import random
import tracemalloc

import numpy as np
import pygame
import pytest

from xadrez.ui.hud import clock_font_size

from xadrez.core import Color, EndReason, GameState, Square, TimeControl, legal_moves
from xadrez.graphics import piece_matrix, square_to_world
from xadrez.graphics.renderer import _build_geometry, _rasterize, _visible_polygons
from xadrez.ui import App, GameOverScene, GameScene, MatchOptions, MenuScene
from xadrez.ui import theme as tokens
from xadrez.ui.autoplay import Autoplayer, click_point, post_click, post_key, post_mouse_move, post_text
from xadrez.ui.board_view import PIECE_FACING

SCHOLARS_SETUP = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6"
AFTER_D4_D5 = "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"
AFTER_E4_E5 = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
RESUME, RESTART, DRAW, RESIGN, MENU = range(5)


def cell(name):
    return tuple(Square.from_name(name))


@pytest.fixture
def app():
    application = App(seed=11)
    pygame.event.clear()
    yield application
    pygame.event.clear()


def start(app, fen=None, time_control=TimeControl.RAPID_10, auto_rotate=False, names=("Ana", "Bia")):
    options = MatchOptions(names[0], names[1], time_control, auto_rotate)
    app.scene.next_scene = app.game_scene(options.create_engine(fen), options)
    player = Autoplayer(app)
    player.frames(1)
    player.settle()
    return app.scene, player


def click(player, name):
    player.click_square(cell(name))


def pixel_on_piece(scene, name, fraction):
    """Pixel do eixo da peça, a `fraction` da altura dela: é onde o olho vê a peça."""
    height = scene.view.piece_height_at(cell(name))
    x, _, z = square_to_world(*cell(name))
    pixels, _ = scene.view.camera.project(np.array([(x, height * fraction, z)], dtype=float))
    return round(float(pixels[0, 0])), round(float(pixels[0, 1]))


def resize(player, size):
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
    player.frames(1)


def finish_by_resignation(app, player):
    scene = app.scene
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[RESIGN])
    player.click_widget(scene.modals[-1].buttons[0])
    player.seconds(1.1)
    assert isinstance(app.scene, GameOverScene)
    return app.scene


def visible_piece_map(scene):
    """Desenha cada peça com um código de cor, na ordem do pintor: é o que o jogador vê em cada pixel."""
    view, camera = scene.view, scene.view.camera
    x, y, width, height = camera.viewport
    surface = pygame.Surface((x + width, y + height))
    surface.fill((0, 0, 0))
    items = []
    for square, piece in scene.engine.board.pieces():
        matrix = piece_matrix(*tuple(square), PIECE_FACING[piece.color])
        geometry = _build_geometry(view.meshes[piece.kind.value], matrix, np.full(3, 200.0), view.renderer.light)
        offset = geometry.homogeneous[:, :3].mean(axis=0) - camera.eye
        items.append(((offset * offset).sum(), tuple(square), geometry))
    items.sort(key=lambda item: -item[0])
    codes = {}
    for index, (_, square, geometry) in enumerate(items, start=1):
        codes[index] = square
        polygons = _visible_polygons(geometry, camera, view.renderer.light)
        order = np.argsort(-polygons.distances)
        color = np.tile(np.array((index, 0, 0), dtype=np.uint8), (len(order), 1))
        _rasterize(surface, polygons.quads[order], color)
    return pygame.surfarray.array3d(surface)[:, :, 0], codes


# Corridas entre relógio, voo, pausa e fim ---------------------------------------------------------------


@pytest.mark.ct("CT-58")
def test_ataque_tempo_acaba_com_dialogo_de_promocao_aberto(app):
    scene, player = start(app, fen="7k/1P6/8/8/8/8/P7/K7 w - - 0 1", time_control=TimeControl(0.02))
    click(player, "b7")
    click(player, "b8")
    assert scene.modals
    player.seconds(1.5)
    assert scene.engine.result.reason is EndReason.TIMEOUT and scene.engine.result.is_draw, "as Pretas só têm o rei"
    assert not scene.modals and scene.selection is None
    assert scene.engine.history == [], "o peão não pode promover depois do tempo"
    player.seconds(1.2)
    assert isinstance(app.scene, GameOverScene)


@pytest.mark.ct("CT-58")
def test_ataque_pausa_durante_o_voo_congela_a_peca_e_o_relogio(app):
    scene, player = start(app, time_control=TimeControl.BLITZ_5)
    click(player, "e2")
    click(player, "e4")
    assert scene.view.is_flying
    player.press(pygame.K_p)
    frozen = scene.engine.clock.remaining(Color.BLACK)
    player.frames(120)
    assert scene.view.is_flying and scene.engine.clock.remaining(Color.BLACK) == frozen
    player.press(pygame.K_p)
    player.settle()
    assert not scene.view.is_flying and scene.notices.text == "Vez de Bia, Pretas"


@pytest.mark.ct("CT-58")
@pytest.mark.parametrize("size", [(1, 1), (50, 2000), (3000, 200), (640, 360)])
def test_ataque_redimensionar_durante_voo_e_giro(app, size):
    scene, player = start(app, auto_rotate=True)
    click(player, "e2")
    click(player, "e4")
    resize(player, size)
    player.settle()
    player.frames(10)
    assert scene.engine.history == ["e4"] and not scene.view.is_flying
    resize(player, (1280, 720))
    player.settle()
    click(player, "e7")
    assert scene.selection == Square.from_name("e7"), "o clique continua certo depois de voltar"


def land_and_start_turning(scene, player):
    click(player, "e2")
    click(player, "e4")
    while scene.view.is_flying:
        player.frames(1)
    player.frames(3)
    assert scene.view.camera.is_moving, "o giro por turno começou"


@pytest.mark.ct("CT-58")
def test_ataque_t_durante_o_giro_termina_no_lado_certo(app):
    scene, player = start(app, auto_rotate=True)
    land_and_start_turning(scene, player)
    player.press(pygame.K_t)
    assert scene.auto_rotate is False and scene.view.camera.is_moving, "o giro em curso termina"
    player.press(pygame.K_t)
    assert scene.auto_rotate is True
    player.seconds(1.2)
    assert not scene.view.camera.is_moving
    assert math.isclose(abs(scene.view.camera.yaw) % (2.0 * math.pi), math.pi, abs_tol=1e-6)
    click(player, "e7")
    assert scene.selection == Square.from_name("e7")


@pytest.mark.ct("CT-58")
def test_ataque_v_durante_o_giro_volta_para_quem_joga(app):
    scene, player = start(app, auto_rotate=True)
    land_and_start_turning(scene, player)
    player.press(pygame.K_v)
    player.seconds(1.2)
    camera = scene.view.camera
    assert not scene.view.is_camera_moving
    assert math.isclose(abs(camera.yaw) % (2.0 * math.pi), math.pi, abs_tol=1e-6)
    assert math.isclose(camera.distance, 16.5) and math.isclose(camera.pitch, math.radians(52))


@pytest.mark.ct("CT-58")
def test_ataque_arrastar_a_camera_durante_o_giro_interrompe_sem_quebrar(app):
    scene, player = start(app, auto_rotate=True)
    land_and_start_turning(scene, player)
    x, y, width, height = scene.view.camera.viewport
    center = (x + width // 2, y + height // 2)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=center, button=3))
    player.frames(1)
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=center, rel=(120, 900), buttons=(0, 0, 1)))
    player.frames(1)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=center, button=3))
    player.frames(1)
    assert not scene.view.camera.is_moving and scene._is_orbiting is False
    assert math.radians(18) <= scene.view.camera.pitch <= math.radians(85)
    player.press(pygame.K_v)
    player.seconds(0.8)
    click(player, "e7")
    assert scene.selection == Square.from_name("e7")


@pytest.mark.ct("CT-58")
def test_ataque_atalhos_durante_a_queda_do_rei_nao_abrem_nada(app):
    scene, player = start(app, auto_rotate=True)
    player.play_all(SCHOLARS_SETUP + " h5f7")
    player.seconds(0.3)
    assert scene._ending_left is not None
    for key in (pygame.K_r, pygame.K_p, pygame.K_h, pygame.K_F1, pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_UP):
        player.press(key)
    assert not scene.modals and scene.cursor is None
    player.seconds(2.4)
    assert isinstance(app.scene, GameOverScene)


@pytest.mark.ct("CT-58")
def test_ataque_lance_e_tempo_no_mesmo_quadro_vale_o_lance(app):
    """Eventos vêm antes do relógio no quadro: o lance chega antes da bandeira cair."""
    scene, player = start(app, time_control=TimeControl.BLITZ_5)
    scene.engine.clock._remaining[Color.WHITE] = 0.05
    post_click(click_point(scene.view, cell("e2")))
    app.step(0.0)
    post_click(click_point(scene.view, cell("e4")))
    app.step(0.1)
    assert scene.engine.history == ["e4"] and scene.engine.result is None
    assert scene.engine.clock.remaining(Color.WHITE) == 0.05


@pytest.mark.ct("CT-58")
def test_ataque_clique_depois_do_tempo_esgotado_nao_joga(app):
    scene, player = start(app, time_control=TimeControl.BLITZ_5)
    scene.engine.clock._remaining[Color.WHITE] = 0.05
    post_click(click_point(scene.view, cell("e2")))
    app.step(0.0)
    target = click_point(scene.view, cell("e4"))
    app.step(0.1)
    post_click(target)
    app.step(0.0)
    assert scene.engine.history == [] and scene.engine.result.reason is EndReason.TIMEOUT


@pytest.mark.ct("CT-58")
def test_ataque_desistir_com_as_pretas_em_cima_da_hora(app):
    scene, player = start(app, time_control=TimeControl.BLITZ_5)
    player.play("e2e4")
    scene.engine.clock._remaining[Color.BLACK] = 0.2
    player.press(pygame.K_p)
    frozen = scene.engine.clock.remaining(Color.BLACK)
    player.frames(60)
    player.click_widget(scene.modals[-1].buttons[RESIGN])
    assert scene.modals[-1].title == "Desistir da partida?" and "Bia" in scene.modals[-1].lines[0]
    player.frames(60)
    player.click_widget(scene.modals[-1].buttons[0])
    result = scene.engine.result
    assert result.reason is EndReason.RESIGNATION and result.winner is Color.WHITE
    assert scene.engine.clock.remaining(Color.BLACK) == frozen
    player.seconds(1.2)
    assert isinstance(app.scene, GameOverScene)
    assert scene.engine.players[Color.WHITE].match_points == 1.0 and scene.engine.players[Color.BLACK].match_points == 0.0


@pytest.mark.ct("CT-58")
def test_ataque_reiniciar_durante_captura_nao_deixa_fantasma(app):
    scene, player = start(app)
    player.play_all("e2e4 d7d5")
    click(player, "e4")
    click(player, "d5")
    player.frames(16)
    assert scene.view._effects, "a peça capturada está sumindo"
    player.press(pygame.K_r)
    player.click_widget(scene.modals[-1].buttons[0])
    view = scene.view
    assert not view._effects and not view._flights and view._waiting_capture is None and view.particles.alive_count == 0
    assert len(view._placed) == 32 and scene.engine.history == [] and scene._last_move is None
    assert scene.engine.state is GameState.IN_PROGRESS


@pytest.mark.ct("CT-58")
def test_ataque_esc_em_cada_estado(app):
    player = Autoplayer(app)
    menu = app.scene
    player.press(pygame.K_ESCAPE)
    assert app.scene is menu and app.running
    player.press(pygame.K_F1)
    player.press(pygame.K_ESCAPE)
    assert menu.modal is None
    scene, player = start(app)
    player.press(pygame.K_ESCAPE)
    assert len(scene.modals) == 1
    player.press(pygame.K_ESCAPE)
    assert not scene.modals
    click(player, "e2")
    player.press(pygame.K_ESCAPE)
    assert scene.selection is None and not scene.modals
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[RESTART])
    player.press(pygame.K_ESCAPE)
    assert len(scene.modals) == 1 and scene.engine.state is GameState.PAUSED
    player.click_widget(scene.modals[-1].buttons[DRAW])
    player.press(pygame.K_ESCAPE)
    assert not scene.modals and scene.engine.state is GameState.IN_PROGRESS and scene.engine.result is None


# Clique --------------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-59")
@pytest.mark.parametrize("fen, square, fraction", [
    (AFTER_D4_D5, "d1", 0.85),
    (AFTER_E4_E5, "e1", 0.85),
    (AFTER_E4_E5, "e1", 0.7),
])
def test_ataque_clicar_de_novo_na_peca_alta_desmarca(app, fen, square, fraction):
    scene, player = start(app, fen=fen)
    pixel = pixel_on_piece(scene, square, fraction)
    post_click(pixel)
    player.frames(1)
    assert scene.selection == Square.from_name(square)
    post_click(pixel)
    player.frames(1)
    assert scene.engine.history == [], "clique duplo em peça alta jogou a peça"
    assert scene.selection is None


@pytest.mark.ct("CT-59")
def test_ataque_clicar_em_outra_peca_propria_troca_a_selecao(app):
    scene, player = start(app, fen=AFTER_E4_E5)
    click(player, "g1")
    post_click(pixel_on_piece(scene, "e1", 0.85))
    player.frames(1)
    assert scene.engine.history == [], "a jogada Ne2 foi feita sem o jogador pedir"
    assert scene.selection == Square.from_name("e1")


@pytest.mark.ct("CT-59")
@pytest.mark.parametrize("fraction", [0.25, 0.4, 0.55, 0.72])
def test_ataque_primeiro_lance_clicando_no_corpo_do_peao_e2(app, fraction):
    scene, player = start(app)
    post_click(pixel_on_piece(scene, "e2", fraction))
    player.frames(1)
    assert scene.selection == Square.from_name("e2")


@pytest.mark.ct("CT-59")
def test_ataque_pixel_que_mostra_uma_peca_aciona_essa_peca(app):
    scene, _ = start(app)
    view = scene.view
    visible, codes = visible_piece_map(scene)
    x, y, width, height = view.camera.viewport
    seen = wrong = 0
    for pixel_y in range(y, y + height, 3):
        for pixel_x in range(x, x + width, 3):
            square = codes.get(int(visible[pixel_x, pixel_y]))
            if square is None:
                continue
            seen += 1
            wrong += view.pick((pixel_x, pixel_y)) != square
    assert seen > 1000
    assert wrong / seen < 0.02, f"{wrong} de {seen} pixels de peça visível acionam outra casa"


@pytest.mark.ct("CT-59")
def test_ataque_pixel_que_mostra_o_chao_aciona_a_casa(app):
    scene, _ = start(app)
    view = scene.view
    visible, codes = visible_piece_map(scene)
    x, y, width, height = view.camera.viewport
    floor_pixels = wrong = 0
    for pixel_y in range(y, y + height, 3):
        for pixel_x in range(x, x + width, 3):
            if int(visible[pixel_x, pixel_y]) in codes:
                continue
            floor = view.camera.pick_square(pixel_x, pixel_y)
            if floor is None:
                continue
            floor_pixels += 1
            wrong += view.pick((pixel_x, pixel_y)) != floor
    assert floor_pixels > 1000
    assert wrong / floor_pixels < 0.02, f"{wrong} de {floor_pixels} pixels de chão acionam uma peça"


@pytest.mark.ct("CT-59")
def test_ataque_clique_com_zoom_nos_dois_extremos(app):
    scene, player = start(app)
    for wheel, expected in ((1, 9.0), (-1, 32.0)):
        for _ in range(200):
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=wheel, flipped=False))
        player.frames(1)
        assert scene.view.camera.distance == expected
        click(player, "d2")  # e2 fica atrás do rei: esse caso é o QA-03.
        assert scene.selection == Square.from_name("d2")
        player.press(pygame.K_ESCAPE)


@pytest.mark.ct("CT-59")
def test_ataque_setas_com_camera_em_angulo_seguem_o_tabuleiro(app):
    scene, player = start(app)
    player.press(pygame.K_UP)
    assert scene.cursor == (4, 1)
    for _ in range(12):
        player.press(pygame.K_UP)
    assert scene.cursor == (4, 7), "o cursor para na borda"
    for _ in range(12):
        player.press(pygame.K_LEFT)
    assert scene.cursor == (0, 7)


# Clique duplo e eventos no mesmo quadro ------------------------------------------------------------------


@pytest.mark.ct("CT-60")
def test_ataque_clique_duplo_em_propor_empate_nao_aceita_sozinho(app):
    scene, player = start(app)
    player.press(pygame.K_p)
    button = scene.modals[-1].buttons[DRAW]
    pixel = (button.rect.centerx, button.rect.top + 5)
    post_click(pixel)
    player.frames(1)
    assert scene.modals[-1].title == "Proposta de empate"
    post_click(pixel)
    player.frames(1)
    assert scene.engine.result is None, "o empate foi aceito por quem propôs"


@pytest.mark.ct("CT-60")
@pytest.mark.parametrize("index", [RESIGN, MENU])
def test_ataque_clique_duplo_em_desistir_e_menu_nao_confirma(app, index):
    scene, player = start(app)
    player.press(pygame.K_p)
    rect = scene.modals[-1].buttons[index].rect
    post_click(rect.center)
    player.frames(1)
    post_click(rect.center)
    player.frames(1)
    assert scene.engine.result is None and app.scene is scene


@pytest.mark.ct("CT-60")
@pytest.mark.parametrize("key_pair", [True, False])
def test_ataque_revanche_duas_vezes_no_mesmo_quadro_troca_as_cores_uma_vez(app, key_pair):
    scene, player = start(app)
    over = finish_by_resignation(app, player)
    for _ in range(2):
        if key_pair:
            post_key(pygame.K_RETURN)
        else:
            post_click(over.rematch_button.rect.center)
    player.frames(1)
    assert isinstance(app.scene, GameScene)
    assert app.scene.engine.players[Color.WHITE].name == "Bia"


@pytest.mark.ct("CT-60")
def test_ataque_clique_duplo_em_revanche_em_quadros_seguidos(app):
    scene, player = start(app)
    over = finish_by_resignation(app, player)
    pixel = over.rematch_button.rect.center
    post_click(pixel)
    player.frames(1)
    post_click(pixel)
    player.frames(1)
    game = app.scene
    assert isinstance(game, GameScene) and game.engine.players[Color.WHITE].name == "Bia"
    assert game.selection is None and not game.modals


@pytest.mark.ct("CT-60")
def test_ataque_clique_duplo_em_voltar_ao_menu_em_quadros_seguidos(app):
    scene, player = start(app)
    over = finish_by_resignation(app, player)
    pixel = over.menu_button.rect.center
    post_click(pixel)
    player.frames(1)
    menu = app.scene
    post_click(pixel)
    player.frames(1)
    assert app.scene is menu and isinstance(menu, MenuScene)


@pytest.mark.ct("CT-60")
def test_ataque_clique_e_redimensionar_no_mesmo_quadro(app):
    menu = app.scene
    player = Autoplayer(app)
    post_click(menu.start_button.rect.center)
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=(800, 600), w=800, h=600))
    player.frames(1)
    game = app.scene
    assert isinstance(game, GameScene) and app.size == (800, 600)
    assert game.hud.panel.right == 800, f"o painel segue em {game.hud.panel}"


# Nomes ---------------------------------------------------------------------------------------------------


ZERO_WIDTH_TEXTS = ["\ufe0f", "\U0001F336\ufe0f", "\U0001F5A5\ufe0f", "\U0001F321\ufe0f", "\u034f", "\u17b4", "\u180b", "\ufe00"]


@pytest.mark.ct("CT-61")
@pytest.mark.parametrize("text", ZERO_WIDTH_TEXTS, ids=lambda text: "-".join(f"{ord(c):x}" for c in text))
def test_ataque_nome_de_largura_zero_nao_derruba_o_menu(app, text):
    player = Autoplayer(app)
    post_text(text)
    player.frames(2)


@pytest.mark.ct("CT-61")
@pytest.mark.parametrize("text", ["\ud55c\uae00", "\u4e2d\u6587", "\u0645\u0631\u062d\u0628\u0627", "\u265e"])
def test_ataque_campo_recusa_caractere_que_a_fonte_nao_desenha(app, text):
    menu = app.scene
    theme = app.theme
    font = theme.font(tokens.ROLE_DISPLAY, theme.px(19))
    missing = font.render("\ue000", True, (0, 0, 0), (255, 255, 255))
    glyph = font.render(text[0], True, (0, 0, 0), (255, 255, 255))
    same = glyph.get_size() == missing.get_size() and pygame.surfarray.array3d(glyph).tobytes() == pygame.surfarray.array3d(missing).tobytes()
    if not same:
        pytest.skip("esta fonte desenha o caractere; o ataque depende da fonte da máquina")
    player = Autoplayer(app)
    post_text(text)
    player.frames(1)
    assert menu.white_input.text == ""


@pytest.mark.ct("CT-61")
@pytest.mark.parametrize("text", [
    "\x00", "\x07", "\n", "\t", "\r", "\x7f", "\u200b", "\u202e", "\ud83d", "\U0001F600", "\U0001F468\u200d\U0001F469", "\U0010ffff",
    "\uffff", "\ue000",
])
def test_ataque_controle_e_emoji_nao_entram_no_nome(app, text):
    menu = app.scene
    player = Autoplayer(app)
    post_text(text)
    player.frames(2)
    assert all(char.isprintable() for char in menu.white_input.text)
    assert menu.white_input.text == ""
    assert menu.options().white_name == "Jogador 1"


@pytest.mark.ct("CT-61")
def test_ataque_colagem_longa_corta_em_16_e_nome_so_de_espacos_usa_o_padrao(app):
    menu = app.scene
    player = Autoplayer(app)
    post_text("x" * 20000)
    player.frames(1)
    assert menu.white_input.text == "x" * 16
    player.press(pygame.K_TAB)
    post_text("          ")
    player.frames(1)
    assert menu.options().black_name == "Jogador 2"


@pytest.mark.ct("CT-61")
@pytest.mark.parametrize("size", [(640, 360), (1280, 720), (1920, 1080)])
@pytest.mark.parametrize("names", [("W" * 16, "Ç" * 16), ("Ç" * 16, "W" * 16)])
def test_ataque_nomes_largos_nao_vazam_da_placa(names, size):
    application = App(size, seed=11)
    pygame.event.clear()
    menu = application.scene
    player = Autoplayer(application)
    post_text(names[0])
    player.frames(1)
    player.press(pygame.K_TAB)
    post_text(names[1])
    player.frames(1)
    player.click_widget(menu.start_button)
    player.settle()
    game = application.scene
    theme = application.theme
    for color in Color:
        card = game.hud.cards[color]
        assert card.rect.right <= size[0]
        fitted = theme.text_fit(game.engine.players[color].name, tokens.ROLE_DISPLAY, theme.px(24), tokens.IVORY, card.rect.width // 2)
        assert fitted.get_width() <= card.rect.width // 2
    assert game.engine.players[Color.WHITE].name == names[0]
    assert game.engine.players[Color.BLACK].name == names[1]
    pygame.event.clear()


@pytest.mark.ct("CT-61")
def test_ataque_fechar_ajuda_com_h_nao_digita_no_nome(app):
    menu = app.scene
    player = Autoplayer(app)
    player.press(pygame.K_F1)
    assert menu.modal is not None
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h, mod=0, unicode="h", scancode=0))
    pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text="h"))
    player.frames(1)
    assert menu.modal is None
    assert menu.white_input.text == ""


# Janelas e números extremos -------------------------------------------------------------------------------


@pytest.mark.ct("CT-62")
@pytest.mark.parametrize("size", [(1, 1), (100, 100), (400, 300), (600, 400), (800, 200), (1000, 300), (50, 2000), (3000, 200)])
def test_ataque_f4_e_f3_em_janela_minuscula(size):
    application = App(size, seed=11)
    pygame.event.clear()
    scene, player = start(application)
    player.press(pygame.K_F4)
    player.press(pygame.K_F3)
    post_mouse_move((size[0] // 2, size[1] // 2))
    player.frames(3)
    player.press(pygame.K_F4)
    player.press(pygame.K_F3)
    player.frames(1)
    x, _, width, height = scene.view.camera.viewport
    assert x == 0 and width >= 1 and height >= 1
    pygame.event.clear()


@pytest.mark.ct("CT-62")
@pytest.mark.parametrize("dt", [1e9, -1.0, 0.0, math.inf, -math.inf])
def test_ataque_dt_absurdo_e_limitado_pelo_app(app, dt):
    scene, player = start(app, time_control=TimeControl.BLITZ_5)
    before = scene.engine.clock.remaining(Color.WHITE)
    app.step(dt)
    spent = before - scene.engine.clock.remaining(Color.WHITE)
    assert 0.0 <= spent <= 0.1 + 1e-9 and scene.engine.result is None


@pytest.mark.ct("CT-62")
@pytest.mark.parametrize("in_game", [False, True])
def test_ataque_dt_nan_nao_derruba(app, in_game):
    if in_game:
        start(app)
    with np.errstate(all="ignore"):
        app.step(float("nan"))
        app.step(1 / 60)


@pytest.mark.ct("CT-62")
def test_ataque_roda_gigante_nao_derruba(app):
    scene, player = start(app)
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-(10**6), flipped=False))
    player.frames(1)
    assert scene.view.camera.distance == 32.0


@pytest.mark.ct("CT-62")
def test_ataque_roda_grande_de_verdade_fica_no_limite(app):
    scene, player = start(app)
    for steps, expected in ((500, 9.0), (-500, 32.0)):
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=steps, flipped=False))
        player.frames(1)
        assert scene.view.camera.distance == expected


@pytest.mark.ct("CT-62")
def test_ataque_vista_padrao_termina_mesmo_com_jogada_no_meio(app):
    scene, player = start(app, auto_rotate=True)
    for _ in range(10):
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=3, flipped=False))
    player.frames(1)
    player.press(pygame.K_v)
    player.frames(5)
    click(player, "e2")
    click(player, "e4")
    player.settle()
    player.seconds(1.0)
    assert math.isclose(scene.view.camera.distance, 16.5), f"zoom ficou em {scene.view.camera.distance}"


@pytest.mark.ct("CT-62")
def test_ataque_particulas_no_limite_nao_estouram(app):
    scene, player = start(app)
    particles = scene.view.particles
    for _ in range(40):
        particles.victory_fireworks((0.0, 3.0, 0.0), ((255, 255, 255), (10, 200, 30)))
    assert particles.alive_count == particles.capacity
    player.frames(5)
    assert particles.alive_count <= particles.capacity
    particles.update(1000.0)
    assert particles.alive_count == 0


# Fim de jogo, revanche e menu --------------------------------------------------------------------------


@pytest.mark.ct("CT-63")
def test_ataque_reiniciar_no_voo_do_mate_nao_pula_a_vitoria(app):
    scene, player = start(app)
    player.play_all(SCHOLARS_SETUP)
    click(player, "h5")
    click(player, "f7")
    assert scene.engine.result is not None and scene.view.is_flying
    player.press(pygame.K_r)
    assert not scene.modals, "não há o que reiniciar: a partida já acabou"


@pytest.mark.ct("CT-63")
def test_ataque_ajuda_no_voo_do_mate_so_adia_a_vitoria(app):
    scene, player = start(app)
    player.play_all(SCHOLARS_SETUP)
    click(player, "h5")
    click(player, "f7")
    player.press(pygame.K_h)
    player.seconds(4.0)
    assert app.scene is scene
    player.press(pygame.K_ESCAPE)
    player.seconds(3.2)
    assert isinstance(app.scene, GameOverScene)


@pytest.mark.ct("CT-63")
def test_ataque_ciclo_menu_partida_fim_menu_partida_mantem_nomes_e_opcoes(app):
    menu = app.scene
    player = Autoplayer(app)
    post_text("Ana")
    player.frames(1)
    player.press(pygame.K_TAB)
    post_text("Bia")
    player.frames(1)
    menu.time_selector.step(1)
    menu.camera_selector.step(1)
    expected = menu.options()
    player.click_widget(menu.start_button)
    player.settle()
    game = app.scene
    assert game.engine.time_control == TimeControl.CLASSIC_30 and game.auto_rotate is False
    player.play_all(SCHOLARS_SETUP + " h5f7")
    player.seconds(3.0)
    over = app.scene
    assert isinstance(over, GameOverScene) and over.engine.players[Color.WHITE].match_points == 1.0
    player.click_widget(over.rematch_button)
    player.settle()
    second = app.scene
    assert second.engine.players[Color.WHITE].name == "Bia" and second.engine.players[Color.BLACK].match_points == 1.0
    over = finish_by_resignation(app, player)
    assert over.engine.players[Color.BLACK].match_points == 2.0
    player.click_widget(over.menu_button)
    menu_again = app.scene
    assert isinstance(menu_again, MenuScene) and menu_again.options() == expected
    assert menu_again.white_input.text == "Ana" and menu_again.black_input.text == "Bia"
    player.click_widget(menu_again.start_button)
    player.settle()
    third = app.scene
    assert third.engine.players[Color.WHITE].name == "Ana" and third.engine.players[Color.WHITE].match_points == 0.0


@pytest.mark.ct("CT-63")
def test_ataque_relogio_acima_de_uma_hora_nao_invade_a_etiqueta(app):
    scene, player = start(app, time_control=TimeControl.UNLIMITED)
    scene.engine.clock._elapsed[Color.WHITE] = 3725.0
    player.frames(2)
    card = scene.hud.cards[Color.WHITE]
    theme = app.theme
    digits = theme.tabular(card.info.clock, tokens.ROLE_NUMERIC, theme.px(clock_font_size(card.info.clock)), tokens.INK)
    label = theme.text("Joga agora", tokens.ROLE_LABEL, theme.px(15), tokens.IVORY)
    tag_left = card.rect.width - theme.px(11) - label.get_width() - theme.px(14)
    assert theme.px(11) + digits.get_width() <= tag_left, f"relógio {card.info.clock} passa da etiqueta"


@pytest.mark.ct("CT-63")
def test_ataque_planilha_com_as_pretas_primeiro(app):
    """O primeiro lance é das Pretas: a tinta da linha 1 precisa estar só na coluna da direita."""
    scene, player = start(app, fen="4k3/8/8/8/8/8/4P3/4K3 b - - 3 10")
    player.play("e8e7")
    player.frames(1)
    sheet = scene.hud.sheet
    theme = app.theme
    _, white_x, black_x = sheet._column_x()
    top = theme.px(25)
    bottom = top + theme.px(23)
    pixels = pygame.surfarray.array3d(sheet._surface)[:, top + 2:bottom - 2].sum(axis=2)
    assert (pixels[black_x:] < 200).any(), "o lance das Pretas não apareceu na coluna delas"
    assert not (pixels[white_x:black_x - theme.px(7)] < 200).any(), "lance das Pretas na coluna das Brancas"


@pytest.mark.ct("CT-63")
def test_ataque_giro_na_queda_do_rei_nao_troca_o_aviso(app):
    scene, player = start(app, auto_rotate=False)
    player.play_all(SCHOLARS_SETUP + " h5f7")
    player.seconds(0.2)
    status = scene.notices.text
    assert status.startswith("Xeque-mate!")
    player.press(pygame.K_t)
    assert scene.notices.text == status and not scene.view.camera.is_moving


@pytest.mark.ct("CT-63")
def test_ataque_botao_do_hud_nao_fica_preso_quando_a_sobreposicao_abre(app):
    scene, player = start(app)
    button = scene.hud.buttons[0]
    post_mouse_move(button.rect.center)
    player.frames(1)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=button.rect.center, button=1))
    player.frames(1)
    player.press(pygame.K_h)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=button.rect.center, button=1))
    player.frames(1)
    assert len(scene.modals) == 1 and not button.is_pressed


@pytest.mark.ct("CT-63")
@pytest.mark.parametrize("button", [DRAW, RESIGN])
def test_ataque_titulo_da_confirmacao_nao_corta_a_acao(app, button):
    scene, player = start(app, names=("W" * 16, "\u00c7" * 16))
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[button])
    modal = scene.modals[-1]
    theme = app.theme
    available = modal._panel.width - 2 * theme.px(26)
    size = theme._size_that_fits(modal.title, tokens.ROLE_DISPLAY, theme.px(30), available)
    assert theme.font(tokens.ROLE_DISPLAY, size).size(modal.title)[0] <= available, f"{modal.title!r} não cabe"


@pytest.mark.ct("CT-63")
def test_ataque_revanche_de_partida_empatada_mantem_meio_ponto(app):
    scene, player = start(app)
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[DRAW])
    player.click_widget(scene.modals[-1].buttons[0])
    player.seconds(1.1)
    over = app.scene
    assert over.engine.players[Color.WHITE].match_points == 0.5
    player.click_widget(over.rematch_button)
    game = app.scene
    assert game.engine.players[Color.WHITE].name == "Bia" and game.engine.players[Color.WHITE].match_points == 0.5


@pytest.mark.ct("CT-63")
def test_ataque_fen_com_pretas_primeiro_na_interface(app):
    scene, player = start(app, fen="4k3/8/8/8/8/8/4P3/4K3 b - - 3 10")
    assert scene.notices.text == "Vez de Bia, Pretas" and scene.hud.active_color is Color.BLACK
    click(player, "e2")
    assert scene.selection is None and scene.notices.text == "Essa peça é do adversário."
    player.play("e8e7")
    assert scene.engine.turn is Color.WHITE


# Vazamento -----------------------------------------------------------------------------------------------


def rematch_loop(app, player, rounds):
    for _ in range(rounds):
        scene = app.scene
        scene.engine.resign()
        scene._begin_ending(scene.engine.result)
        for _ in range(60):
            player.frames(1)
            if isinstance(app.scene, GameOverScene):
                break
        over = app.scene
        assert isinstance(over, GameOverScene)
        player.frames(2)
        post_click(over.rematch_button.rect.center)
        player.frames(2)
        assert isinstance(app.scene, GameScene)


def traced_growth_mb(action):
    gc.collect()
    tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]
    action()
    gc.collect()
    current = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    return (current - baseline) / 1e6


@pytest.mark.ct("CT-64")
def test_ataque_revanches_em_serie_nao_acumulam_memoria(app):
    scene, player = start(app)
    rematch_loop(app, player, 3)
    growth = traced_growth_mb(lambda: rematch_loop(app, player, 12))
    assert growth < 2.0, f"12 revanches somaram {growth:.2f} MB"


@pytest.mark.ct("CT-64")
@pytest.mark.slow
def test_ataque_200_revanches_nao_acumulam_memoria(app):
    scene, player = start(app)
    rematch_loop(app, player, 5)
    growth = traced_growth_mb(lambda: rematch_loop(app, player, 200))
    assert growth < 3.0, f"200 revanches somaram {growth:.2f} MB"
    white, black = app.scene.engine.players[Color.WHITE], app.scene.engine.players[Color.BLACK]
    assert white.match_points + black.match_points == 205.0
    print(f"200 revanches: crescimento {growth:.2f} MB, textos {len(app.theme._texts)}")


@pytest.mark.ct("CT-64")
@pytest.mark.slow
def test_ataque_cinco_minutos_de_partida_nao_acumulam_memoria(app):
    """Lances sorteados com semente, um a cada 2 s, e revanche quando a partida acaba: cinco minutos sempre jogando."""
    start(app, time_control=TimeControl.UNLIMITED, auto_rotate=True)
    player = Autoplayer(app)
    rng = random.Random(5)
    played = []

    def run():
        for frame in range(5 * 60 * 60):
            scene = app.scene
            if frame % 120 == 0:
                if isinstance(scene, GameOverScene):
                    post_click(scene.rematch_button.rect.center)
                elif isinstance(scene, GameScene) and scene.engine.result is None and not scene.view.is_flying:
                    move = rng.choice(legal_moves(scene.engine.board))
                    played.append(move.uci)
                    uci = move.uci
                    player.click_square(cell(uci[:2]))
                    player.click_square(cell(uci[2:4]))
                    if scene.modals:
                        post_key(pygame.K_1)
            player.frames(1)

    growth = traced_growth_mb(run)
    assert len(played) > 100
    assert growth < 5.0, f"5 minutos somaram {growth:.2f} MB"
    assert len(app.theme._texts) <= 1600
    renderer = app.scene.view.renderer
    assert len(renderer._cell_sprites) <= 2048 and len(renderer._glow_sprites) <= 4096
    print(f"lances {len(played)}, crescimento {growth:.2f} MB, textos {len(app.theme._texts)}")
