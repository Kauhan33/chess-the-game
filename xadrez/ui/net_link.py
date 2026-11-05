"""Partida em rede do lado da interface: a sessão de `xadrez.net`, a fila de eventos e as regras da mesa.

Regra do tempo esgotado, igual nos dois computadores (`docs/plans/notas-ui.md`):

- Só quem esgota o próprio relógio decide. Ele perde na hora e avisa com `send_resign`.
- Quem recebe essa desistência com o relógio do outro quase zerado registra tempo esgotado, com a mesma regra do
  motor (adversário só com o rei empata). Se o relógio ainda tinha folga, foi desistência comum.
- O relógio do outro lado, visto daqui, para em zero sem decidir nada: uma jogada pode estar a caminho. Passados
  `REMOTE_FLAG_GRACE_SECONDS` sem jogada nem aviso, o outro lado sumiu, e a partida acaba por abandono.

O `clock_ms` que chega é informativo e pode ser falso: não entra em nenhuma decisão.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from xadrez.core import Color, TimeControl
from xadrez.net import (
    ClientSession,
    DrawAnswered,
    DrawOffered,
    HostSession,
    MoveReceived,
    NetEvent,
    NetworkError,
    PeerLeft,
    PeerResigned,
    RematchRequested,
    parse_uci,
)

if TYPE_CHECKING:
    from xadrez.ui.game_scene import GameScene

REMOTE_FLAG_GRACE_SECONDS = 5.0
DECLARED_FLAG_WINDOW_SECONDS = 2.0
_MILLISECONDS = 1000.0
ILLEGAL_MOVE_MESSAGE = "O adversário enviou uma jogada ilegal, e a sala foi encerrada."
SILENT_PEER_MESSAGE = "O adversário não jogou nem respondeu depois de o tempo acabar."


class LanNetwork:
    """Sessões de verdade, na porta padrão, em todas as placas de rede desta máquina."""

    def host(self, name: str, time_control: TimeControl) -> HostSession:
        return HostSession(name, time_control)

    def client(self, name: str, code: str) -> ClientSession:
        return ClientSession(name, code)


class NetLink:
    """A sessão e o que precisa sobreviver à troca de cena: nada que `poll` entrega pode se perder."""

    def __init__(self, session) -> None:
        self.session = session
        self.inbox: deque[NetEvent] = deque()
        self.peer_name = "Adversário"
        self.peer_is_gone = False
        self.peer_wants_rematch = False
        self.rematch_requested = False

    def pump(self) -> None:
        self.inbox.extend(self.session.poll())

    def leave(self) -> None:
        self.session.send_bye()
        self.session.close()

    def begin_new_game(self) -> None:
        self.peer_wants_rematch = False
        self.rematch_requested = False


class NetMatch:
    """Liga a sessão à `GameScene`: o outro lado joga por aqui, e o que este lado faz sai por aqui."""

    def __init__(self, scene: GameScene, link: NetLink) -> None:
        self._scene = scene
        self.link = link
        self.draw_answer_pending = False
        self._peer_offer_open = False
        self._flag_wait = 0.0
        self._handlers = {
            MoveReceived: self._on_move,
            PeerResigned: self._on_peer_resigned,
            DrawOffered: self._on_draw_offered,
            DrawAnswered: self._on_draw_answered,
            RematchRequested: self._on_rematch_requested,
            PeerLeft: self._on_peer_left,
            NetworkError: self._on_network_error,
        }

    # Entrada ------------------------------------------------------------------------------------

    def receive_events(self) -> None:
        """Eventos em ordem, um voo de cada vez: duas jogadas seguidas não podem cortar a animação uma da outra."""
        self.link.pump()
        while self.link.inbox and not self._scene.view.is_flying:
            event = self.link.inbox.popleft()
            handler = self._handlers.get(type(event))
            if handler is not None:
                handler(event)

    def _on_move(self, event: MoveReceived) -> None:
        scene = self._scene
        engine = scene.engine
        if engine.result is not None:
            return  # Cruzou com o fim da partida neste lado.
        if engine.turn is scene.local_color:
            self._close_room_for_cheating()
            return
        outcome = engine.play(*parse_uci(event.uci))
        if not outcome.ok:
            self._close_room_for_cheating()
            return
        self._flag_wait = 0.0
        scene.show_opponent_move(outcome)

    def _close_room_for_cheating(self) -> None:
        scene = self._scene
        self.link.peer_is_gone = True
        self.link.leave()
        scene.end_match(scene.engine.abandon(scene.remote_color))
        scene.notices.show(ILLEGAL_MOVE_MESSAGE)

    def _on_peer_resigned(self, _: PeerResigned) -> None:
        scene = self._scene
        engine, remote = scene.engine, scene.remote_color
        if engine.result is not None:
            return
        remaining = engine.clock.remaining(remote)
        is_flag_fall = engine.turn is remote and remaining <= DECLARED_FLAG_WINDOW_SECONDS
        scene.end_match(engine.tick(remaining) if is_flag_fall else engine.resign(remote))

    def _on_draw_offered(self, _: DrawOffered) -> None:
        if self._scene.engine.result is None and not self._peer_offer_open:
            self._peer_offer_open = True
            self._scene.show_peer_draw_offer(self._answer_draw)

    def _answer_draw(self, accept: bool) -> None:
        self._peer_offer_open = False
        self.link.session.send_draw_answer(accept)

    def _on_draw_answered(self, event: DrawAnswered) -> None:
        scene = self._scene
        self.draw_answer_pending = False
        if event.accept:
            scene.end_match(scene.engine.agree_draw())
        elif scene.engine.result is None:
            scene.notices.show(f"{self.link.peer_name} recusou o empate.")

    def _on_rematch_requested(self, _: RematchRequested) -> None:
        """No meio da partida não vale. Com a partida encerrada, a tela de fim precisa saber."""
        if self._scene.engine.result is not None:
            self.link.peer_wants_rematch = True

    def _on_peer_left(self, event: PeerLeft) -> None:
        self._end_by_abandonment(f"{event.reason} A vitória é sua.")

    def _on_network_error(self, event: NetworkError) -> None:
        self._end_by_abandonment(event.message)

    def _end_by_abandonment(self, message: str) -> None:
        scene = self._scene
        self.link.peer_is_gone = True
        if scene.engine.result is None:
            scene.end_match(scene.engine.abandon(scene.remote_color))
        scene.notices.show(message)

    # Relógio ------------------------------------------------------------------------------------

    def tick(self, dt: float) -> None:
        scene = self._scene
        engine = scene.engine
        if engine.result is not None or scene.view.is_flying:
            return
        if engine.turn is scene.local_color:
            self._tick_own_clock(dt)
        else:
            self._tick_remote_clock(engine.turn, dt)

    def _tick_own_clock(self, dt: float) -> None:
        result = self._scene.engine.tick(dt)
        if result is not None:
            self.link.session.send_resign()
            self._scene.end_match(result)

    def _tick_remote_clock(self, remote: Color, dt: float) -> None:
        clock = self._scene.engine.clock
        clock.tick(remote, dt)
        if not clock.is_flagged(remote):
            return
        self._flag_wait += dt
        if self._flag_wait >= REMOTE_FLAG_GRACE_SECONDS:
            scene = self._scene
            self.link.peer_is_gone = True
            self.link.leave()
            scene.end_match(scene.engine.abandon(remote))
            scene.notices.show(SILENT_PEER_MESSAGE)

    # Saída --------------------------------------------------------------------------------------

    def send_move(self, uci: str) -> None:
        engine = self._scene.engine
        self.link.session.send_move(uci, engine.clock.remaining(self._scene.local_color) * _MILLISECONDS)

    def send_resign(self) -> None:
        self.link.session.send_resign()

    def send_draw_offer(self) -> None:
        self.draw_answer_pending = True
        self.link.session.send_draw_offer()
