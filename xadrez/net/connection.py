"""Socket não bloqueante que conversa por linhas. Nenhum método aqui pode segurar a thread da sessão."""
from __future__ import annotations

import socket
import time

from .protocol import LineSplitter, ProtocolError

REASON_PEER_CLOSED = "O adversário saiu da partida."
REASON_CONNECTION_LOST = "A conexão com o adversário caiu."

_RECEIVE_BYTES = 4096
# Muito acima do que uma partida produz, e baixo o bastante para uma enxurrada não roubar CPU do jogo.
_MAX_MESSAGES_PER_SECOND = 2000


class PeerGone(Exception):
    """O outro lado sumiu. O texto é o motivo, pronto para a tela."""


class LineConnection:
    def __init__(self, connected_socket: socket.socket) -> None:
        connected_socket.setblocking(False)
        self._socket = connected_socket
        self._splitter = LineSplitter()
        self._outgoing = bytearray()
        self._window_start = time.monotonic()
        self._window_messages = 0

    def fileno(self) -> int:
        return self._socket.fileno()

    def read_lines(self) -> list[bytes]:
        """Linhas completas que chegaram. Levanta `PeerGone` ou, se o outro lado abusar, `ProtocolError`."""
        chunk = self._receive()
        if not chunk:
            return []
        lines = self._splitter.feed(chunk)
        self._count_messages(len(lines))
        return lines

    def discard_input(self) -> None:
        """Joga fora o que chegar. Levanta `PeerGone` quando o outro lado fechar."""
        self._receive()

    def queue(self, line: bytes) -> None:
        self._outgoing += line

    def flush(self) -> None:
        """Envia o que couber agora. O resto fica guardado para o próximo ciclo da sessão."""
        while self._outgoing:
            try:
                sent = self._socket.send(self._outgoing)
            except (BlockingIOError, InterruptedError):
                return
            except OSError as error:
                raise PeerGone(REASON_CONNECTION_LOST) from error
            del self._outgoing[:sent]

    def shutdown_write(self) -> None:
        """Avisa que acabou, sem fechar: fechar com dados por ler vira RST, que pode apagar a resposta no outro lado."""
        try:
            self._socket.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    def close_gracefully(self) -> None:
        try:
            self.flush()
        except PeerGone:
            pass
        self.shutdown_write()
        self.close()

    def close(self) -> None:
        self._socket.close()

    def _receive(self) -> bytes:
        try:
            chunk = self._socket.recv(_RECEIVE_BYTES)
        except (BlockingIOError, InterruptedError):
            return b""
        except OSError as error:
            raise PeerGone(REASON_CONNECTION_LOST) from error
        if not chunk:
            raise PeerGone(REASON_PEER_CLOSED)
        return chunk

    def _count_messages(self, count: int) -> None:
        now = time.monotonic()
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._window_messages = 0
        self._window_messages += count
        if self._window_messages > _MAX_MESSAGES_PER_SECOND:
            raise ProtocolError("Mensagens demais por segundo.")
