"""Controles de tela: botão, campo de texto, seletores e abas, todos operáveis por mouse e por teclado."""
from __future__ import annotations

from itertools import islice
from typing import Callable, Sequence

import pygame

from xadrez.ui import drawing, theme as tokens
from xadrez.ui.theme import Theme

STYLE_PRIMARY = "primary"
STYLE_SECONDARY = "secondary"
STYLE_DANGER = "danger"

_BUTTON_PLATES = {
    STYLE_PRIMARY: (tokens.PLATE_PRIMARY, tokens.PLATE_PRIMARY_HOVER, tokens.INK),
    STYLE_SECONDARY: (tokens.PLATE_BUTTON, tokens.PLATE_BUTTON_HOVER, tokens.IVORY),
    STYLE_DANGER: (tokens.PLATE_DANGER, tokens.PLATE_DANGER_HOVER, tokens.IVORY),
}
_CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)
_CARET_PERIOD = 1.0
_FOCUS_MARGIN = 4
_SECRET_DOT_RADIUS = 4
_SECRET_DOT_STEP = 13
_TAB_UNDERLINE = 3


def _draw_focus_ring(surface: pygame.Surface, theme: Theme, rect: pygame.Rect, cut: int) -> None:
    margin = theme.px(_FOCUS_MARGIN)
    ring = rect.inflate(2 * margin, 2 * margin)
    surface.blit(theme.outline(ring.size, tokens.BRASS_BRIGHT, cut + _FOCUS_MARGIN // 2), ring.topleft)


def _blit_centered(surface: pygame.Surface, image: pygame.Surface, center: tuple[int, int]) -> None:
    surface.blit(image, image.get_rect(center=center))


def _draw_field_label(surface: pygame.Surface, theme: Theme, label: str, rect: pygame.Rect) -> None:
    if not label:
        return
    text = theme.text(label, tokens.ROLE_LABEL, theme.px(15), tokens.TEXT_MUTED)
    # Acima do anel de foco, que sai 4 pixels para fora do campo.
    surface.blit(text, (rect.x, rect.y - text.get_height() - theme.px(_FOCUS_MARGIN + 2)))


def draw_keycap(surface: pygame.Surface, theme: Theme, label: str, midright: tuple[int, int],
                font_size: int = 14) -> pygame.Rect:
    """Tecla desenhada: mostra o atalho com a forma de uma tecla, sem depender de glifo especial."""
    text = theme.text(label, tokens.ROLE_LABEL, theme.px(font_size), tokens.INK)
    size = (max(text.get_width() + theme.px(10), theme.px(22)), max(text.get_height() + theme.px(2), theme.px(20)))
    rect = pygame.Rect((0, 0), size)
    rect.midright = midright
    surface.blit(theme.plate(size, tokens.PLATE_KEYCAP), rect.topleft)
    _blit_centered(surface, text, rect.center)
    return rect


class Button:
    def __init__(self, label: str, on_click: Callable[[], None], style: str = STYLE_SECONDARY, hint: str | None = None,
                 font_size: int = 17):
        self.label = label
        self.on_click = on_click
        self.style = style
        self.hint = hint
        self.font_size = font_size
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.is_pressed = False
        self.is_focused = False
        self.is_enabled = True
        self.advances_on_enter = False

    def activate(self) -> None:
        if self.is_enabled:
            self.on_click()

    def handle_mouse(self, event: pygame.event.Event) -> bool:
        """Devolve se o evento era deste botão. O clique vale ao soltar, sobre o próprio botão."""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.is_pressed = True
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_pressed:
            self.is_pressed = False
            if self.rect.collidepoint(event.pos):
                self.activate()
            return True
        return False

    def handle_key(self, event: pygame.event.Event) -> bool:
        if event.key in _CONFIRM_KEYS or event.key == pygame.K_SPACE:
            self.activate()
            return True
        return False

    def _plate_and_text_color(self) -> tuple[tokens.PlateStyle, tuple]:
        if not self.is_enabled:
            return tokens.PLATE_DISABLED, tokens.TEXT_MUTED
        base, hover, text_color = _BUTTON_PLATES[self.style]
        return (hover if self.is_hovered or self.is_focused else base), text_color

    def draw(self, surface: pygame.Surface, theme: Theme) -> None:
        plate, text_color = self._plate_and_text_color()
        offset = theme.px(1) if self.is_pressed else 0
        rect = self.rect.move(0, offset)
        surface.blit(theme.plate(rect.size, plate), rect.topleft)
        hint_space = self._draw_hint(surface, theme, rect)
        available = max(rect.width - hint_space - theme.px(16), 1)
        label = theme.text_fit(self.label, tokens.ROLE_LABEL, theme.px(self.font_size), text_color, available)
        _blit_centered(surface, label, (rect.centerx - hint_space // 2, rect.centery))
        if self.is_focused:
            _draw_focus_ring(surface, theme, rect, tokens.PLATE_BUTTON.cut)

    def _draw_hint(self, surface: pygame.Surface, theme: Theme, rect: pygame.Rect) -> int:
        if self.hint is None:
            return 0
        cap = draw_keycap(surface, theme, self.hint, (rect.right - theme.px(8), rect.centery))
        return cap.width + theme.px(8)


class TextInput:
    """Campo de texto. Vazio, mostra o padrão, que no nome de jogador é o usado se ninguém digitar nada.

    Com `is_secret`, o conteúdo vira pontos desenhados: nunca passa pelo cache de texto do tema. Com
    `on_submit`, Enter confirma em vez de ir para o próximo campo.
    """

    def __init__(self, label: str, placeholder: str, max_length: int = 16, value: str = "", is_secret: bool = False,
                 on_submit: Callable[[], None] | None = None, transform: Callable[[str], str] = str):
        self.label = label
        self.placeholder = placeholder
        self.max_length = max_length
        self.text = value
        self.is_secret = is_secret
        self.on_submit = on_submit
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_focused = False
        self.advances_on_enter = on_submit is None
        self._time = 0.0
        self._accepts: Callable[[str], bool] = str.isprintable
        self._transform = transform

    @property
    def value(self) -> str:
        return " ".join(self.text.split()) or self.placeholder

    def set_character_filter(self, accepts: Callable[[str], bool]) -> None:
        self._accepts = accepts

    def clear(self) -> None:
        self.text = ""
        self._time = 0.0

    def activate(self) -> None:
        """No campo de texto, ativar é só receber o foco: o `FocusGroup` já cuidou disso."""

    def handle_mouse(self, event: pygame.event.Event) -> bool:
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def handle_key(self, event: pygame.event.Event) -> bool:
        if event.key in _CONFIRM_KEYS and self.on_submit is not None:
            self.on_submit()
            return True
        if event.key != pygame.K_BACKSPACE:
            return False
        self.text = self.text[:-1]
        self._time = 0.0
        return True

    def handle_text(self, content: str) -> None:
        room = max(self.max_length - len(self.text), 0)
        # `islice` para no limite: uma colagem enorme não paga o filtro de cada caractere.
        allowed = (char for char in content if char.isprintable() and self._accepts(char))
        self.text += self._transform("".join(islice(allowed, room)))
        self._time = 0.0

    def update(self, dt: float) -> None:
        self._time += dt

    def draw(self, surface: pygame.Surface, theme: Theme) -> None:
        _draw_field_label(surface, theme, self.label, self.rect)
        style = tokens.PLATE_INPUT_FOCUS if self.is_focused else tokens.PLATE_INPUT
        surface.blit(theme.plate(self.rect.size, style), self.rect.topleft)
        text_right = self._draw_secret(surface, theme) if self.is_secret and self.text else self._draw_content(surface, theme)
        if self.is_focused:
            self._draw_caret(surface, theme, text_right)
            _draw_focus_ring(surface, theme, self.rect, tokens.PLATE_INPUT.cut)

    def _draw_content(self, surface: pygame.Surface, theme: Theme) -> int:
        padding = theme.px(10)
        color = tokens.INK if self.text else tokens.INK_SOFT
        available = max(self.rect.width - 2 * padding - theme.px(3), 1)
        content = theme.text_fit(self.text or self.placeholder, tokens.ROLE_DISPLAY, theme.px(19), color, available)
        rect = content.get_rect(midleft=(self.rect.x + padding, self.rect.centery))
        surface.blit(content, rect)
        return rect.right if self.text else rect.left

    def _draw_secret(self, surface: pygame.Surface, theme: Theme) -> int:
        padding, step = theme.px(10), theme.px(_SECRET_DOT_STEP)
        visible = min(len(self.text), max((self.rect.width - 2 * padding) // step, 1))
        x = self.rect.x + padding + step // 2
        for index in range(visible):
            pygame.draw.circle(surface, tokens.INK, (x + index * step, self.rect.centery), theme.px(_SECRET_DOT_RADIUS))
        return self.rect.x + padding + visible * step

    def _draw_caret(self, surface: pygame.Surface, theme: Theme, x: int) -> None:
        if self._time % _CARET_PERIOD > _CARET_PERIOD / 2.0:
            return
        half_height = self.rect.height // 2 - theme.px(8)
        top, bottom = self.rect.centery - half_height, self.rect.centery + half_height
        pygame.draw.line(surface, tokens.INK, (x + 1, top), (x + 1, bottom), theme.px(2))


class Selector:
    """Escolha entre opções, com setas nas pontas. Clique na ponta, ou setas do teclado."""

    def __init__(self, label: str, options: Sequence[tuple[str, object]], index: int = 0,
                 on_change: Callable[[], None] | None = None):
        self.label = label
        self.options = list(options)
        self.index = index
        self.on_change = on_change
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.is_focused = False
        self.advances_on_enter = True

    @property
    def value(self) -> object:
        return self.options[self.index][1]

    @property
    def current_label(self) -> str:
        return self.options[self.index][0]

    def step(self, delta: int) -> None:
        self.select((self.index + delta) % len(self.options))

    def select(self, index: int) -> None:
        changed = index != self.index
        self.index = index
        if changed and self.on_change is not None:
            self.on_change()

    def activate(self) -> None:
        self.step(1)

    def handle_mouse(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1 or not self.rect.collidepoint(event.pos):
            return False
        self._click(event.pos)
        return True

    def _click(self, position: tuple[int, int]) -> None:
        self.step(-1 if position[0] < self.rect.centerx else 1)

    def handle_key(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_LEFT:
            self.step(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_SPACE):
            self.step(1)
        else:
            return False
        return True

    def draw(self, surface: pygame.Surface, theme: Theme) -> None:
        _draw_field_label(surface, theme, self.label, self.rect)
        is_lit = self.is_hovered or self.is_focused
        style = tokens.PLATE_BUTTON_HOVER if is_lit else tokens.PLATE_BUTTON
        surface.blit(theme.plate(self.rect.size, style), self.rect.topleft)
        self._draw_arrows(surface, theme)
        available = max(self.rect.width - theme.px(64), 1)
        text = theme.text_fit(self.current_label, tokens.ROLE_DISPLAY, theme.px(19), tokens.IVORY, available)
        _blit_centered(surface, text, self.rect.center)
        if self.is_focused:
            _draw_focus_ring(surface, theme, self.rect, tokens.PLATE_BUTTON.cut)

    def _draw_arrows(self, surface: pygame.Surface, theme: Theme) -> None:
        inset = theme.px(18)
        radius = theme.px(7)
        y = self.rect.centery
        drawing.draw_arrow(surface, (self.rect.x + inset, y), radius, False, tokens.BRASS_BRIGHT)
        drawing.draw_arrow(surface, (self.rect.right - inset, y), radius, True, tokens.BRASS_BRIGHT)


class SegmentedControl(Selector):
    """Todas as opções à vista, com a escolhida acesa: um clique, sem ciclar. O teclado é o do seletor."""

    def __init__(self, label: str, options: Sequence[tuple[str, object]], index: int = 0,
                 on_change: Callable[[], None] | None = None, font_size: int = 17):
        super().__init__(label, options, index, on_change)
        self.font_size = font_size
        self._hovered_segment: int | None = None

    def segment_rect(self, index: int) -> pygame.Rect:
        width = self.rect.width / len(self.options)
        left = self.rect.x + round(index * width)
        right = self.rect.x + round((index + 1) * width)
        gap = 2 if index < len(self.options) - 1 else 0
        return pygame.Rect(left, self.rect.y, max(right - left - gap, 1), self.rect.height)

    def _segment_at(self, position: tuple[int, int]) -> int | None:
        return next((index for index in range(len(self.options)) if self.segment_rect(index).collidepoint(position)), None)

    def handle_mouse(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered_segment = self._segment_at(event.pos)
        return super().handle_mouse(event)

    def _click(self, position: tuple[int, int]) -> None:
        segment = self._segment_at(position)
        if segment is not None:
            self.select(segment)

    def draw(self, surface: pygame.Surface, theme: Theme) -> None:
        _draw_field_label(surface, theme, self.label, self.rect)
        for index, (label, _) in enumerate(self.options):
            self._draw_segment(surface, theme, index, label)
        if self.is_focused:
            _draw_focus_ring(surface, theme, self.rect, tokens.PLATE_BUTTON.cut)

    def _draw_segment(self, surface: pygame.Surface, theme: Theme, index: int, label: str) -> None:
        rect = self.segment_rect(index)
        if index == self.index:
            plate, color = tokens.PLATE_PRIMARY, tokens.INK
        else:
            plate = tokens.PLATE_BUTTON_HOVER if index == self._hovered_segment else tokens.PLATE_BUTTON
            color = tokens.IVORY
        surface.blit(theme.plate(rect.size, plate), rect.topleft)
        available = max(rect.width - theme.px(8), 1)
        text = theme.text_fit(label, tokens.ROLE_LABEL, theme.px(self.font_size), color, available)
        _blit_centered(surface, text, rect.center)


class TabBar(SegmentedControl):
    """Abas do menu: só o texto, com o filete de latão embaixo da aberta. Hierarquia acima dos campos."""

    def __init__(self, options: Sequence[tuple[str, object]], index: int = 0, on_change: Callable[[], None] | None = None):
        super().__init__("", options, index, on_change)

    def _draw_segment(self, surface: pygame.Surface, theme: Theme, index: int, label: str) -> None:
        rect = self.segment_rect(index)
        is_open = index == self.index
        color = tokens.BRASS_BRIGHT if is_open or index == self._hovered_segment else tokens.TEXT_MUTED
        text = theme.text_fit(label, tokens.ROLE_DISPLAY, theme.px(21), color, max(rect.width - theme.px(8), 1))
        _blit_centered(surface, text, rect.center)
        thickness = theme.px(_TAB_UNDERLINE) if is_open else 1
        line_color = tokens.BRASS if is_open else tokens.WALNUT_EDGE
        pygame.draw.rect(surface, line_color, (rect.x, rect.bottom - thickness, rect.width, thickness))


class FocusGroup:
    """Percorre os controles pelo teclado: Tab e setas verticais movem, Enter confirma."""

    def __init__(self, widgets: Sequence, start: int = 0):
        self.widgets = list(widgets)
        self._index = start
        self._apply_focus()

    @property
    def focused(self):
        return self.widgets[self._index]

    def move(self, delta: int) -> None:
        self._index = (self._index + delta) % len(self.widgets)
        self._apply_focus()

    def focus(self, widget) -> None:
        self._index = self.widgets.index(widget)
        self._apply_focus()

    def set_widgets(self, widgets: Sequence, focused=None) -> None:
        """Troca os controles do grupo, como quando o formulário muda. O foco fica onde pedido, ou no primeiro."""
        for widget in self.widgets:
            widget.is_focused = False
        self.widgets = list(widgets)
        self._index = self.widgets.index(focused) if focused in self.widgets else 0
        self._apply_focus()

    def _apply_focus(self) -> None:
        for position, widget in enumerate(self.widgets):
            widget.is_focused = position == self._index

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event)
        if event.type == pygame.TEXTINPUT:
            return self._handle_text(event)
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return self._handle_mouse(event)
        return False

    def _handle_key(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_TAB:
            self.move(-1 if event.mod & pygame.KMOD_SHIFT else 1)
            return True
        # Uma lista rolável usa as setas verticais para si: sair dela é com Tab.
        if event.key in (pygame.K_UP, pygame.K_DOWN) and not getattr(self.focused, "uses_vertical_keys", False):
            self.move(-1 if event.key == pygame.K_UP else 1)
            return True
        if event.key in _CONFIRM_KEYS and self.focused.advances_on_enter:
            self.move(1)
            return True
        return self.focused.handle_key(event)

    def _handle_text(self, event: pygame.event.Event) -> bool:
        receiver = self.focused
        if not isinstance(receiver, TextInput):
            return False
        receiver.handle_text(event.text)
        return True

    def _handle_mouse(self, event: pygame.event.Event) -> bool:
        consumed = False
        # A lista é copiada porque o clique de um botão pode fechar a tela e trocar os controles.
        for widget in tuple(self.widgets):
            if widget.handle_mouse(event):
                consumed = True
                if event.type == pygame.MOUSEBUTTONDOWN and widget in self.widgets:
                    self.focus(widget)
        return consumed

    def draw(self, surface: pygame.Surface, theme: Theme) -> None:
        for widget in self.widgets:
            widget.draw(surface, theme)
