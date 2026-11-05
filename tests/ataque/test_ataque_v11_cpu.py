"""CPU em thread sob ataque: cada saída enquanto ela pensa, jogada atrasada, relógio, lances especiais e entrada fora de hora.

CT-105: pausar, reiniciar, desistir, menu, fechar e redimensionar com a CPU pensando: nenhuma jogada chega depois, e nenhuma thread sobra.
CT-106: tempo esgotado na busca, jogada atrasada e fim da partida não aplicam lance no tabuleiro errado.
CT-107: a CPU promove, faz roque e en passant, dá mate, abre a partida de brancas, e o relógio dela anda.
CT-108: limite de tempo: a busca nunca pode gastar mais do que resta no relógio.
CT-109: clique, arrasto e teclado na vez dela não mudam nada; exceção na busca e lance recusado mantêm a partida viva.
"""
from __future__ import annotations

import sys
import threading
import time

import pygame
import pytest
from test_ataque_v11_apoio import *  # noqa: F403

from xadrez.core import Color, Difficulty, EndReason, GameState, Move, Square, TimeControl, legal_moves
from xadrez.ui import cpu_player as cpu_module
from xadrez.ui import MenuScene
from xadrez.ui.cpu_player import SEARCH_SWITCH_INTERVAL, THREAD_NAME, search_budget
from xadrez.ui.game_scene import CPU_FAILURE_NOTICE, CPU_TURN_NOTICE

BLACK_CASTLES = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/4K3 b kq - 0 1"
BLACK_TAKES_EN_PASSANT = "4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1"
BLACK_PROMOTES = "4k3/8/8/8/8/8/p7/4K3 b - - 0 1"
BLACK_MATES = "4r1k1/8/8/8/8/8/5PPP/6K1 b - - 0 1"
CPU_IS_MATED = "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"
CPU_IS_STALEMATED = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
LONE_KING_LEFT = "4k3/8/8/8/8/8/P7/4K3 b - - 0 1"


def cpu_threads():
    return [thread for thread in threading.enumerate() if thread.name == THREAD_NAME]


def wait_thread_started(limit=10.0):
    deadline = time.monotonic() + limit
    while not cpu_threads():
        assert time.monotonic() < deadline
        time.sleep(0.001)


@pytest.fixture
def stuck_search(monkeypatch):
    """Busca que só termina quando mandam parar: qualquer jogada que apareça sem cancelamento é defeito."""
    returned = []

    def choose(board, difficulty, rng, should_stop, max_seconds):
        while not should_stop():
            time.sleep(0.0005)
        returned.append(legal_moves(board)[0])
        return returned[-1]

    monkeypatch.setattr(cpu_module, "choose_move", choose)
    return returned


def cpu_game(app, fen=None, level=Difficulty.HARDCORE, time_control=TimeControl.RAPID_10, human=Color.WHITE, mode=GameMode.TRAINING):
    return open_game(app, fen, time_control=time_control, mode=mode, opponent_kind="cpu", difficulty=level, human_color=human)


def thinking_game(app, stuck_search, level=Difficulty.HARDCORE, time_control=TimeControl.RAPID_10):
    """CPU de brancas com a thread já pensando."""
    scene, player = cpu_game(app, level=level, human=Color.BLACK, time_control=time_control)
    wait_thread_started()
    assert scene.cpu.is_thinking
    return scene, player


def step_for_real(app, seconds, frame=1 / 120):
    """Quadros em tempo real, curtos: o relógio do jogo e o da busca andam juntos."""
    end = time.monotonic() + seconds
    previous = time.monotonic()
    while time.monotonic() < end:
        time.sleep(frame)
        now = time.monotonic()
        app.step(now - previous)
        previous = now


# Saídas enquanto ela pensa -------------------------------------------------------------------------


@pytest.mark.ct("CT-105")
def test_pausar_congela_o_lance_e_o_relogio_e_retomar_entrega_uma_vez(app, stuck_search):
    scene, player = thinking_game(app, stuck_search)
    player.press(pygame.K_p)
    assert scene.is_frozen and scene.engine.state is GameState.PAUSED
    clock = scene.engine.clock.remaining(Color.WHITE)
    fen = scene.engine.board.to_fen()
    # Nem com a thread livre a jogada entra com a tela pausada.
    scene.cpu._job.stop.set()
    while cpu_threads():
        time.sleep(0.001)
    player.frames(30)
    assert scene.engine.board.to_fen() == fen
    assert scene.engine.clock.remaining(Color.WHITE) == clock
    player.press(pygame.K_p)
    player.frames(1)
    assert len(scene.engine.history) == 1
    player.settle()
    player.frames(30)
    assert len(scene.engine.history) == 1


@pytest.mark.ct("CT-105")
@pytest.mark.parametrize("exit_path", ["restart", "resign", "menu", "close", "flag"])
def test_cada_saida_cancela_a_busca_e_nada_chega_depois(app, stuck_search, exit_path):
    scene, player = thinking_game(app, stuck_search)
    engine = scene.engine
    if exit_path == "restart":
        scene.confirm_restart()
        player.frames(1)
        player.click_widget(scene.modals[-1].buttons[0])
        assert engine.history == []
    elif exit_path == "resign":
        scene._confirm_resign()
        player.frames(1)
        player.click_widget(scene.modals[-1].buttons[0])
        assert engine.result.reason is EndReason.RESIGNATION
    elif exit_path == "menu":
        scene._confirm_menu()
        player.frames(1)
        player.click_widget(scene.modals[-1].buttons[0])
        assert isinstance(app.scene, MenuScene)
    elif exit_path == "close":
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        player.frames(1)
        assert app.running is False
        app.scene.shutdown()
    else:
        fast_forward_clock(scene, Color.WHITE, 0.01)
        player.frames(2)
        assert engine.result.reason is EndReason.TIMEOUT
    if exit_path != "restart":
        assert stuck_search, "a busca precisa ter sido avisada para parar"
        assert not cpu_threads()
    player.frames(10)
    assert engine.history == [] or exit_path == "restart"
    assert len(engine.history) == 0


@pytest.mark.ct("CT-105")
def test_redimensionar_e_virar_com_a_cpu_pensando_nao_cancela_nem_atrasa(app, stuck_search):
    scene, player = thinking_game(app, stuck_search)
    for size in ((800, 600), (1920, 1080), (321, 240), (1280, 720)):
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
        player.frames(1)
        assert scene.cpu.is_thinking
    player.press(pygame.K_f)
    player.press(pygame.K_F4)
    player.press(pygame.K_F3)
    player.frames(3)
    assert scene.cpu.is_thinking and cpu_threads()


@pytest.mark.ct("CT-105")
def test_trocar_de_partida_mil_vezes_devolve_o_intervalo_de_thread(app, stuck_search):
    original = sys.getswitchinterval()
    scene, player = thinking_game(app, stuck_search)
    assert sys.getswitchinterval() == pytest.approx(SEARCH_SWITCH_INTERVAL)
    for _ in range(40):
        scene.restart()
        player.frames(1)
    scene.shutdown()
    assert not wait_threads_gone()
    assert sys.getswitchinterval() == pytest.approx(original)


@pytest.mark.ct("CT-105")
def test_excecao_na_busca_tambem_devolve_o_intervalo_de_thread(app, monkeypatch):
    original = sys.getswitchinterval()

    def broken(*_):
        raise RuntimeError("defeito de propósito")

    monkeypatch.setattr(cpu_module, "choose_move", broken)
    scene, player = cpu_game(app, BLACK_PROMOTES, Difficulty.EASY, human=Color.WHITE)
    for _ in range(600):
        if scene.engine.history:
            break
        time.sleep(0.001)
        player.frames(1)
    assert scene.engine.history, "a partida não pode travar quando a busca quebra"
    assert scene.notices.text == CPU_FAILURE_NOTICE
    assert sys.getswitchinterval() == pytest.approx(original)


# Jogada atrasada ------------------------------------------------------------------------------------


@pytest.mark.ct("CT-106")
def test_busca_cancelada_que_ainda_termina_nao_vira_jogada_da_partida_seguinte(app, monkeypatch):
    """A primeira busca ignora o cancelamento por um instante e devolve um lance de outra partida."""
    release = threading.Event()
    answers = iter(("a2a3", "h2h3"))

    def choose(board, difficulty, rng, should_stop, max_seconds):
        uci = next(answers)
        if uci == "a2a3":
            release.wait(5.0)
        return next(move for move in legal_moves(board) if move.uci == uci)

    monkeypatch.setattr(cpu_module, "_JOIN_SECONDS", 0.01)
    monkeypatch.setattr(cpu_module, "choose_move", choose)
    scene, player = cpu_game(app, human=Color.BLACK)
    wait_thread_started()
    scene.restart()
    release.set()
    deadline = time.monotonic() + 20.0
    while not scene.engine.history:
        assert time.monotonic() < deadline
        time.sleep(0.001)
        player.frames(1)
    assert scene.engine.history == ["h3"]


@pytest.mark.ct("CT-106")
def test_tempo_da_cpu_acaba_no_mesmo_quadro_em_que_a_busca_termina(app, monkeypatch):
    gate = threading.Event()

    def choose(board, difficulty, rng, should_stop, max_seconds):
        gate.wait(5.0)
        return legal_moves(board)[0]

    monkeypatch.setattr(cpu_module, "choose_move", choose)
    scene, player = cpu_game(app, human=Color.BLACK, level=Difficulty.HARDCORE)
    fast_forward_clock(scene, Color.WHITE, 0.001)
    gate.set()
    while cpu_threads():
        time.sleep(0.001)
    player.frames(1)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.engine.history == [], "a partida já acabou: a jogada pronta não entra"


@pytest.mark.ct("CT-106")
def test_cpu_sem_tempo_contra_rei_sozinho_empata(app, stuck_search):
    scene, player = cpu_game(app, "4k3/8/8/8/8/8/P7/4K3 b - - 0 1", human=Color.BLACK, time_control=TimeControl.BLITZ_5)
    # Aqui o humano é preto e joga, e a CPU fica com o peão. Primeiro o lance dele, depois o relógio dela.
    player.click_square(cell("e8"))
    player.click_square(cell("e7"))
    player.settle()
    wait_thread_started()
    fast_forward_clock(scene, Color.WHITE, 0.001)
    player.frames(2)
    assert scene.engine.result.winner is None
    assert scene.engine.result.reason is EndReason.TIMEOUT


@pytest.mark.ct("CT-106")
@pytest.mark.parametrize("fen, expected", [(CPU_IS_MATED, EndReason.CHECKMATE), (CPU_IS_STALEMATED, EndReason.STALEMATE)])
def test_partida_que_comeca_sem_lance_para_a_cpu_nao_abre_thread(app, fen, expected):
    scene, player = cpu_game(app, fen, human=Color.WHITE)
    assert not cpu_threads()
    assert scene.engine.result.reason is expected
    player.seconds(3.0)
    assert isinstance(app.scene, GameOverScene)


# Lances especiais e relógio -------------------------------------------------------------------------


def force_cpu_move(monkeypatch, uci):
    def choose(board, difficulty, rng, should_stop, max_seconds):
        return next(move for move in legal_moves(board) if move.uci == uci)

    monkeypatch.setattr(cpu_module, "choose_move", choose)


def wait_cpu_move(scene, player, ply=1, limit=20.0):
    deadline = time.monotonic() + limit
    while len(scene.engine.history) < ply:
        assert time.monotonic() < deadline, "a CPU não jogou"
        time.sleep(0.001)
        player.frames(1)


@pytest.mark.ct("CT-107")
@pytest.mark.parametrize("fen, uci, san, final_piece_at", [
    (BLACK_CASTLES, "e8g8", "O-O", "g8"),
    (BLACK_CASTLES, "e8c8", "O-O-O", "c8"),
    (BLACK_TAKES_EN_PASSANT, "e4d3", "exd3", "d3"),
    (BLACK_PROMOTES, "a2a1q", "a1=Q+", "a1"),
])
def test_lances_especiais_da_cpu_valem_e_animam(app, monkeypatch, fen, uci, san, final_piece_at):
    force_cpu_move(monkeypatch, uci)
    scene, player = cpu_game(app, fen, Difficulty.HARDCORE, human=Color.WHITE)
    wait_cpu_move(scene, player)
    assert scene.engine.history == [san]
    assert scene.view.is_flying
    player.settle()
    assert scene.engine.board.piece_at(Square.from_name(final_piece_at)) is not None
    assert scene.engine.turn is Color.WHITE


@pytest.mark.ct("CT-107")
def test_mate_real_da_cpu_vai_ate_a_tela_de_fim_e_grava_derrota(app, isolated_data_dir, monkeypatch):
    monkeypatch.setattr(cpu_module, "search_budget", lambda remaining, increment: 0.1)
    app.account = "Ana"
    scene, player = cpu_game(app, BLACK_MATES, Difficulty.MEDIUM, human=Color.WHITE)
    wait_cpu_move(scene, player)
    assert scene.engine.result is not None and scene.engine.result.reason is EndReason.CHECKMATE
    player.seconds(3.2)
    assert isinstance(app.scene, GameOverScene)
    from xadrez.data import HistoryStore
    record = HistoryStore("Ana").records()[0]
    assert record.outcome == "derrota"
    assert record.opponent == "CPU (Medium)"
    assert record.difficulty == "Medium"
    assert record.reason == EndReason.CHECKMATE.label
    assert record.color == Color.WHITE.label


@pytest.mark.ct("CT-107")
def test_relogio_da_cpu_anda_enquanto_ela_pensa_e_o_do_humano_nao(app, stuck_search):
    scene, player = thinking_game(app, stuck_search)
    clock = scene.engine.clock
    white, black = clock.remaining(Color.WHITE), clock.remaining(Color.BLACK)
    player.seconds(1.0)
    assert clock.remaining(Color.WHITE) == pytest.approx(white - 1.0, abs=0.05)
    assert clock.remaining(Color.BLACK) == black


@pytest.mark.ct("CT-107")
def test_revanche_com_cores_trocadas_faz_a_cpu_abrir(app, monkeypatch):
    force_cpu_move(monkeypatch, "e2e4")
    scene, player = cpu_game(app, level=Difficulty.HARDCORE, human=Color.WHITE)
    resign = next(button for button in scene.hud.buttons if button.label == "Desistir")
    player.click_widget(resign)
    player.click_widget(scene.modals[-1].buttons[0])
    player.seconds(1.2)
    assert isinstance(app.scene, GameOverScene)
    app.scene.rematch()
    player.frames(1)
    second = app.scene
    assert second.local_color is Color.BLACK
    wait_cpu_move(second, player)
    assert second.engine.history == ["e4"]
    assert second.engine.players[Color.WHITE].name.startswith("CPU")


# Limite de tempo ------------------------------------------------------------------------------------


@pytest.mark.ct("CT-108")
@pytest.mark.parametrize("remaining, increment", [(600.0, 0.0), (180.0, 2.0), (30.0, 2.0), (900.0, 10.0), (20.0, 10.0)])
def test_orcamento_cabe_no_relogio_em_situacao_normal(remaining, increment):
    assert search_budget(remaining, increment) < remaining


@pytest.mark.ct("CT-108")
@pytest.mark.xfail(strict=True, reason="QA11-05: search_budget passa do que resta no relógio em Blitz 3+2 e Clássica 15+10 com pouco tempo")
@pytest.mark.parametrize("remaining, increment", [(1.0, 2.0), (1.5, 2.0), (5.0, 10.0), (7.0, 10.0)])
def test_orcamento_nunca_passa_do_que_resta(remaining, increment):
    assert search_budget(remaining, increment) < remaining


@pytest.mark.ct("CT-108")
@pytest.mark.xfail(strict=True, reason="QA11-05: Hardcore perde no relógio com 1 s em Blitz 3+2, pensando 1,54 s")
def test_hardcore_com_pouco_tempo_e_incremento_nao_estoura_o_proprio_relogio(app):
    """Lance real, em tempo real: 1 s no relógio, com 2 s de incremento, em uma posição de meio-jogo."""
    fen = "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2QK2R b KQ - 0 8"
    scene, player = cpu_game(app, fen, Difficulty.HARDCORE, human=Color.WHITE, time_control=TimeControl.BLITZ_3_2)
    scene.cpu.cancel()
    fast_forward_clock(scene, Color.BLACK, 1.0)
    scene._start_cpu_turn()
    deadline = time.monotonic() + 4.0
    previous = time.monotonic()
    while time.monotonic() < deadline and scene.engine.result is None and not scene.engine.history:
        time.sleep(1 / 120)
        now = time.monotonic()
        app.step(now - previous)
        previous = now
    assert scene.engine.history, f"a CPU perdeu no tempo: {scene.engine.result}"


@pytest.mark.ct("CT-108")
def test_cpu_em_tempo_baixo_sem_incremento_joga_antes_de_acabar(app):
    fen = "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2QK2R b KQ - 0 8"
    scene, player = cpu_game(app, fen, Difficulty.HARDCORE, human=Color.WHITE, time_control=TimeControl.BLITZ_5)
    scene.cpu.cancel()
    fast_forward_clock(scene, Color.BLACK, 0.5)
    scene._start_cpu_turn()
    deadline = time.monotonic() + 3.0
    previous = time.monotonic()
    while time.monotonic() < deadline and scene.engine.result is None and not scene.engine.history:
        time.sleep(1 / 120)
        now = time.monotonic()
        app.step(now - previous)
        previous = now
    assert scene.engine.history, f"a CPU perdeu no tempo: {scene.engine.result}"


# Entrada fora de hora -------------------------------------------------------------------------------


@pytest.mark.ct("CT-109")
def test_clique_arrasto_e_teclado_na_vez_dela_nao_mudam_nada(app, stuck_search):
    scene, player = thinking_game(app, stuck_search)
    fen = scene.engine.board.to_fen()
    own = point_of(scene.view, "e7")
    other = point_of(scene.view, "e2")
    empty = point_of(scene.view, "e4")
    for position in (own, other, empty):
        post_click(position)
        player.frames(1)
        assert scene.selection is None
        assert scene.notices.text == CPU_TURN_NOTICE
    press_at(own)
    move_to((own[0] + 30, own[1] + 30))
    move_to(empty)
    release_at(empty)
    player.frames(1)
    assert scene.view.dragged_square is None and scene.selection is None
    for code in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN, pygame.K_LEFT, pygame.K_SPACE):
        player.press(code)
    assert scene.selection is None
    assert scene.engine.board.to_fen() == fen
    assert scene.cpu.is_thinking


@pytest.mark.ct("CT-109")
def test_rotacao_nao_existe_contra_a_cpu_nem_por_tecla(app, stuck_search):
    scene, player = thinking_game(app, stuck_search)
    label_before = scene._rotation_button.label
    player.press(pygame.K_t)
    assert scene.auto_rotate is False
    assert scene._rotation_button.label == label_before
    assert all(button.label != label_before for button in scene.hud.buttons)


@pytest.mark.ct("CT-109")
def test_motor_recusa_a_jogada_da_busca_e_a_partida_segue(app, monkeypatch):
    bad = Move(Square.from_name("a2"), Square.from_name("a7"))
    monkeypatch.setattr(cpu_module, "choose_move", lambda *_: bad)
    scene, player = cpu_game(app, BLACK_PROMOTES, Difficulty.HARDCORE, human=Color.WHITE)
    wait_cpu_move(scene, player)
    assert scene.notices.text == CPU_FAILURE_NOTICE
    assert scene.engine.history


@pytest.mark.ct("CT-109")
def test_primeiro_quadro_com_cpu_e_humano_de_pretas_nao_bloqueia(app, stuck_search):
    """Abrir a partida com a CPU pensando não pode custar mais que o trabalho da própria tela."""
    started = time.perf_counter()
    scene, player = thinking_game(app, stuck_search)
    player.frames(5)
    assert time.perf_counter() - started < 5.0
    assert scene.hud.thinking_color is Color.WHITE
    assert scene.hud.cards[Color.WHITE].info.status == "thinking"
    assert scene.notices.text.endswith("está pensando")


@pytest.mark.ct("CT-109")
@pytest.mark.xfail(strict=True, reason="QA11-02: dois Enter no mesmo quadro em 'Iniciar partida' abrem duas partidas, e a CPU da primeira segue pensando sem dono")
def test_enter_repetido_no_menu_abre_uma_partida_so(app, stuck_search):
    menu = app.scene
    player = Autoplayer(app)
    player.click_segment(menu.opponent_selector, 1)
    player.click_segment(menu.color_selector, 1)
    player.click_segment(menu.difficulty_selector, 3)
    created = []
    original = app.game_scene
    app.game_scene = lambda *args, **kwargs: created.append(original(*args, **kwargs)) or created[-1]
    menu.focus.focus(menu.start_button)
    post_key(pygame.K_RETURN)
    post_key(pygame.K_RETURN)
    player.frames(1)
    extra = [scene for scene in created if scene is not app.scene]
    for scene in extra:
        scene.shutdown()
    assert len(created) == 1, f"{len(created)} partidas abertas"


@pytest.mark.ct("CT-109")
def test_sem_conseguir_abrir_a_thread_a_partida_segue_com_lance_simples(app, monkeypatch):
    monkeypatch.setattr(cpu_module._SearchJob, "begin", lambda self: setattr(self, "error", RuntimeError("sem thread")))
    scene, player = cpu_game(app, BLACK_PROMOTES, Difficulty.HARDCORE, human=Color.WHITE)
    wait_cpu_move(scene, player)
    assert scene.notices.text == CPU_FAILURE_NOTICE
