"""Modo Partida não pode virar dica: compara a tela, pixel a pixel, entre posições em que só o xeque muda.

CT-100: em posições iguais, com e sem xeque, placas, faixa, planilha e tabuleiro saem iguais. O controle em Treinamento prova que o teste enxerga a diferença.
CT-101: a recusa é a mesma em todo motivo, sem tremor nem anel, e a peça sem jogada não avisa nada.
CT-102: só peça selecionada, cursor e último lance aparecem, em 2 jogadores, contra a CPU e em rede, inclusive no painel F4.
CT-103: a planilha esconde `+` e `#` até o fim, e o que sai da mesa no meio da partida também não pode entregar o xeque.
CT-104: Treinamento continua igual à versão 1.0: caminhos, capturas, ameaças, xeque, tremor e motivo da recusa.
"""
from __future__ import annotations

import pygame
import pytest
from test_ataque_v11_apoio import *  # noqa: F403

from xadrez.core import Color, Difficulty, EndReason, TimeControl
from xadrez.graphics import CellState
from xadrez.ui import clipboard
from xadrez.ui.game_scene import GENERIC_REFUSAL

# O peão preto muda de casa: em e4 ele bloqueia a coluna, em h5 deixa a torre dar xeque em e8.
WITH_PAWN_AWAY = "4k3/8/8/7p/8/8/8/R5K1 w - - 0 1"
WITH_PAWN_BLOCKING = "4k3/8/8/8/4p3/8/8/R5K1 w - - 0 1"
PINNED_KNIGHT = "4k3/8/8/8/4n3/8/8/4R1K1 b - - 0 1"
IN_CHECK = "4k3/8/8/8/8/8/8/R3R1K1 b - - 0 1"
PINNED_PAWN_ON_SEVENTH = "6nr/7P/8/8/8/8/8/k6K w - - 0 1"
FREE_PAWN_ON_SEVENTH = "6n1/7P/8/8/8/8/8/k6K w - - 0 1"
SCHOLARS_SETUP = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6"
ALLOWED_STATES = {CellState.NONE, CellState.LAST_MOVE, CellState.SELECTED, CellState.CURSOR}


def frames_after_rook_lift(fen, mode):
    """Joga Ta1-e1 em uma janela própria, com a mesma semente, e devolve a tela e a cena depois do pouso."""
    application = make_app(seed=5)
    scene, player = open_game(application, fen, mode=mode, time_control=TimeControl.RAPID_10)
    player.play("a1e1")
    # A mesma quantidade de quadros nos dois lados: partícula e relógio andam igual.
    player.frames(60)
    post_mouse_move((2, 2))
    player.frames(2)
    return application, scene, player, surface_array(application.screen)


def both_positions(mode):
    away = frames_after_rook_lift(WITH_PAWN_AWAY, mode)
    away_screen = away[3]
    away_scene = away[1]
    away_notice, away_status = away_scene.notices.text, away_scene.hud.checked_color
    away_tints = dict(away_scene.view.tints)
    away_markers = list(away_scene.view.markers)
    blocking = frames_after_rook_lift(WITH_PAWN_BLOCKING, mode)
    return (away_screen, away_scene, away_notice, away_status, away_tints, away_markers), blocking


@pytest.mark.ct("CT-100")
def test_tela_nao_conta_o_xeque_no_modo_partida():
    (away_screen, away_scene, away_notice, away_status, away_tints, away_markers), blocking = both_positions(GameMode.MATCH)
    application, scene, _, screen = blocking
    assert away_scene.engine.in_check and not scene.engine.in_check, "o cenário precisa ter xeque em um lado só"
    assert away_notice == scene.notices.text
    assert away_status is scene.hud.checked_color is None
    assert away_tints == scene.view.tints == {}
    assert away_markers == scene.view.markers
    panel = scene.hud.panel
    left = pygame.Rect(panel.x, 0, panel.width, panel.height)
    x0, y0, x1, y1 = left.left, left.top, left.right - 1, left.bottom - 1
    assert (away_screen[x0:x1, y0:y1] == screen[x0:x1, y0:y1]).all(), "o painel lateral mudou por causa do xeque"
    keep_out = [square_screen_box(scene.view, name) for name in ("e4", "h5")]
    assert changed_pixels_outside(away_screen, screen, keep_out) == 0, "o tabuleiro mudou fora das casas do peão"


@pytest.mark.ct("CT-100")
def test_controle_em_treinamento_a_tela_mostra_o_xeque():
    """Sem isto, o teste de cima poderia passar por não enxergar nada."""
    (away_screen, away_scene, away_notice, _, away_tints, _), blocking = both_positions(GameMode.TRAINING)
    _, scene, _, screen = blocking
    assert away_notice != scene.notices.text
    assert away_tints != {}
    keep_out = [square_screen_box(scene.view, name) for name in ("e4", "h5")]
    assert changed_pixels_outside(away_screen, screen, keep_out) > 500


@pytest.mark.ct("CT-100")
def test_selecionar_peca_com_e_sem_jogada_desenha_igual():
    """Cavalo cravado e cavalo livre: selecionar não pode dizer qual dos dois pode andar."""
    pinned_app = make_app(seed=5)
    pinned, pinned_player = open_game(pinned_app, PINNED_KNIGHT, mode=GameMode.MATCH)
    free_app = make_app(seed=5)
    free, free_player = open_game(free_app, "4k3/8/8/8/4n3/8/8/3R2K1 b - - 0 1", mode=GameMode.MATCH)
    for scene, player in ((pinned, pinned_player), (free, free_player)):
        player.click_square(cell("e4"))
        player.frames(30)
    assert pinned.targets == {} and free.targets != {}
    assert pinned.notices.text == free.notices.text
    assert pinned.selection == free.selection
    assert pinned.view.lifted_square == free.view.lifted_square
    assert pinned.view.markers == free.view.markers
    assert pinned.view.tints == free.view.tints == {}
    assert pinned.view.matrix.state_at(*cell("e4")) is free.view.matrix.state_at(*cell("e4")) is CellState.SELECTED


@pytest.mark.ct("CT-101")
@pytest.mark.parametrize("fen, origin, target, motive", [
    (PINNED_KNIGHT, "e4", "f6", "cravado"),
    (IN_CHECK, "e8", "e7", "rei atacado"),
    ("4k3/8/8/8/8/8/8/R3K3 w Q - 0 1", "a1", "a1", "mesma casa"),
    ("4k3/8/8/8/8/8/8/R3K3 w Q - 0 1", "a1", "b2", "geometria"),
    ("4k3/8/8/8/8/8/P7/R3K3 w Q - 0 1", "a1", "a3", "bloqueio"),
    ("r3k2r/8/8/8/8/5q2/8/R3K2R w KQkq - 0 1", "e1", "g1", "roque sob ataque"),
    ("4k3/8/8/8/8/8/P7/4K3 w - - 0 1", "a2", "b3", "peão sem captura"),
])
def test_recusa_nao_muda_conforme_o_motivo(app, fen, origin, target, motive):
    scene, player = open_game(app, fen, mode=GameMode.MATCH)
    player.click_square(cell(origin))
    player.click_square(cell(target))
    if origin == target:
        assert scene.selection is None
        assert scene.notices.text != GENERIC_REFUSAL, "clicar de novo só desmarca"
        return
    assert scene.notices.text == GENERIC_REFUSAL, motive
    assert scene.view.shake_square is None, "tremor seria mais um marcador"
    assert scene.engine.board.to_fen() == scene.engine.final_fen


@pytest.mark.ct("CT-101")
def test_peca_do_adversario_e_casa_vazia_recebem_a_mesma_recusa(app):
    scene, player = open_game(app, mode=GameMode.MATCH)
    for name in ("e7", "e4"):
        player.seconds(4.0)
        player.click_square(cell(name))
        assert scene.notices.text == GENERIC_REFUSAL
        assert scene.view.shake_square is None
        assert scene.selection is None


@pytest.mark.ct("CT-101")
def test_arrasto_recusado_e_igual_ao_clique_recusado(app):
    scene, player = open_game(app, PINNED_KNIGHT, mode=GameMode.MATCH)
    player.click_square(cell("e4"))
    start, end = point_of(scene.view, "e4"), point_of(scene.view, "f6")
    press_at(start)
    move_to((start[0] + 20, start[1]))
    move_to(end)
    release_at(end)
    player.frames(1)
    assert scene.notices.text == GENERIC_REFUSAL
    assert scene.view.shake_square is None


@pytest.mark.ct("CT-101")
def test_peao_cravado_na_setima_recusa_sem_abrir_a_promocao(app):
    """Cravado, o peão não pode promover. A recusa é a mesma, e o diálogo não abre."""
    scene, player = open_game(app, PINNED_PAWN_ON_SEVENTH, mode=GameMode.MATCH)
    player.click_square(cell("h7"))
    player.click_square(cell("g8"))
    assert not scene.modals
    assert scene.notices.text == GENERIC_REFUSAL
    assert not scene.engine.history


@pytest.mark.ct("CT-101")
def test_peao_livre_na_setima_abre_a_promocao_e_nao_avisa_nada(app):
    scene, player = open_game(app, FREE_PAWN_ON_SEVENTH, mode=GameMode.MATCH)
    player.click_square(cell("h7"))
    player.click_square(cell("g8"))
    assert len(scene.modals) == 1
    assert scene.notices.text != GENERIC_REFUSAL


def _assert_only_neutral(scene):
    view = scene.view
    for file in range(8):
        for rank in range(8):
            state = view.matrix.state_at(file, rank)
            assert state in ALLOWED_STATES, f"{state} em ({file}, {rank})"
    assert view.tints == {}
    selected = {tuple(scene.selection)} if scene.selection is not None else set()
    allowed_marker_cells = selected | ({scene.cursor} if scene.cursor is not None else set())
    assert {tuple(marker[:2]) for marker in view.markers} <= allowed_marker_cells
    assert scene.hud.checked_color is None


@pytest.mark.ct("CT-102")
def test_em_cada_quadro_de_uma_partida_com_xeques_so_ha_indicadores_neutros(app):
    scene, player = open_game(app, mode=GameMode.MATCH)
    moves = SCHOLARS_SETUP.split()
    for uci in moves:
        player.click_square(cell(uci[:2]))
        _assert_only_neutral(scene)
        player.click_square(cell(uci[2:4]))
        _assert_only_neutral(scene)
        player.settle()
        _assert_only_neutral(scene)
    player.click_square(cell("h5"))
    player.click_square(cell("f7"))
    # A partida acabou em mate: a partir daqui, o mate pode ser marcado.
    assert scene.engine.result.reason is EndReason.CHECKMATE


@pytest.mark.ct("CT-102")
def test_o_painel_f4_nao_conta_o_que_a_tela_esconde(app):
    scene, player = open_game(app, IN_CHECK, mode=GameMode.MATCH)
    player.press(pygame.K_F4)
    player.click_square(cell("e8"))
    states = {scene.view.matrix.state_at(file, rank) for file in range(8) for rank in range(8)}
    assert states <= ALLOWED_STATES
    assert CellState.CHECK not in states and CellState.PATH not in states


@pytest.mark.ct("CT-102")
def test_contra_a_cpu_tambem_nao_ha_dica_e_a_revanche_continua_em_partida(app, monkeypatch):
    from xadrez.ui import cpu_player
    monkeypatch.setattr(cpu_player, "search_budget", lambda remaining, increment: 0.01)
    scene, player = open_game(app, IN_CHECK, mode=GameMode.MATCH, opponent_kind="cpu", difficulty=Difficulty.EASY,
                              human_color=Color.BLACK)
    player.frames(1)
    _assert_only_neutral(scene)
    assert scene.notices.text.startswith("Vez de")
    player.press(pygame.K_F1)
    player.press(pygame.K_ESCAPE)
    _assert_only_neutral(scene)
    resign_button = next(button for button in scene.hud.buttons if button.label == "Desistir")
    player.click_widget(resign_button)
    player.click_widget(scene.modals[-1].buttons[0])
    player.seconds(1.2)
    assert isinstance(app.scene, GameOverScene)
    app.scene.rematch()
    player.frames(1)
    rematch = app.scene
    assert isinstance(rematch, GameScene) and rematch.hides_hints is True
    assert rematch.options.mode is GameMode.MATCH


@pytest.mark.ct("CT-102")
def test_em_rede_a_tela_em_modo_partida_nao_avisa_o_xeque(host_app, guest_app):
    host_player = Autoplayer(host_app)
    guest_player = Autoplayer(guest_app)
    host_player.click_segment(host_app.scene.mode_selector, 1)
    guest_player.click_segment(guest_app.scene.mode_selector, 1)
    table = connected_table(host_app, guest_app)
    table.play_all("e2e4 f7f6 d2d4 a7a6 d1h5")
    guest = table.guest
    assert guest.engine.in_check
    table.steps(5)
    _assert_only_neutral(guest)
    assert "Xeque" not in guest.notices.text
    assert guest.hud.cards[guest.local_color].info.status == "turn", "a etiqueta da placa diz só de quem é a vez"


@pytest.mark.ct("CT-103")
def test_planilha_sem_marca_ate_o_fim_e_com_marca_depois(app):
    scene, player = open_game(app, mode=GameMode.MATCH)
    rendered = []
    original = scene.hud.sheet._compose
    scene.hud.sheet._compose = lambda history, first: rendered.append(list(history)) or original(history, first)
    player.play_all("e2e4 f7f6 d2d4 g7g5")
    player.click_square(cell("d1"))
    player.click_square(cell("h5"))
    player.frames(2)
    # O mate é a última coisa da partida: a planilha completa só aparece com a partida encerrada.
    assert rendered[-1][-1] == "Qh5#"
    assert all("+" not in san and "#" not in san for sheet in rendered[:-1] for san in sheet)


@pytest.mark.ct("CT-103")
def test_xeque_comum_nao_aparece_na_planilha_do_modo_partida(app):
    scene, player = open_game(app, mode=GameMode.MATCH)
    rendered = []
    original = scene.hud.sheet._compose
    scene.hud.sheet._compose = lambda history, first: rendered.append(list(history)) or original(history, first)
    player.play_all("e2e4 f7f6 d2d4 a7a6 d1h5")
    player.frames(2)
    assert scene.engine.history[-1] == "Qh5+"
    assert rendered[-1][-1] == "Qh5"


@pytest.mark.ct("CT-103")
@pytest.mark.xfail(strict=True, reason="QA11-14: 'Copiar PGN' no meio da partida leva `+` e `#` para a área de transferência")
def test_copiar_pgn_no_meio_da_partida_nao_entrega_o_xeque(app, monkeypatch):
    copied = []
    monkeypatch.setattr(clipboard, "copy_text", lambda text: copied.append(text) or True)
    scene, player = open_game(app, mode=GameMode.MATCH)
    player.play_all("e2e4 f7f6 d2d4 a7a6 d1h5")
    assert scene.engine.in_check and scene.engine.result is None
    player.press(pygame.K_c)
    assert copied, "o atalho C precisa ter copiado"
    assert "+" not in copied[-1].split("\n\n", 1)[1], "o texto copiado diz que há xeque, e a tela escondeu"


@pytest.mark.ct("CT-104")
def test_treinamento_continua_mostrando_tudo(app):
    scene, player = open_game(app, IN_CHECK, mode=GameMode.TRAINING)
    assert scene.notices.text.startswith("Xeque!")
    assert scene.hud.checked_color is Color.BLACK
    assert scene.view.tints, "rei com tint de xeque"
    player.click_square(cell("e8"))
    assert scene.view.matrix.state_at(*cell("d8")) is CellState.PATH
    player.click_square(cell("e7"))
    assert scene.notices.text != GENERIC_REFUSAL
    assert scene.view.shake_square == cell("e7")


@pytest.mark.ct("CT-104")
def test_treinamento_avisa_a_peca_sem_jogada(app):
    scene, player = open_game(app, PINNED_KNIGHT, mode=GameMode.TRAINING)
    player.click_square(cell("e4"))
    assert scene.notices.text == "Essa peça não tem jogada válida agora."
