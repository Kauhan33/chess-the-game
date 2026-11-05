"""Tela de fim de jogo: o painel da partida vira o resultado, e a posição final segue no mesmo lugar.

O tabuleiro não muda de tamanho nem de posição na troca de tela. Assim, o quadro da troca não
refaz o fundo de madeira, e a festa da vitória não trava no meio.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from xadrez.core import Color, GameEngine, GameResult, Player, game_to_pgn
from xadrez.net import GameStart, NetworkError, PeerLeft, RematchRequested
from xadrez.ui import clipboard, drawing, theme as tokens
from xadrez.ui.board_view import BoardView
from xadrez.ui.hud import NOTICE_TURN, NoticeBar, side_panel_rect
from xadrez.ui.match import MatchOptions, format_points
from xadrez.ui.net_link import NetLink
from xadrez.ui.scene import Scene
from xadrez.ui.theme import PlateStyle
from xadrez.ui.widgets import STYLE_PRIMARY, Button, FocusGroup

if TYPE_CHECKING:
    from xadrez.ui.app import App

_MARGIN = 14
_INNER_PADDING = 14
_ORBIT_SPEED = math.radians(5)
# Afasta a câmera aos poucos: o tabuleiro em diagonal não pode ser cortado enquanto gira.
_ZOOM_OUT = 1.14
_ZOOM_RATE = 2.0
_WIN_FIREWORK_INTERVAL = 0.55
_DRAW_FIREWORK_INTERVAL = 1.6
_GLOW_MARGIN = 26
_GLOW_PEAK_ALPHA = 92
_RESULT_HEIGHT = 216
_SERIES_HEIGHT = 124
_REMATCH_HEIGHT = 54
_MENU_HEIGHT = 44
_SECTION_GAP = 12
_BUTTON_GAP = 9
_BLOCK_HEIGHT = _RESULT_HEIGHT + _SERIES_HEIGHT + _REMATCH_HEIGHT + _MENU_HEIGHT + 2 * _SECTION_GAP + _BUTTON_GAP
_TOP_BIAS = 0.8
_SHORT_NOTICE_SECONDS = 2.0
_REMATCH_LABEL = "Revanche com cores trocadas"
_PEER_GONE_MESSAGE = "O adversário saiu da sala."


def result_score(result: GameResult) -> str:
    """Resultado como se anota em uma planilha de torneio: 1 - 0, 0 - 1 ou ½ - ½."""
    if result.winner is None:
        return "½ - ½"
    return "1 - 0" if result.winner is Color.WHITE else "0 - 1"


def _moves_text(half_moves: int) -> str:
    full_moves = (half_moves + 1) // 2
    return "Partida de 1 lance" if full_moves == 1 else f"Partida de {full_moves} lances"


class GameOverScene(Scene):
    def __init__(self, app: App, engine: GameEngine, options: MatchOptions, view: BoardView,
                 local_player: Player | None = None, link: NetLink | None = None):
        super().__init__(app)
        self.engine = engine
        self.options = options
        self.view = view
        self.local_player = local_player
        self.link = link
        self.result = engine.result
        self.rematch_button = Button(_REMATCH_LABEL, self.rematch, STYLE_PRIMARY, font_size=18)
        self.menu_button = Button("Voltar ao menu", self.go_to_menu)
        self.copy_button = Button("Copiar PGN", self.copy_pgn, hint="C")
        self.focus = FocusGroup([self.rematch_button, self.menu_button, self.copy_button])
        self.notices = NoticeBar(app.theme)
        self._panel = pygame.Rect(0, 0, 1, 1)
        self._result_rect = pygame.Rect(0, 0, 1, 1)
        self._series_rect = pygame.Rect(0, 0, 1, 1)
        self._ground: pygame.Surface | None = None
        self._glow: pygame.Surface | None = None
        self._firework_left = 0.0
        self._target_distance = self.view.camera.distance * _ZOOM_OUT
        self._refresh_rematch_button()
        self.resize(app.size)

    def rematch(self) -> None:
        # Dois Enter no mesmo quadro chegam antes da troca de cena: a segunda revanche destrocaria as cores.
        if self.next_scene is not None:
            return
        if self.link is not None:
            self._request_network_rematch()
            return
        self.engine.rematch()
        self._open_next_game()

    def _open_next_game(self) -> None:
        self.next_scene = self.app.game_scene(self.engine, self.options, self.view, self.local_player, self.link)

    def _request_network_rematch(self) -> None:
        if self.link.rematch_requested or self.link.peer_is_gone:
            return
        self.link.rematch_requested = True
        self.link.session.send_rematch()
        self._refresh_rematch_button()

    def go_to_menu(self) -> None:
        if self.next_scene is None:
            self.shutdown()
            self.next_scene = self.app.menu_scene(self.options)

    def copy_pgn(self) -> None:
        copied = clipboard.copy_text(game_to_pgn(self.engine))
        message = "PGN copiado para a área de transferência." if copied else clipboard.COPY_FAILED_MESSAGE
        self.notices.show(message, NOTICE_TURN, _SHORT_NOTICE_SECONDS)

    def shutdown(self) -> None:
        if self.link is not None:
            self.link.leave()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            self.copy_pgn()
            return
        self.focus.handle_event(event)

    def update(self, dt: float) -> None:
        self._drift_camera(dt)
        self.view.update(dt)
        self.notices.update(dt)
        self._firework_left -= dt
        if self._firework_left <= 0.0:
            self._launch_fireworks()
        if self.link is not None:
            self._receive_network_events()

    # Rede ------------------------------------------------------------------------------------------

    def _receive_network_events(self) -> None:
        link = self.link
        link.pump()
        while link.inbox and self.next_scene is None:
            self._handle_network_event(link.inbox.popleft())

    def _handle_network_event(self, event) -> None:
        if isinstance(event, RematchRequested):
            self.link.peer_wants_rematch = True
        elif isinstance(event, (PeerLeft, NetworkError)):
            self.link.peer_is_gone = True
            self.notices.show(_PEER_GONE_MESSAGE, NOTICE_TURN, _SHORT_NOTICE_SECONDS)
        elif isinstance(event, GameStart):
            self._start_network_rematch(event)
        self._refresh_rematch_button()

    def _start_network_rematch(self, event: GameStart) -> None:
        # A revanche troca as cores. Se a sala mandar outra coisa, as duas telas jogariam partidas diferentes.
        if self.local_player.color.opposite is not event.your_color:
            self.link.peer_is_gone = True
            self.link.leave()
            return
        self.engine.rematch()
        self.link.begin_new_game()
        self._open_next_game()

    def _refresh_rematch_button(self) -> None:
        link = self.link
        if link is None:
            return
        button = self.rematch_button
        button.is_enabled = not (link.peer_is_gone or link.rematch_requested)
        if link.peer_is_gone:
            button.label = "O adversário saiu da sala"
        elif link.rematch_requested:
            button.label = f"Aguardando {link.peer_name}"
        elif link.peer_wants_rematch:
            button.label = f"{link.peer_name} pediu revanche: aceitar"
        else:
            button.label = "Pedir revanche"

    # Festa e câmera ---------------------------------------------------------------------------------

    def _drift_camera(self, dt: float) -> None:
        camera = self.view.camera
        camera.orbit_by(_ORBIT_SPEED * dt)
        approach = min(dt * _ZOOM_RATE, 1.0)
        camera.zoom_by((camera.distance + (self._target_distance - camera.distance) * approach) / camera.distance)

    def _launch_fireworks(self) -> None:
        if self.result.winner is None:
            self._firework_left = _DRAW_FIREWORK_INTERVAL
            self.view.launch_fireworks(tokens.NEUTRAL_FIREWORK_COLORS)
        else:
            self._firework_left = _WIN_FIREWORK_INTERVAL
            self.view.launch_fireworks(tokens.FIREWORK_COLORS)

    # Desenho ---------------------------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        self.view.draw(surface)
        if self._ground is not None:
            surface.blit(self._ground, self._panel.topleft)
        self._draw_result(surface)
        self._draw_series(surface)
        self.focus.draw(surface, self.app.theme)
        self.notices.draw(surface)

    def _headline(self) -> str:
        if self.result.winner is None:
            return "Partida empatada"
        return f"{self.engine.players[self.result.winner].name} venceu"

    def _subline(self) -> str:
        if self.result.winner is None:
            return self.result.reason.label
        return f"{self.result.reason.label}, jogando de {self.result.winner.label}"

    def _result_style(self) -> tuple[PlateStyle, tuple, tuple, tuple]:
        """A luz do abajur fica com quem venceu. No empate, ela não fica com ninguém."""
        if self.result.winner is None:
            return tokens.PLATE_SHADE, tokens.BRASS_BRIGHT, tokens.IVORY, tokens.TEXT_MUTED
        return tokens.PLATE_LIT, tokens.INK, tokens.INK, tokens.INK_SOFT

    def _draw_result(self, surface: pygame.Surface) -> None:
        theme = self.app.theme
        rect = self._result_rect
        style, score_color, title_color, detail_color = self._result_style()
        if self.result.winner is not None and self._glow is not None:
            margin = theme.px(_GLOW_MARGIN)
            surface.blit(self._glow, (rect.x - margin, rect.y - margin))
        surface.blit(theme.plate(rect.size, style), rect.topleft)
        pad = theme.px(_INNER_PADDING)
        x, width = rect.x + pad, max(rect.width - 2 * pad, 1)
        score = theme.text_fit(result_score(self.result), tokens.ROLE_DISPLAY, theme.px(76), score_color, width)
        surface.blit(score, score.get_rect(midtop=(rect.centerx, rect.y + theme.px(10))))
        rows = (
            (self._headline(), tokens.ROLE_DISPLAY, 32, title_color, 106),
            (self._subline(), tokens.ROLE_LABEL, 17, detail_color, 156),
            (_moves_text(len(self.engine.history)), tokens.ROLE_LABEL, 16, detail_color, 182),
        )
        for content, role, size, color, offset in rows:
            text = theme.text_fit(content, role, theme.px(size), color, width)
            surface.blit(text, text.get_rect(midtop=(rect.centerx, rect.y + theme.px(offset))))

    def _draw_series(self, surface: pygame.Surface) -> None:
        """Placar da série como uma placa: nomes à esquerda, pontos alinhados à direita."""
        theme = self.app.theme
        rect = self._series_rect
        surface.blit(theme.plate(rect.size, tokens.PLATE_SHADE), rect.topleft)
        pad = theme.px(_INNER_PADDING)
        label = theme.text("Placar da série", tokens.ROLE_LABEL, theme.px(15), tokens.TEXT_MUTED)
        surface.blit(label, (rect.x + pad, rect.y + theme.px(10)))
        center_y = rect.y + theme.px(54)
        for color in (Color.WHITE, Color.BLACK):
            self._draw_series_row(surface, rect, color, center_y, pad)
            center_y += theme.px(38)

    def _draw_series_row(self, surface: pygame.Surface, rect: pygame.Rect, color: Color, center_y: int, pad: int) -> None:
        theme = self.app.theme
        player = self.engine.players[color]
        points = theme.text(format_points(player.match_points), tokens.ROLE_NUMERIC, theme.px(28), tokens.BRASS_BRIGHT)
        surface.blit(points, points.get_rect(midright=(rect.right - pad, center_y)))
        available = max(rect.width - 2 * pad - points.get_width() - theme.px(10), 1)
        name = theme.text_fit(player.name, tokens.ROLE_DISPLAY, theme.px(23), tokens.IVORY, available)
        surface.blit(name, name.get_rect(midleft=(rect.x + pad, center_y)))

    def resize(self, size: tuple[int, int]) -> None:
        theme = self.app.theme
        self._panel = side_panel_rect(theme, size)
        viewport = pygame.Rect(0, 0, max(size[0] - self._panel.width, 1), max(size[1], 1))
        self.view.set_viewport(viewport)
        self.notices.layout(viewport)
        self._ground = theme.panel_ground(self._panel.size)
        margin = theme.px(_MARGIN)
        x = self._panel.x + margin + theme.px(2)
        width = max(self._panel.width - 2 * margin - theme.px(2), 1)
        gap, button_gap = theme.px(_SECTION_GAP), theme.px(_BUTTON_GAP)
        top = max(round((self._panel.height - theme.px(_BLOCK_HEIGHT)) / 2 * _TOP_BIAS), margin)
        self._result_rect = pygame.Rect(x, top, width, theme.px(_RESULT_HEIGHT))
        self._series_rect = pygame.Rect(x, self._result_rect.bottom + gap, width, theme.px(_SERIES_HEIGHT))
        self.rematch_button.rect = pygame.Rect(x, self._series_rect.bottom + gap, width, theme.px(_REMATCH_HEIGHT))
        half = max((width - button_gap) // 2, 1)
        row_y, row_height = self.rematch_button.rect.bottom + button_gap, theme.px(_MENU_HEIGHT)
        self.menu_button.rect = pygame.Rect(x, row_y, half, row_height)
        self.copy_button.rect = pygame.Rect(x + half + button_gap, row_y, half, row_height)
        glow_margin = theme.px(_GLOW_MARGIN)
        glow_size = (width + 2 * glow_margin, self._result_rect.height + 2 * glow_margin)
        self._glow = drawing.render_glow(glow_size, tokens.LAMP_GLOW, _GLOW_PEAK_ALPHA)
