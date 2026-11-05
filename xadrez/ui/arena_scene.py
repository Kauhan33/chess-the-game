"""Telas fora da partida: a mesa 3D girando à esquerda e o painel de nogueira à direita, com o formulário."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Mapping

import pygame

from xadrez.graphics import (
    EBONY,
    FACING_BLACK,
    FACING_WHITE,
    IVORY,
    Camera,
    ColorMatrix,
    Mesh,
    Renderer3D,
    piece_matrix,
)
from xadrez.ui import drawing, theme as tokens
from xadrez.ui.scene import Scene
from xadrez.ui.theme import Theme

if TYPE_CHECKING:
    from xadrez.ui.app import App

_FORM_WIDTH = 480
_FORM_MAX_FRACTION = 0.62
_FORM_PADDING = 30
_LABEL_ROOM = 26
_MIN_SPACING = 0.3
_NOTE_LINE_HEIGHT = 20
_ERROR_FONT = 16
_ERROR_INDENT = 30
_ERROR_ICON = 10
_ERROR_MARGIN = 8
_SPIN_SPEED = math.radians(14)
_SPOTLIGHT_SQUARE = (3, 3)
# A cena: o rei de marfim em primeiro plano, com o rei de ébano e alguns peões ao fundo.
_TABLEAU = (
    ("king", 3, 3, IVORY, FACING_WHITE),
    ("queen", 4, 5, EBONY, FACING_BLACK),
    ("knight", 1, 4, EBONY, FACING_BLACK),
    ("pawn", 5, 3, IVORY, FACING_WHITE),
    ("rook", 2, 1, IVORY, FACING_WHITE),
)


def _spotlight_target() -> tuple[float, float, float]:
    file, rank = _SPOTLIGHT_SQUARE
    return (file - 3.5, 0.72, 3.5 - rank)


class Tableau:
    """A mesa ao fundo. É uma só no jogo inteiro: trocar de tela não a faz pular nem refazer o fundo."""

    def __init__(self, meshes: Mapping[str, Mesh]):
        self.camera = Camera((0, 0, 1, 1), yaw=math.radians(-28), pitch=math.radians(24), distance=8.4,
                             fov_y=math.radians(30), target=_spotlight_target())
        self.renderer = Renderer3D(self.camera)
        self._matrix = ColorMatrix(palette=tokens.BOARD_STATE_PALETTE)
        self._pieces = [(meshes[kind], piece_matrix(file, rank, facing), color) for kind, file, rank, color, facing in _TABLEAU]

    def fit(self, width: int, height: int) -> None:
        viewport = (0, 0, max(width, 1), max(height, 1))
        if self.camera.viewport != viewport:
            self.camera.set_viewport(*viewport)

    def update(self, dt: float) -> None:
        self.camera.orbit_by(_SPIN_SPEED * dt)

    def draw(self, surface: pygame.Surface) -> None:
        renderer = self.renderer
        renderer.begin(surface)
        renderer.draw_board(self._matrix.rgb())
        for mesh, matrix, color in self._pieces:
            renderer.add_mesh(mesh, matrix, color)
        renderer.flush()


class FormFlow:
    """Empilha os controles de cima para baixo, deixando lugar para o rótulo que cada campo desenha acima de si."""

    def __init__(self, theme: Theme, left: int, top: int, width: int, spacing: float = 1.0):
        self._theme = theme
        self.left = left
        self.y = top
        self.width = width
        self._spacing = spacing
        self.notes: list[tuple[tuple[str, ...], int, int, tuple, int]] = []

    def gap(self, amount: int) -> None:
        self.y += round(self._theme.px(amount) * self._spacing)

    def field(self, widget, height: int = 42) -> None:
        self.gap(_LABEL_ROOM)
        self.place(widget, height)

    def place(self, widget, height: int) -> None:
        widget.rect = pygame.Rect(self.left, self.y, self.width, self._theme.px(height))
        self.y = widget.rect.bottom

    def pair(self, first, second, height: int = 42) -> None:
        self.gap(_LABEL_ROOM)
        gap = self._theme.px(14)
        first_width = max((self.width - gap) // 2, 1)
        pixel_height = self._theme.px(height)
        first.rect = pygame.Rect(self.left, self.y, first_width, pixel_height)
        second_x = self.left + first_width + gap
        second.rect = pygame.Rect(second_x, self.y, max(self.left + self.width - second_x, 1), pixel_height)
        self.y += pixel_height

    def note(self, text: str, color: tuple = tokens.TEXT_MUTED, reserve_lines: int = 0, size: int = 15) -> None:
        """Uma frase explicando o que está acima dela. `reserve_lines` evita que o formulário pule ao trocar de opção."""
        theme = self._theme
        lines = theme.wrap(text, tokens.ROLE_LABEL, theme.px(size), self.width)
        self.y += theme.px(4)
        self.notes.append((lines, self.left, self.y, color, size))
        self.y += max(len(lines), reserve_lines) * theme.px(_NOTE_LINE_HEIGHT)


def draw_notes(surface: pygame.Surface, theme: Theme, notes: list) -> None:
    for lines, x, y, color, size in notes:
        for line in lines:
            surface.blit(theme.text(line, tokens.ROLE_LABEL, theme.px(size), color), (x, y))
            y += theme.px(_NOTE_LINE_HEIGHT)


class ArenaScene(Scene):
    """Base do login, do menu e da sala. O formulário é da cena; a mesa e o painel são daqui."""

    def __init__(self, app: App):
        super().__init__(app)
        self.camera = app.tableau.camera
        self.renderer = app.tableau.renderer
        self._form = pygame.Rect(0, 0, 1, 1)
        self._ground: pygame.Surface | None = None
        self._notes: list = []

    def update(self, dt: float) -> None:
        self.app.tableau.update(dt)

    def draw_arena(self, surface: pygame.Surface) -> None:
        self.app.tableau.draw(surface)
        if self._ground is not None:
            surface.blit(self._ground, self._form.topleft)

    def _content_left(self) -> int:
        theme = self.app.theme
        return self._form.x + theme.px(_FORM_PADDING) + theme.px(2)

    def _content_width(self) -> int:
        theme = self.app.theme
        return max(self._form.width - 2 * theme.px(_FORM_PADDING) - theme.px(2), 1)

    def _flow(self, top: int, spacing: float = 1.0) -> FormFlow:
        return FormFlow(self.app.theme, self._content_left(), top, self._content_width(), spacing)

    def _fit_spacing(self, layout_at) -> None:
        """Monta o formulário; se passar da janela, monta de novo com os espaços encolhidos."""
        bottom = layout_at(1.0)
        room = self._form.height - self.app.theme.px(10)
        if bottom > room:
            layout_at(max(_MIN_SPACING, 1.0 - (bottom - room) / max(bottom * 0.45, 1)))

    def _draw_title(self, surface: pygame.Surface, text: str, top: int, size: int = 42) -> None:
        theme = self.app.theme
        title = theme.text_fit(text, tokens.ROLE_DISPLAY, theme.px(size), tokens.BRASS_BRIGHT, self._content_width())
        surface.blit(title, (self._content_left(), self._form.y + theme.px(top)))

    def _error_lines(self, message: str) -> tuple[str, ...]:
        theme = self.app.theme
        return theme.wrap(message, tokens.ROLE_LABEL, theme.px(_ERROR_FONT), max(self._content_width() - theme.px(_ERROR_INDENT), 1))

    def _error_room(self, message: str, minimum_lines: int = 2) -> int:
        """Altura que a mensagem de erro precisa, sem pular o formulário quando as mensagens são curtas."""
        return max(len(self._error_lines(message)), minimum_lines) * _NOTE_LINE_HEIGHT + _ERROR_MARGIN

    def _draw_error(self, surface: pygame.Surface, message: str, y: int) -> None:
        """Triângulo e texto: o erro não depende só da cor (RNF04)."""
        theme = self.app.theme
        icon, left = theme.px(_ERROR_ICON), self._content_left()
        drawing.draw_warning_triangle(surface, (left + icon, y + theme.px(10)), icon, tokens.ALERT_ON_DARK, tokens.INK)
        for line in self._error_lines(message):
            text = theme.text(line, tokens.ROLE_LABEL, theme.px(_ERROR_FONT), tokens.ALERT_ON_DARK)
            surface.blit(text, (left + theme.px(_ERROR_INDENT), y))
            y += theme.px(_NOTE_LINE_HEIGHT)

    def resize(self, size: tuple[int, int]) -> None:
        theme = self.app.theme
        width, height = max(size[0], 1), max(size[1], 1)
        form_width = max(min(theme.px(_FORM_WIDTH), round(width * _FORM_MAX_FRACTION)), 1)
        self._form = pygame.Rect(width - form_width, 0, form_width, height)
        self.app.tableau.fit(width - form_width, height)
        self._ground = theme.panel_ground(self._form.size)
        self._layout_form()

    def _layout_form(self) -> None:
        """Cada tela posiciona os próprios controles aqui."""
