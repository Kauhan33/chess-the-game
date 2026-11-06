"""Duas instâncias do jogo em rede, com sessões reais em 127.0.0.1, por eventos (RF19, CT-95).

Só há um display no teste: cada jogo é um `App` com a própria cena, e os dois avançam em turnos.
"""
import math
import time

import pygame
import pytest
from ui_helpers import FRAME_SECONDS, SCHOLARS_MATE, LoopbackNetwork, cell, click, drive, hud_button

from xadrez.core import Color, EndReason, GameState, TimeControl
from xadrez.data import HistoryStore
from xadrez.net import GameDecided, GameStart, MoveReceived, NetworkError, PeerLeft, PeerResigned
from xadrez.ui import App, GameOverScene, GameScene, LobbyScene, MenuScene
from xadrez.ui.autoplay import Autoplayer, post_text
from xadrez.ui.game_scene import PEER_TURN_NOTICE
from xadrez.ui.match import OPPONENT_NET
from xadrez.ui.net_link import ILLEGAL_MOVE_MESSAGE, LanNetwork, NetLink

NET_INDEX = 2
CREATE_THEN_MOVE = "e2e4 e7e5"


@pytest.fixture
def network():
    loopback = LoopbackNetwork()
    yield loopback
    loopback.close_all()


@pytest.fixture
def host_app(network):
    application = App(seed=1, network=network)
    pygame.event.clear()
    yield application
    application.scene.shutdown()


@pytest.fixture
def guest_app(network):
    application = App(seed=2, network=network)
    pygame.event.clear()
    yield application
    application.scene.shutdown()


class Table:
    """Os dois jogos conectados. Quem joga é sempre pelo mouse, no jogo de quem tem a vez."""

    def __init__(self, host_app, guest_app):
        self.host_app, self.guest_app = host_app, guest_app
        self.apps = (host_app, guest_app)
        self.host_player, self.guest_player = Autoplayer(host_app), Autoplayer(guest_app)

    @property
    def host(self):
        return self.host_app.scene

    @property
    def guest(self):
        return self.guest_app.scene

    def player_of_turn(self):
        return self.host_player if self.host.engine.turn is self.host.local_color else self.guest_player

    def settle(self):
        drive(self.apps, self._is_settled)

    def _is_settled(self):
        scenes = (self.host, self.guest)
        return all(isinstance(scene, GameScene) for scene in scenes) and all(
            not scene.view.is_flying and not scene.view.is_camera_moving and not scene.net.link.inbox for scene in scenes
        )

    def play(self, uci):
        ply = len(self.host.engine.history)
        player = self.player_of_turn()
        player.click_square(cell(uci[:2]))
        player.click_square(cell(uci[2:4]))
        host, guest = self.host, self.guest
        drive(self.apps, lambda: len(host.engine.history) == len(guest.engine.history) == ply + 1)
        if host.engine.result is None:
            self.settle()

    def play_all(self, moves):
        for uci in moves.split():
            self.play(uci)

    def run_until_both_over(self):
        drive(self.apps, lambda: isinstance(self.host, GameOverScene) and isinstance(self.guest, GameOverScene))

    def seconds(self, duration):
        for _ in range(round(duration / FRAME_SECONDS)):
            for app in self.apps:
                app.step(FRAME_SECONDS)


def open_room(app, time_control=None):
    player = Autoplayer(app)
    menu = app.scene
    player.click_segment(menu.opponent_selector, NET_INDEX)
    if time_control is not None:
        menu.time_selector.options.append(("Teste", time_control))
        menu.time_selector.select(len(menu.time_selector.options) - 1)
    player.click_widget(menu.create_room_button)
    assert isinstance(app.scene, LobbyScene)
    return app.scene


def join_room(app, code):
    player = Autoplayer(app)
    menu = app.scene
    player.click_segment(menu.opponent_selector, NET_INDEX)
    player.click_widget(menu.join_room_button)
    lobby = app.scene
    assert isinstance(lobby, LobbyScene)
    post_text(code)
    player.frames(1)
    player.press(pygame.K_RETURN)
    return lobby


@pytest.fixture
def table(host_app, guest_app):
    lobby = open_room(host_app)
    join_room(guest_app, lobby.code)
    match = Table(host_app, guest_app)
    match.settle()
    return match


def connect_raw(app, network, time_control=None):
    """Um jogo de um lado e, do outro, só a sessão: o teste manda o que quiser, inclusive o que uma tela não mandaria."""
    lobby = open_room(app, time_control)
    raw = network.client("Crua", lobby.code)
    raw.start()
    player = Autoplayer(app)
    deadline = time.monotonic() + 30.0
    while not isinstance(app.scene, GameScene):
        assert time.monotonic() < deadline
        player.frames(1)
    player.settle()
    return app.scene, player, raw


def wait_arrival(app, scene, condition):
    """Quadros de tempo zero: o relógio e as animações ficam parados até a mensagem chegar."""
    deadline = time.monotonic() + 30.0
    while not condition():
        assert time.monotonic() < deadline, "a mensagem não chegou"
        time.sleep(0.0005)
        app.step(0.0)


# Conectar -----------------------------------------------------------------------------------------


@pytest.mark.ct("CT-95")
def test_sala_do_menu_ate_a_partida_nos_dois_lados(table):
    host, guest = table.host, table.guest
    assert isinstance(host, GameScene) and isinstance(guest, GameScene)
    assert host.local_color is Color.WHITE and guest.local_color is Color.BLACK
    assert host.engine.players[Color.WHITE].name == guest.engine.players[Color.WHITE].name
    assert host.options.opponent_kind == OPPONENT_NET
    assert host.auto_rotate is False and guest.auto_rotate is False
    assert host.net.link.peer_name == guest.engine.players[Color.BLACK].name


@pytest.mark.ct("CT-95")
def test_cada_um_fica_do_proprio_lado_do_tabuleiro(table):
    assert table.host.view.camera.yaw % (2 * math.pi) == pytest.approx(0.0, abs=1e-6)
    assert table.guest.view.camera.yaw % (2 * math.pi) == pytest.approx(math.pi)


@pytest.mark.ct("CT-95")
def test_tempo_e_o_de_quem_criou_a_sala(host_app, guest_app):
    lobby = open_room(host_app, TimeControl.BLITZ_3_2)
    join_room(guest_app, lobby.code)
    match = Table(host_app, guest_app)
    match.settle()
    assert match.guest.engine.time_control == TimeControl.BLITZ_3_2
    assert match.host.engine.time_control == TimeControl.BLITZ_3_2


@pytest.mark.ct("CT-95")
def test_cada_jogador_escolhe_o_proprio_modo(host_app, guest_app):
    host_player = Autoplayer(host_app)
    host_player.click_segment(host_app.scene.mode_selector, 1)
    lobby = open_room(host_app)
    join_room(guest_app, lobby.code)
    match = Table(host_app, guest_app)
    match.settle()
    assert match.host.hides_hints is True
    assert match.guest.hides_hints is False


# Jogar --------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-95")
def test_partida_inteira_ate_o_mate_termina_com_o_mesmo_fen(table):
    table.play_all(SCHOLARS_MATE)
    host_engine, guest_engine = table.host.engine, table.guest.engine
    assert host_engine.final_fen == guest_engine.final_fen
    assert host_engine.history == guest_engine.history
    assert host_engine.result == guest_engine.result
    assert host_engine.result.reason is EndReason.CHECKMATE
    table.run_until_both_over()
    assert table.host.result.winner is Color.WHITE
    assert table.guest.result.winner is Color.WHITE


@pytest.mark.ct("CT-95")
def test_jogada_so_de_quem_tem_a_vez(table):
    guest = table.guest
    click(table.guest_player, "e7")
    assert guest.selection is None
    assert guest.notices.text == PEER_TURN_NOTICE
    table.play("e2e4")
    click(table.host_player, "d2")
    assert table.host.selection is None
    assert table.host.notices.text == PEER_TURN_NOTICE


@pytest.mark.ct("CT-95")
def test_en_passant_e_promocao_que_chegam_pela_rede_valem_e_animam(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    for white, black in (("a2a3", "d7d5"), ("a3a4", "d5d4"), ("e2e4", "d4e3"), ("a4a5", "e3d2"), ("e1e2", "d2c1q")):
        player.play(white)
        ply = len(scene.engine.history)
        raw.send_move(black, 0)
        wait_arrival(host_app, scene, lambda: len(scene.engine.history) == ply + 1)
        if black == "d2c1q":
            assert scene.view._waiting_spawn is not None, "a promoção do outro lado anima igual"
        player.settle()
    assert scene.engine.history[-1].startswith("dxc1=Q")
    assert scene.engine.history[5] == "dxe3"
    assert scene.engine.result is None
    raw.close()


@pytest.mark.ct("CT-95")
def test_promocao_daqui_sai_com_a_peca_escolhida(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    line = (("e2e4", "d7d5"), ("e4d5", "c7c6"), ("d5c6", "g8f6"), ("c6b7", "b8d7"))
    for white, black in line:
        player.play(white)
        ply = len(scene.engine.history)
        raw.send_move(black, 0)
        wait_arrival(host_app, scene, lambda: len(scene.engine.history) == ply + 1)
        player.settle()
    player.play("b7a8q")
    assert scene.engine.history[-1].startswith("bxa8=Q")
    received = []
    deadline = time.monotonic() + 30.0
    while "b7a8q" not in received:
        assert time.monotonic() < deadline
        received += [event.uci for event in raw.poll() if isinstance(event, MoveReceived)]
    raw.close()


@pytest.mark.ct("CT-95")
def test_jogada_que_chega_com_a_peca_no_ar_espera_o_pouso(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    click(player, "e2")
    click(player, "e4")
    assert scene.view.is_flying
    raw.send_move("e7e5", 0)
    wait_arrival(host_app, scene, lambda: bool(scene.net.link.inbox))
    assert scene.view.is_flying and scene.engine.history == ["e4"], "o voo não é cortado"
    player.settle()
    player.frames(1)
    assert scene.engine.history == ["e4", "e5"]
    player.settle()
    raw.close()


@pytest.mark.ct("CT-95")
def test_clock_ms_recebido_nao_decide_nada(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    before = scene.engine.clock.remaining(Color.BLACK)
    raw.send_move("e7e5", 1)
    wait_arrival(host_app, scene, lambda: len(scene.engine.history) == 2)
    assert scene.engine.result is None, "o outro lado disse que tem 1 ms: e daí"
    assert scene.engine.clock.remaining(Color.BLACK) == pytest.approx(before, abs=0.2)
    player.settle()
    raw.close()


@pytest.mark.ct("CT-95")
def test_jogada_ilegal_encerra_a_sala(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    player.play("e2e4")
    fen = scene.engine.final_fen
    raw.send_move("e7e4", 0)
    wait_arrival(host_app, scene, lambda: scene.engine.result is not None)
    assert scene.engine.final_fen == fen
    assert scene.engine.result.reason is EndReason.ABANDONMENT
    assert scene.engine.result.winner is Color.WHITE
    assert scene.notices.text == ILLEGAL_MOVE_MESSAGE
    assert scene.net.link.peer_is_gone
    deadline = time.monotonic() + 30.0
    events = []
    while not any(isinstance(event, (PeerLeft, NetworkError)) for event in events):
        assert time.monotonic() < deadline
        events += raw.poll()
    raw.close()


@pytest.mark.ct("CT-95")
def test_jogada_fora_da_vez_tambem_encerra_a_sala(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    raw.send_move("e2e4", 0)
    wait_arrival(host_app, scene, lambda: scene.engine.result is not None)
    assert scene.engine.history == [], "peça de quem está na tela, movida pelo outro lado"
    assert scene.engine.result.reason is EndReason.ABANDONMENT
    raw.close()


@pytest.mark.ct("CT-95")
def test_revanche_pedida_no_meio_da_partida_e_ignorada(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    raw.send_rematch()
    player.seconds(0.3)
    wait_arrival(host_app, scene, lambda: not scene.net.link.inbox)
    assert scene.net.link.peer_wants_rematch is False
    assert scene.engine.result is None
    raw.close()


# Queda --------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-95")
def test_queda_de_conexao_vira_vitoria_por_abandono_com_aviso(table):
    table.play("e2e4")
    table.guest.net.link.session.close()
    host = table.host
    drive([table.host_app], lambda: host.engine.result is not None)
    assert host.engine.final_fen == table.guest.engine.final_fen
    assert host.engine.result.reason is EndReason.ABANDONMENT
    assert host.engine.result.winner is Color.WHITE
    assert "vitória" in host.notices.text
    drive([table.host_app], lambda: isinstance(table.host_app.scene, GameOverScene))
    over = table.host_app.scene
    assert over.rematch_button.is_enabled is False
    assert "saiu" in over.rematch_button.label


@pytest.mark.ct("CT-95")
def test_erro_de_rede_tambem_encerra_sem_travar(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    scene.net.link.inbox.append(NetworkError("Erro inesperado na conexão de rede."))
    player.frames(1)
    assert scene.engine.result.reason is EndReason.ABANDONMENT
    assert scene.notices.text == "Erro inesperado na conexão de rede."
    raw.close()


@pytest.mark.ct("CT-95")
def test_sair_da_sala_avisa_o_outro_e_conta_como_abandono(table):
    host = table.host
    table.host_player.press(pygame.K_p)
    assert [button.label for button in host.modals[-1].buttons][-1] == "Sair da sala"
    table.host_player.click_widget(host.modals[-1].buttons[-1])
    assert host.modals[-1].title == "Sair da sala?"
    table.host_player.click_widget(host.modals[-1].buttons[0])
    assert isinstance(table.host_app.scene, MenuScene)
    guest = table.guest
    drive([table.guest_app], lambda: guest.engine.result is not None)
    assert guest.engine.result.reason is EndReason.ABANDONMENT
    assert guest.engine.result.winner is Color.BLACK


@pytest.mark.ct("CT-95")
def test_sair_da_sala_entra_no_historico_como_derrota(host_app, network):
    host_app.account = "Jogador 1"
    scene, player, raw = connect_raw(host_app, network)
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[-1])
    player.click_widget(scene.modals[-1].buttons[0])
    saved = HistoryStore("Jogador 1").records()[0]
    assert saved.outcome == "derrota" and saved.opponent_kind == "rede" and saved.opponent == "Crua"
    raw.close()


# Relógio ------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-95")
def test_sem_pausa_de_relogio_em_rede(table):
    host = table.host
    table.host_player.press(pygame.K_p)
    assert host.engine.state is GameState.IN_PROGRESS
    assert not host.is_frozen
    assert host.modals[-1].freezes_clock is False
    labels = [button.label for button in host.modals[-1].buttons]
    assert labels == ["Voltar ao jogo", "Propor empate", "Desistir", "Sair da sala"]
    table.host_player.press(pygame.K_p)
    table.host_player.press(pygame.K_h)
    assert host.engine.state is GameState.IN_PROGRESS, "nem a ajuda para o relógio"
    table.host_player.press(pygame.K_h)


@pytest.mark.ct("CT-95")
def test_relogio_corre_com_a_sobreposicao_aberta_e_a_jogada_chega(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    player.press(pygame.K_p)
    before = scene.engine.clock.remaining(Color.BLACK)
    player.seconds(1.0)
    assert scene.engine.clock.remaining(Color.BLACK) < before
    raw.send_move("e7e5", 0)
    wait_arrival(host_app, scene, lambda: len(scene.engine.history) == 2)
    assert len(scene.modals) == 1, "a sobreposição continua aberta"
    player.settle()
    raw.close()


@pytest.mark.ct("CT-95")
def test_sem_reiniciar_em_rede(table):
    table.host_player.press(pygame.K_r)
    assert table.host.modals == []


def wait_decision(raw):
    deadline = time.monotonic() + 30.0
    events = []
    while not any(isinstance(event, GameDecided) for event in events):
        assert time.monotonic() < deadline
        events += raw.poll()
    return next(event for event in events if isinstance(event, GameDecided))


@pytest.mark.ct("CT-95")
def test_sala_que_esgota_o_proprio_tempo_perde_e_avisa_quem_entrou(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl(0.005))
    player.seconds(0.5)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.engine.result.winner is Color.BLACK
    decision = wait_decision(raw)
    assert decision.result == scene.engine.result
    assert decision.plies == 0
    raw.close()


@pytest.mark.ct("CT-95")
def test_sala_mede_o_relogio_de_quem_entrou_e_decide(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl(0.005))
    player.play("e2e4")
    player.seconds(4.0)
    assert scene.engine.clock.remaining(Color.BLACK) == 0.0
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.engine.result.winner is Color.WHITE
    decision = wait_decision(raw)
    assert decision.result == scene.engine.result
    assert decision.plies == 1
    raw.close()


@pytest.mark.ct("CT-95")
def test_jogada_que_chega_depois_do_fim_e_ignorada_pela_sala(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl(0.005))
    player.play("e2e4")
    player.seconds(4.0)
    assert scene.engine.result is not None
    fen = scene.engine.final_fen
    raw.send_move("e7e5", 0)
    player.seconds(0.2)
    assert scene.engine.final_fen == fen
    raw.close()


@pytest.mark.ct("CT-95")
def test_desistencia_com_tempo_sobrando_e_desistencia_mesmo(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    raw.send_resign()
    wait_arrival(host_app, scene, lambda: scene.engine.result is not None)
    assert scene.engine.result.reason is EndReason.RESIGNATION
    raw.close()


@pytest.mark.ct("CT-95")
def test_dois_lados_concordam_no_tempo_esgotado(host_app, guest_app):
    lobby = open_room(host_app, TimeControl(0.01))
    join_room(guest_app, lobby.code)
    match = Table(host_app, guest_app)
    match.settle()
    host, guest = match.host, match.guest
    drive(match.apps, lambda: host.engine.result is not None and guest.engine.result is not None)
    assert host.engine.result == guest.engine.result
    assert host.engine.result.reason is EndReason.TIMEOUT
    assert host.engine.result.winner is Color.BLACK


# Empate, desistência e revanche -------------------------------------------------------------------


def offer_draw(table):
    host = table.host
    table.host_player.press(pygame.K_p)
    table.host_player.click_widget(host.modals[-1].buttons[1])
    assert host.modals == []
    assert host.net.draw_answer_pending
    guest = table.guest
    drive(table.apps, lambda: bool(guest.modals))
    assert guest.modals[-1].title == "Proposta de empate"


@pytest.mark.ct("CT-95")
def test_empate_aceito_na_tela_do_outro_encerra_nos_dois(table):
    offer_draw(table)
    guest = table.guest
    table.guest_player.click_widget(guest.modals[-1].buttons[0])
    host = table.host
    drive(table.apps, lambda: host.engine.result is not None and guest.engine.result is not None)
    assert host.engine.result == guest.engine.result
    assert host.engine.result.reason is EndReason.AGREEMENT
    table.run_until_both_over()


@pytest.mark.ct("CT-95")
def test_empate_recusado_avisa_quem_propos(table):
    offer_draw(table)
    guest, host = table.guest, table.host
    table.guest_player.click_widget(guest.modals[-1].buttons[1])
    assert guest.modals == []
    drive(table.apps, lambda: "recusou" in host.notices.text)
    assert host.engine.result is None
    assert host.net.draw_answer_pending is False


@pytest.mark.ct("CT-95")
def test_esc_na_proposta_recusa(table):
    offer_draw(table)
    guest, host = table.guest, table.host
    table.guest_player.press(pygame.K_ESCAPE)
    drive(table.apps, lambda: "recusou" in host.notices.text)
    assert guest.engine.result is None


@pytest.mark.ct("CT-95")
def test_proposta_repetida_nao_empilha_nem_reenvia(table):
    offer_draw(table)
    host = table.host
    table.host_player.press(pygame.K_p)
    table.host_player.seconds(0.3)
    table.host_player.click_widget(host.modals[-1].buttons[1])
    assert "já foi enviada" in host.notices.text
    table.seconds(0.2)
    assert len(table.guest.modals) == 1


@pytest.mark.ct("CT-95")
def test_desistir_vale_nos_dois_lados(table):
    table.play("e2e4")
    guest = table.guest
    table.guest_player.click_widget(hud_button(guest, "Desistir"))
    assert "Jogador 1" in guest.modals[-1].lines[0] or guest.engine.players[Color.BLACK].name in guest.modals[-1].lines[0]
    table.guest_player.click_widget(guest.modals[-1].buttons[0])
    host = table.host
    assert guest.engine.result is None, "quem entrou pede: quem decide é a sala"
    drive(table.apps, lambda: host.engine.result is not None and guest.engine.result is not None)
    assert host.engine.result == guest.engine.result
    assert host.engine.result.reason is EndReason.RESIGNATION
    assert host.engine.result.winner is Color.WHITE
    table.run_until_both_over()


@pytest.mark.ct("CT-95")
def test_revanche_espera_o_outro_e_troca_as_cores(table):
    table.play_all(SCHOLARS_MATE)
    table.run_until_both_over()
    host_over, guest_over = table.host, table.guest
    assert host_over.rematch_button.label == "Pedir revanche"
    table.host_player.seconds(0.3)
    table.host_player.click_widget(host_over.rematch_button)
    assert "Aguardando" in host_over.rematch_button.label
    assert host_over.rematch_button.is_enabled is False
    drive(table.apps, lambda: "pediu revanche" in guest_over.rematch_button.label)
    table.guest_player.seconds(0.3)
    table.guest_player.click_widget(guest_over.rematch_button)
    drive(table.apps, lambda: isinstance(table.host, GameScene) and isinstance(table.guest, GameScene))
    table.settle()
    host, guest = table.host, table.guest
    assert host.local_color is Color.BLACK and guest.local_color is Color.WHITE
    assert host.engine.players[Color.BLACK].match_points == 1.0
    assert guest.engine.players[Color.WHITE].match_points == 0.0
    assert host.view.camera.yaw % (2 * math.pi) == pytest.approx(math.pi)
    assert guest.view.camera.yaw % (2 * math.pi) == pytest.approx(0.0, abs=1e-6)
    table.play(CREATE_THEN_MOVE.split()[0])
    assert host.engine.final_fen == guest.engine.final_fen


@pytest.mark.ct("CT-95")
def test_inicio_de_revanche_com_a_cor_errada_encerra_a_sala(table):
    table.play_all(SCHOLARS_MATE)
    table.run_until_both_over()
    host_over = table.host
    fen = host_over.engine.final_fen
    host_over.link.inbox.append(GameStart("A", "B", Color.WHITE, 0, 0))
    table.host_player.frames(1)
    assert isinstance(table.host_app.scene, GameOverScene), "quem era Brancas teria de virar Pretas"
    assert host_over.link.peer_is_gone
    assert host_over.engine.final_fen == fen


@pytest.mark.ct("CT-95")
def test_adversario_sai_na_tela_de_fim(table):
    table.play_all(SCHOLARS_MATE)
    table.run_until_both_over()
    host_over = table.host
    table.guest_player.seconds(0.3)
    table.guest_player.click_widget(table.guest.menu_button)
    assert isinstance(table.guest_app.scene, MenuScene)
    drive([table.host_app], lambda: host_over.link.peer_is_gone)
    assert host_over.rematch_button.is_enabled is False
    host_over.rematch()
    assert host_over.link.rematch_requested is False


@pytest.mark.ct("CT-95")
def test_historico_grava_a_partida_em_rede_nos_dois_lados(table):
    table.host_app.account = "Jogador 1"
    table.play_all(SCHOLARS_MATE)
    saved = HistoryStore("Jogador 1").records()[0]
    assert saved.opponent_kind == "rede"
    assert saved.outcome == "vitoria"
    assert saved.color == "Brancas"


def test_fechar_o_jogo_em_partida_avisa_o_outro(table):
    table.host.shutdown()
    guest = table.guest
    drive([table.guest_app], lambda: guest.engine.result is not None)
    assert guest.engine.result.winner is Color.BLACK


def test_rede_de_verdade_usa_as_sessoes_de_verdade():
    from xadrez.net import ClientSession, HostSession

    network = LanNetwork()
    assert isinstance(network.host("Jogador 1", TimeControl.BLITZ_5), HostSession)
    assert isinstance(network.client("Jogador 2", "ABCDEFG"), ClientSession)


def test_link_guarda_o_que_a_sessao_entrega():
    class FakeSession:
        def __init__(self):
            self.calls = []

        def poll(self):
            return [PeerResigned()]

        def send_bye(self):
            self.calls.append("bye")

        def close(self):
            self.calls.append("close")

    session = FakeSession()
    link = NetLink(session)
    link.pump()
    assert list(link.inbox) == [PeerResigned()]
    link.leave()
    assert session.calls == ["bye", "close"]
