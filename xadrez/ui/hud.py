"""HUD da partida: o painel lateral é uma extensão da mesa de torneio.

Duas placas de jogador, uma em cima e outra embaixo, com a planilha de anotação entre elas. A luz
do abajur acende a placa de quem joga: de longe, placa clara é a vez, placa escura é a espera.
Tudo o que tem texto é composto em superfícies guardadas e só refeito quando o conteúdo muda.
"""
from __future__ import annotations

import math
from typing import Mapping, NamedTuple, Sequence

import pygame

from xadrez.core import Color, GameEngine, GameState, PieceType
from xadrez.graphics import Mesh, Renderer3D
from xadrez.ui import drawing, theme as tokens
from xadrez.ui.board_view import PIECE_COLORS
from xadrez.ui.match import format_clock, format_points
from xadrez.ui.theme import PlateStyle, Theme
from xadrez.ui.widgets import Button

PANEL_WIDTH = 320
_PANEL_MAX_FRACTION = 0.5
_PANEL_PADDING = 12
_CARD_HEIGHT = 152
_SECTION_GAP = 8
_BUTTON_HEIGHT = 36
_BUTTON_GAP = 6
_SHEET_ROW_HEIGHT = 23
_SHEET_HEADER_HEIGHT = 25
_SHEET_MIN_HEIGHT = 48
_LAMP_FADE_SECONDS = 0.28
_LOW_TIME_SECONDS = 30.0
_GLOW_MARGIN = 26
_GLOW_PEAK_ALPHA = 92
_SHEET_PLATE = PlateStyle(tokens.PAPER, (224, 210, 178), tokens.PAPER_RULE, 1)

STATUS_TURN = "turn"
STATUS_CHECK = "check"

NOTICE_TURN = "turn"
NOTICE_WARNING = "warning"
NOTICE_DANGER = "danger"
_NOTICE_SECONDS = 3.0
_NOTICE_FADE_SECONDS = 0.2
_NOTICE_HEIGHT = 38
_NOTICE_TOP = 10
_NOTICE_MARGIN = 12
_NOTICE_STYLES = {
    NOTICE_TURN: (tokens.PLATE_NOTICE_TURN, tokens.IVORY),
    NOTICE_WARNING: (tokens.PLATE_NOTICE_WARNING, tokens.INK),
    NOTICE_DANGER: (tokens.PLATE_NOTICE_DANGER, tokens.IVORY),
}

_CAPTURE_ORDER = {kind: -kind.points for kind in PieceType}


class _CardColors(NamedTuple):
    title: tuple
    detail: tuple
    clock: tuple
    low_clock: tuple
    lead: tuple


_LIT_COLORS = _CardColors(tokens.INK, tokens.INK_SOFT, tokens.INK, tokens.ALERT_ON_LIGHT, tokens.INK)
_SHADE_COLORS = _CardColors(tokens.IVORY, tokens.TEXT_MUTED, tokens.TEXT_MUTED, tokens.ALERT_ON_DARK, tokens.BRASS_BRIGHT)


class CardInfo(NamedTuple):
    """Tudo o que aparece na placa. Se a tupla não mudou, a placa pronta continua valendo."""

    name: str
    clock: str
    is_low_time: bool
    is_elapsed: bool
    captured: tuple[PieceType, ...]
    points: int
    lead: int
    series: str
    status: str | None


def _tray_style(piece_color: Color) -> PlateStyle:
    """Peça de ébano sobre fundo claro, peça de marfim sobre fundo escuro: nenhuma das duas some."""
    return tokens.PLATE_LIGHT_TRAY if piece_color is Color.BLACK else tokens.PLATE_DARK_TRAY


def _tray_text_color(piece_color: Color) -> tuple:
    return tokens.INK_SOFT if piece_color is Color.BLACK else tokens.TEXT_MUTED


class PlayerCard:
    """Placa de um jogador, pronta em duas versões: na sombra e sob a luz. A luz funde uma na outra."""

    def __init__(self, theme: Theme, renderer: Renderer3D, meshes: Mapping[str, Mesh], color: Color):
        self._theme = theme
        self._renderer = renderer
        self._meshes = meshes
        self.color = color
        self.rect = pygame.Rect(0, 0, 1, 1)
        self.info: CardInfo | None = None
        self._lit: pygame.Surface | None = None
        self._shade: pygame.Surface | None = None
        self._glow: pygame.Surface | None = None

    def layout(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.info = None
        margin = self._theme.px(_GLOW_MARGIN)
        glow_size = (rect.width + 2 * margin, rect.height + 2 * margin)
        self._glow = drawing.render_glow(glow_size, tokens.LAMP_GLOW, _GLOW_PEAK_ALPHA)

    def refresh(self, info: CardInfo) -> None:
        if info == self.info:
            return
        self.info = info
        self._shade = self._compose(info, _SHADE_COLORS, tokens.PLATE_SHADE)
        self._lit = self._compose(info, _LIT_COLORS, tokens.PLATE_LIT)

    def _compose(self, info: CardInfo, colors: _CardColors, style: PlateStyle) -> pygame.Surface:
        size = self.rect.size
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.blit(self._theme.plate(size, style), (0, 0))
        self._draw_identity(surface, info, colors)
        self._draw_clock(surface, info, colors)
        self._draw_captures(surface, info, colors)
        return surface

    def _draw_identity(self, surface: pygame.Surface, info: CardInfo, colors: _CardColors) -> None:
        theme = self._theme
        pad = theme.px(11)
        badge = theme.px(40)
        self._draw_color_badge(surface, (pad, pad), badge)
        text_x = pad + badge + theme.px(9)
        stats = self._render_stats(info, colors)
        stats_width = max(image.get_width() for image in stats)
        available = max(self.rect.width - text_x - stats_width - pad - theme.px(6), 1)
        name = theme.text_fit(info.name, tokens.ROLE_DISPLAY, theme.px(24), colors.title, available)
        surface.blit(name, (text_x, pad - theme.px(3)))
        side = theme.text(self.color.label, tokens.ROLE_LABEL, theme.px(14), colors.detail)
        surface.blit(side, (text_x, pad + badge - side.get_height()))
        for index, image in enumerate(stats):
            y = pad + index * (image.get_height() + theme.px(3))
            surface.blit(image, (self.rect.width - pad - image.get_width(), y))

    def _render_stats(self, info: CardInfo, colors: _CardColors) -> list[pygame.Surface]:
        size = self._theme.px(14)
        return [
            self._theme.text(f"Série {info.series}", tokens.ROLE_LABEL, size, colors.title),
            self._theme.text(f"Pontos {info.points}", tokens.ROLE_LABEL, size, colors.detail),
        ]

    def _draw_color_badge(self, surface: pygame.Surface, topleft: tuple[int, int], size: int) -> None:
        surface.blit(self._theme.plate((size, size), _tray_style(self.color)), topleft)
        icon_size = max(size - self._theme.px(6), 1)
        icon = self._renderer.render_icon(self._meshes["pawn"], PIECE_COLORS[self.color], icon_size)
        inset = (size - icon_size) // 2
        surface.blit(icon, (topleft[0] + inset, topleft[1] + inset))

    def _draw_clock(self, surface: pygame.Surface, info: CardInfo, colors: _CardColors) -> None:
        theme = self._theme
        pad = theme.px(11)
        color = colors.low_clock if info.is_low_time else colors.clock
        digits = theme.tabular(info.clock, tokens.ROLE_NUMERIC, theme.px(60), color)
        top = pad + theme.px(40)
        bottom = self.rect.height - pad - theme.px(28)
        center_y = (top + bottom) // 2
        surface.blit(digits, digits.get_rect(midleft=(pad, center_y)))
        self._draw_status(surface, info, colors, center_y)

    def _draw_status(self, surface: pygame.Surface, info: CardInfo, colors: _CardColors, center_y: int) -> None:
        theme = self._theme
        right = self.rect.width - theme.px(11)
        if info.status is not None:
            self._draw_status_tag(surface, info.status, right, center_y)
        if info.is_elapsed:
            note = theme.text("decorrido", tokens.ROLE_LABEL, theme.px(13), colors.detail)
            offset = theme.px(19) if info.status is not None else 0
            surface.blit(note, note.get_rect(midright=(right, center_y + offset)))

    def _draw_status_tag(self, surface: pygame.Surface, status: str, right: int, center_y: int) -> None:
        theme = self._theme
        is_check = status == STATUS_CHECK
        label = theme.text("Xeque!" if is_check else "Joga agora", tokens.ROLE_LABEL, theme.px(15), tokens.IVORY)
        size = (label.get_width() + theme.px(14), label.get_height() + theme.px(5))
        rect = pygame.Rect((0, 0), size)
        rect.midright = (right, center_y)
        surface.blit(theme.plate(size, tokens.PLATE_TAG_CHECK if is_check else tokens.PLATE_TAG_TURN), rect.topleft)
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_captures(self, surface: pygame.Surface, info: CardInfo, colors: _CardColors) -> None:
        theme = self._theme
        pad = theme.px(11)
        height = theme.px(28)
        lead_space = theme.px(42)
        tray = pygame.Rect(pad, self.rect.height - pad - height, max(self.rect.width - 2 * pad - lead_space, 1), height)
        captured_color = self.color.opposite
        surface.blit(theme.plate(tray.size, _tray_style(captured_color)), tray.topleft)
        if info.captured:
            self._draw_captured_icons(surface, tray, info.captured, captured_color)
        else:
            empty = theme.text("Sem capturas", tokens.ROLE_LABEL, theme.px(13), _tray_text_color(captured_color))
            surface.blit(empty, empty.get_rect(midleft=(tray.x + theme.px(8), tray.centery)))
        if info.lead > 0:
            lead = theme.text(f"+{info.lead}", tokens.ROLE_DISPLAY, theme.px(22), colors.lead)
            surface.blit(lead, lead.get_rect(midright=(self.rect.width - pad, tray.centery)))

    def _draw_captured_icons(self, surface: pygame.Surface, tray: pygame.Rect, captured: Sequence[PieceType],
                             color: Color) -> None:
        theme = self._theme
        icon_size = max(tray.height - theme.px(3), 1)
        inset = theme.px(4)
        ordered = sorted(captured, key=_CAPTURE_ORDER.__getitem__)
        room = tray.width - 2 * inset - icon_size
        step = min(icon_size * 0.72, room / max(len(ordered) - 1, 1))
        for index, kind in enumerate(ordered):
            icon = self._renderer.render_icon(self._meshes[kind.value], PIECE_COLORS[color], icon_size)
            x = tray.x + inset + round(index * step)
            surface.blit(icon, (x, tray.y + (tray.height - icon_size) // 2))

    def draw(self, surface: pygame.Surface, lamp: float) -> None:
        if self._shade is None or self._lit is None:
            return
        if lamp <= 0.0:
            surface.blit(self._shade, self.rect.topleft)
            return
        alpha = round(255 * min(lamp, 1.0))
        margin = self._theme.px(_GLOW_MARGIN)
        self._glow.set_alpha(alpha)
        surface.blit(self._glow, (self.rect.x - margin, self.rect.y - margin))
        if lamp < 1.0:
            surface.blit(self._shade, self.rect.topleft)
        self._lit.set_alpha(alpha)
        surface.blit(self._lit, self.rect.topleft)


class ScoreSheet:
    """Planilha de anotação: papel pautado, número do lance e as colunas das Brancas e das Pretas."""

    def __init__(self, theme: Theme):
        self._theme = theme
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._surface: pygame.Surface | None = None
        self._shadow: pygame.Surface | None = None
        self._rendered_count = -1

    def layout(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self._rendered_count = -1
        margin = self._theme.px(5)
        self._shadow = drawing.render_soft_shadow(rect.size, margin, 120) if rect.height > 0 else None

    def refresh(self, history: Sequence[str], first_color: Color) -> None:
        if len(history) == self._rendered_count or self.rect.height <= 0:
            return
        self._rendered_count = len(history)
        self._surface = self._compose(history, first_color)

    def _compose(self, history: Sequence[str], first_color: Color) -> pygame.Surface:
        theme = self._theme
        surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        surface.blit(theme.plate(self.rect.size, _SHEET_PLATE), (0, 0))
        header = theme.px(_SHEET_HEADER_HEIGHT)
        row_height = theme.px(_SHEET_ROW_HEIGHT)
        row_count = max((self.rect.height - header) // row_height, 0)
        self._draw_rules(surface, header, row_height, row_count, has_moves=bool(history))
        self._draw_header(surface, header)
        if history:
            self._draw_moves(surface, history, header, row_height, row_count)
        else:
            self._draw_empty_hint(surface, header, row_height, first_color)
        return surface

    def _column_x(self) -> tuple[int, int, int]:
        width = self.rect.width
        return round(width * 0.15), round(width * 0.2), round(width * 0.6)

    def _draw_rules(self, surface: pygame.Surface, header: int, row_height: int, row_count: int, has_moves: bool) -> None:
        width = self.rect.width
        for row in range(row_count + 1):
            y = header + row * row_height
            pygame.draw.line(surface, tokens.PAPER_RULE, (self._theme.px(2), y), (width - self._theme.px(3), y))
        margin_x, _, black_x = self._column_x()
        top, bottom = self._theme.px(2), self.rect.height - self._theme.px(3)
        pygame.draw.line(surface, tokens.PAPER_MARGIN, (margin_x, top), (margin_x, bottom))
        if has_moves:
            divider_x = black_x - self._theme.px(7)
            pygame.draw.line(surface, tokens.PAPER_RULE, (divider_x, top), (divider_x, bottom))

    def _draw_header(self, surface: pygame.Surface, header: int) -> None:
        theme = self._theme
        _, white_x, black_x = self._column_x()
        for label, x in (("Brancas", white_x), ("Pretas", black_x)):
            text = theme.text(label, tokens.ROLE_LABEL, theme.px(14), tokens.INK_SOFT)
            surface.blit(text, text.get_rect(midleft=(x, header // 2 + theme.px(1))))

    def _draw_empty_hint(self, surface: pygame.Surface, header: int, row_height: int, first_color: Color) -> None:
        theme = self._theme
        _, white_x, _ = self._column_x()
        hint = theme.text(f"As {first_color.label} começam.", tokens.ROLE_SERIF, theme.px(17), tokens.INK_SOFT)
        surface.blit(hint, hint.get_rect(midleft=(white_x, header + row_height // 2)))

    def _draw_moves(self, surface: pygame.Surface, history: Sequence[str], header: int, row_height: int,
                    row_count: int) -> None:
        total_rows = (len(history) + 1) // 2
        first_row = max(total_rows - row_count, 0)
        for row in range(first_row, total_rows):
            y = header + (row - first_row) * row_height
            self._draw_row(surface, history, row, y, row_height)

    def _draw_row(self, surface: pygame.Surface, history: Sequence[str], row: int, y: int, row_height: int) -> None:
        theme = self._theme
        margin_x, white_x, black_x = self._column_x()
        center_y = y + row_height // 2
        number = theme.text(str(row + 1), tokens.ROLE_LABEL, theme.px(14), tokens.INK_SOFT)
        surface.blit(number, number.get_rect(midright=(margin_x - theme.px(5), center_y)))
        last_index = len(history) - 1
        for index, x in ((row * 2, white_x), (row * 2 + 1, black_x)):
            if index > last_index:
                continue
            if index == last_index:
                self._draw_current_mark(surface, x, y, row_height, history[index])
            san = theme.text(history[index], tokens.ROLE_DISPLAY, theme.px(17), tokens.INK)
            surface.blit(san, san.get_rect(midleft=(x, center_y)))

    def _draw_current_mark(self, surface: pygame.Surface, x: int, y: int, row_height: int, san: str) -> None:
        theme = self._theme
        width = theme.font(tokens.ROLE_DISPLAY, theme.px(17)).size(san)[0] + theme.px(8)
        pygame.draw.rect(surface, tokens.BRASS_BRIGHT, (x - theme.px(4), y + 2, width, max(row_height - 3, 1)))

    def draw(self, surface: pygame.Surface) -> None:
        if self._surface is None or self.rect.height <= 0:
            return
        if self._shadow is not None:
            margin = self._theme.px(5)
            surface.blit(self._shadow, (self.rect.x - margin + self._theme.px(1), self.rect.y - margin + self._theme.px(2)))
        surface.blit(self._surface, self.rect.topleft)


def side_panel_rect(theme: Theme, size: tuple[int, int]) -> pygame.Rect:
    """Faixa da direita da janela, a mesma durante a partida e na tela de fim."""
    width, height = max(size[0], 1), max(size[1], 1)
    panel_width = max(min(theme.px(PANEL_WIDTH), round(width * _PANEL_MAX_FRACTION)), 1)
    return pygame.Rect(width - panel_width, 0, panel_width, height)


class Hud:
    """Painel lateral inteiro: chão de madeira, placas, planilha e botões de ação."""

    def __init__(self, theme: Theme, renderer: Renderer3D, meshes: Mapping[str, Mesh], engine: GameEngine,
                 buttons: Sequence[Button]):
        self._theme = theme
        self.engine = engine
        self.buttons = list(buttons)
        self.cards = {color: PlayerCard(theme, renderer, meshes, color) for color in Color}
        self.sheet = ScoreSheet(theme)
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.viewport = pygame.Rect(0, 0, 1, 1)
        self.active_color: Color | None = engine.turn
        self.checked_color: Color | None = None
        self._lamp = {color: 1.0 if color is engine.turn else 0.0 for color in Color}
        self._ground: pygame.Surface | None = None

    def layout(self, size: tuple[int, int]) -> pygame.Rect:
        """Reparte a janela entre o tabuleiro e o painel. Devolve o retângulo do tabuleiro."""
        self.panel = side_panel_rect(self._theme, size)
        self.viewport = pygame.Rect(0, 0, max(size[0] - self.panel.width, 1), self.panel.height)
        self._ground = self._theme.panel_ground(self.panel.size)
        self._layout_contents()
        return self.viewport

    def _layout_contents(self) -> None:
        theme = self._theme
        pad, gap = theme.px(_PANEL_PADDING), theme.px(_SECTION_GAP)
        left = self.panel.x + pad + theme.px(2)
        width = max(self.panel.width - 2 * pad - theme.px(2), 1)
        card_height = theme.px(_CARD_HEIGHT)
        buttons_height = self._buttons_height()
        bottom_card_y = max(self.panel.height - pad - buttons_height - gap - card_height, pad + card_height)
        self.cards[Color.BLACK].layout(pygame.Rect(left, pad, width, card_height))
        self.cards[Color.WHITE].layout(pygame.Rect(left, bottom_card_y, width, card_height))
        sheet_y = pad + card_height + gap
        sheet_height = bottom_card_y - gap - sheet_y
        visible_height = sheet_height if sheet_height >= theme.px(_SHEET_MIN_HEIGHT) else 0
        self.sheet.layout(pygame.Rect(left, sheet_y, width, visible_height))
        self._layout_buttons(left, bottom_card_y + card_height + gap, width)

    def _buttons_height(self) -> int:
        rows = (len(self.buttons) + 1) // 2
        return rows * self._theme.px(_BUTTON_HEIGHT) + (rows - 1) * self._theme.px(_BUTTON_GAP)

    def _layout_buttons(self, left: int, top: int, width: int) -> None:
        theme = self._theme
        gap = theme.px(_BUTTON_GAP)
        button_width = max((width - gap) // 2, 1)
        button_height = theme.px(_BUTTON_HEIGHT)
        for index, button in enumerate(self.buttons):
            column, row = index % 2, index // 2
            x, y = left + column * (button_width + gap), top + row * (button_height + gap)
            button.rect = pygame.Rect(x, y, button_width, button_height)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Devolve se o painel consumiu o evento, para o clique não atravessar até o tabuleiro."""
        consumed = False
        for button in self.buttons:
            consumed = button.handle_mouse(event) or consumed
        position = getattr(event, "pos", None)
        is_click = event.type == pygame.MOUSEBUTTONDOWN
        return consumed or (is_click and position is not None and self.panel.collidepoint(position))

    def update(self, dt: float) -> None:
        self._advance_lamp(dt)
        for color, card in self.cards.items():
            card.refresh(self._card_info(color))
        self.sheet.refresh(self.engine.history, self.engine.turn)

    def _advance_lamp(self, dt: float) -> None:
        step = dt / _LAMP_FADE_SECONDS
        for color in Color:
            target = 1.0 if color is self.active_color else 0.0
            current = self._lamp[color]
            self._lamp[color] = min(current + step, target) if target > current else max(current - step, target)

    def _card_info(self, color: Color) -> CardInfo:
        engine = self.engine
        player = engine.players[color]
        remaining = engine.clock.remaining(color)
        is_unlimited = math.isinf(remaining)
        seconds = math.floor(engine.clock.elapsed(color)) if is_unlimited else remaining
        balance = engine.material_balance() if color is Color.WHITE else -engine.material_balance()
        return CardInfo(
            name=player.name,
            clock=format_clock(seconds),
            is_low_time=not is_unlimited and remaining < _LOW_TIME_SECONDS,
            is_elapsed=is_unlimited,
            captured=tuple(player.captured),
            points=player.material_score,
            lead=balance,
            series=format_points(player.match_points),
            status=self._status_of(color),
        )

    def _status_of(self, color: Color) -> str | None:
        if self.engine.state is GameState.FINISHED or color is not self.active_color:
            return None
        return STATUS_CHECK if color is self.checked_color else STATUS_TURN

    def draw(self, surface: pygame.Surface) -> None:
        if self._ground is not None:
            surface.blit(self._ground, self.panel.topleft)
        for color, card in self.cards.items():
            card.draw(surface, self._lamp[color])
        self.sheet.draw(surface)
        for button in self.buttons:
            button.draw(surface, self._theme)


class NoticeBar:
    """Faixa de avisos no alto do tabuleiro. Mostra a vez, e os avisos passam por cima dela."""

    def __init__(self, theme: Theme):
        self._theme = theme
        self._viewport = pygame.Rect(0, 0, 1, 1)
        self._status: tuple[str, str] = ("", NOTICE_TURN)
        self._message: tuple[str, str] | None = None
        self._message_left = 0.0
        self._rendered_key: tuple | None = None
        self._rendered: pygame.Surface | None = None

    def layout(self, viewport: pygame.Rect) -> None:
        self._viewport = viewport
        self._rendered_key = None

    @property
    def text(self) -> str:
        return self._current()[0]

    @property
    def kind(self) -> str:
        return self._current()[1]

    def _current(self) -> tuple[str, str]:
        return self._message if self._message is not None else self._status

    def set_status(self, text: str, kind: str = NOTICE_TURN) -> None:
        self._status = (text, kind)

    def show(self, text: str, kind: str = NOTICE_WARNING, seconds: float = _NOTICE_SECONDS) -> None:
        self._message = (text, kind)
        self._message_left = seconds

    def clear_message(self) -> None:
        self._message = None

    def update(self, dt: float) -> None:
        if self._message is None:
            return
        self._message_left -= dt
        if self._message_left <= 0.0:
            self._message = None

    def draw(self, surface: pygame.Surface) -> None:
        text, kind = self._current()
        if not text:
            return
        key = (text, kind, self._viewport.width)
        if key != self._rendered_key:
            self._rendered = self._compose(text, kind)
            self._rendered_key = key
        rect = self._rendered.get_rect(midtop=(self._viewport.centerx, self._theme.px(_NOTICE_TOP)))
        if self._message is not None:
            self._rendered.set_alpha(round(255 * min(self._message_left / _NOTICE_FADE_SECONDS, 1.0)))
        else:
            self._rendered.set_alpha(255)
        surface.blit(self._rendered, rect)

    def _compose(self, text: str, kind: str) -> pygame.Surface:
        theme = self._theme
        style, color = _NOTICE_STYLES[kind]
        has_icon = kind != NOTICE_TURN
        icon_space = theme.px(30) if has_icon else 0
        side = theme.px(16)
        available = max(self._viewport.width - 2 * theme.px(_NOTICE_MARGIN) - 2 * side - icon_space, 1)
        label = theme.text_fit(text, tokens.ROLE_DISPLAY, theme.px(20), color, available)
        size = (label.get_width() + 2 * side + icon_space, theme.px(_NOTICE_HEIGHT))
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.blit(theme.plate(size, style), (0, 0))
        if has_icon:
            self._draw_icon(surface, kind, (side + theme.px(9), size[1] // 2))
        surface.blit(label, label.get_rect(midleft=(side + icon_space, size[1] // 2)))
        return surface

    def _draw_icon(self, surface: pygame.Surface, kind: str, center: tuple[int, int]) -> None:
        fill = tokens.IVORY if kind == NOTICE_DANGER else tokens.ALERT_PLATE
        mark = tokens.ALERT_PLATE if kind == NOTICE_DANGER else tokens.IVORY
        drawing.draw_warning_triangle(surface, center, self._theme.px(10), fill, mark)
