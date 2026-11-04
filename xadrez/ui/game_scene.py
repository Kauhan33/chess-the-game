"""Tela principal: liga a entrada do jogador ao motor de regras e o motor à apresentação 3D.

O motor é a única autoridade sobre as regras. Quando uma ação é recusada, a mensagem exibida é a
que ele devolveu, nunca um texto decidido aqui.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from xadrez.core import Color, EndReason, GameEngine, GameResult, GameState, Move, MoveError, MoveOutcome, PieceType, Square
from xadrez.graphics import MARKER_CORNERS, MARKER_DOT, MARKER_RING, MARKER_TRIANGLE, CellState
from xadrez.ui import theme as tokens
from xadrez.ui.board_view import BoardView
from xadrez.ui.debug_panels import DidacticPanel, PerformancePanel
from xadrez.ui.hud import NOTICE_DANGER, NOTICE_TURN, NOTICE_WARNING, Hud, NoticeBar
from xadrez.ui.match import MatchOptions
from xadrez.ui.overlays import ChoiceOverlay, HelpOverlay, Overlay, PromotionDialog
from xadrez.ui.scene import Scene
from xadrez.ui.widgets import STYLE_DANGER, STYLE_PRIMARY, Button

if TYPE_CHECKING:
    from xadrez.ui.app import App

Cell = tuple[int, int]

_MOUSE_MODE = "mouse"
_KEYBOARD_MODE = "keyboard"
_MATE_ENDING_SECONDS = 2.2
_QUICK_ENDING_SECONDS = 0.9
_FIREWORK_INTERVAL = 0.42
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


class GameScene(Scene):
    def __init__(self, app: App, engine: GameEngine, options: MatchOptions, view: BoardView | None = None):
        super().__init__(app)
        self.engine = engine
        self.options = options
        self.view = view if view is not None else BoardView(app.meshes, seed=app.seed)
        self.auto_rotate = options.auto_rotate
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
        self._ending_left: float | None = None
        self._firework_left = 0.0
        self._rotation_button = Button(self._rotation_label(), self._toggle_rotation, hint="T", font_size=16)
        self.hud = Hud(app.theme, self.view.renderer, app.meshes, engine, [
            Button("Pausar", self.open_pause, hint="P", font_size=16),
            self._rotation_button,
            Button("Vista padrão", self._restore_view, hint="V", font_size=16),
            Button("Ajuda", self.open_help, hint="H", font_size=16),
        ])
        self._key_actions = {
            pygame.K_p: self.open_pause,
            pygame.K_r: self.confirm_restart,
            pygame.K_t: self._toggle_rotation,
            pygame.K_v: self._restore_view,
            pygame.K_h: self.open_help,
            pygame.K_F1: self.open_help,
            pygame.K_ESCAPE: self._cancel,
        }
        self._cursor_keys = {pygame.K_UP: (0, 1), pygame.K_DOWN: (0, -1), pygame.K_RIGHT: (1, 0), pygame.K_LEFT: (-1, 0)}
        self.resize(app.size)
        self._start_game()

    # Ciclo de vida da partida --------------------------------------------------------------------

    def _start_game(self) -> None:
        """Vale para a primeira partida, para o reinício e para a revanche."""
        self.view.reset()
        self.view.sync(self.engine.board)
        self.selection = None
        self.targets = {}
        self.cursor = None
        self._last_move = None
        self._ending_left = None
        self.notices.clear_message()
        self._begin_turn()
        self._restore_view()

    def _begin_turn(self) -> None:
        """Início de um turno: é o único ponto em que ameaças e xeque são recalculados."""
        engine = self.engine
        if engine.result is not None:
            self._begin_ending(engine.result)
            return
        self._alerts = self._compute_alerts()
        self.hud.active_color = engine.turn
        self.hud.checked_color = engine.turn if self._alerts.checked_king is not None else None
        self._announce_turn()
        self._paint_highlights()
        if self.auto_rotate:
            self.view.face(engine.turn)

    def _compute_alerts(self) -> _TurnAlerts:
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
        else:
            self.notices.set_status(f"Vez de {player.name}, {player.color.label}", NOTICE_TURN)

    def _begin_ending(self, result: GameResult) -> None:
        if self._ending_left is not None:
            return
        self._close_all_modals()
        self.selection = None
        self.targets = {}
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

    def _ending_status(self, result: GameResult) -> str:
        if result.winner is None:
            return f"Empate: {result.reason.label}"
        return f"{result.reason.label}! {self.engine.players[result.winner].name} venceu."

    def _drop_defeated_king(self, result: GameResult) -> None:
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
            self.next_scene = self.app.game_over_scene(self.engine, self.options, self.view)

    def _launch_ending_fireworks(self, dt: float) -> None:
        result = self.engine.result
        if result is None or result.winner is None:
            return
        self._firework_left -= dt
        if self._firework_left <= 0.0:
            self._firework_left = _FIREWORK_INTERVAL
            self.view.launch_fireworks(tokens.FIREWORK_COLORS)

    # Entrada -------------------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
        if event.type == pygame.KEYDOWN and self._handle_panel_key(event.key):
            return
        if self.modals:
            self.modals[-1].handle_event(event)
            return
        if self.hud.handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self._is_orbiting = False
        elif event.type == pygame.MOUSEWHEEL:
            self.view.zoom(event.y)

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
            cell = self.pick_at(event.pos)
            self._set_cursor(cell)
            self._activate_square(cell)

    def pick_at(self, position: tuple[int, int]) -> Cell | None:
        """Casa que um clique neste pixel aciona.

        O volume de clique de uma peça é um cilindro, mais largo que a cintura dela. Assim, a casa
        visível atrás de uma peça alta cairia dentro do cilindro. Se o raio pousa em um destino
        válido da peça selecionada, é esse destino que o jogador está vendo destacado e quer.
        """
        cell = self.view.pick(position)
        if self.selection is None or cell in self.targets:
            return cell
        floor = self.view.camera.pick_square(*position)
        return floor if floor in self.targets else cell

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
        return self.view.is_flying or self._ending_left is not None or self.engine.state is not GameState.IN_PROGRESS

    def _activate_square(self, cell: Cell | None) -> None:
        if self.is_board_locked:
            return
        if cell is None:
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
        if not self.targets:
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
        else:
            self._refuse(outcome.error, target)

    def _refuse(self, error: MoveError, square: Square) -> None:
        self.notices.show(error.message, NOTICE_WARNING)
        self.view.shake(tuple(square))

    def _show_move(self, outcome: MoveOutcome) -> None:
        move = outcome.move
        self._last_move = (tuple(move.origin), tuple(move.target))
        self._alerts = _TurnAlerts()
        self.notices.clear_message()
        self.hud.checked_color = None
        # A luz acompanha o relógio, que já passou para o outro jogador enquanto a peça voa.
        self.hud.active_color = self.engine.turn
        self.view.start_move(outcome)
        self._paint_highlights()

    def _set_selection(self, square: Square | None) -> None:
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
        if self._input_mode != _MOUSE_MODE or self._mouse_pos is None or self.modals or self._ending_left is not None:
            return
        key = (self._mouse_pos, self.view.camera.revision)
        if key != self._hover_key:
            self._hover_key = key
            self._set_cursor(self.pick_at(self._mouse_pos))

    # Sobreposições -------------------------------------------------------------------------------

    def _push_modal(self, overlay: Overlay) -> None:
        self._is_orbiting = False
        overlay.layout(self.app.size)
        self.modals.append(overlay)
        if overlay.freezes_clock:
            self.engine.pause()

    def _pop_modal(self) -> None:
        if self.modals:
            self.modals.pop()
        if not any(overlay.freezes_clock for overlay in self.modals):
            self.engine.resume()
        self._hover_key = None

    def _close_all_modals(self) -> None:
        self.modals.clear()
        self.engine.resume()
        self._hover_key = None

    def open_pause(self) -> None:
        if self.engine.state is not GameState.IN_PROGRESS or self._ending_left is not None:
            return
        self._push_modal(ChoiceOverlay(
            self.app.theme,
            "Partida pausada",
            ["O relógio está parado."],
            [
                Button("Retomar", self._pop_modal, STYLE_PRIMARY, hint="P"),
                Button("Reiniciar partida", self.confirm_restart),
                Button("Propor empate", self._propose_draw),
                Button("Desistir", self._confirm_resign, STYLE_DANGER),
                Button("Voltar ao menu", self._confirm_menu),
            ],
            on_cancel=self._pop_modal,
            cancel_keys=(pygame.K_ESCAPE, pygame.K_p),
        ))

    def open_help(self) -> None:
        if self._ending_left is None:
            self._push_modal(HelpOverlay(self.app.theme, self._pop_modal))

    def confirm_restart(self) -> None:
        if self._ending_left is not None:
            return
        lines = ["O tabuleiro volta ao início.", "O placar da série é mantido."]
        self._confirm("Reiniciar a partida?", lines, "Reiniciar", self.restart)

    def restart(self) -> None:
        self._close_all_modals()
        self.engine.restart()
        self._start_game()

    def _confirm_resign(self) -> None:
        player, opponent = self.engine.current_player, self.engine.players[self.engine.turn.opposite]
        lines = [f"A vitória vai para {opponent.name}."]
        self._confirm(f"{player.name} desiste?", lines, "Desistir", self._resign, STYLE_DANGER)

    def _resign(self) -> None:
        self._begin_ending(self.engine.resign())

    def _propose_draw(self) -> None:
        player, opponent = self.engine.current_player, self.engine.players[self.engine.turn.opposite]
        self._push_modal(ChoiceOverlay(
            self.app.theme,
            f"{player.name} propõe empate",
            [f"{opponent.name}, você aceita?"],
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

    def _confirm_menu(self) -> None:
        lines = ["A partida é abandonada e o placar", "da série começa de novo."]
        self._confirm("Voltar ao menu?", lines, "Voltar ao menu", self._go_to_menu)

    def _go_to_menu(self) -> None:
        self.next_scene = self.app.menu_scene(self.options)

    def _confirm(self, title: str, lines: list[str], action_label: str, on_accept, style: str = STYLE_PRIMARY) -> None:
        self._push_modal(ChoiceOverlay(
            self.app.theme, title, lines,
            [Button(action_label, on_accept, style), Button("Voltar", self._pop_modal)],
            on_cancel=self._pop_modal,
            initial_focus=1,
        ))

    # Câmera --------------------------------------------------------------------------------------

    def _rotation_label(self) -> str:
        return "Giro ligado" if self.auto_rotate else "Giro desligado"

    def _toggle_rotation(self) -> None:
        self.auto_rotate = not self.auto_rotate
        self._rotation_button.label = self._rotation_label()
        self.notices.show(f"Giro por turno {'ligado' if self.auto_rotate else 'desligado'}.", NOTICE_TURN, 1.6)
        if self.auto_rotate:
            self.view.face(self.engine.turn)

    def _restore_view(self) -> None:
        self.view.restore_default_view(self.engine.turn if self.auto_rotate else Color.WHITE)

    # Quadro --------------------------------------------------------------------------------------

    @property
    def is_frozen(self) -> bool:
        return any(overlay.freezes_clock for overlay in self.modals)

    def update(self, dt: float) -> None:
        if not self.is_frozen:
            self._advance_world(dt)
        for overlay in self.modals:
            overlay.update(dt)
        self.hud.update(dt)

    def _advance_world(self, dt: float) -> None:
        result = self.engine.tick(dt)
        if result is not None:
            self._begin_ending(result)
        self.view.update(dt)
        if self.view.consume_landing():
            self._begin_turn()
        self._refresh_hover()
        self.notices.update(dt)
        self._advance_ending(dt)

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
