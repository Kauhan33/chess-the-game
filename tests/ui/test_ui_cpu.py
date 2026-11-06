"""Contra a CPU: partida por eventos, thread fora do quadro, cancelamento e falha da busca (RF18, RNF09, CT-91, CT-92)."""
import math
import sys
import threading
import time

import pygame
import pytest
from ui_helpers import (
    cell,
    click,
    hud_button,
    move_mouse_off_board,
    new_rng,
    open_cpu_game,
    play_random_move,
    resign_by_buttons,
    start_cpu_game,
    wait_for_cpu,
)

from xadrez.core import Board, Color, Difficulty, EndReason, GameState, TimeControl, legal_moves
from xadrez.ui import CpuPlayer, GameOverScene, GameScene, MatchOptions, MenuScene
from xadrez.ui import cpu_player as cpu_module
from xadrez.ui.autoplay import click_point, post_click, post_mouse_move
from xadrez.ui.cpu_player import SEARCH_SWITCH_INTERVAL, THREAD_NAME, search_budget
from xadrez.ui.game_scene import CPU_FAILURE_NOTICE, CPU_TURN_NOTICE
from xadrez.ui.hud import STATUS_THINKING
from xadrez.ui.match import OPPONENT_CPU

BACK_RANK_FOR_BLACK = "4r1k1/8/8/8/8/8/P4PPP/6K1 w - - 0 1"
ONLY_MOVE_THEN_MATE = "k7/7R/1K6/8/8/8/8/8 b - - 0 1"
PAWN_ABOUT_TO_PROMOTE = "4k3/8/8/8/8/8/p7/4K3 b - - 0 1"
HANGING_QUEEN = "r3k3/8/8/8/8/8/8/Q3K3 b - - 0 1"
ROUND_SECONDS = 0.2


def cpu_threads():
    return [thread for thread in threading.enumerate() if thread.name == THREAD_NAME]


@pytest.fixture
def short_search(monkeypatch):
    """O Hardcore pensa 4 s por lance: nos testes de fluxo, a mesma busca de verdade, com menos tempo."""
    monkeypatch.setattr(cpu_module, "search_budget", lambda remaining, increment: ROUND_SECONDS)


@pytest.fixture
def stuck_search(monkeypatch):
    """Busca que só termina quando mandam parar, para testar o cancelamento sem depender de tempo."""
    def choose(board, difficulty, rng, should_stop, max_seconds):
        while not should_stop():
            time.sleep(0.0005)
        return legal_moves(board)[0]

    monkeypatch.setattr(cpu_module, "choose_move", choose)


def wait_thread_started():
    deadline = time.monotonic() + 10.0
    while not cpu_threads():
        assert time.monotonic() < deadline
        time.sleep(0.001)


# Partida inteira ----------------------------------------------------------------------------------


@pytest.mark.ct("CT-91")
@pytest.mark.parametrize("level", list(Difficulty))
def test_partida_do_menu_ate_a_tela_de_fim_com_cada_nivel(app, player, short_search, level):
    menu = app.scene
    player.click_segment(menu.opponent_selector, 1)
    player.click_segment(menu.difficulty_selector, list(Difficulty).index(level))
    player.click_segment(menu.color_selector, 0)
    player.click_widget(menu.start_button)
    scene = app.scene
    assert isinstance(scene, GameScene)
    assert scene.cpu.difficulty is level
    assert scene.engine.players[Color.BLACK].name == f"CPU ({level.label})"
    rng = new_rng()
    for _ in range(3):
        play_random_move(player, scene, rng)
        wait_for_cpu(app, scene)
        player.settle()
        if scene.engine.result is not None:
            break
    assert len(scene.engine.history) >= 2
    if scene.engine.result is None:
        resign_by_buttons(player, scene)
    player.seconds(3.0)
    assert isinstance(app.scene, GameOverScene)
    assert scene.engine.result is not None


@pytest.mark.ct("CT-91")
@pytest.mark.parametrize("level", [Difficulty.MEDIUM, Difficulty.HARD, Difficulty.HARDCORE])
def test_cpu_da_mate_e_a_tela_de_fim_mostra(app, short_search, level):
    scene, player = start_cpu_game(app, level, fen=BACK_RANK_FOR_BLACK, auto_rotate=False)
    player.play("a2a3")
    wait_for_cpu(app, scene)
    player.settle()
    assert scene.engine.result.reason is EndReason.CHECKMATE
    assert scene.engine.result.winner is Color.BLACK
    player.seconds(3.0)
    end = app.scene
    assert isinstance(end, GameOverScene)
    assert end._headline() == f"CPU ({level.label}) venceu"


@pytest.mark.ct("CT-91")
@pytest.mark.parametrize("level", list(Difficulty))
def test_jogador_da_mate_na_cpu(app, level):
    scene, player = start_cpu_game(app, level, fen=ONLY_MOVE_THEN_MATE, auto_rotate=False)
    wait_for_cpu(app, scene)
    player.settle()
    assert scene.engine.history == ["Kb8"], "as Pretas começam nesta posição, com um lance só"
    player.play("h7h8")
    assert scene.engine.result.reason is EndReason.CHECKMATE
    player.seconds(3.0)
    assert isinstance(app.scene, GameOverScene)
    assert scene.engine.result.winner is Color.WHITE
    assert not cpu_threads()


@pytest.mark.ct("CT-91")
def test_cpu_promove_sem_abrir_dialogo(app):
    scene, player = open_cpu_game(app, Difficulty.HARD, Color.WHITE, fen=PAWN_ABOUT_TO_PROMOTE)
    wait_for_cpu(app, scene)
    assert scene.engine.history[0].startswith("a1=")
    assert scene.modals == []
    assert scene.view.is_flying
    assert scene.view._waiting_spawn is not None, "a promoção da CPU anima como a do jogador"


@pytest.mark.ct("CT-91")
def test_jogada_da_cpu_anima_a_captura(app):
    scene, player = open_cpu_game(app, Difficulty.HARD, Color.WHITE, fen=HANGING_QUEEN)
    wait_for_cpu(app, scene)
    assert scene.engine.history[0] == "Rxa1+"
    assert scene.view.is_flying
    assert scene.view._waiting_capture is not None


@pytest.mark.ct("CT-91")
def test_jogada_da_cpu_anima_o_roque(app, monkeypatch):
    fen = "r3k2r/8/8/8/8/8/8/4K3 b kq - 0 1"
    def castle(board, difficulty, rng, should_stop, max_seconds):
        return next(move for move in legal_moves(board) if move.is_castling)

    monkeypatch.setattr(cpu_module, "choose_move", castle)
    scene, player = open_cpu_game(app, Difficulty.HARD, Color.WHITE, fen=fen)
    wait_for_cpu(app, scene)
    assert scene.engine.history[0].startswith("O-O")
    assert len(scene.view._flights) == 2, "o rei e a torre voam"


@pytest.mark.ct("CT-91")
def test_cpu_de_brancas_joga_primeiro_e_a_camera_fica_do_lado_do_jogador(app):
    scene, player = start_cpu_game(app, Difficulty.EASY, human_color=Color.BLACK)
    assert scene.local_color is Color.BLACK
    assert scene.engine.players[Color.WHITE].name == "CPU (Easy)"
    assert scene.engine.players[Color.BLACK].name == "Jogador 1"
    assert math.isclose(abs(scene.view.camera.yaw) % (2 * math.pi), math.pi, abs_tol=1e-6)
    wait_for_cpu(app, scene)
    player.settle()
    assert len(scene.engine.history) == 1
    assert math.isclose(abs(scene.view.camera.yaw) % (2 * math.pi), math.pi, abs_tol=1e-6), "não há giro por turno"


@pytest.mark.ct("CT-91")
def test_giro_por_turno_nao_existe_contra_a_cpu(app):
    scene, player = start_cpu_game(app, Difficulty.EASY, auto_rotate=True)
    assert scene.auto_rotate is False
    assert all(button.label not in ("Giro ligado", "Giro desligado") for button in scene.hud.buttons)
    player.press(pygame.K_t)
    assert scene.auto_rotate is False


@pytest.mark.ct("CT-91")
def test_revanche_troca_as_cores_e_a_camera_acompanha(app):
    scene, player = start_cpu_game(app, Difficulty.EASY)
    resign_by_buttons(player, scene)
    player.seconds(1.5)
    over = app.scene
    assert isinstance(over, GameOverScene)
    assert over.engine.players[Color.BLACK].match_points == 1.0
    player.click_widget(over.rematch_button)
    second = app.scene
    assert second.local_color is Color.BLACK
    assert second.engine.players[Color.WHITE].name == "CPU (Easy)"
    assert second.engine.players[Color.WHITE].match_points == 1.0, "o placar da série segue com a CPU"
    assert second.cpu.is_thinking, "agora a CPU é quem começa"
    wait_for_cpu(app, second)
    player.settle()
    assert math.isclose(abs(second.view.camera.yaw) % (2 * math.pi), math.pi, abs_tol=1e-6)
    assert len(second.engine.history) == 1


@pytest.mark.ct("CT-91")
def test_sorteio_escolhe_uma_cor_e_o_menu_lembra_o_sorteio(app, player):
    menu = app.scene
    player.click_segment(menu.opponent_selector, 1)
    player.click_segment(menu.color_selector, 2)
    assert menu.color_selector.value is None
    player.click_widget(menu.start_button)
    scene = app.scene
    assert scene.local_color in (Color.WHITE, Color.BLACK)
    assert scene.options.human_color is None
    scene.shutdown()
    scene._go_to_menu()
    player.frames(1)
    assert isinstance(app.scene, MenuScene)
    assert app.scene.color_selector.value is None


def test_cpu_sem_menu_usa_a_cor_das_opcoes(app):
    options = MatchOptions(opponent_kind=OPPONENT_CPU, human_color=Color.BLACK, difficulty=Difficulty.HARD)
    engine = options.create_engine()
    assert engine.players[Color.WHITE].name == "CPU (Hard)"
    assert engine.players[Color.BLACK].name == "Jogador 1"
    assert options.create_engine(human_color=Color.WHITE).players[Color.WHITE].name == "Jogador 1"


# Sem bloquear a tela ------------------------------------------------------------------------------


@pytest.mark.ct("CT-92")
def test_cpu_pensando_nao_bloqueia_quadro_nem_entrada(app):
    scene, player = open_cpu_game(app, Difficulty.HARDCORE, time_control=TimeControl.UNLIMITED)
    assert scene.cpu.is_thinking
    fen = scene.engine.board.to_fen()
    assert cpu_threads()
    longest = 0.0
    for name in ("e2", "d4", "a7", "h1"):
        post_mouse_move(click_point(scene.view, cell(name)))
        started = time.perf_counter()
        app.step(1 / 60)
        longest = max(longest, time.perf_counter() - started)
        assert scene.cursor == cell(name), "o cursor responde no mesmo quadro"
    assert longest < 1.0, f"um quadro levou {longest:.3f} s"
    player.press(pygame.K_F3)
    assert scene.performance_panel.is_visible
    assert scene.cpu.is_thinking, "a busca segue durante tudo isso"
    assert scene.engine.board.to_fen() == fen, "o tabuleiro de verdade não é tocado pela busca"


@pytest.mark.ct("CT-92")
def test_hud_mostra_cpu_pensando(app):
    scene, player = open_cpu_game(app, Difficulty.HARDCORE, time_control=TimeControl.UNLIMITED)
    player.frames(2)
    assert scene.hud.thinking_color is Color.WHITE
    assert scene.hud.cards[Color.WHITE].info.status == STATUS_THINKING
    assert "pensando" in scene.notices.text


@pytest.mark.ct("CT-92")
def test_clique_na_vez_da_cpu_avisa_sem_mudar_nada(app):
    scene, player = open_cpu_game(app, Difficulty.HARDCORE, time_control=TimeControl.UNLIMITED)
    fen = scene.engine.board.to_fen()
    click(player, "e7")
    assert scene.selection is None
    assert scene.notices.text == CPU_TURN_NOTICE
    assert scene.engine.board.to_fen() == fen
    player.press(pygame.K_UP)
    player.press(pygame.K_RETURN)
    assert scene.selection is None


@pytest.mark.ct("CT-92")
def test_busca_recebe_uma_copia_do_tabuleiro(app, monkeypatch):
    seen = []
    original = cpu_module.choose_move

    def spy(board, difficulty, rng, should_stop, max_seconds):
        seen.append((board, max_seconds))
        return original(board, difficulty, rng, should_stop, max_seconds)

    monkeypatch.setattr(cpu_module, "choose_move", spy)
    scene, player = open_cpu_game(app, Difficulty.EASY, time_control=TimeControl.BLITZ_3_2)
    wait_for_cpu(app, scene)
    board, max_seconds = seen[0]
    assert board is not scene.engine.board
    assert max_seconds == pytest.approx(search_budget(180.0, 2.0), abs=0.2)


@pytest.mark.ct("CT-92")
@pytest.mark.parametrize("remaining, increment, expected", [
    (math.inf, 0.0, None), (math.inf, 5.0, None), (100.0, 0.0, 4.0), (180.0, 2.0, 8.7), (0.0, 0.0, 0.0), (10.0, 10.0, 5.0),
])
def test_tempo_de_busca_segue_o_relogio(remaining, increment, expected):
    budget = search_budget(remaining, increment)
    assert budget is None if expected is None else budget == pytest.approx(expected)


@pytest.mark.ct("CT-92")
def test_intervalo_de_troca_vale_durante_a_busca_e_volta_depois(app, stuck_search):
    original = sys.getswitchinterval()
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_thread_started()
    deadline = time.monotonic() + 10.0
    while sys.getswitchinterval() != pytest.approx(SEARCH_SWITCH_INTERVAL):
        assert time.monotonic() < deadline
        time.sleep(0.001)
    scene.cpu.cancel()
    assert sys.getswitchinterval() == original


@pytest.mark.ct("CT-92")
def test_intervalo_da_busca_fica_bem_abaixo_do_padrao_de_5_ms():
    """O padrão do Python derruba a tela com a CPU pensando. O efeito só se mede rodando; aqui fica o limite do valor."""
    assert SEARCH_SWITCH_INTERVAL <= 0.0005


@pytest.mark.ct("CT-92")
def test_intervalo_volta_ao_original_quando_a_busca_falha(monkeypatch):
    def broken(*_):
        raise RuntimeError("defeito de propósito")

    monkeypatch.setattr(cpu_module, "choose_move", broken)
    original = sys.getswitchinterval()
    cpu = CpuPlayer(Difficulty.HARD)
    cpu.start(Board.initial())
    cpu._job.thread.join(10.0)
    assert sys.getswitchinterval() == original
    assert cpu.poll(1.0) in legal_moves(Board.initial())
    assert isinstance(cpu.last_error, RuntimeError)


@pytest.mark.ct("CT-92")
def test_intervalo_so_volta_quando_a_ultima_busca_termina():
    guard = cpu_module._fast_switching
    original = sys.getswitchinterval()
    with guard:
        with guard:
            assert sys.getswitchinterval() == pytest.approx(SEARCH_SWITCH_INTERVAL)
        assert sys.getswitchinterval() == pytest.approx(SEARCH_SWITCH_INTERVAL), "ainda há uma busca viva"
    assert sys.getswitchinterval() == original


@pytest.mark.ct("CT-92")
def test_com_a_camera_em_movimento_a_busca_dorme_a_cada_consulta(monkeypatch):
    naps = []
    monkeypatch.setattr(cpu_module.time, "sleep", naps.append)
    job = cpu_module._SearchJob(Board.initial(), Difficulty.HARD, new_rng(), lambda: True, None)
    assert job._should_stop() is False
    assert job._should_stop() is False
    assert naps == [cpu_module._BUSY_NAP_SECONDS] * 2
    job.stop.set()
    assert job._should_stop() is True
    assert len(naps) == 2


@pytest.mark.ct("CT-92")
def test_cena_diz_a_busca_quando_ha_animacao(app, monkeypatch):
    seen = []
    def choose(board, difficulty, rng, should_stop, max_seconds):
        seen.append(should_stop)
        return legal_moves(board)[0]

    monkeypatch.setattr(cpu_module, "choose_move", choose)
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_for_cpu(app, scene)
    assert scene.view.is_flying and scene.view.is_animating
    player.settle()
    assert not scene.view.is_animating


@pytest.mark.ct("CT-92")
def test_espera_minima_visivel_em_easy_e_medium():
    cpu = CpuPlayer(Difficulty.EASY, new_rng())
    cpu.start(Board.initial())
    cpu._job.thread.join(10.0)
    assert cpu.poll(0.2) is None, "jogada instantânea parece defeito"
    assert cpu.poll(0.2) is None
    assert cpu.is_thinking
    move = cpu.poll(0.2)
    assert move in legal_moves(Board.initial())
    assert not cpu.is_thinking
    assert cpu.poll(1.0) is None, "a jogada é entregue uma vez"


@pytest.mark.ct("CT-92")
def test_espera_minima_nao_faz_perder_no_relogio():
    cpu = CpuPlayer(Difficulty.EASY, new_rng())
    cpu.start(Board.initial(), remaining=1.0)
    assert cpu._job.minimum_wait == pytest.approx(0.04)
    cpu.cancel()


@pytest.mark.ct("CT-92")
def test_niveis_altos_nao_tem_espera_artificial():
    cpu = CpuPlayer(Difficulty.HARD, new_rng())
    cpu.start(Board.initial())
    assert cpu._job.minimum_wait == 0.0
    cpu.cancel()


# Cancelar -----------------------------------------------------------------------------------------


@pytest.mark.ct("CT-92")
def test_reiniciar_cancela_a_busca_e_descarta_a_jogada(app, stuck_search):
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_thread_started()
    old_thread = scene.cpu._job.thread
    player.press(pygame.K_r)
    player.click_widget(scene.modals[-1].buttons[0])
    assert not old_thread.is_alive(), "a busca antiga terminou no ato"
    assert scene.engine.history == []
    new_thread = scene.cpu._job.thread
    assert new_thread is not old_thread, "a CPU começa de novo, de Brancas"
    player.frames(30)
    assert scene.engine.history == [], "a jogada da busca cancelada não chega"


@pytest.mark.ct("CT-92")
def test_desistir_cancela_a_busca_sem_deixar_thread(app, stuck_search):
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_thread_started()
    resign_by_buttons(player, scene)
    assert not cpu_threads()
    assert scene.engine.result.reason is EndReason.RESIGNATION
    assert scene.engine.result.winner is Color.WHITE, "quem desiste é o jogador, mesmo na vez da CPU"


@pytest.mark.ct("CT-92")
def test_voltar_ao_menu_cancela_a_busca_sem_deixar_thread(app, stuck_search):
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_thread_started()
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[-1])
    player.click_widget(scene.modals[-1].buttons[0])
    assert isinstance(app.scene, MenuScene)
    assert not cpu_threads()


@pytest.mark.ct("CT-92")
def test_tempo_esgotado_com_a_cpu_pensando_cancela_a_busca(app, stuck_search):
    scene, player = open_cpu_game(app, Difficulty.HARD, time_control=TimeControl(0.005))
    wait_thread_started()
    player.seconds(0.5)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.engine.result.winner is Color.BLACK, "o tempo da CPU acabou"
    assert not cpu_threads()


@pytest.mark.ct("CT-92")
def test_fechar_o_jogo_nao_deixa_thread_nem_demora(app, stuck_search):
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_thread_started()
    started = time.perf_counter()
    app.scene.shutdown()
    assert time.perf_counter() - started < 1.0
    assert not cpu_threads()


@pytest.mark.ct("CT-92")
def test_cancelar_a_busca_real_do_hardcore_e_imediato(app):
    scene, player = open_cpu_game(app, Difficulty.HARDCORE, time_control=TimeControl.UNLIMITED)
    wait_thread_started()
    started = time.perf_counter()
    scene.cpu.cancel()
    assert time.perf_counter() - started < 1.0
    assert not [thread for thread in threading.enumerate() if thread.name == THREAD_NAME]


@pytest.mark.ct("CT-92")
def test_pausa_segura_a_jogada_e_congela_o_relogio(app):
    scene, player = open_cpu_game(app, Difficulty.EASY, time_control=TimeControl.BLITZ_5)
    player.press(pygame.K_p)
    assert scene.engine.state is GameState.PAUSED
    clock = scene.engine.clock.remaining(Color.WHITE)
    scene.cpu._job.thread.join(10.0)
    player.seconds(2.0)
    assert scene.engine.history == [], "a jogada espera a pausa acabar"
    assert scene.engine.clock.remaining(Color.WHITE) == clock
    player.press(pygame.K_p)
    wait_for_cpu(app, scene)
    assert len(scene.engine.history) == 1


# Falha --------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-92")
def test_excecao_na_thread_vira_jogada_legal_e_aviso(app, monkeypatch):
    def broken(*_):
        raise RuntimeError("defeito de propósito")

    monkeypatch.setattr(cpu_module, "choose_move", broken)
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_for_cpu(app, scene)
    assert len(scene.engine.history) == 1, "a partida não pode travar"
    assert scene.notices.text == CPU_FAILURE_NOTICE
    assert scene.engine.turn is Color.BLACK


@pytest.mark.ct("CT-92")
def test_jogada_recusada_pelo_motor_nao_trava_a_partida(app, monkeypatch):
    from xadrez.core import Move, Square
    def illegal(*_):
        return Move(Square.from_name("e2"), Square.from_name("e6"))

    monkeypatch.setattr(cpu_module, "choose_move", illegal)
    scene, player = open_cpu_game(app, Difficulty.HARD)
    wait_for_cpu(app, scene)
    assert len(scene.engine.history) == 1
    assert scene.notices.text == CPU_FAILURE_NOTICE


@pytest.mark.ct("CT-92")
def test_thread_que_nao_inicia_vira_jogada_legal(monkeypatch):
    def refuse_to_start(self):
        raise RuntimeError("sem threads")

    monkeypatch.setattr(threading.Thread, "start", refuse_to_start)
    cpu = CpuPlayer(Difficulty.EASY, new_rng())
    cpu.start(Board.initial())
    assert cpu.poll(1.0) in legal_moves(Board.initial())
    assert isinstance(cpu.last_error, RuntimeError)


def test_posicao_sem_jogada_legal_nao_derruba():
    cpu = CpuPlayer(Difficulty.EASY, new_rng())
    cpu.start(Board.from_fen("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1"))
    cpu._job.thread.join(10.0)
    assert cpu.poll(1.0) is None
    assert isinstance(cpu.last_error, ValueError)


def test_hud_desistir_fica_a_um_clique_e_pede_confirmacao(app):
    scene, player = start_cpu_game(app, Difficulty.EASY)
    player.click_widget(hud_button(scene, "Desistir"))
    assert scene.modals[-1].title == "Desistir da partida?"
    assert "Jogador 1" in scene.modals[-1].lines[0]
    assert scene.engine.result is None
    player.click_widget(scene.modals[-1].buttons[1])
    assert scene.modals == []
    assert scene.engine.state is GameState.IN_PROGRESS


def test_pausa_contra_a_cpu_nao_tem_proposta_de_empate(app):
    scene, player = start_cpu_game(app, Difficulty.EASY)
    player.press(pygame.K_p)
    labels = [button.label for button in scene.modals[-1].buttons]
    assert labels == ["Retomar", "Reiniciar partida", "Desistir", "Voltar ao menu"]


def test_vista_padrao_contra_a_cpu_volta_para_o_lado_do_jogador(app):
    scene, player = start_cpu_game(app, Difficulty.EASY, human_color=Color.BLACK)
    scene.view.camera.orbit_by(1.0, -0.2)
    player.press(pygame.K_v)
    player.settle()
    assert math.isclose(abs(scene.view.camera.yaw) % (2 * math.pi), math.pi, abs_tol=1e-6)


def test_macaco_de_cliques_na_vez_da_cpu(app, monkeypatch):
    scene, player = start_cpu_game(app, Difficulty.EASY, human_color=Color.BLACK)
    for name in ("a1", "h8", "e4"):
        post_click(click_point(scene.view, cell(name)))
    player.frames(2)
    move_mouse_off_board(player)
    wait_for_cpu(app, scene)
    player.settle()
    assert len(scene.engine.history) == 1
