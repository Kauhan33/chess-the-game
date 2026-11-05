"""Arrastar, virar, copiar e clique duplo: entrada fora de ordem, no meio do arrasto e entre telas.

CT-124: soltar fora da janela, no painel, sem ter apertado; botão direito, tecla, janela e pausa no meio do arrasto.
CT-125: arrastar na vez de quem não deve, em peça do outro, em voo, com a partida acabando e com o tempo esgotando.
CT-126: arrastar até a promoção e misturar clique com arrasto.
CT-127: virar durante o giro e a animação, e o clique continua certo depois.
CT-128: copiar PGN sem lances, com a partida acabada, com nomes difíceis e com a área de transferência falhando; o texto é um PGN válido.
CT-129: o 2º clique de um clique duplo não aciona nada na tela que acabou de abrir.
"""
from __future__ import annotations

import math
import re

import pygame
import pytest
from test_ataque_v11_apoio import *  # noqa: F403

from xadrez.core import Board, Color, Difficulty, EndReason, GameState, Square, TimeControl, legal_moves, move_to_san
from xadrez.ui import LoginScene, MenuScene, clipboard
from xadrez.ui.game_scene import CPU_TURN_NOTICE, GENERIC_REFUSAL

PROMOTION = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
SCHOLARS_MATE = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"


def begin_drag(scene, name, player):
    start = point_of(scene.view, name)
    move_to(start, (0, 0, 0))
    press_at(start)
    move_to((start[0] + 12, start[1] - 12))
    player.frames(1)
    assert scene.view.dragged_square == cell(name), "o arrasto precisa ter começado"
    return start


def game(app, **options):
    options.setdefault("mode", GameMode.TRAINING)
    return open_game(app, **options)


# Saídas do arrasto ---------------------------------------------------------------------------------


@pytest.mark.ct("CT-124")
def test_soltar_no_painel_devolve_a_peca(app):
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    panel_point = scene.hud.panel.center
    move_to(panel_point)
    release_at(panel_point)
    player.frames(1)
    assert scene.view.dragged_square is None
    assert scene.engine.history == []
    assert scene.engine.board.piece_at(Square.from_name("e2")) is not None
    assert scene.notices.text != GENERIC_REFUSAL


@pytest.mark.ct("CT-124")
def test_soltar_sobre_um_botao_do_painel_nao_aciona_o_botao(app):
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    button = scene.hud.buttons[0].rect.center
    move_to(button)
    release_at(button)
    player.frames(1)
    assert not scene.modals, "soltar a peça em cima de um botão não é clicar nele"
    assert scene.view.dragged_square is None


@pytest.mark.ct("CT-124")
def test_soltar_fora_da_janela_e_voltar_sem_botao(app):
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    # O SDL não entrega o MOUSEBUTTONUP fora da janela: o próximo movimento já vem com o botão solto.
    move_to((50, 50), (0, 0, 0))
    player.frames(1)
    assert scene.view.dragged_square is None
    assert scene.selection == Square.from_name("e2"), "a seleção fica"
    release_at((300, 300))
    player.frames(1)
    assert scene.engine.history == []


@pytest.mark.ct("CT-124")
def test_soltar_com_coordenada_negativa_ou_alem_da_janela(app):
    scene, player = game(app)
    for position in ((-5, -5), (5000, 300), (300, 5000)):
        begin_drag(scene, "e2", player)
        move_to(position)
        release_at(position)
        player.frames(1)
        assert scene.view.dragged_square is None
        assert scene.engine.history == []
        scene._set_selection(None)
        player.seconds(0.3)


@pytest.mark.ct("CT-124")
def test_soltar_sem_ter_apertado_nao_faz_nada(app):
    scene, player = game(app)
    for name in ("e2", "e4", "e7"):
        release_at(point_of(scene.view, name))
        player.frames(1)
    assert scene.selection is None and not scene.engine.history


@pytest.mark.ct("CT-124")
@pytest.mark.parametrize("code, opens_modal", [(pygame.K_p, True), (pygame.K_h, True), (pygame.K_F1, True), (pygame.K_r, True), (pygame.K_ESCAPE, False)])
def test_tecla_com_a_peca_no_ar_devolve_a_peca(app, code, opens_modal):
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    post_key(code)
    player.frames(1)
    assert scene.view.dragged_square is None
    assert bool(scene.modals) is opens_modal
    target = point_of(scene.view, "e4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.engine.history == [], "o soltar depois da tecla não vale como jogada"


@pytest.mark.ct("CT-124")
def test_botao_direito_no_meio_do_arrasto_gira_e_o_arrasto_continua(app):
    scene, player = game(app)
    start = begin_drag(scene, "e2", player)
    press_at(start, 3)
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(start[0] + 40, start[1]), rel=(40, 0), buttons=(1, 0, 1)))
    release_at((start[0] + 40, start[1]), 3)
    player.frames(1)
    assert scene.view.dragged_square == cell("e2")
    target = point_of(scene.view, "e4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-124")
@pytest.mark.parametrize("size", [(800, 600), (1920, 1080), (321, 240), (100, 100)])
def test_janela_muda_com_a_peca_no_ar(app, size):
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
    player.frames(1)
    assert scene.view.dragged_square == cell("e2")
    move_to((size[0] // 3, size[1] // 2))
    player.frames(1)
    release_at((size[0] // 3, size[1] // 2))
    player.frames(1)
    assert scene.view.dragged_square is None


@pytest.mark.ct("CT-124")
def test_f3_f4_e_f11_com_a_peca_no_ar(app):
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    for code in (pygame.K_F3, pygame.K_F4, pygame.K_F11):
        post_key(code)
        player.frames(1)
    move_to((400, 300))
    player.frames(1)
    post_key(pygame.K_F4)
    post_key(pygame.K_F3)
    post_key(pygame.K_F11)
    player.frames(1)
    target = point_of(scene.view, "e4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.view.dragged_square is None
    assert scene.engine.history == ["e4"]


# Quem não pode arrastar ----------------------------------------------------------------------------


@pytest.mark.ct("CT-125")
def test_peca_do_outro_e_casa_vazia_nao_comecam_arrasto(app):
    scene, player = game(app)
    for name in ("e7", "e5"):
        start = point_of(scene.view, name)
        press_at(start)
        move_to((start[0] + 40, start[1]))
        player.frames(1)
        assert scene.view.dragged_square is None
        release_at((start[0] + 40, start[1]))
        player.frames(1)


@pytest.mark.ct("CT-125")
def test_nao_arrasta_durante_o_voo(app):
    scene, player = game(app)
    player.click_square(cell("e2"))
    player.click_square(cell("e4"))
    assert scene.view.is_flying
    start = point_of(scene.view, "d7")
    press_at(start)
    move_to((start[0] + 40, start[1]))
    player.frames(1)
    assert scene.view.dragged_square is None
    assert scene.selection is None


@pytest.mark.ct("CT-125")
def test_tempo_esgota_com_a_peca_no_ar(app):
    scene, player = game(app, time_control=TimeControl.BLITZ_5)
    begin_drag(scene, "e2", player)
    fast_forward_clock(scene, Color.WHITE, 0.01)
    player.frames(2)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.view.dragged_square is None
    assert scene.view.lifted_square is None
    target = point_of(scene.view, "e4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.engine.history == []
    player.seconds(1.2)
    assert isinstance(app.scene, GameOverScene)


@pytest.mark.ct("CT-125")
def test_em_rede_o_outro_desiste_com_a_peca_no_ar(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    begin_drag(scene, "e2", player)
    raw.send_resign()
    wait_until(host_app, lambda: scene.engine.result is not None)
    assert scene.view.dragged_square is None and scene.view.lifted_square is None
    target = point_of(scene.view, "e4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.engine.history == []
    raw.close()


@pytest.mark.ct("CT-125")
def test_em_rede_arrasto_soltado_envia_a_jogada(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, player = table.host, table.host_player
    begin_drag(host, "e2", player)
    target = point_of(host.view, "e4")
    move_to(target)
    release_at(target)
    host_app.step(FRAME)
    drive(table.apps, lambda: table.guest.engine.history == ["e4"])
    assert table.host.engine.board.to_fen() == table.guest.engine.board.to_fen()


@pytest.mark.ct("CT-125")
def test_em_rede_nao_arrasta_na_vez_do_outro(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    guest, player = table.guest, table.guest_player
    start = point_of(guest.view, "e7")
    press_at(start)
    move_to((start[0] + 30, start[1]))
    player.frames(1)
    assert guest.view.dragged_square is None and guest.selection is None


# Promoção e mistura com clique ---------------------------------------------------------------------


@pytest.mark.ct("CT-126")
def test_arrastar_para_a_promocao_escolher_e_cancelar(app):
    scene, player = game(app, fen=PROMOTION)
    begin_drag(scene, "a7", player)
    target = point_of(scene.view, "a8")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.modals and type(scene.modals[-1]).__name__ == "PromotionDialog"
    assert scene.view.dragged_square is None
    player.press(pygame.K_ESCAPE)
    assert not scene.modals and scene.selection is None
    assert scene.engine.history == []
    begin_drag(scene, "a7", player)
    target = point_of(scene.view, "a8")
    move_to(target)
    release_at(target)
    player.frames(1)
    player.press(pygame.K_2)
    assert scene.engine.history == ["a8=R+"]


@pytest.mark.ct("CT-126")
def test_tempo_esgota_com_o_dialogo_de_promocao_aberto_depois_do_arrasto(app):
    scene, player = game(app, fen=PROMOTION, time_control=TimeControl.BLITZ_5)
    begin_drag(scene, "a7", player)
    target = point_of(scene.view, "a8")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.modals
    assert not scene.is_frozen, "o relógio segue na promoção"
    fast_forward_clock(scene, Color.WHITE, 0.01)
    player.frames(2)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert not scene.modals


@pytest.mark.ct("CT-126")
def test_clique_clique_depois_de_arrasto_que_voltou(app):
    scene, player = game(app)
    start = begin_drag(scene, "e2", player)
    move_to(start)
    release_at(start)
    player.frames(1)
    assert scene.selection == Square.from_name("e2"), "soltar na própria casa mantém a seleção"
    player.click_square(cell("e4"))
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-126")
def test_clique_em_peca_selecionada_desmarca_so_ao_soltar_e_arrastar_nao_desmarca(app):
    scene, player = game(app)
    player.click_square(cell("e2"))
    start = point_of(scene.view, "e2")
    press_at(start)
    player.frames(1)
    assert scene.selection == Square.from_name("e2"), "ao apertar ainda não desmarca"
    release_at(start)
    player.frames(1)
    assert scene.selection is None
    player.click_square(cell("e2"))
    start = point_of(scene.view, "e2")
    press_at(start)
    move_to((start[0] + 20, start[1]))
    target = point_of(scene.view, "e4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-126")
def test_trocar_de_peca_apertando_em_outra_e_ja_arrastar(app):
    scene, player = game(app)
    player.click_square(cell("e2"))
    start = point_of(scene.view, "d2")
    press_at(start)
    move_to((start[0] + 20, start[1]))
    target = point_of(scene.view, "d4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.engine.history == ["d4"]


@pytest.mark.ct("CT-126")
def test_segundo_aperto_sem_soltar_o_primeiro(app):
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    other = point_of(scene.view, "d2")
    press_at(other)
    player.frames(1)
    assert scene.view.dragged_square is None or scene.view.dragged_square == cell("d2")
    release_at(other)
    player.frames(1)
    assert scene.engine.history == []
    assert scene.view.dragged_square is None


@pytest.mark.ct("CT-126")
def test_arrasto_pelo_teclado_no_meio(app):
    """Enter com a peça no ar: o teclado age sobre o cursor e o arrasto termina."""
    scene, player = game(app)
    begin_drag(scene, "e2", player)
    player.press(pygame.K_RETURN)
    assert scene.view.dragged_square is None or scene.selection is not None
    target = point_of(scene.view, "e4")
    move_to(target)
    release_at(target)
    player.frames(1)
    assert scene.view.dragged_square is None
    assert len(scene.engine.history) <= 1


# Virar ---------------------------------------------------------------------------------------------


def settle_camera(player):
    while player.view.is_camera_moving:
        player.frames(1)


def assert_click_reaches(scene, player, name):
    """O ponto da tela sai da projeção, e o clique tem de voltar para a mesma casa."""
    assert scene.view.pick(point_of(scene.view, name)) == cell(name)


@pytest.mark.ct("CT-127")
def test_virar_em_giro_termina_de_frente_e_o_clique_continua_certo(app, monkeypatch):
    from xadrez.ui import cpu_player
    monkeypatch.setattr(cpu_player, "choose_move", lambda board, *_: legal_moves(board)[0])
    scene, player = open_game(app, mode=GameMode.TRAINING, opponent_kind="cpu", difficulty=Difficulty.EASY)
    settle_camera(player)
    for presses in (1, 2, 3):
        for _ in range(presses):
            post_key(pygame.K_f)
            player.frames(5)
        settle_camera(player)
        yaw = scene.view.camera.yaw % (2 * math.pi)
        expected = math.pi if presses % 2 else 0.0
        assert math.isclose(yaw, expected, abs_tol=1e-6) or math.isclose(yaw, expected + 2 * math.pi, abs_tol=1e-6)
        assert_click_reaches(scene, player, "e2")
        post_key(pygame.K_v)
        player.frames(1)
        settle_camera(player)


@pytest.mark.ct("CT-127")
@pytest.mark.xfail(strict=True, reason="QA11-11: em 2 jogadores, Virar durante o giro por turno não vira: a referência é a última virada, não para onde a câmera vai")
def test_virar_durante_o_giro_por_turno_vai_para_o_lado_oposto(app):
    scene, player = open_game(app, mode=GameMode.TRAINING, auto_rotate=True)
    player.click_square(cell("e2"))
    player.click_square(cell("e4"))
    while not scene.view.camera.is_moving:
        player.frames(1)
    # A câmera está indo para as pretas (yaw pi). Virar, agora, pede o lado oposto ao destino.
    player.press(pygame.K_f)
    settle_camera(player)
    yaw = scene.view.camera.yaw % (2 * math.pi)
    assert yaw == pytest.approx(0.0, abs=1e-6) or yaw == pytest.approx(2 * math.pi, abs=1e-6)


@pytest.mark.ct("CT-127")
def test_virar_durante_voo_da_peca_e_da_volta_a_vista_padrao(app):
    scene, player = game(app)
    player.click_square(cell("e2"))
    player.click_square(cell("e4"))
    player.press(pygame.K_f)
    player.press(pygame.K_v)
    player.press(pygame.K_f)
    player.settle()
    settle_camera(player)
    assert_click_reaches(scene, player, "e5")
    player.click_square(cell("e7"))
    player.click_square(cell("e5"))
    assert scene.engine.history == ["e4", "e5"]


@pytest.mark.ct("CT-127")
def test_setas_seguem_o_lado_depois_de_virar(app):
    scene, player = game(app, auto_rotate=False)
    settle_camera(player)
    player.press(pygame.K_UP)
    start = scene.cursor
    player.press(pygame.K_UP)
    assert scene.cursor == (start[0], start[1] + 1)
    player.press(pygame.K_f)
    settle_camera(player)
    before = scene.cursor
    player.press(pygame.K_UP)
    assert scene.cursor == (before[0], before[1] - 1), "de cima para baixo: 'para cima' agora é fileira menor"


@pytest.mark.ct("CT-127")
def test_virar_na_animacao_de_fim_nao_atrapalha_a_tela_de_fim(app):
    scene, player = game(app)
    player.play_all(SCHOLARS_MATE)
    assert scene.engine.result is not None
    player.press(pygame.K_f)
    player.press(pygame.K_v)
    player.seconds(3.2)
    assert isinstance(app.scene, GameOverScene)
    player.frames(20)


# Copiar --------------------------------------------------------------------------------------------


TAG = re.compile(r'^\[(\w+) "((?:[^"\\]|\\.)*)"\]$')


def parse_pgn(text):
    header, _, moves = text.partition("\n\n")
    tags = {}
    for line in header.split("\n"):
        match = TAG.match(line)
        assert match, f"cabeçalho inválido: {line!r}"
        tags[match.group(1)] = match.group(2).replace('\\"', '"').replace("\\\\", "\\")
    tokens = [token for token in moves.split() if not re.fullmatch(r"\d+\.+", token)]
    return tags, tokens


def assert_valid_pgn(text, engine):
    tags, tokens = parse_pgn(text)
    assert tags["White"] == engine.players[Color.WHITE].name
    assert tags["Black"] == engine.players[Color.BLACK].name
    result = tokens[-1]
    assert result == tags["Result"] and result in ("1-0", "0-1", "1/2-1/2", "*")
    board = Board.from_fen(tags.get("FEN", engine.start_fen))
    for san in tokens[:-1]:
        matches = [move for move in legal_moves(board) if move_to_san(board, move) == san]
        assert len(matches) == 1, f"{san} em {board.to_fen()}"
        board.apply(matches[0])
    assert board.to_fen() == engine.final_fen
    assert all(len(line) <= 80 for line in text.split("\n\n")[1].split("\n"))


@pytest.fixture
def copied(monkeypatch):
    texts = []
    monkeypatch.setattr(clipboard, "copy_text", lambda text: texts.append(text) or True)
    return texts


@pytest.mark.ct("CT-128")
def test_copiar_sem_lances(app, copied):
    scene, player = game(app)
    player.press(pygame.K_c)
    assert_valid_pgn(copied[-1], scene.engine)
    assert parse_pgn(copied[-1])[1] == ["*"]


@pytest.mark.ct("CT-128")
@pytest.mark.parametrize("names", [
    ('Ana "A"', "Bia [B]"), ("a\\b", 'c\\"d'), ("]", "["), ('"]', '[x "y"]'), ("%", ";"), ("{", "}"),
    ("João", "Çã"),
])
def test_nomes_dificeis_ainda_dao_pgn_valido(app, copied, names):
    scene, player = game(app, names=names)
    player.play_all(SCHOLARS_MATE)
    player.seconds(3.2)
    assert isinstance(app.scene, GameOverScene)
    player.press(pygame.K_c)
    assert_valid_pgn(copied[-1], scene.engine)
    assert parse_pgn(copied[-1])[0]["Result"] == "1-0"


@pytest.mark.ct("CT-128")
def test_copiar_depois_da_revanche_troca_os_nomes_nos_cabecalhos(app, copied):
    scene, player = game(app, names=("Ana", "Bia"))
    player.play_all(SCHOLARS_MATE)
    player.seconds(3.2)
    app.scene.rematch()
    player.frames(1)
    player.settle()
    player.press(pygame.K_c)
    tags, _ = parse_pgn(copied[-1])
    assert (tags["White"], tags["Black"]) == ("Bia", "Ana")
    assert tags["Result"] == "*"


@pytest.mark.ct("CT-128")
@pytest.mark.parametrize("error", [pygame.error("sem janela"), NotImplementedError(), OSError("bloqueada"), ValueError("texto")])
def test_area_de_transferencia_falhando_vira_aviso(app, monkeypatch, error):
    def fails(*_):
        raise error

    monkeypatch.setattr(pygame.scrap, "get_init", lambda: True)
    monkeypatch.setattr(pygame.scrap, "put", fails)
    scene, player = game(app)
    player.press(pygame.K_c)
    assert scene.notices.text == clipboard.COPY_FAILED_MESSAGE


@pytest.mark.ct("CT-128")
def test_copiar_varias_vezes_e_durante_o_voo(app, copied):
    scene, player = game(app)
    player.click_square(cell("e2"))
    player.click_square(cell("e4"))
    for _ in range(5):
        post_key(pygame.K_c)
    player.frames(1)
    assert len(copied) == 5
    assert "1. e4 *" in copied[-1]


@pytest.mark.ct("CT-128")
def test_copiar_na_vez_da_cpu_nao_toca_na_busca(app, copied, monkeypatch):
    from xadrez.ui import cpu_player
    import time as _time

    def stuck(board, difficulty, rng, should_stop, max_seconds):
        while not should_stop():
            _time.sleep(0.0005)
        return legal_moves(board)[0]

    monkeypatch.setattr(cpu_player, "choose_move", stuck)
    scene, player = open_game(app, mode=GameMode.MATCH, opponent_kind="cpu", difficulty=Difficulty.HARDCORE, human_color=Color.BLACK)
    player.press(pygame.K_c)
    assert scene.cpu.is_thinking
    assert_valid_pgn(copied[-1], scene.engine)
    assert parse_pgn(copied[-1])[0]["White"].startswith("CPU")
    scene.shutdown()


# Clique duplo entre telas --------------------------------------------------------------------------


def double(player, position):
    """O 2º clique de um clique duplo, com menos de 0,25 s de intervalo."""
    post_click(position)
    player.frames(1)


@pytest.mark.ct("CT-129")
def test_menu_para_partida_e_partida_para_menu(app):
    player = Autoplayer(app)
    menu = app.scene
    position = menu.start_button.rect.center
    post_click(position)
    player.frames(1)
    game_scene = app.scene
    assert isinstance(game_scene, GameScene)
    double(player, position)
    assert app.scene is game_scene
    assert game_scene.selection is None and not game_scene.modals


@pytest.mark.ct("CT-129")
def test_entrar_no_login_nao_aciona_o_que_esta_embaixo_no_menu():
    application = make_app(require_login=True)
    player = Autoplayer(application)
    scene = application.scene
    position = scene.guest_button.rect.center
    post_click(position)
    player.frames(1)
    menu = application.scene
    assert isinstance(menu, MenuScene)
    state = (menu.opponent_selector.index, menu.mode_selector.index, menu.tab_bar.index, menu.time_selector.index)
    double(player, position)
    assert application.scene is menu
    assert state == (menu.opponent_selector.index, menu.mode_selector.index, menu.tab_bar.index, menu.time_selector.index)


@pytest.mark.ct("CT-129")
def test_sair_da_conta_nao_aciona_o_login():
    application = make_app(require_login=True)
    player = Autoplayer(application)
    application.account = "Ana"
    application.scene.next_scene = application.menu_scene()
    player.frames(1)
    menu = application.scene
    position = menu.account_button.rect.center
    post_click(position)
    player.frames(1)
    login = application.scene
    assert isinstance(login, LoginScene)
    double(player, position)
    assert application.scene is login


@pytest.mark.ct("CT-129")
def test_criar_sala_e_cancelar_com_clique_duplo(host_app, network):
    player = Autoplayer(host_app)
    menu = host_app.scene
    player.click_segment(menu.opponent_selector, NET_SEGMENT)
    position = menu.create_room_button.rect.center
    post_click(position)
    player.frames(1)
    lobby = host_app.scene
    assert isinstance(lobby, LobbyScene)
    double(player, position)
    assert host_app.scene is lobby
    assert lobby.is_connecting and len(network.opened) == 1
    cancel = lobby.cancel_button.rect.center
    post_click(cancel)
    player.frames(1)
    back = host_app.scene
    assert isinstance(back, MenuScene)
    double(player, cancel)
    assert host_app.scene is back
    assert len(network.opened) == 1


@pytest.mark.ct("CT-129")
def test_fim_de_jogo_para_menu_e_para_revanche(app):
    scene, player = game(app)
    player.play_all(SCHOLARS_MATE)
    player.seconds(3.2)
    over = app.scene
    assert isinstance(over, GameOverScene)
    position = over.rematch_button.rect.center
    post_click(position)
    player.frames(1)
    second = app.scene
    assert isinstance(second, GameScene)
    double(player, position)
    assert app.scene is second and second.selection is None
    assert second.engine.players[Color.WHITE].name == "Bia", "uma revanche só"


@pytest.mark.ct("CT-129")
def test_abrir_folha_do_historico_com_clique_duplo_nao_abre_outra(monkeypatch):
    from xadrez.data import HistoryStore, MatchRecord
    application = make_app()
    application.account = "Ana"
    store = HistoryStore("Ana")
    for index in range(3):
        store.add(MatchRecord(f"2026-01-0{index + 1}T10:00:00", f"R{index}", "local", None, "Brancas", "vitoria", "Xeque-mate", 3, 1.0, "Blitz 5", "Partida", "1. e4 *\n", "8/8 w"))
    application.scene.next_scene = application.menu_scene()
    player = Autoplayer(application)
    player.frames(1)
    menu = application.scene
    player.click_segment(menu.tab_bar, 1)
    row = menu.history.list.row_rect(1).center
    post_click(row)
    player.frames(1)
    first = menu.history.opened
    assert first is menu.history.list.records[1]
    double(player, row)
    assert menu.history.opened is first
