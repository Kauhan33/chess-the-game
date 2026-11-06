"""Rede sob ataque: socket cru de atacante e duas telas reais, sempre em 127.0.0.1.

CT-110: o que chega pelo socket: jogada ilegal, fora da vez, formato errado, relógio falso e enxurrada.
CT-111: nome hostil chega pela rede e passa por HUD, faixa, sobreposição e tela de fim sem derrubar nem vazar.
CT-112: queda em cada estado: sala, promoção, sobreposição aberta, voo da peça e tela de fim.
CT-113: os dois lados terminam com o mesmo FEN e o mesmo resultado em cada fim de partida.
CT-114: regra do tempo em rede, de `docs/plans/notas-ui.md`: quem criou a sala decide.
CT-115: revanche e proposta de empate, cruzadas e sem resposta.
CT-116: entrada na sala: código errado, em minúsculas, com espaços, Enter repetido e reabertura logo depois de sair.
CT-117: thread e socket não sobram, por nenhum caminho de saída.
"""
from __future__ import annotations

import json
import socket
import threading
import time

import pygame
import pytest
from test_ataque_v11_apoio import *  # noqa: F403

from xadrez.core import Color, EndReason, GameResult, GameState, Square, TimeControl
from xadrez.net import PROTOCOL_VERSION, ClientSession, HostSession, NetTimings, GameStart, NetworkError
from xadrez.data import HistoryStore
from xadrez.net.room_code import encode_room_code
from xadrez.ui import MenuScene
from xadrez.ui.game_scene import DRAW_OFFER_AGAIN_NOTICE
from xadrez.ui.net_link import DECISION_WAIT_SECONDS, ILLEGAL_MOVE_MESSAGE, INVALID_RESULT_MESSAGE, NO_DECISION_MESSAGE

SCHOLARS_MATE = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
QUICK = NetTimings(tick=0.002)
HOSTILE_NAMES = [
    "W" * 16,
    "́" * 16,  # só acento combinante: largura zero
    "\U0001f600" * 16,  # emoji
    "ﷺ" * 16,  # um dos glifos mais largos do Unicode
    "مرحبا",  # árabe: direção do texto
    "한글한글",  # coreano
    "%s%d{0}\\n",
    '"]\n[Evil'.replace("\n", " "),  # tenta sair do cabeçalho do PGN
    "[White \"x\"]",
    "⠀" * 3,  # espaço em branco que `strip` não tira
    "..\\..\\x",
    "CON",
]


def raw_host(port=0):
    """Sala real, sem tela: para atacar quem entra."""
    host = HostSession("Crua", TimeControl.BLITZ_5, port=port, bind="127.0.0.1", timings=QUICK)
    host.start()
    return host


def hello_socket(port, name="Pretas", version=PROTOCOL_VERSION):
    connected = socket.create_connection(("127.0.0.1", port), timeout=10.0)
    connected.sendall(json.dumps({"type": "hello", "version": version, "name": name}).encode() + b"\n")
    return connected


# Socket cru --------------------------------------------------------------------------------------


@pytest.mark.ct("CT-110")
@pytest.mark.parametrize("uci, motive", [
    ("e2e5", "peão não anda 3"),
    ("e2e3", "peça da outra cor"),
    ("a1a1", "mesma casa"),
    ("e2e4q", "promoção em lance comum"),
])
def test_jogada_recusada_encerra_a_sala_com_vitoria_de_quem_ficou(host_app, network, uci, motive):
    """A sala é das brancas, e o cru é preto: o primeiro lance dele já é fora da vez."""
    scene, player, raw = connect_raw(host_app, network)
    player.play("e2e4")
    raw.send_move(uci, 0)
    wait_until(host_app, lambda: scene.engine.result is not None)
    assert scene.engine.result.reason is EndReason.ABANDONMENT
    assert scene.engine.result.winner is scene.local_color, motive
    assert scene.engine.history == ["e4"]
    raw.close()


@pytest.mark.ct("CT-110")
def test_lance_fora_da_vez_no_primeiro_turno_nao_acontece_no_tabuleiro(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    raw.send_move("e7e5", 0)
    wait_until(host_app, lambda: scene.engine.result is not None)
    assert scene.engine.history == []
    assert scene.engine.result.winner is scene.local_color
    raw.close()


@pytest.mark.ct("CT-110")
def test_dois_lances_colados_valem_na_ordem_e_a_animacao_de_um_nao_corta_a_do_outro(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    player.play("e2e4")
    raw.send_move("e7e5", 0)
    raw.send_move("d7d5", 0)
    wait_until(host_app, lambda: scene.engine.result is not None, dt=1 / 60)
    assert scene.engine.history == ["e4", "e5"], "o segundo lance é fora da vez e encerra a sala"
    raw.close()


@pytest.mark.ct("CT-110")
@pytest.mark.parametrize("line", [
    b'{"type":"move","uci":"e7e5","clock_ms":-1}\n',
    b'{"type":"move","uci":"e7e5","clock_ms":1e999}\n',
    b'{"type":"move","uci":"e7e5","clock_ms":99999999999999999999}\n',
    b'{"type":"move","uci":"e7e5","clock_ms":true}\n',
    b'{"type":"move","uci":"e7e5"}\n',
    b'{"type":"move","uci":"E7E5","clock_ms":0}\n',
    b'{"type":"move","uci":"e7e5","clock_ms":0,"extra":1}\n',
    b'{"type":"start","white":"a","black":"b","your_color":"white","minutes":0,"increment":0}\n',
    b'{"type":"hello","version":1,"name":"outra vez"}\n',
    b'{"type":"nada"}\n',
    b'[1,2,3]\n',
    b'NaN\n',
    b'\xff\xfe\n',
    b'[' * 3000 + b'\n',
    b'{"type":"draw_answer","accept":1}\n',
    b'{"type":"result","winner":"black","reason":"resignation","plies":1}\n',
])
def test_mensagem_invalida_encerra_sem_derrubar_e_sem_aplicar_nada(host_app, network, line):
    scene, player, raw = connect_raw(host_app, network)
    player.play("e2e4")
    # A partir daqui, o atacante escreve direto no socket da sessão cliente.
    raw._peer._socket.sendall(line)
    wait_until(host_app, lambda: scene.engine.result is not None or isinstance(host_app.scene, GameOverScene))
    assert scene.engine.history == ["e4"]
    assert scene.engine.result.winner is scene.local_color
    raw.close()


@pytest.mark.ct("CT-110")
def test_relogio_falso_nao_muda_nenhum_relogio(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    before = scene.engine.clock.remaining(Color.BLACK)
    raw.send_move("e7e5", 7 * 24 * 60 * 60 * 1000)
    wait_until(host_app, lambda: len(scene.engine.history) == 2)
    assert scene.engine.clock.remaining(Color.BLACK) <= before
    raw.close()


@pytest.mark.ct("CT-110")
def test_enxurrada_de_draw_offer_nao_empilha_sobreposicoes(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    for _ in range(500):
        raw.send_draw_offer()
    wait_until(host_app, lambda: scene.modals)
    player.frames(10)
    assert len(scene.modals) == 1
    raw.close()


@pytest.mark.ct("CT-110")
def test_mesmo_hello_duas_vezes_e_segundo_jogador_sao_recusados(network):
    host = raw_host()
    deadline = time.monotonic() + 10.0
    first = hello_socket(host.port, "Primeiro")
    while not host._peer and time.monotonic() < deadline:
        time.sleep(0.002)
    second = hello_socket(host.port, "Segundo")
    second.settimeout(5.0)
    assert b"room_full" in second.recv(4096)
    second.close()
    first.close()
    host.close()


# Nome hostil -------------------------------------------------------------------------------------


@pytest.mark.ct("CT-111")
@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_nome_hostil_passa_por_toda_a_tela_sem_derrubar_nem_vazar(host_app, network, name):
    scene, player, raw = connect_raw(host_app, network, name=name)
    expected = raw.name
    assert scene.engine.players[Color.BLACK].name == expected
    width, height = host_app.size
    player.play("e2e4")
    player.frames(2)
    assert expected in scene.notices.text or scene.notices.text
    player.click_widget(scene.hud.buttons[0])
    assert scene.modals
    player.frames(2)
    player.press(pygame.K_ESCAPE)
    # Tela de fim: o nome aparece no resultado e na série.
    raw.send_bye()
    wait_until(host_app, lambda: isinstance(host_app.scene, GameOverScene), dt=1 / 60)
    player.frames(3)
    over = host_app.scene
    for button in over.focus.widgets:
        assert button.rect.right <= width and button.rect.bottom <= height
    raw.close()


@pytest.mark.ct("CT-111")
def test_nome_com_direcao_invertida_e_controle_e_recusado_pelo_protocolo(network):
    host = raw_host()
    for name in (chr(0x202e) + "abc", "a" + chr(0x200b) + "b", "a" + chr(0) + "b", chr(0xd83d), "a" + chr(10) + "b", "   ", ""):
        attacker = socket.create_connection(("127.0.0.1", host.port), timeout=10.0)
        attacker.sendall(json.dumps({"type": "hello", "version": PROTOCOL_VERSION, "name": name}).encode() + b"\n")
        attacker.settimeout(5.0)
        try:
            data = attacker.recv(4096)
        except OSError:
            data = b""
        assert b"start" not in data, f"{name!r} entrou na sala"
        attacker.close()
    assert not host.poll(), "um estranho recusado não pode gerar evento na sala"
    host.close()


@pytest.mark.ct("CT-111")
@pytest.mark.parametrize("name", ["W" * 16, "ﷺ" * 16])
def test_nome_longo_nao_vaza_na_sala_antes_de_a_partida_comecar(host_app, network, name):
    """O texto de quem entrou tem de caber no painel, com qualquer nome."""
    lobby = open_room(host_app)
    lobby.peer_name = name
    host_app.step(0.0)
    theme = host_app.theme
    text = f"{lobby._status_text()}..."
    from xadrez.ui import theme as tokens
    width = theme.font(tokens.ROLE_DISPLAY, theme.px(22)).size(text)[0]
    assert lobby._content_left() + width <= host_app.size[0], "o texto sai pela direita da janela"


# Queda em cada estado ----------------------------------------------------------------------------


@pytest.mark.ct("CT-112")
def test_queda_com_o_dialogo_de_promocao_aberto(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    for white, black in (("a2a4", "h7h6"), ("a4a5", "h6h5"), ("a5a6", "h5h4"), ("a6b7", "h4h3")):
        player.play(white)
        ply = len(scene.engine.history)
        raw.send_move(black, 0)
        wait_until(host_app, lambda: len(scene.engine.history) == ply + 1)
        player.settle()
    player.click_square(cell("b7"))
    player.click_square(cell("a8"))
    assert scene.modals, "o diálogo de promoção precisa estar aberto"
    raw.send_bye()
    raw.close()
    wait_until(host_app, lambda: scene.engine.result is not None)
    assert not scene.modals
    assert scene.engine.result.reason is EndReason.ABANDONMENT
    assert scene.engine.result.winner is scene.local_color


@pytest.mark.ct("CT-112")
def test_queda_durante_o_voo_so_encerra_depois_do_pouso(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    post_click(point_of(scene.view, "e2"))
    player.frames(1)
    post_click(point_of(scene.view, "e4"))
    player.frames(1)
    assert scene.view.is_flying
    raw.send_bye()
    raw.close()
    wait_until(host_app, lambda: scene.engine.result is not None, dt=1 / 60)
    assert not scene.view.is_flying
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-112")
@pytest.mark.parametrize("opening", ["pausa", "ajuda", "confirmar"])
def test_queda_com_sobreposicao_aberta(host_app, network, opening):
    scene, player, raw = connect_raw(host_app, network)
    if opening == "pausa":
        player.press(pygame.K_p)
    elif opening == "ajuda":
        player.press(pygame.K_h)
    else:
        scene._confirm_resign()
        player.frames(1)
    assert scene.modals and not scene.is_frozen, "em rede a sobreposição não congela nada"
    raw.send_bye()
    raw.close()
    wait_until(host_app, lambda: scene.engine.result is not None)
    assert not scene.modals
    assert scene.engine.state is GameState.FINISHED


@pytest.mark.ct("CT-112")
def test_queda_na_sala_antes_da_partida(host_app, network):
    lobby = open_room(host_app)
    attacker = hello_socket(lobby.link.session.port)
    attacker.close()
    wait_until(host_app, lambda: lobby.error or isinstance(host_app.scene, GameScene), dt=1 / 60)
    scene = host_app.scene
    if isinstance(scene, GameScene):
        wait_until(host_app, lambda: scene.engine.result is not None, dt=1 / 60)
        assert scene.engine.result.reason is EndReason.ABANDONMENT
    else:
        assert lobby.error


@pytest.mark.ct("CT-112")
def test_queda_na_tela_de_fim_desliga_a_revanche(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play_all(SCHOLARS_MATE)
    table.run_until_both_over()
    host_over, guest_over = table.host, table.guest
    guest_over.go_to_menu()
    drive(table.apps, lambda: host_over.link.peer_is_gone)
    assert host_over.rematch_button.is_enabled is False
    host_over.rematch()
    table.steps(3)
    assert isinstance(table.host, GameOverScene)


@pytest.mark.ct("CT-112")
def test_quem_perdeu_nao_le_que_venceu_quando_o_outro_sai_na_animacao_de_fim(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = table.host, table.guest
    host._resign()
    # O outro lado fecha o jogo logo depois de ver o resultado, antes de o perdedor chegar à tela de fim.
    drive(table.apps, lambda: guest.engine.result is not None)
    assert host.engine.result.winner is guest.local_color
    guest.shutdown()
    drive(table.apps, lambda: host.net.link.peer_is_gone or isinstance(table.host, GameOverScene))
    assert "vitória é sua" not in host.notices.text


# Fim igual nos dois lados --------------------------------------------------------------------------


def assert_same_end(table):
    host, guest = table.host, table.guest
    assert host.engine.result is not None and guest.engine.result is not None
    assert host.engine.final_fen == guest.engine.final_fen, "FEN diferente nos dois lados"
    assert host.engine.history == guest.engine.history
    assert host.engine.result == guest.engine.result, f"{host.engine.result} x {guest.engine.result}"


@pytest.mark.ct("CT-113")
def test_mate_empate_e_desistencia_terminam_iguais_dos_dois_lados(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    table.play("e7e5")
    table.host._resign()
    drive(table.apps, lambda: table.guest.engine.result is not None)
    assert_same_end(table)
    assert table.host.engine.result.reason is EndReason.RESIGNATION
    table.run_until_both_over()
    assert table.host.result == table.guest.result


@pytest.mark.ct("CT-113")
def test_abandono_pela_saida_do_menu_termina_igual(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    host, guest = table.host, table.guest
    host._leave_room()
    drive([guest_app], lambda: guest.engine.result is not None)
    assert host.engine.result.winner is Color.BLACK
    assert guest.engine.result.winner is Color.BLACK
    assert host.engine.final_fen == guest.engine.final_fen


@pytest.mark.ct("CT-113")
def test_proposta_aceita_termina_igual(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    host, guest = table.host, table.guest
    host.net.send_draw_offer()
    drive(table.apps, lambda: guest.modals)
    guest.modals[-1].buttons[0].activate()
    drive(table.apps, lambda: host.engine.result is not None)
    assert_same_end(table)
    assert host.engine.result.reason is EndReason.AGREEMENT


@pytest.mark.ct("CT-113")
def test_desistencias_cruzadas_nao_podem_dar_dois_perdedores(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    host, guest = table.host, table.guest
    host._resign()
    guest._resign()
    table.steps(30)
    assert host.engine.result == guest.engine.result


@pytest.mark.ct("CT-113")
@pytest.mark.parametrize("ending", ["aceite", "desistencia"])
def test_lance_cruzado_com_o_fim_nao_pode_dar_fen_diferente(host_app, guest_app, ending):
    """Brancas propõem e, sem esperar, jogam. Do outro lado, as pretas respondem antes de receber esse lance."""
    table = connected_table(host_app, guest_app)
    host, guest = table.host, table.guest
    if ending == "aceite":
        host.net.send_draw_offer()
        drive([guest_app], lambda: guest.modals)
        # Nenhum dos dois quadros passa pelo outro: as mensagens se cruzam no fio.
        table.host_player.click_square(cell("e2"))
        table.host_player.click_square(cell("e4"))
        assert host.engine.history == ["e4"]
        guest.modals[-1].buttons[0].activate()
    else:
        table.host_player.click_square(cell("e2"))
        table.host_player.click_square(cell("e4"))
        guest._resign()
    table.steps(120)
    assert host.engine.result is not None and guest.engine.result is not None
    assert host.engine.final_fen == guest.engine.final_fen


# Tempo esgotado ------------------------------------------------------------------------------------


@pytest.mark.ct("CT-114")
def test_quem_esgota_o_proprio_relogio_perde_e_o_outro_registra_tempo(host_app, guest_app):
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    host, guest = table.host, table.guest
    fast_forward_clock(host, Color.WHITE, 0.05)
    fast_forward_clock(guest, Color.WHITE, 0.05)
    drive(table.apps, lambda: host.engine.result is not None and guest.engine.result is not None)
    assert_same_end(table)
    assert host.engine.result.reason is EndReason.TIMEOUT
    assert host.engine.result.winner is Color.BLACK


@pytest.mark.ct("CT-114")
def test_relogio_do_convidado_zera_na_sala_e_a_jogada_atrasada_e_ignorada(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    fast_forward_clock(scene, Color.BLACK, 0.01)
    player.seconds(0.5)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.engine.result.winner is Color.WHITE
    raw.send_move("e7e5", 0)
    player.seconds(0.2)
    assert scene.engine.history == ["e4"], "lance que chega depois do fim é ignorado pela autoridade"
    raw.close()


@pytest.mark.ct("CT-114")
def test_no_convidado_nenhum_relogio_decide_e_a_jogada_atrasada_da_sala_vale(host_app, guest_app):
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    host, guest = table.host, table.guest
    fast_forward_clock(guest, Color.WHITE, 0.0)
    fast_forward_clock(guest, Color.BLACK, 0.0)
    table.steps(120)
    assert guest.engine.result is None and host.engine.result is None
    table.play("e2e4")
    table.play("e7e5")
    table.steps(60)
    assert guest.engine.result is None, "o relógio dele, na tela dele, também não encerra"
    assert host.engine.final_fen == guest.engine.final_fen


@pytest.mark.ct("CT-114")
def test_sala_que_some_com_o_relogio_dela_em_zero_nao_prende_o_convidado(host_app, guest_app):
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    guest = table.guest
    fast_forward_clock(guest, Color.WHITE, 0.0)
    table.steps(60)
    assert guest.engine.result is None
    # Queda brusca: sem `result` nem `bye`.
    table.host.net.link.session.close()
    drive([guest_app], lambda: guest.engine.result is not None)
    assert guest.engine.result.reason is EndReason.ABANDONMENT
    assert guest.engine.result.winner is Color.BLACK


@pytest.mark.ct("CT-114")
def test_aviso_com_folga_no_relogio_e_desistencia_comum(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    raw.send_resign()
    wait_until(host_app, lambda: scene.engine.result is not None)
    assert scene.engine.result.reason is EndReason.RESIGNATION


@pytest.mark.ct("CT-114")
def test_desistencia_que_chega_depois_do_tempo_nao_muda_o_motivo(host_app, network):
    """`engine.tick(0.0)` precisa encerrar mesmo sem tempo a descontar."""
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    fast_forward_clock(scene, Color.BLACK, 0.0)
    wait_until(host_app, lambda: scene.engine.result is not None)
    raw.send_resign()
    player.seconds(0.2)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    raw.close()


@pytest.mark.ct("CT-114")
def test_empate_por_tempo_quando_quem_fica_so_tem_o_rei(host_app, network):
    """Quem fica só com o rei não ganha no tempo. Os dois lados chegam ao empate, pela mesma regra."""
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    board = scene.engine.board
    for square, piece in list(board.pieces(Color.WHITE)):
        if piece.kind.value != "king":
            board.remove(square)
    fast_forward_clock(scene, Color.BLACK, 0.01)
    player.seconds(0.2)
    assert scene.engine.result.winner is None
    assert scene.engine.result.reason is EndReason.TIMEOUT
    raw.close()


# Revanche e empate ---------------------------------------------------------------------------------


def play_to_end(table):
    table.play_all(SCHOLARS_MATE)
    table.run_until_both_over()


@pytest.mark.ct("CT-115")
def test_revanche_cruzada_comeca_uma_partida_so_com_cores_trocadas(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    play_to_end(table)
    table.host.rematch()
    table.guest.rematch()
    drive(table.apps, lambda: isinstance(table.host, GameScene) and isinstance(table.guest, GameScene))
    assert table.host.local_color is Color.BLACK
    assert table.guest.local_color is Color.WHITE
    table.play("d2d4")
    assert table.host.engine.history == ["d4"]
    assert table.host.engine.players[Color.WHITE].name == table.guest.engine.players[Color.WHITE].name


@pytest.mark.ct("CT-115")
def test_duas_partidas_seguidas_mantem_o_placar_igual(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    for _ in range(2):
        play_to_end(table)
        table.host.rematch()
        drive(table.apps, lambda: table.guest.link.peer_wants_rematch)
        table.guest.rematch()
        drive(table.apps, lambda: isinstance(table.host, GameScene) and isinstance(table.guest, GameScene))
        table.settle()
        # Depois da troca, quem joga de brancas muda, e o mate de pastor segue valendo com as outras mãos.
    points = lambda scene: {player.name: player.match_points for player in scene.engine.players.values()}
    assert points(table.host) == points(table.guest)


@pytest.mark.ct("CT-115")
def test_pedido_de_revanche_no_meio_da_partida_nao_muda_nada(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    raw.send_rematch()
    player.frames(20)
    assert isinstance(host_app.scene, GameScene)
    assert scene.engine.result is None
    assert scene.net.link.peer_wants_rematch is False
    raw.close()


@pytest.mark.ct("CT-115")
def test_propostas_de_empate_cruzadas(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = table.host, table.guest
    host.net.send_draw_offer()
    guest.net.send_draw_offer()
    drive(table.apps, lambda: host.modals and guest.modals)
    # Os dois diálogos ficam abertos. Um aceita e o outro recusa ao mesmo tempo.
    host.modals[-1].buttons[0].activate()
    guest.modals[-1].buttons[1].activate()
    table.steps(120)
    assert host.engine.result is not None and guest.engine.result is not None
    assert host.engine.result == guest.engine.result


@pytest.mark.ct("CT-115")
def test_proposta_sem_resposta_nao_trava_nem_para_o_relogio(host_app, guest_app):
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    host, guest = table.host, table.guest
    before = guest.engine.clock.remaining(Color.WHITE)
    host.net.send_draw_offer()
    drive(table.apps, lambda: guest.modals)
    table.steps(60)
    assert guest.engine.clock.remaining(Color.WHITE) < before
    table.host_player.click_square(cell("e2"))
    table.host_player.click_square(cell("e4"))
    drive(table.apps, lambda: len(guest.engine.history) == 1)
    assert guest.modals, "o diálogo continua: a resposta ainda é devida"
    # A proposta não prende ninguém: dá para responder a qualquer hora, ou jogar, e isso recusa.
    table.settle()
    guest.modals[-1].buttons[1].activate()
    drive(table.apps, lambda: not guest.modals)


@pytest.mark.ct("CT-115")
def test_proposta_repetida_nao_vira_duas_na_tela_e_resposta_sem_proposta_e_ignorada(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    player.frames(2)
    raw.send_draw_answer(True)
    player.frames(10)
    assert scene.engine.result is None, "resposta sem oferta não pode virar empate"
    raw.close()


@pytest.mark.ct("CT-115")
def test_resposta_de_empate_que_chega_depois_do_fim_nao_muda_o_resultado(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = table.host, table.guest
    host.net.send_draw_offer()
    drive(table.apps, lambda: guest.modals)
    guest.modals[-1].buttons[0].activate()
    host._resign()
    table.steps(120)
    assert host.engine.result.reason is EndReason.RESIGNATION


# Sala ----------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-116")
@pytest.mark.parametrize("typed", ["", "ABC", "AAAAAAA", "0OIL1LL", "ÇÇÇÇÇÇÇ", "ß" * 7, "٣" * 7, "abc def"])
def test_codigo_errado_vira_mensagem_e_o_campo_continua_funcionando(guest_app, network, typed):
    menu = guest_app.scene
    player = Autoplayer(guest_app)
    player.click_segment(menu.opponent_selector, NET_SEGMENT)
    player.click_widget(menu.join_room_button)
    lobby = guest_app.scene
    post_text(typed)
    player.frames(1)
    player.press(pygame.K_RETURN)
    wait_until(guest_app, lambda: lobby.error, dt=1 / 60)
    assert lobby.link is None
    assert isinstance(guest_app.scene, LobbyScene)


@pytest.mark.ct("CT-116")
@pytest.mark.parametrize("transform", [str.lower, lambda code: f"  {code}  ", lambda code: f"{code[:3]} {code[3:]}", lambda code: code.lower().replace("", " ")])
def test_codigo_em_minusculas_ou_com_espacos_entra_na_sala(host_app, guest_app, transform):
    lobby = open_room(host_app)
    join_room(guest_app, transform(lobby.code))
    table = Table(host_app, guest_app)
    table.settle()
    assert isinstance(table.guest, GameScene)


@pytest.mark.ct("CT-116")
def test_enter_repetido_no_campo_do_codigo_cria_uma_sessao_so(host_app, guest_app, network):
    lobby = open_room(host_app)
    menu = guest_app.scene
    player = Autoplayer(guest_app)
    player.click_segment(menu.opponent_selector, NET_SEGMENT)
    player.click_widget(menu.join_room_button)
    guest_lobby = guest_app.scene
    post_text(lobby.code)
    player.frames(1)
    before = len(network.opened)
    for _ in range(5):
        post_key(pygame.K_RETURN)
    player.frames(1)
    assert len(network.opened) == before + 1
    assert guest_lobby.is_connecting or isinstance(guest_app.scene, GameScene)


@pytest.mark.ct("CT-116")
def test_enter_repetido_em_criar_sala_abre_uma_sessao_so(host_app, network):
    menu = host_app.scene
    player = Autoplayer(host_app)
    player.click_segment(menu.opponent_selector, NET_SEGMENT)
    menu.focus.focus(menu.create_room_button)
    post_key(pygame.K_RETURN)
    post_key(pygame.K_RETURN)
    player.frames(1)
    opened = len(network.opened)
    alive = [session for session in network.opened if session._thread is not None and session._thread.is_alive()]
    host_app.scene.shutdown()
    still_alive = [session for session in network.opened if session._thread is not None and session._thread.is_alive()]
    for session in network.opened:
        session.close()
    assert opened == 1, f"{opened} sessões abertas, {len(alive)} vivas, {len(still_alive)} ainda vivas depois de sair"


@pytest.mark.ct("CT-116")
def test_sair_da_sala_e_criar_outra_na_mesma_porta_na_hora():
    """Porta fixa em 127.0.0.1, como a padrão: nem o TIME_WAIT de quem saiu primeiro pode prender a porta."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    for first_to_leave in ("sala", "convidado"):
        host = HostSession("A", TimeControl.BLITZ_5, port=port, bind="127.0.0.1", timings=QUICK)
        host.start()
        guest = ClientSession("B", "127.0.0.1", port=port, timings=QUICK)
        guest.start()
        deadline = time.monotonic() + 10.0
        while not any(isinstance(event, GameStart) for event in guest.poll()):
            assert time.monotonic() < deadline
            time.sleep(0.002)
        for leaver in ((host, guest) if first_to_leave == "sala" else (guest, host)):
            leaver.send_bye()
            leaver.close()
        reopened = HostSession("A", TimeControl.BLITZ_5, port=port, bind="127.0.0.1", timings=QUICK)
        reopened.start()
        time.sleep(0.05)
        events = reopened.poll()
        reopened.close()
        assert not any(isinstance(event, NetworkError) for event in events), f"porta presa depois da saída de {first_to_leave}: {events}"


@pytest.mark.ct("CT-116")
def test_porta_ocupada_vira_mensagem_e_abrir_de_novo_funciona(host_app, network):
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    port = holder.getsockname()[1]
    original = network.host
    network.host = lambda name, time_control: network._track(HostSession(name, time_control, port=port, bind="127.0.0.1", timings=QUICK))
    lobby = open_room(host_app)
    wait_until(host_app, lambda: lobby.error, dt=1 / 60)
    assert str(port) in lobby.error
    assert lobby.link is None
    holder.close()
    network.host = original
    lobby.open_room()
    host_app.step(0.0)
    assert lobby.error == "" and lobby.link is not None


# Nada sobra ----------------------------------------------------------------------------------------


@pytest.mark.ct("CT-117")
@pytest.mark.parametrize("path", ["cancelar", "fechar_sala", "fechar_entrando", "partida_menu", "partida_fechar", "fim_menu", "fim_fechar", "trapaca"])
def test_nenhum_caminho_deixa_thread_ou_socket(host_app, guest_app, network, path):
    if path == "cancelar":
        open_room(host_app).cancel()
        host_app.step(0.0)
    elif path == "fechar_sala":
        open_room(host_app)
        host_app.scene.shutdown()
    elif path == "fechar_entrando":
        lobby = join_room(guest_app, encode_room_code("127.0.0.1"))
        lobby.shutdown()
    else:
        table = connected_table(host_app, guest_app)
        if path == "partida_menu":
            table.host._leave_room()
            drive([guest_app], lambda: table.guest.engine.result is not None)
            table.host_app.step(FRAME)
            table.guest.shutdown()
        elif path == "partida_fechar":
            table.host.shutdown()
            table.guest.shutdown()
        elif path == "trapaca":
            table.guest.net.link.session.send_move("e7e5", 0)
            drive(table.apps, lambda: table.host.engine.result is not None)
            table.guest.shutdown()
        else:
            table.play_all(SCHOLARS_MATE)
            table.run_until_both_over()
            if path == "fim_menu":
                table.host.go_to_menu()
                table.guest.go_to_menu()
            else:
                table.host.shutdown()
                table.guest.shutdown()
    assert not wait_threads_gone(5.0), f"sobrou thread em {path}"
    for session in network.opened:
        listener = getattr(session, "_listener", None)
        assert listener is None or listener.fileno() == -1, "porta aberta depois de sair"


# Sala de atacante: quem entra é a tela, e o outro lado manda o que quiser --------------------------------


class AttackerRoom:
    """Um socket que finge ser a sala. Nada aqui segue o protocolo além do que o teste pedir."""

    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(10.0)
        self.port = self.listener.getsockname()[1]
        self.connection = None
        self.buffer = b""

    def accept_hello(self):
        self.connection, _ = self.listener.accept()
        self.connection.settimeout(10.0)
        while b"\n" not in self.buffer:
            self.buffer += self.connection.recv(4096)
        return json.loads(self.buffer.split(b"\n", 1)[0])

    def send(self, **message):
        self.connection.sendall(json.dumps(message).encode() + b"\n")

    def close(self):
        if self.connection is not None:
            self.connection.close()
        self.listener.close()


START = {"type": "start", "white": "Atacante", "black": "Tela", "your_color": "black", "minutes": 5, "increment": 0}


@pytest.fixture
def attacker(network):
    room = AttackerRoom()

    class Target:
        port = room.port

    network.last_host = Target
    yield room
    room.close()


def enter_attacker_room(guest_app, attacker, **start):
    lobby = join_room(guest_app, encode_room_code("127.0.0.1"))
    attacker.accept_hello()
    attacker.send(**{**START, **start})
    wait_until(guest_app, lambda: isinstance(guest_app.scene, GameScene))
    scene = guest_app.scene
    Autoplayer(guest_app).settle()
    return lobby, scene


@pytest.mark.ct("CT-110")
@pytest.mark.parametrize("start", [
    {"minutes": 1e-9},
    {"minutes": 1440, "increment": 3600},
    {"minutes": 0, "increment": 3600},
    {"minutes": 0.5, "increment": 0.25},
    {"white": "W" * 16, "black": "W" * 16},
    {"white": chr(0x301) * 16},
    {"black": chr(0xfdfa) * 16, "your_color": "white"},
])
def test_sala_hostil_com_inicio_estranho_nao_derruba_quem_entra(guest_app, attacker, start):
    _, scene = enter_attacker_room(guest_app, attacker, **start)
    player = Autoplayer(guest_app)
    player.seconds(0.5)
    player.press(pygame.K_p)
    player.press(pygame.K_p)
    attacker.close()
    wait_until(guest_app, lambda: isinstance(guest_app.scene, GameOverScene), dt=1 / 60)
    player.frames(3)
    assert guest_app.scene.result is not None


@pytest.mark.ct("CT-110")
def test_segundo_inicio_no_meio_da_partida_encerra_em_vez_de_apagar_o_jogo(guest_app, attacker):
    _, scene = enter_attacker_room(guest_app, attacker)
    attacker.send(type="move", uci="e2e4", clock_ms=0)
    wait_until(guest_app, lambda: len(scene.engine.history) == 1)
    Autoplayer(guest_app).settle()
    attacker.send(**START)
    wait_until(guest_app, lambda: scene.engine.result is not None)
    assert scene.engine.history == ["e4"]
    assert scene.engine.result.reason is EndReason.ABANDONMENT
    assert scene.net.link.peer_is_gone


@pytest.mark.ct("CT-110")
@pytest.mark.parametrize("reply, expected", [
    ({"type": "refused", "code": "room_full"}, "cheia"),
    ({"type": "refused", "code": "version"}, "versões"),
    ({"type": "refused", "code": "outra coisa"}, "inválidos"),
    ({"type": "move", "uci": "e2e4", "clock_ms": 0}, "inválidos"),
    ({"type": "start", "white": "a"}, "inválidos"),
])
def test_resposta_estranha_da_sala_vira_mensagem(guest_app, attacker, reply, expected):
    lobby = join_room(guest_app, encode_room_code("127.0.0.1"))
    attacker.accept_hello()
    attacker.send(**reply)
    wait_until(guest_app, lambda: lobby.error)
    assert expected in lobby.error
    assert lobby.link is None and isinstance(guest_app.scene, LobbyScene)


@pytest.mark.ct("CT-110")
def test_sala_muda_que_nao_responde_nao_prende_quem_entra(guest_app, attacker, network):
    original = network.client
    network.client = lambda name, code: network._track(ClientSession(name, code, port=attacker.port, timeout=0.2, timings=QUICK))
    lobby = join_room(guest_app, encode_room_code("127.0.0.1"))
    attacker.accept_hello()
    wait_until(guest_app, lambda: lobby.error, dt=1 / 60)
    assert "não respondeu" in lobby.error
    network.client = original


@pytest.mark.ct("CT-115")
def test_revanche_com_a_cor_errada_encerra_a_sala_em_vez_de_duas_partidas_diferentes(guest_app, attacker):
    _, scene = enter_attacker_room(guest_app, attacker)
    attacker.send(type="resign")
    wait_until(guest_app, lambda: isinstance(guest_app.scene, GameOverScene), dt=1 / 60)
    over = guest_app.scene
    over.rematch()
    guest_app.step(0.0)
    # Depois de pedir, a sala tem de dar a outra cor. O atacante repete a mesma.
    time.sleep(0.05)
    attacker.send(**START)
    wait_until(guest_app, lambda: over.link.peer_is_gone)
    assert guest_app.scene is over
    assert over.engine.history == []


# Relógios que não batem ----------------------------------------------------------------------------


@pytest.mark.ct("CT-114")
def test_quem_ignora_o_proprio_relogio_nao_joga_para_sempre(host_app, network):
    """Uma cópia alterada do jogo não se declara sem tempo: quem mede é a sala."""
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    white_moves = iter(("d2d4", "g1f3", "b1c3", "f1c4"))
    for black_move in ("e7e5", "b8c6", "g8f6", "f8c5"):
        fast_forward_clock(scene, Color.BLACK, 0.0)
        player.seconds(4.0)
        if scene.engine.result is not None:
            break
        ply = len(scene.engine.history)
        raw.send_move(black_move, 0)
        wait_until(host_app, lambda: len(scene.engine.history) == ply + 1)
        player.settle()
        player.play(next(white_moves))
    raw.close()
    assert scene.engine.result is not None, "16 s de jogo com o relógio do outro em zero"


@pytest.mark.ct("CT-114")
def test_relogios_defasados_nao_podem_dar_dois_vencedores(host_app, guest_app):
    """Janela arrastada ou quadro lento: o `dt` é limitado a 0,1 s, e o relógio daquela máquina fica para trás."""
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    host, guest = table.host, table.guest
    # Vez das brancas. Na tela das pretas, o relógio das brancas já zerou; na das brancas, ainda há tempo.
    fast_forward_clock(guest, Color.WHITE, 0.0)
    table.steps(330)
    assert guest.engine.result is None, "o convidado não decide: na sala ainda há tempo"
    fast_forward_clock(host, Color.WHITE, 0.01)
    drive(table.apps, lambda: host.engine.result is not None and guest.engine.result is not None)
    assert_same_end(table)


@pytest.mark.ct("CT-114")
def test_relogios_defasados_nao_podem_dar_motivos_diferentes(host_app, guest_app):
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    host, guest = table.host, table.guest
    fast_forward_clock(host, Color.WHITE, 0.01)
    fast_forward_clock(guest, Color.WHITE, 3.0)
    drive(table.apps, lambda: host.engine.result is not None and guest.engine.result is not None)
    assert host.engine.result == guest.engine.result


@pytest.mark.ct("CT-113")
def test_dois_convidados_nao_ficam_com_o_mesmo_nome(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    names = table.host.engine.players
    assert names[Color.WHITE].name != names[Color.BLACK].name
    assert {player.name for player in names.values()} == {player.name for player in table.guest.engine.players.values()}
    assert table.host.net.link.peer_name == names[Color.BLACK].name
    assert table.guest.net.link.peer_name == names[Color.WHITE].name


@pytest.mark.ct("CT-116")
def test_enter_repetido_em_criar_sala_nao_prende_a_porta(host_app, network):
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    network.host = lambda name, time_control: network._track(HostSession(name, time_control, port=port, bind="127.0.0.1", timings=QUICK))
    menu = host_app.scene
    player = Autoplayer(host_app)
    player.click_segment(menu.opponent_selector, NET_SEGMENT)
    menu.focus.focus(menu.create_room_button)
    post_key(pygame.K_RETURN)
    post_key(pygame.K_RETURN)
    player.frames(1)
    lobby = host_app.scene
    wait_until(host_app, lambda: lobby.error or lobby.link is not None, limit=2.0, dt=1 / 60)
    player.seconds(0.2)
    error = lobby.error
    host_app.scene.shutdown()
    network.close_all()
    assert not error, f"a tela mostra: {error}"


@pytest.mark.ct("CT-112")
def test_motivo_da_sala_encerrada_chega_a_tela_de_fim(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    raw.send_move("e7e5", 0)
    wait_until(host_app, lambda: scene.engine.result is not None)
    assert scene.notices.text == ILLEGAL_MOVE_MESSAGE
    player.seconds(1.2)
    over = host_app.scene
    assert isinstance(over, GameOverScene)
    raw.close()
    assert over.notices.text == ILLEGAL_MOVE_MESSAGE, f"a tela de fim mostra: {over.notices.text!r}"


@pytest.mark.ct("CT-115")
def test_proposta_recusada_nao_reabre_sem_um_lance_no_meio(host_app, network):
    """Regra do xadrez: uma proposta por lance. Sem isso, uma cópia alterada do jogo ganha no tempo só mandando propostas."""
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    raw.send_draw_offer()
    wait_until(host_app, lambda: scene.modals)
    player.press(pygame.K_ESCAPE)
    assert not scene.modals
    raw.send_draw_offer()
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline and not scene.modals:
        player.frames(1)
    reopened = bool(scene.modals)
    raw.close()
    assert not reopened, "o mesmo jogador propôs de novo sem nenhum lance no meio"


# A sala decide: lances e fins cruzados -------------------------------------------------------------------


def guest_moves_without_the_host_seeing(table, uci):
    """Só o quadro de quem entrou anda: o lance fica no fio enquanto a sala decide outra coisa."""
    table.guest_player.click_square(cell(uci[:2]))
    table.guest_player.click_square(cell(uci[2:4]))


@pytest.mark.ct("CT-113")
def test_lance_do_convidado_cruzado_com_a_desistencia_da_sala_volta_atras(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    host, guest = table.host, table.guest
    guest_moves_without_the_host_seeing(table, "e7e5")
    assert guest.engine.history == ["e4", "e5"]
    host._resign()
    table.steps(120)
    assert_same_end(table)
    assert guest.engine.history == ["e4"], "o lance que a sala não viu volta"
    assert guest.engine.board.piece_at(Square.from_name("e7")) is not None
    assert host.engine.result.winner is Color.BLACK


@pytest.mark.ct("CT-113")
def test_captura_do_convidado_cruzada_com_o_fim_devolve_a_peca(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play_all("e2e4 d7d5 g1f3")
    host, guest = table.host, table.guest
    guest_moves_without_the_host_seeing(table, "d5e4")
    assert guest.engine.players[Color.BLACK].captured
    host._resign()
    table.steps(120)
    assert_same_end(table)
    assert guest.engine.players[Color.BLACK].captured == []


@pytest.mark.ct("CT-113")
def test_mate_do_convidado_cruzado_com_o_tempo_dele_vale_o_tempo(host_app, guest_app):
    """O pior cruzamento: o motor de quem entrou já deu o mate e a vitória. A sala, que mede o relógio, deu o contrário."""
    guest_app.account = "Bia"
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    table.play_all("f2f3 e7e5 g2g4")
    host, guest = table.host, table.guest
    # A sala decide primeiro: o `result` só sai no quadro seguinte, e o lance dele já está a caminho.
    fast_forward_clock(host, Color.BLACK, 0.0)
    host_app.step(FRAME)
    assert host.engine.result is not None
    guest_moves_without_the_host_seeing(table, "d8h4")
    assert guest.engine.result.reason is EndReason.CHECKMATE, "o mate saiu na tela dele"
    assert not HistoryStore("Bia").records(), "ainda não é definitivo: não pode gravar"
    table.steps(180)
    assert_same_end(table)
    assert host.engine.result == GameResult(Color.WHITE, EndReason.TIMEOUT)
    assert guest.engine.clock.remaining(Color.BLACK) == 0.0, "o relógio de quem perdeu aparece zerado"
    points = lambda scene: {color: player.match_points for color, player in scene.engine.players.items()}
    assert points(host) == points(guest) == {Color.WHITE: 1.0, Color.BLACK: 0.0}, "o ponto do mate desfeito não fica"
    records = HistoryStore("Bia").records()
    assert [record.outcome for record in records] == ["derrota"]
    assert records[0].final_fen == host.engine.final_fen


@pytest.mark.ct("CT-113")
def test_sala_que_sai_com_lance_do_convidado_no_fio_termina_igual(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    host, guest = table.host, table.guest
    guest_moves_without_the_host_seeing(table, "e7e5")
    host._leave_room()
    drive([guest_app], lambda: guest.engine.result is not None and guest.net.link.peer_is_gone)
    assert host.engine.final_fen == guest.engine.final_fen
    assert guest.engine.result == GameResult(Color.BLACK, EndReason.ABANDONMENT)


@pytest.mark.ct("CT-113")
def test_convidado_que_desiste_espera_a_sala_com_o_tabuleiro_parado(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    guest = table.guest
    guest._resign()
    assert guest.engine.result is None
    assert guest.is_board_locked
    table.guest_player.click_square(cell("e7"))
    assert guest.selection is None
    guest._resign()
    drive(table.apps, lambda: guest.engine.result is not None)
    assert_same_end(table)
    assert guest.engine.result == GameResult(Color.WHITE, EndReason.RESIGNATION)


@pytest.mark.ct("CT-113")
def test_sala_que_cai_depois_da_desistencia_vale_a_desistencia(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    guest = table.guest
    table.host.net.link.session.close()
    guest._resign()
    drive([guest_app], lambda: guest.engine.result is not None)
    assert guest.engine.result == GameResult(Color.WHITE, EndReason.RESIGNATION), "ninguém ganha o que entregou"
    assert "vitória" not in guest.notices.text


def attacker_result(**changes):
    return {"type": "result", "winner": "white", "reason": "resignation", "plies": 0, **changes}


@pytest.mark.ct("CT-110")
def test_resultado_da_sala_vale_em_quem_entrou(guest_app, attacker):
    _, scene = enter_attacker_room(guest_app, attacker)
    attacker.send(**attacker_result())
    wait_until(guest_app, lambda: scene.engine.result is not None)
    assert scene.engine.result == GameResult(Color.WHITE, EndReason.RESIGNATION)


@pytest.mark.ct("CT-110")
@pytest.mark.parametrize("message", [
    attacker_result(reason="checkmate"),
    attacker_result(reason="stalemate", winner=None),
    attacker_result(reason="fifty_moves", winner=None),
    attacker_result(plies=5),
])
def test_resultado_que_nao_confere_com_o_tabuleiro_encerra_a_sala(guest_app, attacker, message):
    _, scene = enter_attacker_room(guest_app, attacker)
    attacker.send(**message)
    wait_until(guest_app, lambda: scene.engine.result is not None)
    assert scene.engine.result == GameResult(Color.BLACK, EndReason.ABANDONMENT)
    assert scene.notices.text == INVALID_RESULT_MESSAGE
    assert scene.net.link.peer_is_gone


@pytest.mark.ct("CT-110")
@pytest.mark.parametrize("message", [
    attacker_result(winner="green"),
    attacker_result(winner=None),
    attacker_result(reason="stalemate"),
    attacker_result(reason="desistiu"),
    attacker_result(plies=-1),
    attacker_result(plies=1.5),
    attacker_result(plies=True),
    attacker_result(extra=1),
])
def test_resultado_malformado_vira_erro_de_rede(guest_app, attacker, message):
    _, scene = enter_attacker_room(guest_app, attacker)
    attacker.send(**message)
    wait_until(guest_app, lambda: scene.engine.result is not None)
    assert scene.engine.result == GameResult(Color.BLACK, EndReason.ABANDONMENT)
    assert scene.net.link.peer_is_gone


@pytest.mark.ct("CT-110")
def test_sala_viva_que_nao_responde_nao_prende_quem_desistiu(guest_app, attacker):
    _, scene = enter_attacker_room(guest_app, attacker)
    scene._resign()
    player = Autoplayer(guest_app)
    player.seconds(DECISION_WAIT_SECONDS - 1.0)
    assert scene.engine.result is None
    player.seconds(1.5)
    assert scene.engine.result == GameResult(Color.WHITE, EndReason.RESIGNATION)
    assert scene.notices.text == NO_DECISION_MESSAGE
    assert scene.net.link.peer_is_gone


# Proposta de empate não prende ninguém ------------------------------------------------------------------


def offer_to_guest(table):
    table.play("e2e4")
    host, guest = table.host, table.guest
    host.net.send_draw_offer()
    drive(table.apps, lambda: guest.modals)
    return host, guest


@pytest.mark.ct("CT-115")
def test_quem_recebe_a_proposta_joga_e_isso_recusa(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = offer_to_guest(table)
    table.guest_player.click_square(cell("e7"))
    assert guest.selection is not None, "a proposta não bloqueia o tabuleiro"
    table.guest_player.click_square(cell("e5"))
    assert guest.modals == [], "jogar responde à proposta"
    drive(table.apps, lambda: "recusou" in host.notices.text)
    assert len(host.engine.history) == 2
    assert host.net.draw_answer_pending is False
    assert host.engine.result is None


@pytest.mark.ct("CT-115")
def test_recusa_barra_nova_proposta_ate_o_proximo_lance_de_quem_propos(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = offer_to_guest(table)
    table.guest_player.press(pygame.K_ESCAPE)
    drive(table.apps, lambda: not host.net.draw_answer_pending)
    assert host.net.may_offer_draw is False
    table.host_player.press(pygame.K_p)
    table.host_player.click_widget(host.modals[-1].buttons[1])
    assert host.net.draw_answer_pending is False, "não sai outra proposta"
    assert DRAW_OFFER_AGAIN_NOTICE in host.notices.text
    table.play("e7e5")
    assert host.net.may_offer_draw is False, "o lance do outro não libera"
    table.play("g1f3")
    assert host.net.may_offer_draw is True


@pytest.mark.ct("CT-115")
def test_proposta_volta_a_abrir_depois_de_um_lance_de_quem_propos(host_app, network):
    scene, player, raw = connect_raw(host_app, network, TimeControl.BLITZ_5)
    player.play("e2e4")
    raw.send_draw_offer()
    wait_until(host_app, lambda: scene.modals)
    player.press(pygame.K_ESCAPE)
    raw.send_move("e7e5", 0)
    wait_until(host_app, lambda: len(scene.engine.history) == 2)
    player.settle()
    raw.send_draw_offer()
    wait_until(host_app, lambda: scene.modals)
    assert scene.modals[-1].title == "Proposta de empate"
    raw.close()


@pytest.mark.ct("CT-115")
def test_proposta_depois_do_fim_e_ignorada(host_app, network):
    scene, player, raw = connect_raw(host_app, network)
    scene._resign()
    raw.send_draw_offer()
    player.seconds(0.3)
    assert scene.modals == []
    raw.close()


@pytest.mark.ct("CT-115")
def test_cartao_da_proposta_responde_ao_teclado_e_deixa_as_setas_para_o_tabuleiro(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = offer_to_guest(table)
    table.settle()
    table.guest_player.press(pygame.K_UP)
    assert guest.cursor is not None, "as setas seguem com o tabuleiro"
    assert guest.modals, "e o cartão continua"
    table.guest_player.press(pygame.K_a)
    drive(table.apps, lambda: guest.engine.result is not None)
    assert_same_end(table)
    assert guest.engine.result == GameResult(None, EndReason.AGREEMENT)


@pytest.mark.ct("CT-115")
def test_cartao_fica_sobre_a_planilha_com_o_tabuleiro_inteiro_a_vista(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = offer_to_guest(table)
    table.settle()
    card = guest.modals[-1]
    assert not card._panel.colliderect(guest.hud.viewport), "o cartão não pode esconder casas"
    assert card._panel.colliderect(guest.hud.sheet.rect)
    width, height = guest_app.size
    assert card._panel.right <= width and card._panel.bottom <= height
    post_click(card._panel.center)
    table.guest_player.frames(1)
    assert guest.modals == [card], "clique no corpo do cartão não responde nada"


@pytest.mark.ct("CT-115")
def test_sobreposicao_aberta_por_cima_do_cartao_fecha_primeiro(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    host, guest = offer_to_guest(table)
    table.settle()
    card = guest.modals[-1]
    table.guest_player.press(pygame.K_p)
    assert len(guest.modals) == 2 and guest.modals[0] is card
    table.guest_player.press(pygame.K_p)
    assert guest.modals == [card], "fechar a pausa não fecha a proposta"


@pytest.mark.ct("CT-115")
def test_ajuda_em_rede_nao_lista_o_que_nao_vale(host_app, guest_app):
    table = connected_table(host_app, guest_app)
    table.host_player.press(pygame.K_h)
    keys = [hint.keys for hint in table.host.modals[-1]._hints]
    assert "R" not in keys and "T" not in keys and "F" in keys


@pytest.mark.ct("CT-114")
def test_na_revanche_quem_criou_a_sala_continua_decidindo(host_app, guest_app):
    """A cor troca, a autoridade não: é a sala, mesmo jogando de Pretas."""
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    play_to_end(table)
    table.host.rematch()
    table.guest.rematch()
    drive(table.apps, lambda: isinstance(table.host, GameScene) and isinstance(table.guest, GameScene))
    table.settle()
    host, guest = table.host, table.guest
    assert host.local_color is Color.BLACK and host.net.is_authority and not guest.net.is_authority
    fast_forward_clock(guest, Color.WHITE, 0.0)
    table.steps(60)
    assert guest.engine.result is None, "o relógio dele, na tela dele, não encerra"
    fast_forward_clock(host, Color.WHITE, 0.01)
    drive(table.apps, lambda: host.engine.result is not None and guest.engine.result is not None)
    assert_same_end(table)
    assert host.engine.result == GameResult(Color.BLACK, EndReason.TIMEOUT)


# Todo fim cruzado: nenhum dos dois lados lê a rede entre uma ação e outra --------------------------------


OPENING = ("e2e4", "e7e5", "g1f3")
NEXT_MOVE = {2: "g1f3", 3: "b8c6"}


def cross_move(scene, plies):
    """Joga pelo mesmo caminho do clique, mas sem quadro: o que está no fio continua sem ser lido."""
    uci = NEXT_MOVE[plies]
    if scene.engine.turn is scene.local_color:
        scene._submit_move(Square.from_name(uci[:2]), Square.from_name(uci[2:4]))


def host_acts(host, action, plies):
    if action == "lance":
        cross_move(host, plies)
    elif action == "desiste":
        host._resign()
    elif action == "tempo":
        fast_forward_clock(host, host.engine.turn, 0.0)
    elif action == "propoe":
        host.net.send_draw_offer()
    elif action == "sai":
        host._leave_room()


def guest_acts(guest, action, plies):
    if action == "lance":
        cross_move(guest, plies)
    elif action == "desiste":
        guest._resign()
    elif action == "aceita":
        guest.modals[-1].buttons[0].activate()
    elif action == "propoe":
        guest.net.send_draw_offer()


@pytest.mark.ct("CT-113")
@pytest.mark.parametrize("plies", [2, 3], ids=["vez-da-sala", "vez-de-quem-entrou"])
@pytest.mark.parametrize("guest_action", ["lance", "desiste", "aceita", "propoe"])
@pytest.mark.parametrize("host_action", ["lance", "desiste", "tempo", "propoe", "sai"])
def test_fins_cruzados_terminam_iguais_nos_dois_lados(host_app, guest_app, host_action, guest_action, plies):
    """Quem entrou age primeiro: o que ele mandou fica por ler na sala, e até o fechamento dela precisa aguentar isso."""
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    table.play_all(" ".join(OPENING[:plies]))
    host, guest = table.host, table.guest
    if guest_action == "aceita":
        host.net.send_draw_offer()
        drive(table.apps, lambda: guest.modals)
    guest_acts(guest, guest_action, plies)
    host_acts(host, host_action, plies)
    table.steps(90)
    if host.engine.result is None:
        host._resign()
        table.steps(60)
    assert host.engine.result is not None and guest.engine.result is not None
    assert host.engine.result == guest.engine.result
    assert host.engine.final_fen == guest.engine.final_fen
    assert host.engine.history == guest.engine.history
    points = lambda scene: {color: player.match_points for color, player in scene.engine.players.items()}
    assert points(host) == points(guest)


@pytest.mark.ct("CT-113")
def test_convidado_que_sai_com_lance_da_sala_a_caminho_continua_derrotado_nos_dois(host_app, guest_app):
    """Único caso sem como igualar o FEN: quem saiu não está mais lá para receber o lance. O vencedor é o mesmo."""
    table = connected_table(host_app, guest_app, TimeControl.BLITZ_5)
    table.play_all("e2e4 e7e5")
    host, guest = table.host, table.guest
    cross_move(host, 2)
    guest._leave_room()
    drive([host_app], lambda: host.engine.result is not None and not host.view.is_flying)
    assert host.engine.result.winner is guest.engine.result.winner is Color.WHITE
