"""Aba "Meu histórico": estatísticas e lista no painel, e a partida aberta como uma folha de papel sobre a mesa (RF21)."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Callable, Sequence

import pygame

from xadrez.data import HistoryStats, MatchRecord
from xadrez.data.history import OUTCOME_DRAW, OUTCOME_WIN
from xadrez.ui import clipboard, drawing, theme as tokens
from xadrez.ui.match import format_clock
from xadrez.ui.theme import PlateStyle, Theme
from xadrez.ui.widgets import STYLE_PRIMARY, Button

_ROW_HEIGHT = 58
_ROW_GAP = 5
_STAT_HEIGHT = 58
_STAT_GAP = 6
_WHEEL_ROWS = 1
_PAGE_ROWS = 4
_SHEET_MARGIN = 26
_SHEET_PADDING = 24
_SHEET_MIN_WIDTH = 260
_PGN_LINE_HEIGHT = 21
_PGN_FONT = 16
_FEN_FONT = 13
_SCROLL_MARK_WIDTH = 3
_OUTCOME_WORDS = {OUTCOME_WIN: "Vitória", OUTCOME_DRAW: "Empate"}
LOSS_WORD = "Derrota"
_STAT_LABELS = (("Partidas", "played"), ("Vitórias", "wins"), ("Derrotas", "losses"), ("Empates", "draws"))
# Mesma linguagem do jogo: a luz fica com quem venceu, o vermelho é da derrota, e o empate fica na sombra.
_OUTCOME_STYLES = {
    OUTCOME_WIN: (tokens.PLATE_LIT, tokens.INK),
    OUTCOME_DRAW: (tokens.PLATE_SHADE, tokens.BRASS_BRIGHT),
}
_LOSS_STYLE = (tokens.PLATE_DANGER, tokens.IVORY)
NO_ACCOUNT_LINES = ("O histórico é só de quem tem conta.", "Crie uma conta para guardar suas partidas, com placar, PGN e posição final.")
EMPTY_LINES = ("Nenhuma partida guardada ainda.", "Termine uma partida e ela aparece aqui.")
_SHOWN_TEXT_FIELDS = ("played_at", "opponent", "color", "reason", "time_control", "mode", "pgn", "final_fen")


def _printable(text: str) -> str:
    return "".join(char for char in text if char.isprintable() or char == "\n")


def displayable(record: MatchRecord) -> MatchRecord:
    """O arquivo pode ter sido editado à mão: um caractere de controle derrubaria o desenho do texto."""
    return replace(record, **{name: _printable(getattr(record, name)) for name in _SHOWN_TEXT_FIELDS})


def outcome_word(outcome: str) -> str:
    return _OUTCOME_WORDS.get(outcome, LOSS_WORD)


def format_played_at(played_at: str) -> str:
    """Vem de um arquivo: se não for uma data, mostra o que estiver lá, sem derrubar a tela."""
    try:
        return datetime.fromisoformat(played_at).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return played_at[:16]


def _moves_word(moves: int) -> str:
    return "1 lance" if moves == 1 else f"{moves} lances"


def _opponent_text(record: MatchRecord) -> str:
    connector = "contra" if record.outcome != OUTCOME_DRAW else "com"
    return f"{outcome_word(record.outcome)} {connector} {record.opponent}"


def _movetext(pgn: str) -> str:
    """Só os lances, para caber na folha. Os cabeçalhos seguem completos em "Copiar PGN"."""
    return " ".join(line for line in pgn.splitlines() if line and not line.startswith("["))


class HistoryList:
    """Lista rolável: roda do mouse, setas, Page Up e Page Down. Clique ou Enter abre a partida."""

    uses_vertical_keys = True
    advances_on_enter = False

    def __init__(self, theme: Theme, on_open: Callable[[int], None]):
        self._theme = theme
        self._on_open = on_open
        self.records: list[MatchRecord] = []
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.index = 0
        self.scroll = 0
        self.is_focused = False
        self._hovered: int | None = None

    def set_records(self, records: Sequence[MatchRecord]) -> None:
        self.records = list(records)
        self.index = 0
        self.scroll = 0

    def _row_step(self) -> int:
        return self._theme.px(_ROW_HEIGHT) + self._theme.px(_ROW_GAP)

    def row_rect(self, index: int) -> pygame.Rect:
        y = self.rect.y + index * self._row_step() - self.scroll
        return pygame.Rect(self.rect.x, y, max(self.rect.width - self._theme.px(8), 1), self._theme.px(_ROW_HEIGHT))

    def _max_scroll(self) -> int:
        total = len(self.records) * self._row_step() - self._theme.px(_ROW_GAP)
        return max(total - self.rect.height, 0)

    def clamp_scroll(self) -> None:
        self.scroll = max(0, min(self.scroll, self._max_scroll()))

    def _row_at(self, position: tuple[int, int]) -> int | None:
        if not self.rect.collidepoint(position):
            return None
        return next((index for index in range(len(self.records)) if self.row_rect(index).collidepoint(position)), None)

    def handle_mouse(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self._row_at(event.pos)
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1 or not self.rect.collidepoint(event.pos):
            return False
        row = self._row_at(event.pos)
        if row is not None:
            self.index = row
            self._on_open(row)
        return True

    def handle_key(self, event: pygame.event.Event) -> bool:
        moves = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -_PAGE_ROWS, pygame.K_PAGEDOWN: _PAGE_ROWS}
        if event.key in moves:
            self._move_selection(moves[event.key])
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.records:
            self._on_open(self.index)
            return True
        return False

    def _move_selection(self, delta: int) -> None:
        if not self.records:
            return
        self.index = max(0, min(self.index + delta, len(self.records) - 1))
        row = self.row_rect(self.index)
        if row.top < self.rect.top:
            self.scroll -= self.rect.top - row.top
        elif row.bottom > self.rect.bottom:
            self.scroll += row.bottom - self.rect.bottom
        self.clamp_scroll()

    def scroll_by_wheel(self, steps: int) -> None:
        self.scroll -= steps * _WHEEL_ROWS * self._row_step()
        self.clamp_scroll()

    def activate(self) -> None:
        """O foco já fica na lista: quem abre uma partida é o Enter, tratado em `handle_key`."""

    def draw(self, surface: pygame.Surface, theme: Theme) -> None:
        previous_clip = surface.get_clip()
        surface.set_clip(self.rect)
        for index, record in enumerate(self.records):
            row = self.row_rect(index)
            if row.bottom >= self.rect.top and row.top <= self.rect.bottom:
                self._draw_row(surface, theme, record, row, index)
        surface.set_clip(previous_clip)
        self._draw_scroll_mark(surface)

    def _draw_row(self, surface: pygame.Surface, theme: Theme, record: MatchRecord, row: pygame.Rect, index: int) -> None:
        is_lit = index == self._hovered or (self.is_focused and index == self.index)
        surface.blit(theme.plate(row.size, tokens.PLATE_BUTTON_HOVER if is_lit else tokens.PLATE_BUTTON), row.topleft)
        pad = theme.px(9)
        tag_right = self._draw_outcome_tag(surface, theme, record.outcome, (row.x + pad, row.y + pad))
        date = theme.text(format_played_at(record.played_at), tokens.ROLE_LABEL, theme.px(13), tokens.TEXT_MUTED)
        surface.blit(date, date.get_rect(topright=(row.right - pad, row.y + pad)))
        name_width = max(date.get_rect(topright=(row.right - pad, 0)).left - tag_right - theme.px(14), 1)
        name = theme.text_fit(record.opponent, tokens.ROLE_DISPLAY, theme.px(18), tokens.IVORY, name_width)
        surface.blit(name, (tag_right + theme.px(8), row.y + pad - theme.px(1)))
        details = f"{record.mode}, {record.color}, {_moves_word(record.moves)}, {format_clock(record.seconds)}"
        line = theme.text_fit(details, tokens.ROLE_LABEL, theme.px(14), tokens.TEXT_MUTED, max(row.width - 2 * pad, 1))
        surface.blit(line, (row.x + pad, row.bottom - pad - line.get_height() + theme.px(2)))

    def _draw_outcome_tag(self, surface: pygame.Surface, theme: Theme, outcome: str, topleft: tuple[int, int]) -> int:
        plate, color = _OUTCOME_STYLES.get(outcome, _LOSS_STYLE)
        label = theme.text(outcome_word(outcome), tokens.ROLE_LABEL, theme.px(14), color)
        size = (label.get_width() + theme.px(12), label.get_height() + theme.px(3))
        surface.blit(theme.plate(size, PlateStyle(plate.top, plate.bottom, plate.border, 3)), topleft)
        surface.blit(label, label.get_rect(center=(topleft[0] + size[0] // 2, topleft[1] + size[1] // 2)))
        return topleft[0] + size[0]

    def _draw_scroll_mark(self, surface: pygame.Surface) -> None:
        limit = self._max_scroll()
        if limit <= 0:
            return
        theme = self._theme
        visible = self.rect.height / (self.rect.height + limit)
        mark_height = max(round(self.rect.height * visible), theme.px(18))
        top = self.rect.y + round((self.rect.height - mark_height) * self.scroll / limit)
        x = self.rect.right - theme.px(_SCROLL_MARK_WIDTH)
        pygame.draw.rect(surface, tokens.BRASS, (x, top, theme.px(_SCROLL_MARK_WIDTH), mark_height))


class HistoryPanel:
    """Conteúdo da aba. `store` é `None` para o convidado, que vê o convite em vez da lista."""

    def __init__(self, theme: Theme, store, on_invite: Callable[[], None] | None = None):
        self._theme = theme
        self._store = store
        self.stats: HistoryStats | None = None
        self.opened: MatchRecord | None = None
        self.message = ""
        self.list = HistoryList(theme, self.open_record)
        self.copy_button = Button("Copiar PGN", self.copy_pgn, STYLE_PRIMARY, hint="C")
        self.close_button = Button("Fechar", self.close_record, hint="Esc")
        self.invite_button = Button("Criar conta", on_invite, STYLE_PRIMARY, font_size=20) if on_invite else None
        self._stats_rect = pygame.Rect(0, 0, 0, 0)
        self._text_rect = pygame.Rect(0, 0, 0, 0)
        self._sheet = pygame.Rect(0, 0, 0, 0)
        self._sheet_shadow: pygame.Surface | None = None
        self._moves_rect = pygame.Rect(0, 0, 0, 0)
        self._moves_scroll = 0

    @property
    def has_account(self) -> bool:
        return self._store is not None

    def reload(self) -> None:
        if self._store is None:
            return
        self.list.set_records([displayable(record) for record in self._store.records()])
        self.stats = self._store.stats()
        self.close_record()

    def widgets(self) -> list:
        if not self.has_account:
            return [self.invite_button] if self.invite_button is not None else []
        details = [self.copy_button, self.close_button] if self.opened is not None else []
        return [self.list, *details]

    def open_record(self, index: int) -> None:
        self.opened = self.list.records[index]
        self.message = ""
        self._moves_scroll = 0

    def close_record(self) -> None:
        self.opened = None
        self.message = ""

    def copy_pgn(self) -> None:
        if self.opened is None:
            return
        self.message = "PGN copiado." if clipboard.copy_text(self.opened.pgn) else clipboard.COPY_FAILED_MESSAGE

    def handle_wheel(self, steps: int, position: tuple[int, int] | None) -> None:
        if self.opened is not None and position is not None and self._sheet.collidepoint(position):
            self._moves_scroll = max(0, self._moves_scroll - steps)
        else:
            self.list.scroll_by_wheel(steps)

    # Layout ---------------------------------------------------------------------------------------

    def layout(self, column: pygame.Rect, table: pygame.Rect) -> None:
        """`column` é o espaço no painel; `table`, o espaço da mesa onde a folha fica aberta."""
        theme = self._theme
        self._stats_rect = pygame.Rect(column.x, column.y, column.width, theme.px(_STAT_HEIGHT))
        list_top = self._stats_rect.bottom + theme.px(12)
        self.list.rect = pygame.Rect(column.x, list_top, column.width, max(column.bottom - list_top, 1))
        self.list.clamp_scroll()
        self._text_rect = column
        if self.invite_button is not None:
            self.invite_button.rect = pygame.Rect(column.x, column.y + theme.px(110), column.width, theme.px(50))
        self._layout_sheet(table, column)

    def _layout_sheet(self, table: pygame.Rect, column: pygame.Rect) -> None:
        theme = self._theme
        margin = theme.px(_SHEET_MARGIN)
        # Janela estreita demais para a folha ao lado: ela abre por cima do painel, inteira.
        area = table if table.width - 2 * margin >= theme.px(_SHEET_MIN_WIDTH) else table.union(column)
        self._sheet = area.inflate(-2 * margin, -2 * margin)
        self._sheet.width, self._sheet.height = max(self._sheet.width, 1), max(self._sheet.height, 1)
        self._sheet_shadow = drawing.render_soft_shadow(self._sheet.size, theme.px(8), 150)
        pad = theme.px(_SHEET_PADDING)
        button_height = theme.px(40)
        gap = theme.px(10)
        half = max((self._sheet.width - 2 * pad - gap) // 2, 1)
        y = self._sheet.bottom - pad - button_height
        self.copy_button.rect = pygame.Rect(self._sheet.x + pad, y, half, button_height)
        self.close_button.rect = pygame.Rect(self._sheet.x + pad + half + gap, y, half, button_height)

    # Desenho --------------------------------------------------------------------------------------

    def draw_column(self, surface: pygame.Surface) -> None:
        if not self.has_account:
            self._draw_lines(surface, NO_ACCOUNT_LINES, self._text_rect)
        elif not self.list.records:
            self._draw_stats(surface)
            self._draw_lines(surface, EMPTY_LINES, self.list.rect)
        else:
            self._draw_stats(surface)

    def _draw_lines(self, surface: pygame.Surface, lines: Sequence[str], rect: pygame.Rect) -> None:
        theme = self._theme
        y = rect.y + theme.px(10)
        title = theme.text_fit(lines[0], tokens.ROLE_DISPLAY, theme.px(22), tokens.IVORY, max(rect.width, 1))
        surface.blit(title, (rect.x, y))
        y += theme.px(32)
        for line in theme.wrap(lines[1], tokens.ROLE_LABEL, theme.px(16), rect.width):
            surface.blit(theme.text(line, tokens.ROLE_LABEL, theme.px(16), tokens.TEXT_MUTED), (rect.x, y))
            y += theme.px(21)

    def _draw_stats(self, surface: pygame.Surface) -> None:
        theme = self._theme
        rect = self._stats_rect
        gap = theme.px(_STAT_GAP)
        width = max((rect.width - 3 * gap) // 4, 1)
        for index, (label, attribute) in enumerate(_STAT_LABELS):
            cell = pygame.Rect(rect.x + index * (width + gap), rect.y, width, rect.height)
            surface.blit(theme.plate(cell.size, tokens.PLATE_SHADE), cell.topleft)
            value = theme.text(str(getattr(self.stats, attribute)), tokens.ROLE_NUMERIC, theme.px(26), tokens.BRASS_BRIGHT)
            surface.blit(value, value.get_rect(midtop=(cell.centerx, cell.y + theme.px(4))))
            text = theme.text_fit(label, tokens.ROLE_LABEL, theme.px(14), tokens.TEXT_MUTED, max(width - theme.px(6), 1))
            surface.blit(text, text.get_rect(midbottom=(cell.centerx, cell.bottom - theme.px(5))))

    def draw_sheet(self, surface: pygame.Surface) -> None:
        """A partida aberta, como a planilha de verdade: papel sobre a mesa, escrito à tinta."""
        record = self.opened
        if record is None:
            return
        theme = self._theme
        sheet = self._sheet
        if self._sheet_shadow is not None:
            surface.blit(self._sheet_shadow, (sheet.x - theme.px(8) + theme.px(2), sheet.y - theme.px(8) + theme.px(4)))
        surface.blit(theme.plate(sheet.size, tokens.PLATE_PAPER), sheet.topleft)
        pad = theme.px(_SHEET_PADDING)
        left, width = sheet.x + pad, max(sheet.width - 2 * pad, 1)
        y = self._draw_sheet_header(surface, record, left, sheet.y + pad - theme.px(4), width)
        y = self._draw_sheet_facts(surface, record, left, y + theme.px(8), width)
        self._draw_sheet_moves(surface, record, left, y + theme.px(8), width)
        self.copy_button.draw(surface, theme)
        self.close_button.draw(surface, theme)
        if self.message:
            text = theme.text_fit(self.message, tokens.ROLE_LABEL, theme.px(15), tokens.INK_SOFT, width)
            surface.blit(text, (left, self.copy_button.rect.y - text.get_height() - theme.px(4)))

    def _draw_sheet_header(self, surface: pygame.Surface, record: MatchRecord, left: int, y: int, width: int) -> int:
        theme = self._theme
        title = theme.text_fit(_opponent_text(record), tokens.ROLE_DISPLAY, theme.px(27), tokens.INK, width)
        surface.blit(title, (left, y))
        y += title.get_height() + theme.px(2)
        reason = theme.text_fit(record.reason, tokens.ROLE_LABEL, theme.px(17), tokens.INK_SOFT, width)
        surface.blit(reason, (left, y))
        return y + reason.get_height()

    def _draw_sheet_facts(self, surface: pygame.Surface, record: MatchRecord, left: int, y: int, width: int) -> int:
        theme = self._theme
        facts = (
            ("Data", format_played_at(record.played_at)), ("Tempo", record.time_control),
            ("Modo", record.mode), ("Cor", record.color),
            ("Lances", str(record.moves)), ("Duração", format_clock(record.seconds)),
        )
        pygame.draw.line(surface, tokens.PAPER_RULE, (left, y), (left + width, y))
        y += theme.px(6)
        column = width // 2
        row_height = theme.px(21)
        label_width = theme.px(64)
        for index, (label, value) in enumerate(facts):
            row, side = divmod(index, 2)
            x, line_y = left + side * column, y + row * row_height
            text = theme.text(label, tokens.ROLE_LABEL, theme.px(14), tokens.INK_SOFT)
            surface.blit(text, (x, line_y + theme.px(1)))
            content = theme.text_fit(value, tokens.ROLE_SERIF, theme.px(16), tokens.INK, max(column - label_width - theme.px(6), 1))
            surface.blit(content, (x + label_width, line_y))
        y += 3 * row_height + theme.px(4)
        pygame.draw.line(surface, tokens.PAPER_RULE, (left, y), (left + width, y))
        return y

    def _draw_sheet_moves(self, surface: pygame.Surface, record: MatchRecord, left: int, y: int, width: int) -> None:
        theme = self._theme
        fen_lines = theme.wrap(record.final_fen, tokens.ROLE_MONO, theme.px(_FEN_FONT), width)
        fen_height = theme.px(19) + len(fen_lines) * theme.px(17)
        bottom = self.copy_button.rect.y - theme.px(26) - fen_height
        self._moves_rect = pygame.Rect(left, y, width, max(bottom - y, 0))
        self._draw_moves_block(surface, record)
        self._draw_fen(surface, fen_lines, left, bottom + theme.px(2))

    def _draw_moves_block(self, surface: pygame.Surface, record: MatchRecord) -> None:
        theme = self._theme
        rect = self._moves_rect
        lines = theme.wrap(_movetext(record.pgn), tokens.ROLE_SERIF, theme.px(_PGN_FONT), rect.width)
        visible = max(rect.height // theme.px(_PGN_LINE_HEIGHT), 0)
        self._moves_scroll = min(self._moves_scroll, max(len(lines) - visible, 0))
        y = rect.y
        for line in lines[self._moves_scroll:self._moves_scroll + visible]:
            surface.blit(theme.text(line, tokens.ROLE_SERIF, theme.px(_PGN_FONT), tokens.INK), (rect.x, y))
            y += theme.px(_PGN_LINE_HEIGHT)

    def _draw_fen(self, surface: pygame.Surface, fen_lines: Sequence[str], left: int, y: int) -> None:
        theme = self._theme
        label = theme.text("Posição final (FEN)", tokens.ROLE_LABEL, theme.px(14), tokens.INK_SOFT)
        surface.blit(label, (left, y))
        y += theme.px(19)
        for line in fen_lines:
            surface.blit(theme.text(line, tokens.ROLE_MONO, theme.px(_FEN_FONT), tokens.INK), (left, y))
            y += theme.px(17)
