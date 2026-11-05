"""CT-86: partida real entre duas sessões por socket. CT-87: queda de conexão vira evento, sem travar."""
import random
import selectors
import socket
import threading
import time

import pytest
from net_helpers import LOCALHOST, QUICK, WAIT_SECONDS, FakeHost, Inbox, RawPeer, open_client, open_host, start_message

from xadrez.core import Color, EndReason, GameEngine, GameState, TimeControl, legal_moves
from xadrez.net import (
    ClientSession,
    DrawAnswered,
    DrawOffered,
    GameStart,
    HostSession,
    MoveReceived,
    NetTimings,
    NetworkError,
    PeerJoined,
    PeerLeft,
    PeerResigned,
    RematchRequested,
    encode_room_code,
    parse_uci,
)
from xadrez.net.connection import LineConnection
from xadrez.net.session import THREAD_NAME_PREFIX

# En passant, os dois roques, duas promoções e xeque-mate na mesma partida, conferidos pelo motor nos dois lados.
FULL_GAME = (
    "e2e4 a7a6 e4e5 d7d5 e5d6 e7d6 g1f3 b8c6 f1c4 c8e6 e1g1 d8d7 h2h4 e8c8 "
    "h4h5 a6a5 h5h6 a5a4 h6g7 a4a3 g7h8q a3b2 a2a3 c6b4 a3b4 b2c1q a1a8"
).split()
FAST_HEARTBEAT = NetTimings(heartbeat_interval=0.05, heartbeat_timeout=0.5, tick=0.002)


def session_threads():
    return [thread for thread in threading.enumerate() if thread.name.startswith(THREAD_NAME_PREFIX)]


def wait_until(condition, timeout=WAIT_SECONDS):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "a condição não aconteceu a tempo"
        time.sleep(0.002)


def thread_of(session):
    return session._thread


def wait_finished(session):
    thread = thread_of(session)
    if thread is not None:
        thread.join(WAIT_SECONDS)
        assert not thread.is_alive()


@pytest.fixture
def pair(opened):
    """Sala e cliente já em partida, com os eventos de início consumidos."""
    host = open_host(opened)
    client = open_client(opened, host)
    host_inbox, client_inbox = Inbox(host), Inbox(client)
    for inbox in (host_inbox, client_inbox):
        inbox.wait_for(PeerJoined)
        inbox.wait_for(GameStart)
    return host, client, host_inbox, client_inbox


def relay_move(sender, sender_engine, receiver_inbox, receiver_engine, uci, clock_ms=1000):
    """O caminho real da interface: joga, envia, recebe, valida no motor do outro lado."""
    origin, target, promotion = parse_uci(uci)
    outcome = sender_engine.play(origin, target, promotion)
    assert outcome.ok, f"{uci}: {outcome.error}"
    sender.send_move(uci, clock_ms)
    received = receiver_inbox.wait_for(MoveReceived)
    assert received == MoveReceived(uci, clock_ms)
    origin, target, promotion = parse_uci(received.uci)
    assert receiver_engine.play(origin, target, promotion).ok
    return outcome


@pytest.mark.ct("CT-86")
def test_net_partida_inteira_termina_com_o_mesmo_fen(pair):
    host, client, host_inbox, client_inbox = pair
    host_engine, client_engine = GameEngine(), GameEngine()
    specials = {"en_passant": 0, "castling": 0, "promotion": 0}
    outcome = None
    for ply, uci in enumerate(FULL_GAME):
        if ply % 2 == 0:
            outcome = relay_move(host, host_engine, client_inbox, client_engine, uci, clock_ms=ply * 10)
        else:
            outcome = relay_move(client, client_engine, host_inbox, host_engine, uci, clock_ms=ply * 10)
        specials["en_passant"] += outcome.move.is_en_passant
        specials["castling"] += outcome.move.is_castling
        specials["promotion"] += outcome.move.promotion is not None
    assert specials == {"en_passant": 1, "castling": 2, "promotion": 2}
    assert outcome.result.reason is EndReason.CHECKMATE
    assert host_engine.result == client_engine.result
    assert host_engine.state is client_engine.state is GameState.FINISHED
    assert host_engine.board.to_fen() == client_engine.board.to_fen()
    assert host_engine.history == client_engine.history
    assert not host_inbox.has(NetworkError) and not client_inbox.has(NetworkError)


@pytest.mark.ct("CT-86")
def test_net_partida_aleatoria_ate_o_fim_termina_com_o_mesmo_fen(pair):
    host, client, host_inbox, client_inbox = pair
    rng = random.Random(2)
    engines = {Color.WHITE: GameEngine(), Color.BLACK: GameEngine()}
    peers = {Color.WHITE: (host, client_inbox), Color.BLACK: (client, host_inbox)}
    while engines[Color.WHITE].state is GameState.IN_PROGRESS:
        mover = engines[Color.WHITE].turn
        move = rng.choice(list(legal_moves(engines[mover].board)))
        sender, receiver_inbox = peers[mover]
        relay_move(sender, engines[mover], receiver_inbox, engines[mover.opposite], move.uci)
    assert engines[Color.WHITE].result is not None
    assert engines[Color.WHITE].result == engines[Color.BLACK].result
    assert engines[Color.WHITE].board.to_fen() == engines[Color.BLACK].board.to_fen()


@pytest.mark.ct("CT-86")
def test_net_jogada_ilegal_recebida_e_recusada_pelo_motor_de_quem_recebe(pair):
    """A sessão confere o formato; a legalidade fica com o `GameEngine`, e quem recebe é quem encerra a sala."""
    host, _, _, client_inbox = pair
    host.send_move("e2e5", 0)
    received = client_inbox.wait_for(MoveReceived)
    origin, target, promotion = parse_uci(received.uci)
    assert not GameEngine().play(origin, target, promotion).ok


@pytest.mark.ct("CT-86")
def test_net_inicio_tem_nomes_cores_e_tempo(opened):
    host = open_host(opened, time_control=TimeControl(5, 3), name="Dona da Sala")
    client = open_client(opened, host, name="Visita")
    host_inbox, client_inbox = Inbox(host), Inbox(client)
    assert host_inbox.wait_for(PeerJoined) == PeerJoined("Visita")
    assert client_inbox.wait_for(PeerJoined) == PeerJoined("Dona da Sala")
    assert host_inbox.wait_for(GameStart) == GameStart("Dona da Sala", "Visita", Color.WHITE, 5, 3)
    assert client_inbox.wait_for(GameStart) == GameStart("Dona da Sala", "Visita", Color.BLACK, 5, 3)


@pytest.mark.ct("CT-86")
def test_net_cliente_entra_digitando_o_ip(opened):
    host = open_host(opened)
    client = opened(ClientSession("Pretas", LOCALHOST, port=host.port, timings=QUICK))
    client.start()
    assert Inbox(client).wait_for(GameStart).your_color is Color.BLACK


@pytest.mark.ct("CT-86")
def test_net_cliente_entra_digitando_localhost(opened):
    host = open_host(opened)
    client = opened(ClientSession("Pretas", "LocalHost", port=host.port, timings=QUICK))
    client.start()
    assert Inbox(client).wait_for(GameStart).your_color is Color.BLACK


@pytest.mark.ct("CT-86")
def test_net_cliente_entra_com_o_codigo_em_minusculas_e_espacos(opened):
    host = open_host(opened)
    typed = f" {host.code[:3].lower()} {host.code[3:].lower()} "
    client = opened(ClientSession("Pretas", typed, port=host.port, timings=QUICK))
    client.start()
    assert Inbox(client).wait_for(GameStart).your_color is Color.BLACK


@pytest.mark.ct("CT-86")
def test_net_nome_local_com_caractere_de_controle_nao_impede_a_entrada(opened):
    host = open_host(opened, name="Dona\nda\x00Sala")
    client = open_client(opened, host, name="x" * 100)
    start = Inbox(client).wait_for(GameStart)
    assert start.white == "DonadaSala"
    assert start.black == "x" * 16


@pytest.mark.ct("CT-86")
def test_net_desistencia_chega_ao_outro_lado_nos_dois_sentidos(pair):
    host, client, host_inbox, client_inbox = pair
    host.send_resign()
    client_inbox.wait_for(PeerResigned)
    client.send_resign()
    host_inbox.wait_for(PeerResigned)


@pytest.mark.ct("CT-86")
@pytest.mark.parametrize("accept", [True, False])
def test_net_oferta_e_resposta_de_empate(pair, accept):
    host, client, host_inbox, client_inbox = pair
    host.send_draw_offer()
    client_inbox.wait_for(DrawOffered)
    client.send_draw_answer(accept)
    assert host_inbox.wait_for(DrawAnswered) == DrawAnswered(accept)


@pytest.mark.ct("CT-86")
def test_net_resposta_de_empate_sem_oferta_e_ignorada(pair):
    host, client, host_inbox, _ = pair
    client.send_draw_answer(True)
    client.send_resign()
    host_inbox.wait_for(PeerResigned)
    assert not host_inbox.has(DrawAnswered)


@pytest.mark.ct("CT-86")
def test_net_uma_oferta_aceita_uma_resposta_so(pair):
    host, client, host_inbox, client_inbox = pair
    host.send_draw_offer()
    client_inbox.wait_for(DrawOffered)
    client.send_draw_answer(False)
    client.send_draw_answer(True)
    client.send_resign()
    assert host_inbox.wait_for(DrawAnswered) == DrawAnswered(False)
    host_inbox.wait_for(PeerResigned)
    assert not host_inbox.has(DrawAnswered)


@pytest.mark.ct("CT-86")
def test_net_revanche_pedida_por_quem_entrou_troca_as_cores(pair):
    host, client, host_inbox, client_inbox = pair
    client.send_rematch()
    host_inbox.wait_for(RematchRequested)
    host.send_rematch()
    assert host_inbox.wait_for(GameStart) == GameStart("Pretas", "Brancas", Color.BLACK, 0, 0)
    assert client_inbox.wait_for(GameStart) == GameStart("Pretas", "Brancas", Color.WHITE, 0, 0)


@pytest.mark.ct("CT-86")
def test_net_revanche_pedida_por_quem_criou_troca_as_cores(pair):
    host, client, host_inbox, client_inbox = pair
    host.send_rematch()
    client_inbox.wait_for(RematchRequested)
    client.send_rematch()
    assert host_inbox.wait_for(GameStart).your_color is Color.BLACK
    assert client_inbox.wait_for(GameStart).your_color is Color.WHITE


@pytest.mark.ct("CT-86")
def test_net_revanche_pedida_ao_mesmo_tempo(pair):
    host, client, host_inbox, client_inbox = pair
    host.send_rematch()
    client.send_rematch()
    assert host_inbox.wait_for(GameStart).your_color is Color.BLACK
    assert client_inbox.wait_for(GameStart).your_color is Color.WHITE


@pytest.mark.ct("CT-86")
def test_net_revanche_nao_comeca_com_um_pedido_so(pair):
    host, client, host_inbox, client_inbox = pair
    client.send_rematch()
    host_inbox.wait_for(RematchRequested)
    # A ida e volta em ordem garante que, se fosse começar, o início já teria chegado.
    host.send_resign()
    client_inbox.wait_for(PeerResigned)
    client.send_resign()
    host_inbox.wait_for(PeerResigned)
    assert not host_inbox.has(GameStart)
    assert not client_inbox.has(GameStart)


@pytest.mark.ct("CT-86")
def test_net_revanches_seguidas_alternam_as_cores_e_a_partida_flui(pair):
    host, client, host_inbox, client_inbox = pair
    for host_color in (Color.BLACK, Color.WHITE, Color.BLACK):
        client.send_rematch()
        host_inbox.wait_for(RematchRequested)
        host.send_rematch()
        assert host_inbox.wait_for(GameStart).your_color is host_color
        assert client_inbox.wait_for(GameStart).your_color is host_color.opposite
        white_session, white_receiver = (host, client_inbox) if host_color is Color.WHITE else (client, host_inbox)
        white_session.send_move("e2e4", 5)
        assert white_receiver.wait_for(MoveReceived) == MoveReceived("e2e4", 5)


@pytest.mark.ct("CT-86")
def test_net_pedido_repetido_de_revanche_avisa_uma_vez(pair):
    host, client, host_inbox, client_inbox = pair
    client.send_rematch()
    client.send_rematch()
    client.send_resign()
    host_inbox.wait_for(RematchRequested)
    host_inbox.wait_for(PeerResigned)
    assert not host_inbox.has(RematchRequested)


@pytest.mark.ct("CT-86")
def test_net_relogio_infinito_vai_como_zero(pair):
    host, _, _, client_inbox = pair
    host.send_move("e2e4", float("inf"))
    assert client_inbox.wait_for(MoveReceived) == MoveReceived("e2e4", 0)


@pytest.mark.ct("CT-86")
def test_net_jogada_antes_de_haver_adversario_nao_aparece_depois(opened):
    host = open_host(opened)
    host_inbox = Inbox(host)
    host.send_move("e2e4", 0)
    host.send_resign()
    time.sleep(0.05)
    client = open_client(opened, host)
    client_inbox = Inbox(client)
    client_inbox.wait_for(GameStart)
    host_inbox.wait_for(GameStart)
    host.send_move("d2d4", 0)
    assert client_inbox.wait_for(MoveReceived).uci == "d2d4"
    assert not client_inbox.has(PeerResigned)


@pytest.mark.ct("CT-86")
def test_net_jogada_mal_formada_do_proprio_lado_vira_erro_e_nao_excecao(pair):
    host, _, host_inbox, client_inbox = pair
    host.send_move("nao-e-jogada", 0)
    assert isinstance(host_inbox.wait_for(NetworkError), NetworkError)
    wait_finished(host)
    client_inbox.wait_for(PeerLeft)


@pytest.mark.ct("CT-86")
def test_net_tempo_absurdo_do_criador_vira_erro_e_nao_excecao(opened):
    host = open_host(opened, time_control=TimeControl(10**9))
    open_client(opened, host)
    assert isinstance(Inbox(host).wait_for(NetworkError), NetworkError)


@pytest.mark.ct("CT-87")
def test_net_close_duplo_e_chamadas_depois_de_fechar(pair):
    host, client, _, _ = pair
    host.close()
    client.close()
    assert not session_threads()
    for session in (host, client):
        session.close()
        session.poll()
        session.send_move("e2e4", 0)
        session.send_resign()
        session.send_draw_offer()
        session.send_draw_answer(True)
        session.send_rematch()
        session.send_bye()
        session.start()
        assert session.poll() == []
    assert not session_threads()


@pytest.mark.ct("CT-87")
@pytest.mark.parametrize("make_session", [
    lambda: HostSession("Brancas", TimeControl.UNLIMITED, port=0, bind=LOCALHOST),
    lambda: ClientSession("Pretas", LOCALHOST, port=1),
], ids=["sala", "cliente"])
def test_net_sessao_nunca_iniciada_aceita_qualquer_chamada(make_session):
    session = make_session()
    session.send_move("e2e4", 0)
    session.send_resign()
    assert session.poll() == []
    session.close()
    session.close()
    session.start()
    assert session.poll() == []
    assert not session_threads()


@pytest.mark.ct("CT-87")
def test_net_start_duplo_abre_uma_thread_so(opened):
    host = open_host(opened)
    host.start()
    host.start()
    assert len(session_threads()) == 1


@pytest.mark.ct("CT-87")
def test_net_close_encerra_a_thread_na_hora(opened):
    host = open_host(opened)
    assert len(session_threads()) == 1
    host.close()
    assert not session_threads()


@pytest.mark.ct("CT-87")
def test_net_close_durante_a_conexao_nao_espera_o_timeout(opened):
    """O endereço de documentação não responde: a thread precisa sair mesmo com a conexão ainda em andamento."""
    client = opened(ClientSession("Pretas", "192.0.2.1", port=9, timeout=60, timings=QUICK))
    began = time.monotonic()
    client.start()
    client.poll()
    client.close()
    assert time.monotonic() - began < 5
    assert not session_threads()


@pytest.mark.ct("CT-87")
def test_net_poll_nao_bloqueia_durante_a_espera(opened):
    host = open_host(opened)
    began = time.monotonic()
    for _ in range(1000):
        assert host.poll() == []
    assert time.monotonic() - began < 2


@pytest.mark.ct("CT-87")
def test_net_cliente_que_fecha_vira_peer_left_na_sala(pair):
    _, client, host_inbox, _ = pair
    client.close()
    assert isinstance(host_inbox.wait_for(PeerLeft).reason, str)


@pytest.mark.ct("CT-87")
def test_net_sala_que_fecha_vira_peer_left_no_cliente(pair):
    host, _, _, client_inbox = pair
    host.close()
    assert client_inbox.wait_for(PeerLeft).reason


@pytest.mark.ct("CT-87")
def test_net_despedida_avisa_o_outro_lado_e_encerra_sem_evento_local(pair):
    host, client, host_inbox, client_inbox = pair
    client.send_bye()
    host_inbox.wait_for(PeerLeft)
    wait_finished(client)
    wait_finished(host)
    assert not client_inbox.collect()


@pytest.mark.ct("CT-87")
def test_net_despedida_seguida_de_close_ainda_e_entregue(opened):
    fake = opened(FakeHost())
    client = open_client_to(opened, fake)
    peer = fake.accept()
    peer.read_message()
    peer.send(**start_message())
    Inbox(client).wait_for(GameStart)
    client.send_bye()
    client.close()
    assert peer.read_message() == {"type": "bye"}
    peer.wait_closed()


@pytest.mark.ct("CT-87")
def test_net_pedido_feito_no_instante_do_close_ainda_sai():
    """Sem thread, para fixar a corrida: o pedido entra na fila depois do último ciclo, com o fechamento já marcado."""
    near, far = socket.socketpair()
    far.settimeout(WAIT_SECONDS)
    client = ClientSession("Pretas", LOCALHOST)
    client._selector = selectors.DefaultSelector()
    client._peer = LineConnection(near)
    client._outbox.append({"type": "bye"})
    client._stop.set()
    client._run()
    assert far.recv(4096) == b'{"type":"bye"}\n'
    far.close()


@pytest.mark.ct("CT-87")
def test_net_queda_brusca_de_quem_entrou(opened):
    host = open_host(opened)
    peer = opened(RawPeer.connect(host.port))
    peer.hello()
    peer.read_message()
    host_inbox = Inbox(host)
    host_inbox.wait_for(GameStart)
    peer.abort()
    assert "caiu" in host_inbox.wait_for(PeerLeft).reason
    wait_finished(host)


@pytest.mark.ct("CT-87")
def test_net_queda_brusca_de_quem_criou(opened):
    fake = opened(FakeHost())
    client = open_client_to(opened, fake)
    peer = fake.accept()
    assert peer.read_message()["type"] == "hello"
    peer.send(**start_message())
    client_inbox = Inbox(client)
    client_inbox.wait_for(GameStart)
    peer.abort()
    client_inbox.wait_for(PeerLeft)
    wait_finished(client)


def open_client_to(opened, fake, timeout=WAIT_SECONDS, timings=QUICK):
    client = opened(ClientSession("Pretas", LOCALHOST, port=fake.port, timeout=timeout, timings=timings))
    client.start()
    return client


@pytest.mark.ct("CT-87")
def test_net_sinal_de_vida_parando_vira_peer_left(opened):
    host = open_host(opened, timings=FAST_HEARTBEAT)
    peer = opened(RawPeer.connect(host.port))
    peer.hello()
    assert peer.read_message()["type"] == "start"
    host_inbox = Inbox(host)
    host_inbox.wait_for(GameStart)
    assert "parou de responder" in host_inbox.wait_for(PeerLeft).reason
    wait_finished(host)


@pytest.mark.ct("CT-87")
def test_net_sinal_de_vida_parando_do_lado_da_sala_vira_peer_left(opened):
    fake = opened(FakeHost())
    client = open_client_to(opened, fake, timings=FAST_HEARTBEAT)
    peer = fake.accept()
    peer.read_message()
    peer.send(**start_message())
    client_inbox = Inbox(client)
    client_inbox.wait_for(GameStart)
    assert "parou de responder" in client_inbox.wait_for(PeerLeft).reason
    wait_finished(client)


@pytest.mark.ct("CT-87")
def test_net_prazo_do_sinal_de_vida_conta_a_partir_da_ultima_mensagem():
    """Sem thread e com o instante passado à mão: os 2 s e os 8 s reais valem sem o teste esperar por eles."""
    near, far = socket.socketpair()
    client = ClientSession("Pretas", LOCALHOST)
    client._peer = LineConnection(near)
    client._handle_peer_line(b'{"type":"ping"}')
    heard = client._last_heard
    assert heard > 0
    client._next_ping = heard + 2.0
    client._check_timers(heard + 1.9)
    assert not client._peer._outgoing
    client._check_timers(heard + 2.0)
    assert client._peer._outgoing == b'{"type":"ping"}\n'
    client._check_timers(heard + 7.9)
    assert client.poll() == []
    client._check_timers(heard + 8.0)
    assert client.poll() == [PeerLeft("O adversário parou de responder.")]
    near.close()
    far.close()


@pytest.mark.ct("CT-87")
def test_net_sinais_de_vida_mantem_a_partida_alem_do_prazo(opened):
    timings = NetTimings(heartbeat_interval=0.05, heartbeat_timeout=2.0, tick=0.002)
    host = open_host(opened, timings=timings)
    client = open_client(opened, host, timings=timings)
    host_inbox, client_inbox = Inbox(host), Inbox(client)
    host_inbox.wait_for(GameStart)
    client_inbox.wait_for(GameStart)
    time.sleep(2.2)
    assert not host_inbox.has(PeerLeft) and not client_inbox.has(PeerLeft)
    host.send_move("e2e4", 1)
    assert client_inbox.wait_for(MoveReceived).uci == "e2e4"


@pytest.mark.ct("CT-87")
def test_net_sinal_de_vida_e_enviado_pela_sala(opened):
    host = open_host(opened, timings=NetTimings(heartbeat_interval=0.02, heartbeat_timeout=30, tick=0.002))
    peer = opened(RawPeer.connect(host.port))
    peer.hello()
    peer.read_message()
    peer.socket.settimeout(WAIT_SECONDS)
    assert b'"ping"' in peer.socket.recv(4096)


@pytest.mark.ct("CT-87")
def test_net_envio_depois_da_queda_nao_levanta_excecao(pair):
    host, client, host_inbox, _ = pair
    client.close()
    host_inbox.wait_for(PeerLeft)
    host.send_move("e2e4", 0)
    host.send_resign()
    host.send_draw_offer()
    host.send_rematch()
    host.send_bye()
    assert host.poll() == []
    wait_finished(host)
    host.close()


@pytest.mark.ct("CT-87")
def test_net_evento_final_e_unico(pair):
    _, client, host_inbox, _ = pair
    client.send_bye()
    host_inbox.wait_for(PeerLeft)
    time.sleep(0.05)
    assert not host_inbox.has(PeerLeft) and not host_inbox.has(NetworkError)


@pytest.mark.ct("CT-87")
def test_net_porta_ocupada_vira_erro_claro(opened):
    blocker = opened(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    blocker.bind((LOCALHOST, 0))
    blocker.listen(1)
    port = blocker.getsockname()[1]
    host = opened(HostSession("Brancas", TimeControl.UNLIMITED, port=port, bind=LOCALHOST, timings=QUICK))
    host.start()
    error = Inbox(host).wait_for(NetworkError)
    assert str(port) in error.message and "ocupada" in error.message
    assert not session_threads()
    host.close()


@pytest.mark.ct("CT-87")
def test_net_duas_salas_na_mesma_porta_a_segunda_recebe_erro(opened):
    """Duas cópias do jogo no mesmo computador: nenhuma pode abrir a porta por cima da outra e roubar a conexão."""
    first = open_host(opened)
    second = opened(HostSession("Outra", TimeControl.UNLIMITED, port=first.port, bind=LOCALHOST, timings=QUICK))
    second.start()
    assert "ocupada" in Inbox(second).wait_for(NetworkError).message
    assert Inbox(open_client(opened, first)).wait_for(GameStart).white == "Brancas"


@pytest.mark.ct("CT-87")
def test_net_porta_impossivel_vira_erro_e_nao_excecao(opened):
    host = opened(HostSession("Brancas", TimeControl.UNLIMITED, port=70000, bind=LOCALHOST, timings=QUICK))
    host.start()
    assert "70000" in Inbox(host).wait_for(NetworkError).message
    client = opened(ClientSession("Pretas", LOCALHOST, port=70000, timings=QUICK))
    client.start()
    assert isinstance(Inbox(client).wait_for(NetworkError), NetworkError)


@pytest.mark.ct("CT-87")
def test_net_porta_fica_livre_depois_que_a_sala_fecha(opened):
    host = open_host(opened)
    port = host.port
    peer = opened(RawPeer.connect(port))
    peer.hello()
    peer.read_message()
    host.close()
    peer.wait_closed()
    reopened = opened(HostSession("Brancas", TimeControl.UNLIMITED, port=port, bind=LOCALHOST, timings=QUICK))
    reopened.start()
    time.sleep(0.05)
    assert not Inbox(reopened).has(NetworkError)
    assert reopened.port == port


@pytest.mark.ct("CT-87")
def test_net_porta_fica_livre_depois_que_o_adversario_sai(opened):
    host = open_host(opened)
    port = host.port
    client = open_client(opened, host)
    host_inbox = Inbox(host)
    host_inbox.wait_for(GameStart)
    client.close()
    host_inbox.wait_for(PeerLeft)
    wait_finished(host)
    assert host._listener.fileno() == -1
    assert port != 0


@pytest.mark.ct("CT-87")
def test_net_segundo_cliente_recusado_sem_derrubar_a_partida(pair, opened):
    host, client, host_inbox, client_inbox = pair
    intruder = opened(ClientSession("Intruso", LOCALHOST, port=host.port, timings=QUICK))
    intruder.start()
    assert "Sala cheia" in Inbox(intruder).wait_for(NetworkError).message
    wait_finished(intruder)
    host.send_move("e2e4", 1)
    assert client_inbox.wait_for(MoveReceived).uci == "e2e4"
    client.send_move("e7e5", 2)
    assert host_inbox.wait_for(MoveReceived).uci == "e7e5"
    assert not host_inbox.has(PeerJoined)
    assert not host_inbox.has(NetworkError) and not host_inbox.has(PeerLeft)


@pytest.mark.ct("CT-87")
def test_net_versao_diferente_e_recusada_com_mensagem_clara(opened):
    host = open_host(opened)
    peer = opened(RawPeer.connect(host.port))
    peer.hello(version=99)
    assert peer.read_message() == {"type": "refused", "code": "version"}
    peer.wait_closed()
    client = open_client(opened, host)
    assert Inbox(client).wait_for(GameStart).your_color is Color.BLACK


@pytest.mark.ct("CT-87")
def test_net_cliente_recusado_por_versao_mostra_a_mensagem(opened):
    fake = opened(FakeHost())
    client = open_client_to(opened, fake)
    peer = fake.accept()
    peer.read_message()
    peer.send(type="refused", code="version")
    assert "versões diferentes" in Inbox(client).wait_for(NetworkError).message


@pytest.mark.ct("CT-87")
@pytest.mark.parametrize("typed", ["", "ABC", "ABCDEF0", "ZZZZZZZ", None, 123, "um.nome.qualquer"])
def test_net_codigo_invalido_vira_erro_em_portugues_sem_thread(opened, typed):
    client = opened(ClientSession("Pretas", typed, timings=QUICK))
    client.start()
    assert Inbox(client).wait_for(NetworkError).message
    assert not session_threads()
    client.close()


@pytest.mark.ct("CT-87")
@pytest.mark.parametrize("typed", ["1.2.3.4", encode_room_code("1.2.3.4")], ids=["ip", "codigo"])
def test_net_destino_fora_da_rede_local_nem_tenta_conectar(opened, monkeypatch, typed):
    def fail_if_used(*args):
        raise AssertionError("não deveria abrir socket")

    monkeypatch.setattr("xadrez.net.session.socket.socket", fail_if_used)
    client = opened(ClientSession("Pretas", typed, timings=QUICK))
    client.start()
    assert "fora da rede local" in Inbox(client).wait_for(NetworkError).message


@pytest.mark.ct("CT-87")
def test_net_ninguem_na_porta_vira_erro(opened):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((LOCALHOST, 0))
        free_port = probe.getsockname()[1]
    client = opened(ClientSession("Pretas", LOCALHOST, port=free_port, timeout=WAIT_SECONDS, timings=QUICK))
    client.start()
    assert "Não foi possível conectar" in Inbox(client).wait_for(NetworkError).message
    wait_finished(client)


@pytest.mark.ct("CT-87")
def test_net_conexao_recusada_de_imediato_vira_erro(opened):
    """A porta 0 não aceita conexão: conforme o sistema, a recusa vem na hora, sem passar pela espera."""
    client = opened(ClientSession("Pretas", LOCALHOST, port=0, timeout=WAIT_SECONDS, timings=QUICK))
    client.start()
    assert "Não foi possível conectar" in Inbox(client).wait_for(NetworkError).message


@pytest.mark.ct("CT-87")
def test_net_sala_que_nao_responde_vira_erro_no_prazo(opened):
    fake = opened(FakeHost())
    client = open_client_to(opened, fake, timeout=0.2)
    assert "não respondeu" in Inbox(client).wait_for(NetworkError).message
    wait_finished(client)


@pytest.mark.ct("CT-87")
def test_net_sala_que_fecha_antes_de_responder_vira_erro(opened):
    fake = opened(FakeHost())
    client = open_client_to(opened, fake)
    fake.accept().close()
    assert "Não foi possível conectar" in Inbox(client).wait_for(NetworkError).message
    wait_finished(client)


@pytest.mark.ct("CT-87")
def test_net_falha_ao_abrir_o_seletor_vira_erro_e_nao_excecao(opened, monkeypatch):
    def refuse():
        raise OSError("sem descritores")

    monkeypatch.setattr("xadrez.net.session.selectors.DefaultSelector", refuse)
    host = opened(HostSession("Brancas", TimeControl.UNLIMITED, port=0, bind=LOCALHOST, timings=QUICK))
    host.start()
    assert isinstance(Inbox(host).wait_for(NetworkError), NetworkError)


@pytest.mark.ct("CT-87")
def test_net_defeito_inesperado_na_thread_vira_erro_e_nao_morte_silenciosa(opened, monkeypatch):
    host = open_host(opened)

    def explode(now):
        raise RuntimeError("defeito simulado")

    monkeypatch.setattr(host, "_check_timers", explode)
    assert "inesperado" in Inbox(host).wait_for(NetworkError).message
    wait_finished(host)
