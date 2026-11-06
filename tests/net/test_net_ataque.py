"""CT-88: ataques com socket cru. Nada que venha da rede pode derrubar, travar nem enganar o jogo."""
import json
import random
import time

import pytest
from net_helpers import QUICK, WAIT_SECONDS, FakeHost, Inbox, RawPeer, open_client, open_host, start_message

from xadrez.net import (
    ClientSession,
    DrawAnswered,
    GameStart,
    MoveReceived,
    NetTimings,
    NetworkError,
    PeerJoined,
    PeerLeft,
)
from xadrez.net import PROTOCOL_VERSION
from xadrez.net import session as session_module
from xadrez.net.protocol import MAX_LINE_BYTES

BIDI_OVERRIDE = chr(0x202E)
SHORT_HANDSHAKE = NetTimings(handshake_timeout=0.2, tick=0.002)


def hello_line(**changes):
    return json.dumps({"type": "hello", "version": PROTOCOL_VERSION, "name": "Pretas", **changes}).encode() + b"\n"


# Linhas inválidas em qualquer momento da conversa, para quem cria a sala e para quem entra.
GARBAGE = {
    "texto": b"isto nao e json\n",
    "binario": b"\xff\xfe\x00\x01\x02\n",
    "linha-vazia": b"\n",
    "objeto-vazio": b"{}\n",
    "lista": b"[]\n",
    "nulo": b"null\n",
    "numero": b"123\n",
    "texto-json": b'"hello"\n',
    "tipo-desconhecido": b'{"type":"desconhecido"}\n',
    "tipo-nao-texto": b'{"type":["hello"]}\n',
    "aninhamento": b"[" * 4000 + b"\n",
    "aninhamento-objeto": b'{"a":' * 800 + b"\n",
    "numero-gigante": b"9" * 4000 + b"\n",
    "constante-nan": b"NaN\n",
    "linha-no-limite": b"x" * MAX_LINE_BYTES + b"\n",
    "linha-gigante": b"x" * 200_000,
    "linha-gigante-com-fim": b"x" * 200_000 + b"\n",
}
BAD_HELLOS = {
    "sem-versao": b'{"type":"hello","name":"x"}\n',
    "sem-nome": b'{"type":"hello","version":1}\n',
    "versao-texto": hello_line(version="1"),
    "versao-booleano": hello_line(version=True),
    "versao-decimal": hello_line(version=1.0),
    "versao-negativa": hello_line(version=-1),
    "versao-gigante": hello_line(version=10**30),
    "versao-nula": hello_line(version=None),
    "nome-numero": hello_line(name=123),
    "nome-nulo": hello_line(name=None),
    "nome-lista": hello_line(name=["x"]),
    "nome-vazio": hello_line(name=""),
    "nome-espacos": hello_line(name="    "),
    "nome-longo": hello_line(name="x" * 17),
    "nome-enorme": hello_line(name="x" * 3000),
    "nome-controle": hello_line(name="a\nb"),
    "nome-nulo-embutido": hello_line(name="a\x00b"),
    "nome-escape-terminal": hello_line(name="\x1b[31mx"),
    "nome-bidi": hello_line(name=f"a{BIDI_OVERRIDE}b"),
    "nome-surrogate": b'{"type":"hello","version":1,"name":"\\ud800"}\n',
    "campo-a-mais": hello_line(admin=True),
}
BAD_IN_GAME = {
    "jogada-sem-relogio": b'{"type":"move","uci":"e2e4"}\n',
    "jogada-fora-do-tabuleiro": b'{"type":"move","uci":"e2e9","clock_ms":1}\n',
    "jogada-com-nova-linha": b'{"type":"move","uci":"e2e4\\n","clock_ms":1}\n',
    "jogada-numero": b'{"type":"move","uci":123,"clock_ms":1}\n',
    "jogada-promove-a-rei": b'{"type":"move","uci":"a7a8k","clock_ms":1}\n',
    "relogio-negativo": b'{"type":"move","uci":"e2e4","clock_ms":-1}\n',
    "relogio-booleano": b'{"type":"move","uci":"e2e4","clock_ms":true}\n',
    "relogio-decimal": b'{"type":"move","uci":"e2e4","clock_ms":1.5}\n',
    "relogio-texto": b'{"type":"move","uci":"e2e4","clock_ms":"1"}\n',
    "relogio-infinito": b'{"type":"move","uci":"e2e4","clock_ms":1e999}\n',
    "relogio-nan": b'{"type":"move","uci":"e2e4","clock_ms":NaN}\n',
    "relogio-gigante": b'{"type":"move","uci":"e2e4","clock_ms":' + b"9" * 4000 + b"}\n",
    "campo-a-mais": b'{"type":"move","uci":"e2e4","clock_ms":1,"extra":1}\n',
    "resposta-nao-booleana": b'{"type":"draw_answer","accept":"sim"}\n',
    "desistencia-com-campo": b'{"type":"resign","color":"white"}\n',
    "hello-fora-de-hora": hello_line(),
    "recusa-fora-de-hora": b'{"type":"refused","code":"room_full"}\n',
}
HOST_LOBBY_ATTACKS = {**GARBAGE, **BAD_HELLOS, "mensagem-valida-fora-de-hora": b'{"type":"ping"}\n'}
IN_GAME_ATTACKS = {**GARBAGE, **BAD_IN_GAME}


def raw_player(opened, host):
    """Entra na sala como um cliente de verdade até o início da partida, para atacar já de dentro."""
    peer = opened(RawPeer.connect(host.port))
    peer.hello()
    assert peer.read_message()["type"] == "start"
    inbox = Inbox(host)
    inbox.wait_for(PeerJoined)
    inbox.wait_for(GameStart)
    return peer, inbox


def joined_fake_host(opened, timings=QUICK):
    """Cliente de verdade numa sala falsa, já em partida."""
    fake = opened(FakeHost())
    client = opened(ClientSession("Pretas", "127.0.0.1", port=fake.port, timeout=WAIT_SECONDS, timings=timings))
    client.start()
    peer = fake.accept()
    assert peer.read_message()["type"] == "hello"
    peer.send(**start_message())
    inbox = Inbox(client)
    inbox.wait_for(PeerJoined)
    inbox.wait_for(GameStart)
    return peer, client, inbox


def assert_real_client_can_still_join(opened, host):
    # O prazo curto de handshake é só para o atacante cair rápido. Num CI lento, um cliente de verdade não caberia nele.
    host._timings = QUICK
    client = open_client(opened, host)
    assert Inbox(client).wait_for(GameStart).black == "Pretas"
    assert Inbox(host).wait_for(GameStart).black == "Pretas"


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize("attack", HOST_LOBBY_ATTACKS.values(), ids=HOST_LOBBY_ATTACKS.keys())
def test_net_ataque_antes_de_entrar_derruba_so_a_conexao_do_atacante(opened, attack):
    host = open_host(opened)
    attacker = opened(RawPeer.connect(host.port))
    attacker.send_bytes(attack)
    attacker.wait_closed()
    assert host.poll() == []
    assert_real_client_can_still_join(opened, host)


@pytest.mark.ct("CT-88")
def test_net_ataque_com_bytes_aleatorios_antes_de_entrar(opened):
    host = open_host(opened)
    rng = random.Random(88)
    for size in (1, 7, 100, 4097, 20000):
        attacker = opened(RawPeer.connect(host.port))
        # O fim de linha garante que os bytes sejam avaliados, em vez de ficarem à espera do resto.
        attacker.send_bytes(rng.randbytes(size) + b"\n")
        attacker.wait_closed()
    assert host.poll() == []
    assert_real_client_can_still_join(opened, host)


@pytest.mark.ct("CT-88")
def test_net_conexao_muda_nao_segura_a_sala(opened):
    host = open_host(opened, timings=SHORT_HANDSHAKE)
    mute = opened(RawPeer.connect(host.port))
    mute.wait_closed()
    assert host.poll() == []
    assert_real_client_can_still_join(opened, host)


@pytest.mark.ct("CT-88")
def test_net_conexao_que_pinga_um_byte_por_vez_tambem_cai_no_prazo(opened):
    host = open_host(opened, timings=SHORT_HANDSHAKE)
    slow = opened(RawPeer.connect(host.port))
    deadline = time.monotonic() + WAIT_SECONDS
    closed = False
    while not closed and time.monotonic() < deadline:
        slow.send_bytes(b"{")
        slow.socket.settimeout(0.02)
        try:
            closed = slow.socket.recv(1) == b""
        except TimeoutError:
            pass
        except OSError:
            closed = True
    assert closed
    assert host.poll() == []


@pytest.mark.ct("CT-88")
def test_net_muitas_conexoes_mudas_nao_acumulam_e_a_sala_sobrevive(opened):
    host = open_host(opened, timings=SHORT_HANDSHAKE)
    attackers = []
    for _ in range(30):
        # Com a fila do sistema cheia, a conexão pode ser recusada: para este ataque, isso também é a sala se defendendo.
        try:
            attackers.append(opened(RawPeer.connect(host.port)))
        except OSError:
            pass
    assert attackers
    for attacker in attackers:
        attacker.wait_closed()
    deadline = time.monotonic() + WAIT_SECONDS
    while (host._handshakes or host._refusals) and time.monotonic() < deadline:
        time.sleep(0.005)
    assert not host._handshakes and not host._refusals
    assert host.poll() == []
    assert_real_client_can_still_join(opened, host)


@pytest.mark.ct("CT-88")
def test_net_sala_recusa_conexao_vinda_de_fora_da_rede_local(opened, monkeypatch):
    monkeypatch.setattr(session_module, "is_lan_address", lambda address: False)
    host = open_host(opened)
    outsider = opened(RawPeer.connect(host.port))
    outsider.hello()
    outsider.wait_closed()
    assert host.poll() == []


@pytest.mark.ct("CT-88")
def test_net_conexao_que_cai_antes_de_entrar_nao_afeta_a_sala(opened):
    host = open_host(opened)
    quitter = RawPeer.connect(host.port)
    quitter.abort()
    assert_real_client_can_still_join(opened, host)


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize("attack", IN_GAME_ATTACKS.values(), ids=IN_GAME_ATTACKS.keys())
def test_net_ataque_de_dentro_da_partida_encerra_a_sala_com_erro(opened, attack):
    host = open_host(opened)
    peer, inbox = raw_player(opened, host)
    peer.send_bytes(attack)
    assert "inválidos" in inbox.wait_for(NetworkError).message
    peer.wait_closed()
    host._thread.join(WAIT_SECONDS)
    assert not host._thread.is_alive()
    assert host._listener.fileno() == -1
    assert not inbox.has(MoveReceived)


@pytest.mark.ct("CT-88")
def test_net_ataque_com_bytes_aleatorios_de_dentro_da_partida(opened):
    host = open_host(opened)
    peer, inbox = raw_player(opened, host)
    peer.send_bytes(random.Random(89).randbytes(8000) + b"\n")
    assert isinstance(inbox.wait_for(NetworkError), NetworkError)
    peer.wait_closed()


@pytest.mark.ct("CT-88")
def test_net_mensagem_valida_antes_da_invalida_ainda_e_entregue(opened):
    host = open_host(opened)
    peer, inbox = raw_player(opened, host)
    peer.send_bytes(b'{"type":"move","uci":"e2e4","clock_ms":1}\nlixo\n{"type":"move","uci":"d2d4","clock_ms":1}\n')
    inbox.wait_for(NetworkError)
    assert inbox.pending == [MoveReceived("e2e4", 1)]


@pytest.mark.ct("CT-88")
def test_net_jogada_colada_na_entrada_e_processada_em_ordem(opened):
    host = open_host(opened)
    peer = opened(RawPeer.connect(host.port))
    peer.send_bytes(hello_line() + b'{"type":"move","uci":"e2e4","clock_ms":1}\n')
    inbox = Inbox(host)
    assert inbox.wait_for(MoveReceived) == MoveReceived("e2e4", 1)
    assert inbox.pending[0] == PeerJoined("Pretas")


@pytest.mark.ct("CT-88")
def test_net_segundo_hello_colado_no_primeiro_encerra_como_mensagem_invalida(opened):
    host = open_host(opened)
    peer = opened(RawPeer.connect(host.port))
    peer.send_bytes(hello_line() + hello_line(name="Outro"))
    assert "inválidos" in Inbox(host).wait_for(NetworkError).message


@pytest.mark.ct("CT-88")
def test_net_enxurrada_de_mensagens_encerra_a_conexao(opened):
    host = open_host(opened)
    peer, inbox = raw_player(opened, host)
    peer.send_bytes(b'{"type":"ping"}\n' * 200_000)
    assert isinstance(inbox.wait_for(NetworkError), NetworkError)
    peer.wait_closed()


@pytest.mark.ct("CT-88")
def test_net_fila_de_eventos_tem_limite_se_a_tela_nao_chamar_poll(opened):
    host = open_host(opened)
    peer, inbox = raw_player(opened, host)
    assert host.poll() == []
    peer.send_bytes(b'{"type":"draw_offer"}\n' * 1500)
    host._thread.join(WAIT_SECONDS)
    assert not host._thread.is_alive()
    events = inbox.collect()
    assert len(events) <= 1025
    assert isinstance(events[-1], NetworkError)


@pytest.mark.ct("CT-88")
def test_net_sinal_de_vida_falso_em_pedacos_nao_segura_a_sala(opened):
    """Um byte por vez nunca completa uma linha, então não conta como sinal de vida."""
    timings = NetTimings(heartbeat_interval=0.05, heartbeat_timeout=0.5, tick=0.002)
    host = open_host(opened, timings=timings)
    peer, inbox = raw_player(opened, host)
    deadline = time.monotonic() + WAIT_SECONDS
    while not inbox.has(PeerLeft) and time.monotonic() < deadline:
        peer.send_bytes(b" ")
        time.sleep(0.02)
    assert "parou de responder" in inbox.wait_for(PeerLeft).reason


@pytest.mark.ct("CT-88")
def test_net_resposta_de_empate_falsa_nao_vira_empate(opened):
    host = open_host(opened)
    peer, inbox = raw_player(opened, host)
    peer.send(type="draw_answer", accept=True)
    peer.send(type="move", uci="e7e5", clock_ms=1)
    inbox.wait_for(MoveReceived)
    assert not inbox.has(DrawAnswered)


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize("attack", GARBAGE.values(), ids=GARBAGE.keys())
def test_net_cliente_recusa_lixo_antes_do_inicio_da_partida(opened, attack):
    fake = opened(FakeHost())
    client = opened(ClientSession("Pretas", "127.0.0.1", port=fake.port, timeout=WAIT_SECONDS, timings=QUICK))
    client.start()
    peer = fake.accept()
    peer.read_message()
    peer.send_bytes(attack)
    assert "inválidos" in Inbox(client).wait_for(NetworkError).message
    client._thread.join(WAIT_SECONDS)
    assert not client._thread.is_alive()


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize(
    "attack",
    [
        b'{"type":"ping"}\n',
        b'{"type":"move","uci":"e2e4","clock_ms":1}\n',
        b'{"type":"refused","code":"qualquer"}\n',
        b'{"type":"refused","code":["room_full"]}\n',
        json.dumps({**start_message(), "your_color": "red"}).encode() + b"\n",
        json.dumps({**start_message(), "minutes": -5}).encode() + b"\n",
        json.dumps({**start_message(), "minutes": True}).encode() + b"\n",
        json.dumps({**start_message(), "white": "a\nb"}).encode() + b"\n",
        json.dumps({**start_message(), "black": "x" * 3000}).encode() + b"\n",
    ],
    ids=["ping", "jogada", "recusa-desconhecida", "recusa-lista", "cor", "tempo-negativo", "tempo-booleano", "nome-controle", "nome-longo"],
)
def test_net_cliente_recusa_resposta_errada_a_entrada(opened, attack):
    fake = opened(FakeHost())
    client = opened(ClientSession("Pretas", "127.0.0.1", port=fake.port, timeout=WAIT_SECONDS, timings=QUICK))
    client.start()
    peer = fake.accept()
    peer.read_message()
    peer.send_bytes(attack)
    assert "inválidos" in Inbox(client).wait_for(NetworkError).message


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize("attack", IN_GAME_ATTACKS.values(), ids=IN_GAME_ATTACKS.keys())
def test_net_cliente_recusa_ataque_durante_a_partida(opened, attack):
    peer, client, inbox = joined_fake_host(opened)
    peer.send_bytes(attack)
    assert "inválidos" in inbox.wait_for(NetworkError).message
    client._thread.join(WAIT_SECONDS)
    assert not client._thread.is_alive()
    assert not inbox.has(MoveReceived)


@pytest.mark.ct("CT-88")
def test_net_sala_nao_pode_reiniciar_a_partida_sem_revanche_pedida(opened):
    peer, _, inbox = joined_fake_host(opened)
    peer.send(**start_message(your_color="white"))
    assert "inválidos" in inbox.wait_for(NetworkError).message
    assert not inbox.has(GameStart)


@pytest.mark.ct("CT-88")
def test_net_cliente_com_revanche_pedida_aceita_o_novo_inicio(opened):
    peer, client, inbox = joined_fake_host(opened)
    client.send_rematch()
    assert peer.read_message() == {"type": "rematch"}
    peer.send(**start_message(your_color="white"))
    assert inbox.wait_for(GameStart).your_color.value == "white"


@pytest.mark.ct("CT-88")
def test_net_cliente_nao_acumula_fala_antes_do_inicio(opened):
    fake = opened(FakeHost())
    client = opened(ClientSession("Pretas", "127.0.0.1", port=fake.port, timeout=WAIT_SECONDS, timings=QUICK))
    client.start()
    client.send_move("e2e4", 1)
    peer = fake.accept()
    assert peer.read_message()["type"] == "hello"
    peer.send(**start_message())
    Inbox(client).wait_for(GameStart)
    client.send_resign()
    assert peer.read_message() == {"type": "resign"}


@pytest.mark.ct("CT-88")
def test_net_nome_do_atacante_nao_chega_a_tela(opened):
    host = open_host(opened)
    attacker = opened(RawPeer.connect(host.port))
    attacker.send_bytes(hello_line(name="\x1b[2J\n\rlimpa"))
    attacker.wait_closed()
    assert not Inbox(host).has(PeerJoined)
