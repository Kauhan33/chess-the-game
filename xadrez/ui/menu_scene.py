"""Menu inicial: identificação dos jogadores e escolha do modo, ao lado de uma peça 3D ao vivo."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from xadrez.core import TimeControl
from xadrez.graphics import (
    EBONY,
    FACING_BLACK,
    FACING_WHITE,
    IVORY,
    Camera,
    ColorMatrix,
    Renderer3D,
    piece_matrix,
)
from xadrez.ui import theme as tokens
from xadrez.ui.match import DEFAULT_BLACK_NAME, DEFAULT_WHITE_NAME, MatchOptions
from xadrez.ui.overlays import CONTROL_HINTS, HelpOverlay, Overlay, draw_control_hint
from xadrez.ui.scene import Scene
from xadrez.ui.widgets import STYLE_PRIMARY, Button, FocusGroup, Selector, TextInput

if TYPE_CHECKING:
    from xadrez.ui.app import App

TIME_OPTIONS = (
    ("Sem limite de tempo", TimeControl.UNLIMITED),
    ("Blitz: 5 minutos", TimeControl.BLITZ_5),
    ("Rápida: 10 minutos", TimeControl.RAPID_10),
    ("Clássica: 30 minutos", TimeControl.CLASSIC_30),
)
CAMERA_OPTIONS = (
    ("Gira a cada turno", True),
    ("Fixa no lado das Brancas", False),
)
_MENU_HINTS = tuple(hint for hint in CONTROL_HINTS if hint.keys in ("Clique", "Direito", "Roda", "Setas", "Enter", "P"))
_FORM_WIDTH = 480
_FORM_MAX_FRACTION = 0.62
_FORM_PADDING = 30
_FIELD_HEIGHT = 44
_FIELD_GAP = 30
_BUTTON_HEIGHT = 54
_QUIT_BUTTON_WIDTH = 92
_HINT_ROW_HEIGHT = 24
_MIN_HEIGHT_FOR_HINTS = 660
_SPIN_SPEED = math.radians(14)
_SPOTLIGHT_SQUARE = (3, 3)
# A cena do menu: o rei de marfim em primeiro plano, com o rei de ébano e alguns peões ao fundo.
_TABLEAU = (
    ("king", 3, 3, IVORY, FACING_WHITE),
    ("queen", 4, 5, EBONY, FACING_BLACK),
    ("knight", 1, 4, EBONY, FACING_BLACK),
    ("pawn", 5, 3, IVORY, FACING_WHITE),
    ("rook", 2, 1, IVORY, FACING_WHITE),
)


class MenuScene(Scene):
    def __init__(self, app: App, defaults: MatchOptions | None = None):
        super().__init__(app)
        options = defaults if defaults is not None else MatchOptions()
        self.white_input = self._name_input("Brancas", DEFAULT_WHITE_NAME, options.white_name)
        self.black_input = self._name_input("Pretas", DEFAULT_BLACK_NAME, options.black_name)
        self.time_selector = Selector("Tempo por jogador", TIME_OPTIONS, _index_of(TIME_OPTIONS, options.time_control))
        self.camera_selector = Selector("Câmera", CAMERA_OPTIONS, _index_of(CAMERA_OPTIONS, options.auto_rotate))
        self.start_button = Button("Iniciar partida", self.start_match, STYLE_PRIMARY, font_size=22)
        self.help_button = Button("Ver todos os controles", self.open_help, hint="F1")
        self.quit_button = Button("Sair", self.quit_game)
        self.focus = FocusGroup([self.white_input, self.black_input, self.time_selector, self.camera_selector,
                                 self.start_button, self.help_button, self.quit_button])
        self.modal: Overlay | None = None
        self._help_just_closed = False
        pygame.key.start_text_input()
        self.camera = Camera((0, 0, 1, 1), yaw=math.radians(-28), pitch=math.radians(24), distance=8.4,
                             fov_y=math.radians(30), target=self._spotlight_target())
        self.renderer = Renderer3D(self.camera)
        self._matrix = ColorMatrix(palette=tokens.BOARD_STATE_PALETTE)
        self._tableau_meshes = [
            (app.meshes[kind], piece_matrix(file, rank, facing), color) for kind, file, rank, color, facing in _TABLEAU
        ]
        self._form = pygame.Rect(0, 0, 1, 1)
        self._ground: pygame.Surface | None = None
        self._show_hints = True
        self.resize(app.size)

    @staticmethod
    def _spotlight_target() -> tuple[float, float, float]:
        file, rank = _SPOTLIGHT_SQUARE
        return (file - 3.5, 0.72, 3.5 - rank)

    def _name_input(self, label: str, placeholder: str, name: str) -> TextInput:
        field = TextInput(label, placeholder, value="" if name == placeholder else name)
        theme = self.app.theme
        field.set_character_filter(lambda char: theme.has_glyph(char, tokens.ROLE_DISPLAY, theme.px(19)))
        return field

    def options(self) -> MatchOptions:
        return MatchOptions(self.white_input.value, self.black_input.value,
                            self.time_selector.value, self.camera_selector.value)

    def start_match(self) -> None:
        options = self.options()
        self.next_scene = self.app.game_scene(options.create_engine(), options)

    def open_help(self) -> None:
        self.modal = HelpOverlay(self.app.theme, self._close_help)
        self.modal.layout(self.app.size)

    def _close_help(self) -> None:
        self.modal = None
        self._help_just_closed = True

    def quit_game(self) -> None:
        self.app.running = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.modal is not None:
            self.modal.handle_event(event)
            return
        # H fecha a ajuda, e o SDL entrega a mesma tecla como texto logo em seguida: não é digitação.
        if event.type == pygame.TEXTINPUT and self._help_just_closed:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.open_help()
            return
        self.focus.handle_event(event)

    def update(self, dt: float) -> None:
        self._help_just_closed = False
        self.camera.orbit_by(_SPIN_SPEED * dt)
        for widget in (self.white_input, self.black_input):
            widget.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_scene_3d(surface)
        if self._ground is not None:
            surface.blit(self._ground, self._form.topleft)
        self._draw_titles(surface)
        self.focus.draw(surface, self.app.theme)
        if self._show_hints:
            self._draw_hints(surface)
        if self.modal is not None:
            self.modal.draw(surface)

    def _draw_scene_3d(self, surface: pygame.Surface) -> None:
        renderer = self.renderer
        renderer.begin(surface)
        renderer.draw_board(self._matrix.rgb())
        for mesh, matrix, color in self._tableau_meshes:
            renderer.add_mesh(mesh, matrix, color)
        renderer.flush()

    def _content_left(self) -> int:
        theme = self.app.theme
        return self._form.x + theme.px(_FORM_PADDING) + theme.px(2)

    def _draw_titles(self, surface: pygame.Surface) -> None:
        theme = self.app.theme
        pad = theme.px(_FORM_PADDING)
        available = max(self._form.width - 2 * pad, 1)
        title = theme.text_fit("Chess - The Game", tokens.ROLE_DISPLAY, theme.px(48), tokens.BRASS_BRIGHT, available)
        surface.blit(title, (self._content_left(), self._form.y + theme.px(24)))
        tagline = "Dois jogadores, uma tela, regras oficiais."
        subtitle = theme.text_fit(tagline, tokens.ROLE_LABEL, theme.px(18), tokens.TEXT_MUTED, available)
        surface.blit(subtitle, (self._content_left(), self._form.y + theme.px(84)))

    def _draw_hints(self, surface: pygame.Surface) -> None:
        theme = self.app.theme
        keycap_right = self._content_left() + theme.px(50)
        y = self.help_button.rect.bottom + theme.px(12)
        for hint in _MENU_HINTS:
            draw_control_hint(surface, theme, hint, keycap_right, y, font_size=15)
            y += theme.px(_HINT_ROW_HEIGHT)

    def resize(self, size: tuple[int, int]) -> None:
        theme = self.app.theme
        width, height = max(size[0], 1), max(size[1], 1)
        form_width = max(min(theme.px(_FORM_WIDTH), round(width * _FORM_MAX_FRACTION)), 1)
        self._form = pygame.Rect(width - form_width, 0, form_width, height)
        self.camera.set_viewport(0, 0, max(width - form_width, 1), height)
        self._ground = theme.panel_ground(self._form.size)
        self._show_hints = height >= theme.px(_MIN_HEIGHT_FOR_HINTS)
        self._layout_form()
        if self.modal is not None:
            self.modal.layout(size)

    def _layout_form(self) -> None:
        theme = self.app.theme
        pad = theme.px(_FORM_PADDING)
        left = self._content_left()
        width = max(self._form.width - 2 * pad - theme.px(2), 1)
        gap = theme.px(_FIELD_GAP)
        field_height = theme.px(_FIELD_HEIGHT)
        y = theme.px(142)
        half = max((width - theme.px(14)) // 2, 1)
        self.white_input.rect = pygame.Rect(left, y, half, field_height)
        self.black_input.rect = pygame.Rect(left + half + theme.px(14), y, half, field_height)
        y += field_height + gap
        self.time_selector.rect = pygame.Rect(left, y, width, field_height)
        y += field_height + gap
        self.camera_selector.rect = pygame.Rect(left, y, width, field_height)
        y += field_height + theme.px(18)
        self.start_button.rect = pygame.Rect(left, y, width, theme.px(_BUTTON_HEIGHT))
        y += theme.px(_BUTTON_HEIGHT) + theme.px(9)
        quit_width = min(theme.px(_QUIT_BUTTON_WIDTH), width // 3)
        row_gap = theme.px(8)
        self.help_button.rect = pygame.Rect(left, y, max(width - quit_width - row_gap, 1), theme.px(36))
        self.quit_button.rect = pygame.Rect(left + width - quit_width, y, max(quit_width, 1), theme.px(36))


def _index_of(options, value) -> int:
    return next((index for index, (_, option) in enumerate(options) if option == value), 0)
