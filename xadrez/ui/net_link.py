"""Partida em rede do lado da interface: a sessão de `xadrez.net`, a fila de eventos e as regras da mesa.

Quem cria a sala é a autoridade do resultado, igual nos dois computadores (`docs/plans/notas-ui.md`):

- A sala valida as jogadas, mede os dois relógios, decide o fim e manda a decisão com `send_result`, dizendo em que
  lance a partida parou. Lance, desistência ou resposta que chega depois do fim é ignorado.
- Quem entrou joga sem esperar, mas nada ali é definitivo antes da palavra da sala. O relógio dele só serve para
  mostrar. Desistir ou aceitar empate é um pedido, e o lance que cruzou com o fim é desfeito.
- Se a sala sumir, vale `PeerLeft` e o sinal de vida da sessão: quem entrou encerra sozinho.

O `clock_ms` que chega é informativo e pode ser falso: não entra em nenhuma decisão.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Callable

from xadrez.core import EndReason, GameResult, TimeControl
from xadrez.net import (
    ClientSession,
    DrawAnswered,
    DrawOffered,
    GameDecided,
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

DECISION_WAIT_SECONDS = 5.0
_MILLISECONDS = 1000.0
ILLEGAL_MOVE_MESSAGE = "O adversário enviou uma jogada ilegal, e a sala foi encerrada."
INVALID_RESULT_MESSAGE = "A sala enviou um resultado que não confere, e a partida foi encerrada."
NO_DECISION_MESSAGE = "A sala não confirmou o resultado, e a conexão foi encerrada."
RESIGN_SENT_MESSAGE = "Desistência enviada."
_VICTORY_SENTENCE = " A vitória é sua."
# O que o próprio tabuleiro diz: quem entrou na sala confere, em vez de só acreditar.
_BOARD_REASONS = frozenset({
    EndReason.CHECKMATE,
    EndReason.STALEMATE,
    EndReason.INSUFFICIENT_MATERIAL,
    EndReason.FIFTY_MOVES,
    EndReason.THREEFOLD_REPETITION,
})


class LanNetwork:
    """Sessões de verdade, na porta padrão, em todas as placas de rede desta máquina."""

    def host(self, name: str, time_control: TimeControl, mode: str) -> HostSession:
        return HostSession(name, time_control, mode=mode)

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
        self.is_authority = link.session.is_authority
        self.draw_answer_pending = False
        self._peer_offer_open = False
        self._peer_may_offer_draw = True
        self._may_offer_draw = True
        self._requested_end: Callable[[], GameResult] | None = None
        self._is_settled = False
        self._is_published = False
        self._decision_wait = 0.0
        self._handlers = {
            MoveReceived: self._on_move,
            GameDecided: self._on_decision,
            PeerResigned: self._on_peer_resigned,
            DrawOffered: self._on_draw_offered,
            DrawAnswered: self._on_draw_answered,
            RematchRequested: self._on_rematch_requested,
            PeerLeft: self._on_peer_left,
            NetworkError: self._on_network_error,
        }

    @property
    def is_decided(self) -> bool:
        """O resultado no motor é definitivo? Na sala, sempre. Em quem entrou, só depois da palavra da sala."""
        return self.is_authority or self._is_settled

    @property
    def awaits_decision(self) -> bool:
        """Quem entrou pediu para encerrar e espera a sala: o tabuleiro fica parado até a resposta."""
        return self._requested_end is not None and not self._is_settled

    @property
    def may_offer_draw(self) -> bool:
        """Uma proposta por lance: depois de uma recusa, só depois do próprio lance."""
        return self._may_offer_draw

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
            self._close_room(ILLEGAL_MOVE_MESSAGE)
            return
        outcome = engine.play(*parse_uci(event.uci))
        if not outcome.ok:
            self._close_room(ILLEGAL_MOVE_MESSAGE)
            return
        self._peer_may_offer_draw = True
        scene.show_opponent_move(outcome)

    def _close_room(self, message: str) -> None:
        """O outro lado mandou o que não podia: a culpa é dele. A sala ainda diz como a partida acabou, antes de fechar."""
        scene = self._scene
        self.link.peer_is_gone = True
        result = scene.engine.abandon(scene.remote_color)
        self.publish_result()
        self.link.leave()
        self._settle(result, message)

    def _on_decision(self, event: GameDecided) -> None:
        """A palavra da sala. Se o último lance daqui cruzou com o fim, a sala nem o viu: ele volta."""
        scene = self._scene
        engine = scene.engine
        if self._is_settled:
            return
        spare_moves = len(engine.history) - event.plies
        if spare_moves == 1 and engine.turn is scene.remote_color:
            engine.take_back_last_move()
            scene.retract_last_move()
        elif spare_moves != 0:
            self._close_room(INVALID_RESULT_MESSAGE)
            return
        if not self._agrees_with_board(event.result):
            self._close_room(INVALID_RESULT_MESSAGE)
            return
        if event.result.reason is EndReason.TIMEOUT:
            engine.clock.tick(engine.turn, engine.clock.remaining(engine.turn))
        self._settle(engine.finish_with(event.result))

    def _agrees_with_board(self, result: GameResult) -> bool:
        board_result = self._scene.engine.result
        if board_result is not None:
            return board_result == result
        return result.reason not in _BOARD_REASONS

    def _settle(self, result: GameResult, notice: str | None = None) -> None:
        self._is_settled = True
        self._scene.end_match(result, notice)

    def _on_peer_resigned(self, _: PeerResigned) -> None:
        scene = self._scene
        if scene.engine.result is None:
            self._settle(scene.engine.resign(scene.remote_color))

    def _on_draw_offered(self, _: DrawOffered) -> None:
        """Proposta repetida, depois de uma recusa ou fora da hora é ignorada: não pode atrapalhar quem joga."""
        is_in_time = self._scene.engine.result is None and not self.awaits_decision
        if is_in_time and self._peer_may_offer_draw and not self._peer_offer_open:
            self._peer_offer_open = True
            self._scene.show_peer_draw_offer(self._answer_draw)

    def _answer_draw(self, accept: bool) -> None:
        scene = self._scene
        self._peer_offer_open = False
        self._peer_may_offer_draw = False
        scene.close_peer_draw_offer()
        self.link.session.send_draw_answer(accept)
        if accept and scene.engine.result is None:
            self._request_end(scene.engine.agree_draw)

    def _on_draw_answered(self, event: DrawAnswered) -> None:
        scene = self._scene
        self.draw_answer_pending = False
        if scene.engine.result is not None:
            return
        if event.accept:
            self._request_end(scene.engine.agree_draw)
        else:
            self._may_offer_draw = False
            scene.notices.show(f"{self.link.peer_name} recusou o empate.")

    def _request_end(self, decide: Callable[[], GameResult]) -> None:
        """Na sala, vale na hora. Quem entrou guarda o pedido: só serve se a sala sumir antes de responder."""
        if self.is_authority:
            self._settle(decide())
        else:
            self._requested_end = decide

    def _on_rematch_requested(self, _: RematchRequested) -> None:
        """No meio da partida não vale. Com a partida encerrada, a tela de fim precisa saber."""
        if self._scene.engine.result is not None:
            self.link.peer_wants_rematch = True

    def _on_peer_left(self, event: PeerLeft) -> None:
        self._end_without_peer(event.reason, _VICTORY_SENTENCE)

    def _on_network_error(self, event: NetworkError) -> None:
        self._end_without_peer(event.message)

    def _end_without_peer(self, message: str, victory_sentence: str = "") -> None:
        """A vitória só é anunciada se foi a saída do outro lado que decidiu a partida."""
        is_decided_by_departure = self._scene.engine.result is None and self._requested_end is None
        self.link.peer_is_gone = True
        result = self._result_without_peer()
        self._settle(result, message + victory_sentence if is_decided_by_departure else message)

    def _result_without_peer(self) -> GameResult:
        """Sem ninguém para decidir, vale o que este lado já sabe: o fim no tabuleiro, o próprio pedido ou o abandono do outro."""
        scene = self._scene
        return self._requested_end() if self._requested_end is not None else scene.engine.abandon(scene.remote_color)

    # Relógio ------------------------------------------------------------------------------------

    def tick(self, dt: float) -> None:
        """Só a sala decide por tempo. Em quem entrou, os relógios andam apenas para mostrar."""
        scene = self._scene
        engine = scene.engine
        self.publish_result()
        self._give_up_waiting_after(dt)
        if engine.result is not None or scene.view.is_flying:
            return
        if not self.is_authority:
            engine.clock.tick(engine.turn, dt)
            return
        result = engine.tick(dt)
        if result is not None:
            self._settle(result)

    def _give_up_waiting_after(self, dt: float) -> None:
        """A sala está viva mas não responde: quem entrou não pode ficar preso esperando."""
        is_waiting = self._scene.engine.result is not None or self._requested_end is not None
        if self.is_decided or not is_waiting:
            return
        self._decision_wait += dt
        if self._decision_wait >= DECISION_WAIT_SECONDS:
            self.link.peer_is_gone = True
            self.link.leave()
            self._settle(self._result_without_peer(), NO_DECISION_MESSAGE)

    # Saída --------------------------------------------------------------------------------------

    def publish_result(self) -> None:
        """A sala diz como a partida acabou e em que lance, uma vez por partida."""
        engine = self._scene.engine
        if self.is_authority and engine.result is not None and not self._is_published:
            self._is_published = True
            self.link.session.send_result(engine.result, len(engine.history))

    def conclude_on_exit(self) -> None:
        """Sair com a partida aberta é abandono de quem sai. Partida já encerrada não muda."""
        scene = self._scene
        scene.engine.abandon(scene.local_color)
        self._is_settled = True
        self.publish_result()

    def send_move(self, uci: str) -> None:
        """Jogar também responde a uma proposta de empate aberta: recusa. A recusa vai depois, para aparecer depois do pouso."""
        self._may_offer_draw = True
        engine = self._scene.engine
        self.link.session.send_move(uci, engine.clock.remaining(self._scene.local_color) * _MILLISECONDS)
        if self._peer_offer_open:
            self._answer_draw(False)

    def resign(self) -> None:
        scene = self._scene
        if not self.is_authority:
            self.link.session.send_resign()
            scene.notices.show(RESIGN_SENT_MESSAGE)
        self._request_end(lambda: scene.engine.resign(scene.local_color))

    def send_draw_offer(self) -> None:
        self.draw_answer_pending = True
        self.link.session.send_draw_offer()
