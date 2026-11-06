"""Atalhos dos testes de rede: esperar eventos com prazo e imitar o outro lado com um socket cru."""
import json
import socket
import struct
import time

from xadrez.core import TimeControl
from xadrez.net import PROTOCOL_VERSION, ClientSession, HostSession, NetTimings

LOCALHOST = "127.0.0.1"
# Prazo só de falha: o teste segue assim que o evento chega, então a folga não o deixa mais lento.
WAIT_SECONDS = 30.0
POLL_STEP_SECONDS = 0.001
# Sinal de vida real, com o ciclo da sessão rápido: uma pausa do CI não pode virar queda de conexão.
QUICK = NetTimings(tick=0.002)


class Inbox:
    """Guarda o que saiu de `poll()`, para esperar um evento sem perder os outros."""

    def __init__(self, session):
        self.session = session
        self.pending = []

    def collect(self):
        self.pending.extend(self.session.poll())
        return self.pending

    def wait_for(self, event_type, timeout=WAIT_SECONDS):
        deadline = time.monotonic() + timeout
        while True:
            for index, event in enumerate(self.collect()):
                if isinstance(event, event_type):
                    del self.pending[index]
                    return event
            if time.monotonic() >= deadline:
                raise AssertionError(f"{event_type.__name__} não chegou em {timeout} s; recebidos: {self.pending}")
            time.sleep(POLL_STEP_SECONDS)

    def has(self, event_type):
        return any(isinstance(event, event_type) for event in self.collect())


class RawPeer:
    """O outro lado sem nenhuma regra do jogo: manda exatamente os bytes que o teste pedir."""

    def __init__(self, connected_socket):
        self.socket = connected_socket
        self.socket.settimeout(WAIT_SECONDS)
        self._buffer = b""

    @classmethod
    def connect(cls, port):
        return cls(socket.create_connection((LOCALHOST, port), timeout=WAIT_SECONDS))

    def send_bytes(self, data):
        """Ignora erro de envio: o outro lado pode já ter fechado por causa do que recebeu antes."""
        try:
            self.socket.sendall(data)
        except OSError:
            pass

    def send(self, **message):
        self.send_bytes(json.dumps(message).encode() + b"\n")

    def hello(self, name="Pretas", version=PROTOCOL_VERSION):
        self.send(type="hello", version=version, name=name)

    def read_message(self):
        """Próxima mensagem, sem os sinais de vida."""
        while True:
            while b"\n" not in self._buffer:
                chunk = self.socket.recv(4096)
                assert chunk, f"conexão fechada antes do fim da linha: {self._buffer!r}"
                self._buffer += chunk
            line, self._buffer = self._buffer.split(b"\n", 1)
            message = json.loads(line)
            if message["type"] != "ping":
                return message

    def wait_closed(self):
        """Falha por timeout se o outro lado não fechar a conexão."""
        try:
            while self.socket.recv(4096):
                pass
        except (ConnectionError, OSError) as error:
            assert not isinstance(error, socket.timeout), "o outro lado não fechou a conexão"

    def abort(self):
        """Queda brusca: o RST não dá ao outro lado a chance de um fechamento normal."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        self.socket.close()

    def close(self):
        self.socket.close()


class FakeHost:
    """Sala de mentira, para atacar `ClientSession` com bytes escolhidos pelo teste."""

    def __init__(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.settimeout(WAIT_SECONDS)
        self.listener.bind((LOCALHOST, 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.peers = []

    def accept(self):
        accepted, _ = self.listener.accept()
        peer = RawPeer(accepted)
        self.peers.append(peer)
        return peer

    def close(self):
        for peer in self.peers:
            peer.close()
        self.listener.close()


def start_message(your_color="black", minutes=10, increment=0):
    return {
        "type": "start",
        "white": "Brancas",
        "black": "Pretas",
        "your_color": your_color,
        "minutes": minutes,
        "increment": increment,
        "mode": "training",
    }


def open_host(track, time_control=TimeControl.UNLIMITED, timings=QUICK, name="Brancas", mode="training"):
    host = track(HostSession(name, time_control, port=0, bind=LOCALHOST, timings=timings, mode=mode))
    host.start()
    return host


def open_client(track, host, timings=QUICK, name="Pretas", timeout=WAIT_SECONDS):
    client = track(ClientSession(name, host.code, port=host.port, timeout=timeout, timings=timings))
    client.start()
    return client
