"""Sala em rede local. Uma thread por sessão cuida dos sockets; a interface só chama `poll()` e `send_*()`.

Nada aqui bloqueia quem chama nem levanta exceção por causa da rede: toda falha vira `NetworkError` ou
`PeerLeft` em `poll()`, e esses dois eventos encerram a sessão, fechando a thread e os sockets.
"""
from __future__ import annotations

import errno
import ipaddress
import selectors
import socket
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Callable

from xadrez.core import Color, TimeControl

from .connection import REASON_PEER_CLOSED, LineConnection, PeerGone
from .events import (
    DrawAnswered,
    DrawOffered,
    GameStart,
    MoveReceived,
    NetEvent,
    NetworkError,
    PeerJoined,
    PeerLeft,
    PeerResigned,
    RematchRequested,
)
from .protocol import (
    PROTOCOL_VERSION,
    REFUSED_ROOM_FULL,
    REFUSED_VERSION,
    ProtocolError,
    clock_to_wire,
    decode_message,
    encode_message,
    sanitize_name,
)
from .room_code import LOOPBACK_IPV4, decode_room_code, encode_room_code, is_lan_address, local_ipv4

DEFAULT_PORT = 50507
THREAD_NAME_PREFIX = "chess-net"
OFFLINE_WARNING = "Sem rede local: esta sala só pode ser acessada neste computador. Conecte-se a uma rede e crie outra."

_ANY_INTERFACE = "0.0.0.0"
_LISTEN_BACKLOG = 8
_MAX_WAITING_CONNECTIONS = 8
_REFUSAL_DRAIN_SECONDS = 1.0
_JOIN_SECONDS = 2.0
_MAX_QUEUED_EVENTS = 1024
_CONNECT_IN_PROGRESS = {0, errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY}
# No Windows, SO_REUSEADDR deixaria outro programa abrir a mesma porta por cima; lá o certo é pedir exclusividade.
# Nos outros sistemas, ele só permite reabrir a porta logo depois de fechar a sala anterior.
_BIND_OPTION = getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR)

_REASON_SILENT = "O adversário parou de responder."
_INVALID_MESSAGE = "O outro lado enviou dados inválidos, e a conexão foi encerrada."
_INTERNAL_ERROR = "Erro inesperado na conexão de rede."
_TOO_MANY_EVENTS = "O outro lado enviou mensagens demais, e a conexão foi encerrada."
_CANNOT_CONNECT = "Não foi possível conectar à sala. Confira o código, a rede e o firewall de quem criou a sala."
_NO_ANSWER = "A sala não respondeu. Confira o código, a rede e o firewall de quem criou a sala."
_OUTSIDE_LAN = "Esse código aponta para fora da rede local. Confira o que foi digitado."
_REFUSAL_MESSAGES = {
    REFUSED_ROOM_FULL: "Sala cheia: já há uma partida em andamento nessa sala.",
    REFUSED_VERSION: "Os dois jogadores estão com versões diferentes do jogo. Atualize para a mesma versão.",
}


@dataclass(frozen=True)
class NetTimings:
    """Tempos em segundos. Ajustáveis para os testes não precisarem esperar os 8 s reais."""

    heartbeat_interval: float = 2.0
    heartbeat_timeout: float = 8.0
    handshake_timeout: float = 5.0
    tick: float = 0.02


class _StartFailure(Exception):
    """Não deu para abrir a sessão. O texto vai para a tela."""


class _Session(ABC):
    """O que a sala e quem entra nela têm em comum: a thread, as filas e a conversa depois do início da partida.

    Só a thread da sessão toca em sockets, e por isso ela não precisa de trava para eles. A interface fala
    com ela por duas filas `deque`, seguras entre threads: `_outbox` na ida e `_events` na volta.
    """

    def __init__(self, name: str, timings: NetTimings) -> None:
        self.name = sanitize_name(name)
        self._timings = timings
        self._events: deque[NetEvent] = deque()
        self._outbox: deque[dict[str, object]] = deque()
        self._stop = threading.Event()
        self._lifecycle = threading.Lock()
        self._thread: threading.Thread | None = None
        self._started = False
        self._finished = False
        self._selector: selectors.BaseSelector | None = None
        self._peer: LineConnection | None = None
        self._last_heard = 0.0
        self._next_ping = 0.0
        self._awaiting_draw_answer = False
        self._rematch_requested = False
        self._peer_wants_rematch = False
        self._game_handlers: dict[str, Callable[[dict[str, object]], None]] = {
            "ping": lambda message: None,
            "move": lambda message: self._emit(MoveReceived(message["uci"], message["clock_ms"])),
            "resign": lambda message: self._emit(PeerResigned()),
            "draw_offer": lambda message: self._emit(DrawOffered()),
            "draw_answer": self._on_draw_answer,
            "rematch": self._on_peer_rematch,
            "bye": lambda message: self._leave(REASON_PEER_CLOSED),
        }

    def start(self) -> None:
        with self._lifecycle:
            if self._started:
                return
            self._started = True
            try:
                self._selector = selectors.DefaultSelector()
                self._open_sockets()
                thread = threading.Thread(target=self._run, name=f"{THREAD_NAME_PREFIX}-{type(self).__name__}", daemon=True)
                thread.start()
                self._thread = thread
            except _StartFailure as failure:
                self._abort_start(str(failure))
            except (OSError, RuntimeError):
                # Falta de descritores de arquivo ou de threads: raro, mas não é motivo para derrubar o jogo.
                self._abort_start(_INTERNAL_ERROR)

    def _abort_start(self, message: str) -> None:
        self._fail(message)
        self._release_sockets()

    def poll(self) -> list[NetEvent]:
        """Entrega o que aconteceu desde a última chamada. Chame a cada quadro."""
        events: list[NetEvent] = []
        try:
            while True:
                events.append(self._events.popleft())
        except IndexError:
            return events

    def close(self) -> None:
        """Encerra a thread e os sockets. Pode ser chamado mais de uma vez, a qualquer momento."""
        with self._lifecycle:
            self._started = True
            self._stop.set()
            thread = self._thread
        if thread is not None:
            thread.join(_JOIN_SECONDS)

    def send_move(self, uci: str, clock_ms: float) -> None:
        self._send("move", uci=uci, clock_ms=clock_to_wire(clock_ms))

    def send_resign(self) -> None:
        self._send("resign")

    def send_draw_offer(self) -> None:
        self._send("draw_offer")

    def send_draw_answer(self, accept: bool) -> None:
        self._send("draw_answer", accept=bool(accept))

    def send_rematch(self) -> None:
        self._send("rematch")

    def send_bye(self) -> None:
        """Avisa que está saindo. A sessão termina depois disso, sem gerar evento deste lado."""
        self._send("bye")

    def _send(self, kind: str, **fields: object) -> None:
        # Sem adversário não há a quem entregar: guardar faria a jogada aparecer fora de hora mais tarde.
        if self._peer is not None and not self._finished and not self._stop.is_set():
            self._outbox.append({"type": kind, **fields})

    def _run(self) -> None:
        try:
            while not self._finished and not self._stop.is_set():
                self._tick()
            # O que foi pedido logo antes de `close`, como a despedida em `send_bye(); close()`, ainda precisa sair.
            self._deliver_outbox()
        except Exception:
            # Último recurso: sem isto, um defeito inesperado mataria a thread em silêncio e a tela esperaria para sempre.
            self._fail(_INTERNAL_ERROR)
        finally:
            self._release_sockets()

    def _tick(self) -> None:
        for key, _ in self._selector.select(self._timings.tick):
            if self._finished:
                return
            key.data(key.fileobj)
        self._deliver_outbox()
        self._flush_peer()
        self._check_timers(time.monotonic())

    def _deliver_outbox(self) -> None:
        while self._outbox and not self._finished:
            self._deliver(self._outbox.popleft())

    def _deliver(self, message: dict[str, object]) -> None:
        kind = message["type"]
        if kind == "rematch":
            self._rematch_requested = True
            self._request_rematch()
            return
        if kind == "draw_offer":
            self._awaiting_draw_answer = True
        self._write(message)
        if kind == "bye":
            self._finished = True

    def _write(self, message: dict[str, object]) -> None:
        try:
            self._peer.queue(encode_message(message))
        except ProtocolError as error:
            self._fail(str(error))

    def _flush_peer(self) -> None:
        if self._peer is None or self._finished:
            return
        try:
            self._peer.flush()
        except PeerGone as gone:
            self._leave(str(gone))

    def _check_timers(self, now: float) -> None:
        if self._peer is None or self._finished:
            return
        if now - self._last_heard >= self._timings.heartbeat_timeout:
            self._leave(_REASON_SILENT)
        elif now >= self._next_ping:
            self._next_ping = now + self._timings.heartbeat_interval
            self._write({"type": "ping"})

    def _adopt_peer(self, connection: LineConnection) -> None:
        self._peer = connection
        self._selector.modify(connection, selectors.EVENT_READ, self._read_peer)
        now = time.monotonic()
        self._last_heard = now
        self._next_ping = now + self._timings.heartbeat_interval

    def _read_peer(self, connection: LineConnection) -> None:
        try:
            lines = connection.read_lines()
        except PeerGone as gone:
            self._leave(str(gone))
        except ProtocolError:
            self._fail(_INVALID_MESSAGE)
        else:
            for line in lines:
                self._handle_peer_line(line)

    def _handle_peer_line(self, line: bytes) -> None:
        if self._finished:
            return
        try:
            message = decode_message(line)
        except ProtocolError:
            self._fail(_INVALID_MESSAGE)
            return
        handler = self._game_handlers.get(message["type"])
        if handler is None:
            self._fail(_INVALID_MESSAGE)
            return
        # Só linha completa e válida conta como sinal de vida: pingar um byte por vez não segura a sala.
        self._last_heard = time.monotonic()
        handler(message)

    def _on_draw_answer(self, message: dict[str, object]) -> None:
        """Resposta sem oferta é ignorada: ela não pode virar um empate que ninguém propôs."""
        if self._awaiting_draw_answer:
            self._awaiting_draw_answer = False
            self._emit(DrawAnswered(message["accept"]))

    def _on_peer_rematch(self, message: dict[str, object]) -> None:
        if self._peer_wants_rematch:
            return
        self._peer_wants_rematch = True
        if not self._rematch_requested:
            self._emit(RematchRequested())
        self._after_peer_rematch()

    def _reset_for_new_game(self) -> None:
        self._rematch_requested = False
        self._peer_wants_rematch = False
        self._awaiting_draw_answer = False

    def _emit(self, event: NetEvent) -> None:
        if len(self._events) >= _MAX_QUEUED_EVENTS:
            self._fail(_TOO_MANY_EVENTS)
        elif not self._finished:
            self._events.append(event)

    def _fail(self, message: str) -> None:
        self._terminate(NetworkError(message))

    def _leave(self, reason: str) -> None:
        self._terminate(PeerLeft(reason))

    def _terminate(self, event: NetEvent) -> None:
        """Garante um único evento final por sessão."""
        if not self._finished:
            self._events.append(event)
            self._finished = True

    def _release_sockets(self) -> None:
        for connection in self._open_connections():
            connection.close_gracefully()
        if self._selector is not None:
            self._selector.close()

    @abstractmethod
    def _open_sockets(self) -> None:
        """Roda em `start`, antes da thread. Levanta `_StartFailure` com o motivo, se não conseguir."""

    @abstractmethod
    def _open_connections(self) -> list[LineConnection]:
        """Fecha o que não é conexão e devolve as conexões que ainda precisam ser encerradas."""

    @abstractmethod
    def _request_rematch(self) -> None:
        """Este lado pediu revanche."""

    @abstractmethod
    def _after_peer_rematch(self) -> None:
        """O outro lado pediu revanche, e o evento já foi emitido se era preciso."""


class HostSession(_Session):
    """Quem cria a sala. A porta fica aberta da chamada a `start` até a sessão terminar."""

    def __init__(
        self,
        name: str,
        time_control: TimeControl,
        port: int = DEFAULT_PORT,
        bind: str = _ANY_INTERFACE,
        *,
        timings: NetTimings = NetTimings(),
    ) -> None:
        super().__init__(name, timings)
        self._time_control = time_control
        self._bind = bind
        self.port = port
        address = local_ipv4() if bind == _ANY_INTERFACE else bind
        self.code = encode_room_code(address)
        self.offline_warning = OFFLINE_WARNING if bind == _ANY_INTERFACE and address == LOOPBACK_IPV4 else None
        self._listener: socket.socket | None = None
        self._handshakes: dict[LineConnection, float] = {}
        self._refusals: dict[LineConnection, float] = {}
        self._peer_name = ""
        self._color = Color.WHITE

    def _open_sockets(self) -> None:
        try:
            self._listener = _open_listener(self._bind, self.port)
        except (OSError, OverflowError) as error:
            raise _StartFailure(
                f"Não foi possível abrir a porta {self.port}: ela está ocupada ou bloqueada. "
                "Feche o outro jogo ou sala e tente de novo."
            ) from error
        self.port = self._listener.getsockname()[1]
        self._selector.register(self._listener, selectors.EVENT_READ, self._accept)

    def _open_connections(self) -> list[LineConnection]:
        if self._listener is not None:
            self._listener.close()
        peer = [] if self._peer is None else [self._peer]
        return [*peer, *self._handshakes, *self._refusals]

    def _accept(self, listener: socket.socket) -> None:
        try:
            accepted, address = listener.accept()
        except OSError:
            return
        is_over_limit = len(self._handshakes) + len(self._refusals) >= _MAX_WAITING_CONNECTIONS
        if is_over_limit or not is_lan_address(address[0]):
            accepted.close()
            return
        connection = LineConnection(accepted)
        self._handshakes[connection] = time.monotonic() + self._timings.handshake_timeout
        self._selector.register(connection, selectors.EVENT_READ, self._read_handshake)

    def _read_handshake(self, connection: LineConnection) -> None:
        """Quem ainda não entrou na sala só derruba a própria conexão: um estranho não pode fechar a sala."""
        try:
            lines = connection.read_lines()
        except (PeerGone, ProtocolError):
            self._drop(connection, self._handshakes)
            return
        for line in lines:
            if connection is self._peer:
                self._handle_peer_line(line)
            elif connection in self._handshakes:
                self._handle_hello(connection, line)

    def _handle_hello(self, connection: LineConnection, line: bytes) -> None:
        try:
            message = decode_message(line)
        except ProtocolError:
            self._drop(connection, self._handshakes)
            return
        if message["type"] != "hello":
            self._drop(connection, self._handshakes)
        elif message["version"] != PROTOCOL_VERSION:
            self._refuse(connection, REFUSED_VERSION)
        elif self._peer is not None:
            self._refuse(connection, REFUSED_ROOM_FULL)
        else:
            self._welcome(connection, message["name"])

    def _welcome(self, connection: LineConnection, name: str) -> None:
        del self._handshakes[connection]
        self._peer_name = name
        self._adopt_peer(connection)
        self._emit(PeerJoined(name))
        self._begin_game()

    def _refuse(self, connection: LineConnection, code: str) -> None:
        """Responde e espera o outro lado fechar: fechar agora com dados por ler poderia apagar a resposta."""
        connection.queue(encode_message({"type": "refused", "code": code}))
        try:
            connection.flush()
        except PeerGone:
            self._drop(connection, self._handshakes)
            return
        del self._handshakes[connection]
        connection.shutdown_write()
        self._refusals[connection] = time.monotonic() + _REFUSAL_DRAIN_SECONDS
        self._selector.modify(connection, selectors.EVENT_READ, self._drain_refused)

    def _drain_refused(self, connection: LineConnection) -> None:
        try:
            connection.discard_input()
        except PeerGone:
            self._drop(connection, self._refusals)

    def _drop(self, connection: LineConnection, waiting: dict[LineConnection, float]) -> None:
        del waiting[connection]
        self._selector.unregister(connection)
        connection.close()

    def _begin_game(self) -> None:
        minutes, increment = self._time_control.minutes, self._time_control.increment
        is_white = self._color is Color.WHITE
        white, black = (self.name, self._peer_name) if is_white else (self._peer_name, self.name)
        self._write(
            {
                "type": "start",
                "white": white,
                "black": black,
                "your_color": self._color.opposite.value,
                "minutes": minutes,
                "increment": increment,
            }
        )
        self._emit(GameStart(white, black, self._color, minutes, increment))

    def _request_rematch(self) -> None:
        if self._peer_wants_rematch:
            self._start_rematch()
        else:
            self._write({"type": "rematch"})

    def _after_peer_rematch(self) -> None:
        if self._rematch_requested:
            self._start_rematch()

    def _start_rematch(self) -> None:
        self._reset_for_new_game()
        self._color = self._color.opposite
        self._begin_game()

    def _check_timers(self, now: float) -> None:
        for waiting in (self._handshakes, self._refusals):
            for connection in [item for item, deadline in waiting.items() if now >= deadline]:
                self._drop(connection, waiting)
        super()._check_timers(now)


class ClientSession(_Session):
    """Quem entra na sala, pelo código de 7 caracteres ou por um IPv4 da rede local."""

    def __init__(
        self,
        name: str,
        code_or_host: str,
        port: int = DEFAULT_PORT,
        timeout: float = 5.0,
        *,
        timings: NetTimings = NetTimings(),
    ) -> None:
        super().__init__(name, timings)
        self._code_or_host = code_or_host
        self._port = port
        self._timeout = timeout
        self._deadline = 0.0
        self._connecting: socket.socket | None = None
        self._joining: LineConnection | None = None
        self._game_handlers["start"] = self._on_rematch_start

    def _open_sockets(self) -> None:
        try:
            address = _target_address(self._code_or_host)
        except ValueError as error:
            raise _StartFailure(str(error)) from error
        self._deadline = time.monotonic() + self._timeout
        try:
            self._connecting = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._connecting.setblocking(False)
            outcome = self._connecting.connect_ex((address, self._port))
        except (OSError, OverflowError) as error:
            raise _StartFailure(_CANNOT_CONNECT) from error
        if outcome not in _CONNECT_IN_PROGRESS:
            raise _StartFailure(_CANNOT_CONNECT)
        self._selector.register(self._connecting, selectors.EVENT_WRITE, self._finish_connect)

    def _open_connections(self) -> list[LineConnection]:
        if self._connecting is not None:
            self._connecting.close()
        return [connection for connection in (self._peer, self._joining) if connection is not None]

    def _finish_connect(self, connecting: socket.socket) -> None:
        if connecting.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) != 0:
            self._fail(_CANNOT_CONNECT)
            return
        self._selector.unregister(connecting)
        self._connecting = None
        self._joining = LineConnection(connecting)
        self._joining.queue(encode_message({"type": "hello", "version": PROTOCOL_VERSION, "name": self.name}))
        self._selector.register(self._joining, selectors.EVENT_READ, self._read_join_reply)

    def _read_join_reply(self, connection: LineConnection) -> None:
        try:
            lines = connection.read_lines()
        except PeerGone:
            self._fail(_CANNOT_CONNECT)
            return
        except ProtocolError:
            self._fail(_INVALID_MESSAGE)
            return
        for line in lines:
            if connection is self._peer:
                self._handle_peer_line(line)
            elif not self._finished:
                self._handle_join_reply(connection, line)

    def _handle_join_reply(self, connection: LineConnection, line: bytes) -> None:
        try:
            message = decode_message(line)
        except ProtocolError:
            self._fail(_INVALID_MESSAGE)
            return
        if message["type"] == "refused":
            self._fail(_REFUSAL_MESSAGES[message["code"]])
        elif message["type"] == "start":
            self._joining = None
            self._adopt_peer(connection)
            your_color = Color(message["your_color"])
            self._emit(PeerJoined(message["black"] if your_color is Color.WHITE else message["white"]))
            self._emit(_game_start_event(message))
        else:
            self._fail(_INVALID_MESSAGE)

    def _on_rematch_start(self, message: dict[str, object]) -> None:
        """Início de partida sem revanche pedida seria o outro lado apagando o jogo em andamento."""
        if not self._rematch_requested:
            self._fail(_INVALID_MESSAGE)
            return
        self._reset_for_new_game()
        self._emit(_game_start_event(message))

    def _request_rematch(self) -> None:
        """Quem decide o início é a sala. Aqui só se avisa e espera a mensagem de início."""
        self._write({"type": "rematch"})

    def _after_peer_rematch(self) -> None:
        pass

    def _check_timers(self, now: float) -> None:
        if self._peer is None:
            self._advance_join(now)
        super()._check_timers(now)

    def _advance_join(self, now: float) -> None:
        if now >= self._deadline:
            self._fail(_NO_ANSWER)
        elif self._joining is not None:
            try:
                self._joining.flush()
            except PeerGone:
                self._fail(_CANNOT_CONNECT)


def _game_start_event(message: dict[str, object]) -> GameStart:
    return GameStart(
        white=message["white"],
        black=message["black"],
        your_color=Color(message["your_color"]),
        minutes=message["minutes"],
        increment=message["increment"],
    )


def _open_listener(bind: str, port: int) -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, _BIND_OPTION, 1)
        listener.bind((bind, port))
        listener.listen(_LISTEN_BACKLOG)
        listener.setblocking(False)
    except (OSError, OverflowError):
        listener.close()
        raise
    return listener


def _target_address(code_or_host: object) -> str:
    """Traduz o que foi digitado em IPv4 sem consultar DNS, que poderia demorar e sair da rede local."""
    text = code_or_host.strip() if isinstance(code_or_host, str) else ""
    if text.lower() == "localhost":
        return LOOPBACK_IPV4
    try:
        address = str(ipaddress.IPv4Address(text))
    except ValueError:
        address = decode_room_code(text)
    if not is_lan_address(address):
        raise ValueError(_OUTSIDE_LAN)
    return address
