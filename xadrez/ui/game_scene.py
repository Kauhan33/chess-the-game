"""Tela principal: liga a entrada do jogador ao motor de regras e o motor à apresentação 3D.

O motor é a única autoridade sobre as regras. Quando uma ação é recusada, a mensagem exibida é a
que ele devolveu, nunca um texto decidido aqui. A exceção é o modo Partida: o motivo seria uma dica,
então o aviso é sempre o mesmo.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Callable

import pygame

from xadrez.core import (
    Color,
    EndReason,
    GameEngine,
    GameResult,
    GameState,
    Move,
    MoveError,
    MoveOutcome,
    PieceType,
    Player,
    Square,
    game_to_pgn,
    legal_moves,
)
from xadrez.graphics import MARKER_CORNERS, MARKER_DOT, MARKER_RING, MARKER_TRIANGLE, CellState
from xadrez.ui import clipboard, theme as tokens
from xadrez.ui.board_view import BoardView
from xadrez.ui.cpu_player import CpuPlayer
from xadrez.ui.debug_panels import DidacticPanel, PerformancePanel
from xadrez.ui.hud import NOTICE_DANGER, NOTICE_TURN, NOTICE_WARNING, Hud, NoticeBar
from xadrez.ui.match import OPPONENT_CPU, GameMode, MatchOptions, pgn_without_check_marks
from xadrez.ui.match_record import save_match
from xadrez.ui.net_link import NetLink, NetMatch
from xadrez.ui.overlays import ChoiceOverlay, HelpOverlay, Overlay, PeerOfferCard, PromotionDialog
from xadrez.ui.scene import Scene
from xadrez.ui.widgets import STYLE_DANGER, STYLE_PRIMARY, Button

if TYPE_CHECKING:
    from xadrez.ui.app import App

Cell = tuple[int, int]

GENERIC_REFUSAL = "Lance inválido."
CPU_TURN_NOTICE = "Aguarde: é a vez da CPU."
PEER_TURN_NOTICE = "Aguarde: é a vez do adversário."
CPU_FAILURE_NOTICE = "A busca da CPU falhou, e ela fez um lance simples para a partida seguir."
DRAW_OFFER_AGAIN_NOTICE = "O adversário recusou: proponha de novo depois do seu próximo lance."
_DOUBLE_CLICK_SECONDS = 0.25
_DOUBLE_CLICK_PIXELS = 6
_DRAG_START_PIXELS = 6
_MOUSE_MODE = "mouse"
_KEYBOARD_MODE = "keyboard"
_MATE_ENDING_SECONDS = 2.2
_QUICK_ENDING_SECONDS = 0.9
_FIREWORK_INTERVAL = 0.42
_SHORT_NOTICE_SECONDS = 1.6
_CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
_START_CURSOR = {Color.WHITE: (4, 1), Color.BLACK: (4, 6)}
# Para cada quarto de volta da câmera: casa "para cima" e "para a direita" na tela, em (file, rank).
_SCREEN_AXES = (
    ((0, 1), (1, 0)),
    ((-1, 0), (0, 1)),
    ((0, -1), (-1, 0)),
    ((1, 0), (0, -1)),
)


@dataclass(frozen=True)
class _TurnAlerts:
    """O que a posição diz neste turno. Calculado uma vez por turno, nunca a cada quadro."""

    threatened: tuple[Cell, ...] = ()
    checked_king: Cell | None = None
    attackers: tuple[Cell, ...] = ()


@dataclass(frozen=True)
class _MousePress:
    """Botão esquerdo apertado em peça própria: ainda pode virar clique simples ou arrasto."""

    cell: Cell
    position: tuple[int, int]
    was_selected: bool


class GameScene(Scene):
    def __init__(self, app: App, engine: GameEngine, options: MatchOptions, view: BoardView | None = None,
                 local_player: Player | None = None, link: NetLink | None = None):
        super().__init__(app)
        self.engine = engine
        self.options = options
        self.view = view if view is not None else BoardView(app.meshes, seed=app.seed)
        self.local_player = local_player if local_player is not None else _default_local_player(engine, options)
        self.hides_hints = options.mode is GameMode.MATCH
        self.auto_rotate = options.auto_rotate and options.is_local
        self.cpu = self._create_cpu()
        self.net = NetMatch(self, link) if link is not None else None
        self.selection: Square | None = None
        self.targets: dict[Square, Move] = {}
        self.cursor: Cell | None = None
        self.modals: list[Overlay] = []
        self.notices = NoticeBar(app.theme)
        self.performance_panel = PerformancePanel(app.theme)
        self.didactic_panel = DidacticPanel(app.theme)
        self._alerts = _TurnAlerts()
        self._last_move: tuple[Cell, Cell] | None = None
        self._input_mode = _MOUSE_MODE
        self._mouse_pos: tuple[int, int] | None = None
        self._hover_key: tuple | None = None
        self._is_orbiting = False
        self._press: _MousePress | None = None
        self._guarded_click: tuple[int, int] | None = None
        self._click_guard_left = 0.0
        self._ending_left: float | None = None
        self._firework_left = 0.0
        self._is_saved = False
        self._save_warning: str | None = None
        self._closing_notice: str | None = None
        self._peer_offer: PeerOfferCard | None = None
        self._rotation_button = Button(self._rotation_label(), self._toggle_rotation, hint="T", font_size=16)
        self.hud = Hud(app.theme, self.view.renderer, app.meshes, engine, self._hud_buttons(),
                       options.mode.label, self.hides_hints)
        self._key_actions = {
            pygame.K_p: self.open_pause,
            pygame.K_r: self.confirm_restart,
            pygame.K_t: self._toggle_rotation,
            pygame.K_v: self._restore_view,
            pygame.K_f: self.flip_board,
            pygame.K_c: self.copy_pgn,
            pygame.K_h: self.open_help,
            pygame.K_F1: self.open_help,
            pygame.K_ESCAPE: self._cancel,
        }
        self._cursor_keys = {pygame.K_UP: (0, 1), pygame.K_DOWN: (0, -1), pygame.K_RIGHT: (1, 0), pygame.K_LEFT: (-1, 0)}
        self.resize(app.size)
        self._start_game()

    def _create_cpu(self) -> CpuPlayer | None:
        if self.options.opponent_kind != OPPONENT_CPU:
            return None
        return CpuPlayer(self.options.difficulty, random.Random(self.app.seed), lambda: self.view.is_animating)

    def _hud_buttons(self) -> list[Button]:
        rotation = [self._rotation_button] if self.options.is_local else []
        return [
            Button("Opções" if self.net else "Pausar", self.open_pause, hint="P", font_size=16),
            *rotation,
            Button("Vista padrão", self._restore_view, hint="V", font_size=16),
            Button("Ajuda", self.open_help, hint="H", font_size=16),
            Button("Virar", self.flip_board, hint="F", font_size=16),
            Button("Copiar PGN", self.copy_pgn, hint="C", font_size=16),
            Button("Desistir", self._confirm_resign, font_size=16),
        ]

    @property
    def local_color(self) -> Color:
        return self.local_player.color

    @property
    def remote_color(self) -> Color:
        return self.local_player.color.opposite

    @property
    def is_local_turn(self) -> bool:
        """Em 2 jogadores, a vez é sempre de quem está nesta tela."""
        return self.options.is_local or self.engine.turn is self.local_color

    # Ciclo de vida da partida --------------------------------------------------------------------

    def _start_game(self) -> None:
        """Vale para a primeira partida, para o reinício e para a revanche."""
        self.view.reset()
        self.view.sync(self.engine.board)
        self.selection = None
        self.targets = {}
        self.cursor = None
        self._press = None
        self._last_move = None
        self._ending_left = None
        self._is_saved = False
        self._save_warning = None
        self._closing_notice = None
        self.notices.clear_message()
        self._begin_turn()
        self._restore_view()

    def _begin_turn(self) -> None:
        """Início de um turno: é o único ponto em que ameaças e xeque são recalculados."""
        engine = self.engine
        if engine.result is not None:
            # Em rede, quem entrou na sala ainda espera a palavra dela: `end_match` chama o fim.
            if self._is_result_final:
                self._begin_ending(engine.result)
            return
        self._alerts = self._compute_alerts()
        self.hud.active_color = engine.turn
        self.hud.checked_color = engine.turn if self._alerts.checked_king is not None else None
        self._announce_turn()
        self._paint_highlights()
        if self.auto_rotate:
            self.view.face(engine.turn)
        self._start_cpu_turn()

    def _compute_alerts(self) -> _TurnAlerts:
        if self.hides_hints:
            return _TurnAlerts()
        engine = self.engine
        threatened = tuple(tuple(square) for square in engine.threatened_pieces(engine.turn))
        king = engine.checked_king_square
        if king is None:
            return _TurnAlerts(threatened)
        return _TurnAlerts(threatened, tuple(king), tuple(tuple(square) for square in engine.checking_pieces))

    def _announce_turn(self) -> None:
        player = self.engine.current_player
        if self._alerts.checked_king is not None:
            self.notices.set_status(f"Xeque! {player.name} precisa defender o rei.", NOTICE_DANGER)
        elif self.is_local_turn:
            self.notices.set_status(f"Vez de {player.name}, {player.color.label}", NOTICE_TURN)
        elif self.cpu is not None:
            self.notices.set_status(f"{player.name} está pensando", NOTICE_TURN)
        else:
            self.notices.set_status(f"Aguardando a jogada de {player.name}", NOTICE_TURN)

    def _begin_ending(self, result: GameResult) -> None:
        if self._ending_left is not None:
            return
        self._stop_cpu()
        self._close_all_modals()
        self.selection = None
        self.targets = {}
        self._end_press()
        self.view.lifted_square = None
        self.cursor = None
        self._alerts = _TurnAlerts()
        self.hud.active_color = result.winner
        self.hud.checked_color = None
        self.notices.clear_message()
        self.notices.set_status(self._ending_status(result), NOTICE_DANGER if result.winner else NOTICE_TURN)
        is_mate = result.reason is EndReason.CHECKMATE
        self._ending_left = _MATE_ENDING_SECONDS if is_mate else _QUICK_ENDING_SECONDS
        if is_mate:
            self._drop_defeated_king(result)
        self._paint_highlights()
        self._save_result()

    def _ending_status(self, result: GameResult) -> str:
        if result.winner is None:
            return f"Empate: {result.reason.label}"
        return f"{result.reason.label}! {self.engine.players[result.winner].name} venceu."

    def _drop_defeated_king(self, result: GameResult) -> None:
        """Depois do fim, a partida pode dizer o que aconteceu: até no modo Partida o rei tomba e o mate é marcado."""
        loser = result.winner.opposite
        king = self.engine.board.king_square(loser)
        attackers = tuple(tuple(square) for square in self.engine.board.attackers_of(king, result.winner))
        self._alerts = _TurnAlerts(checked_king=tuple(king), attackers=attackers)
        self.view.start_king_fall(tuple(king), loser, attackers[0] if attackers else None)

    def _advance_ending(self, dt: float) -> None:
        if self._ending_left is None:
            return
        self._launch_ending_fireworks(dt)
        self._ending_left -= dt
        if self._ending_left <= 0.0:
            self.next_scene = self.app.game_over_scene(self.engine, self.options, self.view, self.local_player,
                                                       self.net.link if self.net else None)
            message = self._save_warning or self._closing_notice
            if message is not None:
                self.next_scene.notices.show(message)

    def _launch_ending_fireworks(self, dt: float) -> None:
        result = self.engine.result
        if result is None or result.winner is None:
            return
        self._firework_left -= dt
        if self._firework_left <= 0.0:
            self._firework_left = _FIREWORK_INTERVAL
            self.view.launch_fireworks(tokens.FIREWORK_COLORS)

    def _save_result(self) -> None:
        """Só conta quem está logado, e uma vez por partida. Falha ao gravar vira aviso, nunca queda."""
        store = None if self._is_saved or self.engine.result is None or not self._is_result_final else self.app.history_store()
        if store is not None:
            self._is_saved = True
            self._save_warning = save_match(store, self.engine, self.options, self.local_player)
        if self._save_warning is not None:
            self.notices.show(self._save_warning)

    def end_match(self, result: GameResult, closing_notice: str | None = None) -> None:
        """A rede encerrou a partida. O motivo, quando há, segue até a tela de fim."""
        self._begin_ending(result)
        if closing_notice is not None:
            self._closing_notice = closing_notice
            self.notices.show(closing_notice)

    @property
    def _is_result_final(self) -> bool:
        return self.net is None or self.net.is_decided

    # Entrada -------------------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
        if event.type == pygame.MOUSEBUTTONDOWN and self._is_double_click_echo(event.pos):
            return
        if event.type == pygame.KEYDOWN and self._handle_panel_key(event.key):
            return
        if self.modals:
            top = self.modals[-1]
            was_taken = top.handle_event(event)
            if top.blocks_game or was_taken:
                return
        if self.hud.handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._handle_mouse_up(event)
        elif event.type == pygame.MOUSEWHEEL:
            self.view.zoom(event.y)

    def _is_double_click_echo(self, position: tuple[int, int]) -> bool:
        """Depois que uma sobreposição abre ou fecha, o 2º clique de um clique duplo acertaria o que apareceu ali."""
        if self._click_guard_left <= 0.0 or self._guarded_click is None:
            return False
        reach = max(abs(position[0] - self._guarded_click[0]), abs(position[1] - self._guarded_click[1]))
        return reach <= _DOUBLE_CLICK_PIXELS

    def _arm_click_guard(self) -> None:
        self._guarded_click = self._mouse_pos
        self._click_guard_left = _DOUBLE_CLICK_SECONDS

    def _handle_panel_key(self, key: int) -> bool:
        if key == pygame.K_F3:
            self.performance_panel.toggle()
        elif key == pygame.K_F4:
            self.didactic_panel.toggle()
            self._fit_board()
        else:
            return False
        return True

    def _handle_key(self, key: int) -> None:
        action = self._key_actions.get(key)
        if action is not None:
            action()
        elif self._ending_left is not None:
            return
        elif key in self._cursor_keys:
            self._move_cursor(self._cursor_keys[key])
        elif key in _CONFIRM_KEYS:
            self._activate_cursor()

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        self._input_mode = _MOUSE_MODE
        self._continue_press(event)
        if not self._is_orbiting:
            return
        # O botão pode ter sido solto fora da janela, sem gerar MOUSEBUTTONUP.
        self._is_orbiting = bool(event.buttons[2])
        if self._is_orbiting:
            self.view.drag_orbit(*event.rel)

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        self._mouse_pos = event.pos
        self._input_mode = _MOUSE_MODE
        if event.button == 3:
            self._is_orbiting = self.hud.viewport.collidepoint(event.pos)
        elif event.button == 1 and self._ending_left is None:
            self._press_square(event.pos)

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 3:
            self._is_orbiting = False
        elif event.button == 1:
            self._release_press(event.pos)

    # Clique e arrasto ----------------------------------------------------------------------------

    def _press_square(self, position: tuple[int, int]) -> None:
        cell = self.view.pick(position)
        self._set_cursor(cell)
        if cell is not None and cell == self._selected_cell() and not self.is_board_locked:
            self._press = _MousePress(cell, position, was_selected=True)
            return
        self._activate_square(cell)
        if cell is not None and cell == self._selected_cell():
            self._press = _MousePress(cell, position, was_selected=False)

    def _continue_press(self, event: pygame.event.Event) -> None:
        press = self._press
        if press is None:
            return
        # Soltou fora da janela: a peça volta para a casa e a seleção fica.
        if not event.buttons[0]:
            self._end_press()
            return
        reach = max(abs(event.pos[0] - press.position[0]), abs(event.pos[1] - press.position[1]))
        if self.view.dragged_square is None and reach >= _DRAG_START_PIXELS:
            self.view.begin_drag(press.cell)
        if self.view.dragged_square is not None:
            self.view.drag_to(event.pos)

    def _release_press(self, position: tuple[int, int]) -> None:
        press = self._press
        if press is None:
            return
        was_dragging = self.view.dragged_square is not None
        self._end_press()
        if was_dragging:
            self._drop_piece(Square(*press.cell), self.view.pick(position))
        elif press.was_selected:
            self._set_selection(None)

    def _end_press(self) -> None:
        self._press = None
        self.view.end_drag()

    def _drop_piece(self, origin: Square, cell: Cell | None) -> None:
        """Soltou na própria casa: nada muda, e a seleção fica. Fora do tabuleiro: a peça só volta. O resto o motor julga."""
        self._set_cursor(cell)
        if cell == tuple(origin):
            return
        if cell is None:
            self._set_selection(None)
        elif Square(*cell) in self.targets:
            self._play_or_ask_promotion(origin, Square(*cell))
        else:
            self._submit_move(origin, Square(*cell))

    def _move_cursor(self, screen_step: Cell) -> None:
        """As setas seguem o que se vê: com a câmera do lado das pretas, "para cima" é fileira menor."""
        self._input_mode = _KEYBOARD_MODE
        if self.cursor is None:
            self._set_cursor(_START_CURSOR[self.engine.turn])
            return
        up, right = _SCREEN_AXES[round(self.view.camera.yaw / (math.pi / 2.0)) % 4]
        file = self.cursor[0] + screen_step[0] * right[0] + screen_step[1] * up[0]
        rank = self.cursor[1] + screen_step[0] * right[1] + screen_step[1] * up[1]
        self._set_cursor((max(0, min(file, 7)), max(0, min(rank, 7))))

    def _activate_cursor(self) -> None:
        self._input_mode = _KEYBOARD_MODE
        if self.cursor is None:
            self._set_cursor(_START_CURSOR[self.engine.turn])
            return
        self._activate_square(self.cursor)

    def _cancel(self) -> None:
        if self.selection is not None:
            self._set_selection(None)
            return
        self.open_pause()

    # Seleção e jogadas ---------------------------------------------------------------------------

    @property
    def is_board_locked(self) -> bool:
        """Durante o voo o clique fica bloqueado. Só o relógio e o cursor continuam."""
        return (self.view.is_flying or self._ending_left is not None or self._awaits_room
                or self.engine.state is not GameState.IN_PROGRESS)

    def _activate_square(self, cell: Cell | None) -> None:
        if self.is_board_locked:
            return
        if not self.is_local_turn:
            self.notices.show(CPU_TURN_NOTICE if self.cpu is not None else PEER_TURN_NOTICE, NOTICE_TURN, _SHORT_NOTICE_SECONDS)
        elif cell is None:
            self._set_selection(None)
        elif self.selection is None:
            self._try_select(Square(*cell))
        else:
            self._act_on_selection(Square(*cell))

    def _try_select(self, square: Square) -> None:
        piece = self.engine.board.piece_at(square)
        if piece is None or piece.color is not self.engine.turn:
            self._submit_move(square, square)
            return
        self._set_selection(square)
        # No modo Partida, dizer que a peça não tem jogada seria uma dica.
        if not self.targets and not self.hides_hints:
            self.notices.show("Essa peça não tem jogada válida agora.")

    def _act_on_selection(self, square: Square) -> None:
        origin = self.selection
        if square == origin:
            self._set_selection(None)
        elif square in self.targets:
            self._play_or_ask_promotion(origin, square)
        else:
            self._redirect_selection(origin, square)

    def _redirect_selection(self, origin: Square, square: Square) -> None:
        piece = self.engine.board.piece_at(square)
        if piece is not None and piece.color is self.engine.turn:
            self._set_selection(square)
        else:
            self._submit_move(origin, square)

    def _play_or_ask_promotion(self, origin: Square, target: Square) -> None:
        if not self.engine.is_promotion_move(origin, target):
            self._submit_move(origin, target)
            return
        self._push_modal(PromotionDialog(
            self.app.theme, self.view.renderer, self.app.meshes, self.engine.turn,
            on_choose=lambda kind: self._choose_promotion(origin, target, kind),
            on_cancel=self._cancel_promotion,
        ))

    def _choose_promotion(self, origin: Square, target: Square, kind: PieceType) -> None:
        self._pop_modal()
        self._submit_move(origin, target, kind)

    def _cancel_promotion(self) -> None:
        self._pop_modal()
        self._set_selection(None)

    def _submit_move(self, origin: Square, target: Square, promotion: PieceType | None = None) -> None:
        outcome = self.engine.play(origin, target, promotion)
        self._set_selection(None)
        if outcome.ok:
            self._show_move(outcome)
            if self.net is not None:
                self.net.send_move(outcome.move.uci)
        else:
            self._refuse(outcome.error, target)

    def _refuse(self, error: MoveError, square: Square) -> None:
        if self.hides_hints:
            self.notices.show(GENERIC_REFUSAL, NOTICE_WARNING)
            return
        self.notices.show(error.message, NOTICE_WARNING)
        self.view.shake(tuple(square))

    def _show_move(self, outcome: MoveOutcome) -> None:
        move = outcome.move
        self._last_move = (tuple(move.origin), tuple(move.target))
        self._alerts = _TurnAlerts()
        self.notices.clear_message()
        self.hud.checked_color = None
        self.hud.thinking_color = None
        # A luz acompanha o relógio, que já passou para o outro jogador enquanto a peça voa.
        self.hud.active_color = self.engine.turn
        self.view.start_move(outcome)
        self._paint_highlights()
        # Se o jogo fechar com a peça no ar, a partida encerrada não pode se perder.
        self._save_result()

    def show_opponent_move(self, outcome: MoveOutcome) -> None:
        """Jogada que chegou de fora: anima igual à de quem está na tela. Se havia seleção, ela já não vale."""
        self._set_selection(None)
        self._show_move(outcome)

    def retract_last_move(self) -> None:
        """A sala não aceitou o último lance daqui, que cruzou com o fim da partida: a peça volta para a casa."""
        self.view.reset()
        self.view.sync(self.engine.board)
        self._last_move = None

    def _set_selection(self, square: Square | None) -> None:
        self._end_press()
        self.selection = square
        moves = [] if square is None else self.engine.legal_moves_from(square)
        # Na promoção há 4 jogadas para a mesma casa: o dicionário guarda uma só por destino.
        self.targets = {move.target: move for move in moves}
        self.view.lifted_square = None if square is None else tuple(square)
        self._hover_key = None
        self._paint_highlights()

    def _set_cursor(self, cell: Cell | None) -> None:
        if cell != self.cursor:
            self.cursor = cell
            self._paint_highlights()

    # CPU -----------------------------------------------------------------------------------------

    def _start_cpu_turn(self) -> None:
        if self.cpu is None or self.is_local_turn or self.engine.state is not GameState.IN_PROGRESS:
            return
        color = self.engine.turn
        self.hud.thinking_color = color
        self.cpu.start(self.engine.board, self.engine.clock.remaining(color), self.engine.time_control.increment)

    def _stop_cpu(self) -> None:
        self.hud.thinking_color = None
        if self.cpu is not None:
            self.cpu.cancel()

    def _advance_cpu(self, dt: float) -> None:
        move = self.cpu.poll(dt)
        if move is None:
            return
        outcome = self.engine.play(move.origin, move.target, move.promotion)
        if not outcome.ok:
            outcome = self._play_any_legal_move()
        self._show_move(outcome)
        if self.cpu.last_error is not None:
            self.notices.show(CPU_FAILURE_NOTICE)

    def _play_any_legal_move(self) -> MoveOutcome:
        """Último recurso, se o motor recusar a jogada da busca: a partida não pode travar na vez da CPU."""
        move = legal_moves(self.engine.board)[0]
        self.cpu.last_error = self.cpu.last_error or ValueError("O motor recusou a jogada da busca.")
        return self.engine.play(move.origin, move.target, move.promotion)

    # Destaques -----------------------------------------------------------------------------------

    def _paint_highlights(self) -> None:
        """Traduz o estado da partida em matriz de cores, marcadores de forma e tints das peças."""
        matrix = self.view.matrix
        matrix.clear()
        markers: list[tuple] = []
        tints: dict[Cell, tuple] = {}
        if self._last_move is not None:
            matrix.set_many(self._last_move, CellState.LAST_MOVE)
        self._paint_alerts(markers, tints)
        self._paint_selection(markers)
        # A casa selecionada continua amarela sob o mouse: é ela que o jogador precisa reconhecer.
        if self.cursor is not None and self.cursor != self._selected_cell():
            matrix.set(*self.cursor, CellState.CURSOR)
            markers.append((*self.cursor, MARKER_CORNERS, tokens.MARKER_CURSOR_COLOR))
        self.view.markers = markers
        self.view.tints = tints

    def _selected_cell(self) -> Cell | None:
        return None if self.selection is None else tuple(self.selection)

    def _paint_alerts(self, markers: list[tuple], tints: dict[Cell, tuple]) -> None:
        matrix, alerts = self.view.matrix, self._alerts
        for cell in alerts.threatened:
            matrix.set(*cell, CellState.THREAT)
            markers.append((*cell, MARKER_TRIANGLE, tokens.MARKER_THREAT_COLOR))
            tints[cell] = tokens.THREAT_TINT
        if alerts.checked_king is not None:
            matrix.set(*alerts.checked_king, CellState.CHECK)
            tints[alerts.checked_king] = tokens.CHECK_TINT
        for cell in alerts.attackers:
            matrix.set(*cell, CellState.CHECK)
            markers.append((*cell, MARKER_CORNERS, tokens.MARKER_CHECK_COLOR))

    def _paint_selection(self, markers: list[tuple]) -> None:
        if self.selection is None:
            return
        matrix = self.view.matrix
        matrix.set(*self.selection, CellState.SELECTED)
        markers.append((*self.selection, MARKER_CORNERS, tokens.MARKER_SELECTED_COLOR))
        if self.hides_hints:
            return
        board = self.engine.board
        for target, move in self.targets.items():
            is_capture = move.is_en_passant or board.piece_at(target) is not None
            matrix.set(*target, CellState.CAPTURE if is_capture else CellState.PATH)
            if is_capture:
                markers.append((*target, MARKER_RING, tokens.MARKER_CAPTURE_COLOR))
            else:
                markers.append((*target, MARKER_DOT, tokens.MARKER_PATH_COLOR))

    def _refresh_hover(self) -> None:
        """Só refaz o picking quando o mouse ou a câmera mudaram (RNF03), e nunca sobre o teclado."""
        has_blocking_overlay = any(overlay.blocks_game for overlay in self.modals)
        if self._input_mode != _MOUSE_MODE or self._mouse_pos is None or has_blocking_overlay or self._ending_left is not None:
            return
        key = (self._mouse_pos, self.view.camera.revision)
        if key != self._hover_key:
            self._hover_key = key
            self._set_cursor(self.view.pick(self._mouse_pos))

    # Sobreposições -------------------------------------------------------------------------------

    def _push_modal(self, overlay: Overlay) -> None:
        self._is_orbiting = False
        self._end_press()
        self.hud.release_buttons()
        self._arm_click_guard()
        overlay.layout(self.app.size)
        self.modals.append(overlay)
        # Em rede, o outro jogador não para: o relógio segue correndo com a sobreposição aberta.
        if self.net is not None:
            overlay.freezes_clock = False
        if overlay.freezes_clock:
            self.engine.pause()

    def _pop_modal(self) -> None:
        if self.modals:
            self.modals.pop()
        if not any(overlay.freezes_clock for overlay in self.modals):
            self.engine.resume()
        self._arm_click_guard()
        self._hover_key = None

    def _close_all_modals(self) -> None:
        self.modals.clear()
        self.engine.resume()
        self._arm_click_guard()
        self._hover_key = None

    def open_pause(self) -> None:
        if self.engine.state is not GameState.IN_PROGRESS or self._ending_left is not None:
            return
        title, line = ("Partida em rede", "O relógio continua correndo.") if self.net else ("Partida pausada", "O relógio está parado.")
        self._push_modal(ChoiceOverlay(
            self.app.theme, title, [line], self._pause_buttons(),
            on_cancel=self._pop_modal,
            cancel_keys=(pygame.K_ESCAPE, pygame.K_p),
        ))

    def _pause_buttons(self) -> list[Button]:
        resume_label = "Voltar ao jogo" if self.net else "Retomar"
        resume = Button(resume_label, self._pop_modal, STYLE_PRIMARY, hint="P")
        resign = Button("Desistir", self._confirm_resign, STYLE_DANGER)
        if self.net is not None:
            return [resume, Button("Propor empate", self._propose_draw), resign, Button("Sair da sala", self._confirm_menu)]
        restart = Button("Reiniciar partida", self.confirm_restart)
        menu = Button("Voltar ao menu", self._confirm_menu)
        # Contra a CPU não há com quem combinar um empate.
        draw = [Button("Propor empate", self._propose_draw)] if self.options.is_local else []
        return [resume, restart, *draw, resign, menu]

    def open_help(self) -> None:
        if self._ending_left is None:
            self._push_modal(HelpOverlay(self.app.theme, self._pop_modal, self._keys_without_effect()))

    def _keys_without_effect(self) -> tuple[str, ...]:
        """A ajuda só lista o que vale nesta partida: em rede não há reinício, e o giro por turno é só de 2 jogadores."""
        if self.options.is_local:
            return ()
        return ("R", "T") if self.net is not None else ("T",)

    def confirm_restart(self) -> None:
        if self._ending_left is not None or self.engine.result is not None or self.net is not None:
            return
        lines = ["O tabuleiro volta ao início.", "O placar da série é mantido."]
        self._confirm("Reiniciar a partida?", lines, "Reiniciar", self.restart)

    def restart(self) -> None:
        self._stop_cpu()
        self._close_all_modals()
        self.engine.restart()
        self._start_game()

    def _confirm_resign(self) -> None:
        if self._ending_left is not None or self.engine.result is not None or self._awaits_room:
            return
        resigning = self.engine.current_player if self.options.is_local else self.local_player
        opponent = self.engine.players[resigning.color.opposite]
        lines = [f"{resigning.name} entrega a partida.", f"A vitória vai para {opponent.name}."]
        self._confirm("Desistir da partida?", lines, "Desistir", self._resign, STYLE_DANGER)

    def _resign(self) -> None:
        if self.net is not None:
            self._close_all_modals()
            self.net.resign()
            return
        color = self.engine.turn if self.options.is_local else self.local_color
        self._begin_ending(self.engine.resign(color))

    @property
    def _awaits_room(self) -> bool:
        return self.net is not None and self.net.awaits_decision

    def _propose_draw(self) -> None:
        if self.net is not None:
            self._propose_draw_to_peer()
            return
        player, opponent = self.engine.current_player, self.engine.players[self.engine.turn.opposite]
        self._push_modal(ChoiceOverlay(
            self.app.theme,
            "Proposta de empate",
            [f"{player.name} propõe empate.", f"{opponent.name}, você aceita?"],
            [Button("Aceitar empate", self._accept_draw, STYLE_PRIMARY), Button("Recusar", self._refuse_draw)],
            on_cancel=self._refuse_draw,
            initial_focus=1,
        ))

    def _accept_draw(self) -> None:
        self._begin_ending(self.engine.agree_draw())

    def _refuse_draw(self) -> None:
        opponent = self.engine.players[self.engine.turn.opposite]
        self._close_all_modals()
        self.notices.show(f"{opponent.name} recusou o empate.", NOTICE_WARNING)

    def _propose_draw_to_peer(self) -> None:
        self._pop_modal()
        if self._awaits_room:
            return
        if self.net.draw_answer_pending:
            self.notices.show("A proposta de empate já foi enviada.", NOTICE_TURN, _SHORT_NOTICE_SECONDS)
            return
        if not self.net.may_offer_draw:
            self.notices.show(DRAW_OFFER_AGAIN_NOTICE, NOTICE_TURN, _SHORT_NOTICE_SECONDS)
            return
        self.net.send_draw_offer()
        self.notices.show(f"Proposta de empate enviada a {self.net.link.peer_name}.", NOTICE_TURN)

    def show_peer_draw_offer(self, answer: Callable[[bool], None]) -> None:
        """O outro jogador propôs empate pela rede. O cartão fica na base da pilha: as outras sobreposições fecham antes dele."""
        peer = self.net.link.peer_name
        self._peer_offer = PeerOfferCard(
            self.app.theme,
            "Proposta de empate",
            [f"{peer} propõe empate.", "Jogar um lance também recusa."],
            on_accept=lambda: answer(True),
            on_refuse=lambda: answer(False),
            anchor=lambda: self.hud.sheet.rect,
        )
        self._peer_offer.layout(self.app.size)
        self.modals.insert(0, self._peer_offer)

    def close_peer_draw_offer(self) -> None:
        if self._peer_offer in self.modals:
            self.modals.remove(self._peer_offer)
            self._arm_click_guard()
            self._hover_key = None
        self._peer_offer = None

    def _confirm_menu(self) -> None:
        if self.net is not None:
            lines = ["Sair da sala conta como abandono:", "a vitória vai para o adversário."]
            self._confirm("Sair da sala?", lines, "Sair da sala", self._leave_room, STYLE_DANGER)
            return
        lines = ["A partida é abandonada e o placar", "da série começa de novo."]
        self._confirm("Voltar ao menu?", lines, "Voltar ao menu", self._go_to_menu)

    def _leave_room(self) -> None:
        self._go_to_menu()

    def _go_to_menu(self) -> None:
        self.shutdown()
        self.next_scene = self.app.menu_scene(self.options)

    def _confirm(self, title: str, lines: list[str], action_label: str, on_accept, style: str = STYLE_PRIMARY) -> None:
        self._push_modal(ChoiceOverlay(
            self.app.theme, title, lines,
            [Button(action_label, on_accept, style), Button("Voltar", self._pop_modal)],
            on_cancel=self._pop_modal,
            initial_focus=1,
        ))

    def shutdown(self) -> None:
        """Em rede, sair ou fechar a janela é abandono: a derrota é gravada antes de a conexão fechar."""
        self._stop_cpu()
        if self.net is None:
            return
        self.net.conclude_on_exit()
        self._save_result()
        self.net.link.leave()

    # Mesa ----------------------------------------------------------------------------------------

    def _copyable_pgn(self) -> str:
        """No modo Partida, enquanto ela corre, a cópia não pode entregar o xeque que a tela esconde."""
        pgn = game_to_pgn(self.engine)
        return pgn_without_check_marks(pgn) if self.hides_hints and self.engine.result is None else pgn

    def copy_pgn(self) -> None:
        if clipboard.copy_text(self._copyable_pgn()):
            self.notices.show("PGN copiado para a área de transferência.", NOTICE_TURN, _SHORT_NOTICE_SECONDS)
        else:
            self.notices.show(clipboard.COPY_FAILED_MESSAGE, NOTICE_WARNING)

    def flip_board(self) -> None:
        self.view.flip()

    # Câmera --------------------------------------------------------------------------------------

    def _rotation_label(self) -> str:
        return "Giro ligado" if self.auto_rotate else "Giro desligado"

    def _toggle_rotation(self) -> None:
        if self._ending_left is not None or not self.options.is_local:
            return
        self.auto_rotate = not self.auto_rotate
        self.options = replace(self.options, auto_rotate=self.auto_rotate)
        self._rotation_button.label = self._rotation_label()
        self.notices.show(f"Giro por turno {'ligado' if self.auto_rotate else 'desligado'}.", NOTICE_TURN, _SHORT_NOTICE_SECONDS)
        if self.auto_rotate:
            self.view.face(self.engine.turn)

    def _restore_view(self) -> None:
        if self.options.is_local:
            self.view.restore_default_view(self.engine.turn if self.auto_rotate else Color.WHITE)
        else:
            self.view.restore_default_view(self.local_color)

    # Quadro --------------------------------------------------------------------------------------

    @property
    def is_frozen(self) -> bool:
        return any(overlay.freezes_clock for overlay in self.modals)

    def update(self, dt: float) -> None:
        self._click_guard_left -= dt
        if not self.is_frozen:
            self._advance_world(dt)
        for overlay in self.modals:
            overlay.update(dt)
        self.hud.update(dt)

    def _advance_world(self, dt: float) -> None:
        if self.net is not None:
            self.net.receive_events()
        self._advance_clock(dt)
        self.view.update(dt)
        if self.view.consume_landing():
            self._begin_turn()
        if self.cpu is not None and not self.view.is_flying:
            self._advance_cpu(dt)
        self._refresh_hover()
        self.notices.update(dt)
        self._advance_ending(dt)

    def _advance_clock(self, dt: float) -> None:
        if self.net is not None:
            self.net.tick(dt)
            return
        # O tabuleiro fica bloqueado no voo: quem vai jogar só começa a gastar tempo quando a peça pousa.
        result = None if self.view.is_flying else self.engine.tick(dt)
        if result is not None:
            self._begin_ending(result)

    def draw(self, surface: pygame.Surface) -> None:
        self.view.draw(surface)
        self.hud.draw(surface)
        self.notices.draw(surface)
        self.performance_panel.draw(surface, self.hud.viewport, self.app.fps, self.app.frame_ms, self.view)
        self.didactic_panel.draw(surface, self.hud.viewport, self.view, self._mouse_pos)
        for overlay in self.modals:
            overlay.draw(surface)

    def resize(self, size: tuple[int, int]) -> None:
        self.hud.layout(size)
        self._fit_board()
        for overlay in self.modals:
            overlay.layout(size)

    def _fit_board(self) -> None:
        """O modo didático abre espaço ao lado do tabuleiro, para não esconder nenhuma casa."""
        viewport = self.didactic_panel.board_area(self.hud.viewport)
        self.view.set_viewport(viewport)
        self.notices.layout(viewport)
        self._hover_key = None


def _default_local_player(engine: GameEngine, options: MatchOptions) -> Player:
    """Quem está neste computador, ao abrir a partida sem o menu: a cor escolhida contra a CPU, ou a primeira cor."""
    is_cpu = options.opponent_kind == OPPONENT_CPU
    return engine.players[(options.human_color or Color.WHITE) if is_cpu else Color.WHITE]
