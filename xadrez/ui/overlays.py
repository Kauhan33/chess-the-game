"""Sobreposições modais: pausa, confirmações, promoção e ajuda. Só a do topo recebe entrada."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Mapping, NamedTuple, Sequence

import pygame

from xadrez.core import Color, PieceType
from xadrez.graphics import Mesh, Renderer3D
from xadrez.ui import theme as tokens
from xadrez.ui.board_view import PIECE_COLORS
from xadrez.ui.theme import PlateStyle, Theme
from xadrez.ui.widgets import STYLE_SECONDARY, Button, FocusGroup, draw_keycap

_VEIL_ALPHA = 168
_PANEL_PADDING = 26
_BUTTON_HEIGHT = 44
_BUTTON_GAP = 9
_PANEL_MIN_WIDTH = 420

PROMOTION_CHOICES = (
    (PieceType.QUEEN, "Dama"),
    (PieceType.ROOK, "Torre"),
    (PieceType.BISHOP, "Bispo"),
    (PieceType.KNIGHT, "Cavalo"),
)
_CHOICE_SIZE = 112
_CHOICE_GAP = 12
_CHOICE_ICON = 74


class ControlHint(NamedTuple):
    keys: str
    description: str


CONTROL_HINTS = (
    ControlHint("Clique", "Seleciona a peça e joga"),
    ControlHint("Direito", "Arraste para girar a câmera"),
    ControlHint("Roda", "Aproxima e afasta a câmera"),
    ControlHint("Setas", "Movem o cursor, conforme a visão"),
    ControlHint("Enter", "Confirma, como o clique (ou Espaço)"),
    ControlHint("Esc", "Cancela a seleção ou abre a pausa"),
    ControlHint("P", "Pausa a partida"),
    ControlHint("R", "Reinicia, depois de confirmar"),
    ControlHint("T", "Liga ou desliga o giro por turno"),
    ControlHint("V", "Volta à vista padrão"),
    ControlHint("H", "Mostra esta ajuda (ou F1)"),
    ControlHint("F3", "Mostra FPS e polígonos"),
    ControlHint("F4", "Modo didático: matrizes ao vivo"),
    ControlHint("F11", "Liga ou desliga a tela cheia"),
)
_HELP_ROW_HEIGHT = 30
_HELP_CLOSE_KEYS = (pygame.K_ESCAPE, pygame.K_h, pygame.K_F1, pygame.K_RETURN, pygame.K_KP_ENTER)


class Overlay(ABC):
    """Tela sobre a partida. `freezes_clock` diz se o relógio para enquanto ela está aberta."""

    freezes_clock = True

    def __init__(self, theme: Theme):
        self._theme = theme
        self._size = (1, 1)
        self._veil: pygame.Surface | None = None

    def layout(self, size: tuple[int, int]) -> None:
        self._size = (max(size[0], 1), max(size[1], 1))
        self._veil = pygame.Surface(self._size)
        self._veil.fill(tokens.DIM_VEIL)
        self._veil.set_alpha(_VEIL_ALPHA)

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None: ...

    def update(self, dt: float) -> None:
        """Por padrão, nada se move sozinho em uma sobreposição."""

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None: ...

    def _draw_veil(self, surface: pygame.Surface) -> None:
        if self._veil is not None:
            surface.blit(self._veil, (0, 0))

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect, style: PlateStyle = tokens.PLATE_MODAL) -> None:
        surface.blit(self._theme.plate(rect.size, style), rect.topleft)


class ChoiceOverlay(Overlay):
    """Título, poucas linhas de explicação e uma coluna de botões: serve à pausa e às confirmações."""

    def __init__(self, theme: Theme, title: str, lines: Sequence[str], buttons: Sequence[Button],
                 on_cancel: Callable[[], None], cancel_keys: Sequence[int] = (pygame.K_ESCAPE,),
                 initial_focus: int = 0):
        super().__init__(theme)
        self.title = title
        self.lines = list(lines)
        self.buttons = list(buttons)
        self._on_cancel = on_cancel
        self._cancel_keys = tuple(cancel_keys)
        self._focus = FocusGroup(self.buttons, initial_focus)
        self._panel = pygame.Rect(0, 0, 1, 1)

    def layout(self, size: tuple[int, int]) -> None:
        super().layout(size)
        theme = self._theme
        pad = theme.px(_PANEL_PADDING)
        button_height, gap = theme.px(_BUTTON_HEIGHT), theme.px(_BUTTON_GAP)
        width = theme.px(_PANEL_MIN_WIDTH)
        height = (pad * 2 + self._text_block_height() + theme.px(16)
                  + len(self.buttons) * button_height + (len(self.buttons) - 1) * gap)
        self._panel = pygame.Rect(0, 0, width, height)
        self._panel.center = (self._size[0] // 2, self._size[1] // 2)
        y = self._panel.y + pad + self._text_block_height() + theme.px(16)
        for button in self.buttons:
            button.rect = pygame.Rect(self._panel.x + pad, y, width - 2 * pad, button_height)
            y += button_height + gap

    def _text_block_height(self) -> int:
        theme = self._theme
        return theme.px(40) + len(self.lines) * theme.px(25)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in self._cancel_keys:
            self._on_cancel()
            return
        self._focus.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_veil(surface)
        self._draw_panel(surface, self._panel)
        self._draw_text(surface)
        self._focus.draw(surface, self._theme)

    def _draw_text(self, surface: pygame.Surface) -> None:
        theme = self._theme
        pad = theme.px(_PANEL_PADDING)
        available = self._panel.width - 2 * pad
        title = theme.text_fit(self.title, tokens.ROLE_DISPLAY, theme.px(30), tokens.IVORY, available)
        y = self._panel.y + pad
        surface.blit(title, (self._panel.x + pad, y - theme.px(4)))
        y += theme.px(40)
        for line in self.lines:
            text = theme.text_fit(line, tokens.ROLE_LABEL, theme.px(17), tokens.TEXT_MUTED, available)
            surface.blit(text, (self._panel.x + pad, y))
            y += theme.px(25)


class _ChoiceButton(Button):
    """Botão da promoção: mostra a peça, em 3D de verdade, sobre uma plaqueta que a destaca."""

    def __init__(self, label: str, on_click: Callable[[], None], icon_source: Callable[[int], pygame.Surface],
                 tray: PlateStyle):
        super().__init__(label, on_click, STYLE_SECONDARY)
        self._icon_source = icon_source
        self._tray = tray

    def draw(self, surface: pygame.Surface, theme: Theme) -> None:
        is_lit = self.is_hovered or self.is_focused
        style = tokens.PLATE_BUTTON_HOVER if is_lit else tokens.PLATE_BUTTON
        surface.blit(theme.plate(self.rect.size, style), self.rect.topleft)
        icon_size = theme.px(_CHOICE_ICON)
        tray_rect = pygame.Rect(0, 0, icon_size + theme.px(8), icon_size + theme.px(8))
        tray_rect.midtop = (self.rect.centerx, self.rect.y + theme.px(6))
        surface.blit(theme.plate(tray_rect.size, self._tray), tray_rect.topleft)
        icon = self._icon_source(icon_size)
        surface.blit(icon, icon.get_rect(center=tray_rect.center))
        label = theme.text(self.label, tokens.ROLE_DISPLAY, theme.px(18), tokens.IVORY)
        surface.blit(label, label.get_rect(midbottom=(self.rect.centerx, self.rect.bottom - theme.px(3))))
        if self.is_focused:
            outline = theme.outline(self.rect.size, tokens.BRASS_BRIGHT, tokens.PLATE_BUTTON.cut)
            surface.blit(outline, self.rect.topleft)


class PromotionDialog(Overlay):
    """As 4 peças da promoção. O relógio segue correndo: escolher faz parte do lance."""

    freezes_clock = False

    def __init__(self, theme: Theme, renderer: Renderer3D, meshes: Mapping[str, Mesh], color: Color,
                 on_choose: Callable[[PieceType], None], on_cancel: Callable[[], None]):
        super().__init__(theme)
        self.color = color
        self._on_cancel = on_cancel
        tray = tokens.PLATE_LIGHT_TRAY if color is Color.BLACK else tokens.PLATE_DARK_TRAY
        self.buttons = [
            _ChoiceButton(label, lambda chosen=kind: on_choose(chosen),
                          self._icon_source(renderer, meshes[kind.value]), tray)
            for kind, label in PROMOTION_CHOICES
        ]
        self.kinds = [kind for kind, _ in PROMOTION_CHOICES]
        self._focus = FocusGroup(self.buttons)
        self._panel = pygame.Rect(0, 0, 1, 1)

    def _icon_source(self, renderer: Renderer3D, mesh: Mesh) -> Callable[[int], pygame.Surface]:
        return lambda size: renderer.render_icon(mesh, PIECE_COLORS[self.color], size)

    def layout(self, size: tuple[int, int]) -> None:
        super().layout(size)
        theme = self._theme
        pad, gap = theme.px(_PANEL_PADDING), theme.px(_CHOICE_GAP)
        choice = theme.px(_CHOICE_SIZE)
        width = 2 * pad + 4 * choice + 3 * gap
        height = 2 * pad + theme.px(62) + choice
        self._panel = pygame.Rect(0, 0, width, height)
        self._panel.center = (self._size[0] // 2, self._size[1] // 2)
        y = self._panel.y + pad + theme.px(62)
        for index, button in enumerate(self.buttons):
            button.rect = pygame.Rect(self._panel.x + pad + index * (choice + gap), y, choice, choice)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and self._handle_key(event):
            return
        self._focus.handle_event(event)

    def _handle_key(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_ESCAPE:
            self._on_cancel()
            return True
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._focus.move(-1 if event.key == pygame.K_LEFT else 1)
            return True
        number = event.key - pygame.K_1
        if 0 <= number < len(self.buttons):
            self.buttons[number].activate()
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_veil(surface)
        self._draw_panel(surface, self._panel)
        theme = self._theme
        pad = theme.px(_PANEL_PADDING)
        title = theme.text("Promoção do peão", tokens.ROLE_DISPLAY, theme.px(28), tokens.IVORY)
        surface.blit(title, (self._panel.x + pad, self._panel.y + pad - theme.px(6)))
        hint = theme.text("Escolha a peça. Esc cancela o lance.", tokens.ROLE_LABEL, theme.px(16), tokens.TEXT_MUTED)
        surface.blit(hint, (self._panel.x + pad, self._panel.y + pad + theme.px(30)))
        self._focus.draw(surface, theme)


class HelpOverlay(Overlay):
    """Lista de controles com teclas desenhadas. Fecha com a mesma tecla que abriu, Esc ou Enter."""

    def __init__(self, theme: Theme, on_close: Callable[[], None]):
        super().__init__(theme)
        self._on_close = on_close
        self._close_button = Button("Fechar", on_close, hint="Esc")
        self._panel = pygame.Rect(0, 0, 1, 1)

    def layout(self, size: tuple[int, int]) -> None:
        super().layout(size)
        theme = self._theme
        pad = theme.px(_PANEL_PADDING)
        width = theme.px(520)
        height = 2 * pad + theme.px(50) + len(CONTROL_HINTS) * theme.px(_HELP_ROW_HEIGHT) + theme.px(52)
        self._panel = pygame.Rect(0, 0, width, height)
        self._panel.center = (self._size[0] // 2, self._size[1] // 2)
        button_height = theme.px(40)
        self._close_button.rect = pygame.Rect(self._panel.x + pad, self._panel.bottom - pad - button_height,
                                              width - 2 * pad, button_height)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in _HELP_CLOSE_KEYS:
            self._on_close()
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self._close_button.handle_mouse(event)

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_veil(surface)
        self._draw_panel(surface, self._panel)
        theme = self._theme
        pad = theme.px(_PANEL_PADDING)
        title = theme.text("Controles", tokens.ROLE_DISPLAY, theme.px(30), tokens.IVORY)
        surface.blit(title, (self._panel.x + pad, self._panel.y + pad - theme.px(4)))
        y = self._panel.y + pad + theme.px(50)
        for hint in CONTROL_HINTS:
            draw_control_hint(surface, theme, hint, self._panel.x + pad + theme.px(80), y)
            y += theme.px(_HELP_ROW_HEIGHT)
        self._close_button.draw(surface, theme)


def draw_control_hint(surface: pygame.Surface, theme: Theme, hint: ControlHint, keycap_right: int, y: int,
                      font_size: int = 16) -> None:
    """Uma linha de ajuda: tecla à esquerda, alinhada pela direita, e a descrição ao lado."""
    center_y = y + theme.px(_HELP_ROW_HEIGHT) // 2
    draw_keycap(surface, theme, hint.keys, (keycap_right, center_y))
    text = theme.text(hint.description, tokens.ROLE_LABEL, theme.px(font_size), tokens.IVORY)
    surface.blit(text, text.get_rect(midleft=(keycap_right + theme.px(12), center_y)))
