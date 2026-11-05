"""CT-87: o socket não bloqueante nunca segura a thread da sessão, nem quando o outro lado para de ler ou some."""
import socket

import pytest
from net_helpers import WAIT_SECONDS

from xadrez.core import TimeControl
from xadrez.net import HostSession
from xadrez.net import connection as connection_module
from xadrez.net.connection import LineConnection, PeerGone
from xadrez.net.protocol import ProtocolError


class BrokenSocket:
    """Imita um socket cujo outro lado já sumiu."""

    def setblocking(self, flag):
        pass

    def send(self, data):
        raise ConnectionResetError("conexão perdida")

    def recv(self, size):
        raise ConnectionResetError("conexão perdida")

    def shutdown(self, how):
        raise OSError("não conectado")

    def close(self):
        self.closed = True


class CloggedSocket:
    """Aceita 4 bytes e então se comporta como um buffer cheio."""

    def __init__(self):
        self.sent = b""
        self.is_clogged = True

    def setblocking(self, flag):
        pass

    def send(self, data):
        if self.is_clogged and self.sent:
            raise BlockingIOError
        accepted = bytes(data[:4])
        self.sent += accepted
        return len(accepted)


@pytest.fixture
def linked():
    near, far = socket.socketpair()
    far.settimeout(WAIT_SECONDS)
    yield LineConnection(near), far
    near.close()
    far.close()


@pytest.mark.ct("CT-87")
def test_net_leitura_sem_dados_nao_bloqueia(linked):
    connection, _ = linked
    assert connection.read_lines() == []
    connection.discard_input()


@pytest.mark.ct("CT-87")
def test_net_outro_lado_que_para_de_ler_nao_bloqueia_o_envio():
    """Com socket falso porque cada sistema aceita um volume diferente antes de encher o buffer de verdade."""
    clogged = CloggedSocket()
    connection = LineConnection(clogged)
    connection.queue(b"0123456789")
    connection.flush()
    assert clogged.sent == b"0123"
    assert connection._outgoing == b"456789"
    clogged.is_clogged = False
    connection.flush()
    assert clogged.sent == b"0123456789"
    assert not connection._outgoing


@pytest.mark.ct("CT-87")
def test_net_outro_lado_que_fecha_vira_peer_gone_na_leitura(linked):
    connection, far = linked
    far.close()
    with pytest.raises(PeerGone):
        connection.read_lines()


@pytest.mark.ct("CT-87")
def test_net_conexao_perdida_vira_peer_gone():
    connection = LineConnection(BrokenSocket())
    with pytest.raises(PeerGone, match="caiu"):
        connection.read_lines()
    connection.queue(b"x")
    with pytest.raises(PeerGone, match="caiu"):
        connection.flush()


@pytest.mark.ct("CT-87")
def test_net_fechar_conexao_perdida_nao_levanta_excecao():
    broken = BrokenSocket()
    connection = LineConnection(broken)
    connection.queue(b"x")
    connection.close_gracefully()
    assert broken.closed


@pytest.mark.ct("CT-87")
def test_net_fechamento_entrega_o_que_estava_na_fila(linked):
    connection, far = linked
    connection.queue(b'{"type":"bye"}\n')
    connection.close_gracefully()
    assert far.recv(4096) == b'{"type":"bye"}\n'
    assert far.recv(4096) == b""


@pytest.mark.ct("CT-88")
def test_net_limite_de_mensagens_vale_por_segundo(linked, monkeypatch):
    connection, far = linked
    monkeypatch.setattr(connection_module, "_MAX_MESSAGES_PER_SECOND", 2)
    far.sendall(b"a\nb\n")
    assert connection_lines(connection) == [b"a", b"b"]
    connection._window_start -= 2.0
    far.sendall(b"c\nd\n")
    assert connection_lines(connection) == [b"c", b"d"]
    far.sendall(b"e\n")
    with pytest.raises(ProtocolError):
        connection_lines(connection)


def connection_lines(connection):
    """Espera os dados chegarem pelo socket, sem depender de tempo."""
    connection._socket.setblocking(True)
    connection._socket.settimeout(WAIT_SECONDS)
    lines = connection.read_lines()
    connection._socket.setblocking(False)
    return lines


@pytest.mark.ct("CT-87")
def test_net_recusa_para_quem_ja_caiu_nao_afeta_a_sala():
    host = HostSession("Brancas", TimeControl.UNLIMITED, port=0, bind="127.0.0.1")

    class Selector:
        unregistered = []

        def unregister(self, item):
            self.unregistered.append(item)

    host._selector = Selector()
    connection = LineConnection(BrokenSocket())
    host._handshakes[connection] = 0.0
    host._refuse(connection, "room_full")
    assert connection not in host._handshakes and connection not in host._refusals
    assert Selector.unregistered == [connection]
