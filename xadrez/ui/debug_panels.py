"""Painéis de bancada: F3 mostra o desempenho, F4 mostra as contas do pipeline ao vivo."""
from __future__ import annotations

import pygame

from xadrez.graphics import CellState
from xadrez.ui import drawing, theme as tokens
from xadrez.ui.board_view import BoardView
from xadrez.ui.theme import Theme

_MARGIN = 10
_LINE_HEIGHT = 18
_PADDING = 9
_FONT_SIZE = 14
_FILE_NAMES = "abcdefgh"
_DIDACTIC_WIDTH = 306
_DIDACTIC_LINES = 26
_MIN_BOARD_WIDTH = 240
_STATE_LEGEND = (
    (CellState.LAST_MOVE, "1 último lance"),
    (CellState.PATH, "2 caminho"),
    (CellState.CAPTURE, "3 captura"),
    (CellState.THREAT, "4 ameaça"),
    (CellState.CHECK, "5 xeque"),
    (CellState.SELECTED, "6 seleção"),
    (CellState.CURSOR, "7 cursor"),
)


def _square_name(cell: tuple[int, int] | None) -> str:
    return "fora do tabuleiro" if cell is None else f"{_FILE_NAMES[cell[0]]}{cell[1] + 1}"


class PerformancePanel:
    """Medidas reais do último quadro: FPS, milissegundos de trabalho, polígonos e partículas."""

    def __init__(self, theme: Theme):
        self._theme = theme
        self.is_visible = False

    def toggle(self) -> None:
        self.is_visible = not self.is_visible

    def draw(self, surface: pygame.Surface, viewport: pygame.Rect, fps: float, frame_ms: float, view: BoardView) -> None:
        if not self.is_visible:
            return
        theme = self._theme
        lines = (
            f"{fps:5.1f} FPS",
            f"{frame_ms:5.2f} ms por quadro",
            f"{view.scene_polygons:5d} polígonos em cena",
            f"{view.renderer.polygons_drawn:5d} redesenhados agora",
            f"{view.particles.alive_count:5d} partículas",
        )
        size = theme.px(_FONT_SIZE)
        height = 2 * theme.px(_PADDING) + len(lines) * theme.px(_LINE_HEIGHT)
        width = theme.px(232)
        margin = theme.px(_MARGIN)
        rect = pygame.Rect(viewport.right - width - margin, viewport.bottom - height - margin, width, height)
        surface.blit(theme.plate(rect.size, tokens.PLATE_DEBUG), rect.topleft)
        y = rect.y + theme.px(_PADDING)
        for line in lines:
            surface.blit(theme.text(line, tokens.ROLE_MONO, size, tokens.IVORY), (rect.x + theme.px(_PADDING), y))
            y += theme.px(_LINE_HEIGHT)


class DidacticPanel:
    """Modo didático para a banca: a matriz de visão, a matriz de estados e o raio do mouse, ao vivo."""

    def __init__(self, theme: Theme):
        self._theme = theme
        self.is_visible = False
        self._ground: pygame.Surface | None = None

    def toggle(self) -> None:
        self.is_visible = not self.is_visible

    def _reserved_width(self) -> int:
        return self._theme.px(_DIDACTIC_WIDTH + 2 * _MARGIN)

    def board_area(self, viewport: pygame.Rect) -> pygame.Rect:
        """O que sobra para o tabuleiro. Em janela estreita, o painel fica por cima dele."""
        reserved = self._reserved_width()
        if not self.is_visible or viewport.width - reserved < self._theme.px(_MIN_BOARD_WIDTH):
            return viewport
        return pygame.Rect(viewport.x + reserved, viewport.y, viewport.width - reserved, viewport.height)

    def _draw_ground(self, surface: pygame.Surface, viewport: pygame.Rect) -> None:
        if self.board_area(viewport) == viewport:
            return
        size = (self._reserved_width(), viewport.height)
        if self._ground is None or self._ground.get_size() != size:
            self._ground = drawing.render_panel_ground(size)
        surface.blit(self._ground, viewport.topleft)

    def draw(self, surface: pygame.Surface, viewport: pygame.Rect, view: BoardView,
             mouse_pos: tuple[int, int] | None) -> None:
        if not self.is_visible:
            return
        self._draw_ground(surface, viewport)
        theme = self._theme
        line = theme.px(_LINE_HEIGHT)
        pad = theme.px(_PADDING)
        margin = theme.px(_MARGIN)
        rect = pygame.Rect(viewport.x + margin, viewport.y + margin, theme.px(_DIDACTIC_WIDTH),
                           2 * pad + _DIDACTIC_LINES * line)
        surface.blit(theme.plate(rect.size, tokens.PLATE_DEBUG), rect.topleft)
        x, y = rect.x + pad, rect.y + pad
        y = self._draw_view_matrix(surface, view, x, y, line)
        y = self._draw_state_matrix(surface, view, x, y + line // 2, line)
        y = self._draw_legend(surface, x, y + line // 2, line)
        self._draw_mouse_ray(surface, view, mouse_pos, x, y + line // 2, line)

    def _heading(self, surface: pygame.Surface, content: str, x: int, y: int) -> None:
        surface.blit(self._theme.text(content, tokens.ROLE_LABEL, self._theme.px(_FONT_SIZE), tokens.BRASS_BRIGHT), (x, y))

    def _mono(self, surface: pygame.Surface, content: str, x: int, y: int, color: tuple = tokens.IVORY) -> None:
        surface.blit(self._theme.text(content, tokens.ROLE_MONO, self._theme.px(_FONT_SIZE), color), (x, y))

    def _draw_view_matrix(self, surface: pygame.Surface, view: BoardView, x: int, y: int, line: int) -> int:
        self._heading(surface, "Matriz de visão: mundo para câmera", x, y)
        y += line
        for row in view.camera.view_matrix:
            self._mono(surface, " ".join(f"{value:7.2f}" for value in row), x, y)
            y += line
        return y

    def _draw_state_matrix(self, surface: pygame.Surface, view: BoardView, x: int, y: int, line: int) -> int:
        theme = self._theme
        self._heading(surface, "Matriz de cores: estado de cada casa", x, y)
        y += line
        cell = theme.px(18)
        for rank in range(7, -1, -1):
            self._mono(surface, str(rank + 1), x, y, tokens.TEXT_MUTED)
            for file in range(8):
                state = CellState(int(view.matrix.states[file, rank]))
                column_x = x + (file + 1) * cell + theme.px(4)
                self._mono(surface, str(int(state)), column_x, y, tokens.STATE_TEXT_COLORS[state])
            y += line
        for file in range(8):
            self._mono(surface, _FILE_NAMES[file], x + (file + 1) * cell + theme.px(4), y, tokens.TEXT_MUTED)
        return y + line

    def _draw_legend(self, surface: pygame.Surface, x: int, y: int, line: int) -> int:
        theme = self._theme
        column = theme.px(145)
        for index, (state, label) in enumerate(_STATE_LEGEND):
            row, side = divmod(index, 2)
            color = tokens.STATE_TEXT_COLORS[state]
            text = theme.text(label, tokens.ROLE_LABEL, theme.px(_FONT_SIZE - 1), color)
            surface.blit(text, (x + side * column, y + row * line))
        return y + ((len(_STATE_LEGEND) + 1) // 2) * line

    def _draw_mouse_ray(self, surface: pygame.Surface, view: BoardView, mouse_pos: tuple[int, int] | None,
                        x: int, y: int, line: int) -> None:
        self._heading(surface, "Raio do mouse", x, y)
        y += line
        if mouse_pos is None:
            self._mono(surface, "mova o mouse sobre o tabuleiro", x, y, tokens.TEXT_MUTED)
            return
        origin, direction = view.camera.screen_ray(*mouse_pos)
        self._mono(surface, f"pixel   ({mouse_pos[0]}, {mouse_pos[1]})", x, y)
        self._mono(surface, f"direção ({direction.x:5.2f}, {direction.y:5.2f}, {direction.z:5.2f})", x, y + line)
        self._mono(surface, f"origem  ({origin.x:5.2f}, {origin.y:5.2f}, {origin.z:5.2f})", x, y + 2 * line)
        self._mono(surface, f"casa    {_square_name(view.pick(mouse_pos))}", x, y + 3 * line, tokens.BRASS_BRIGHT)
