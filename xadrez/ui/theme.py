"""Paleta e tipografia: a mesa de torneio sob a luz do abajur, aplicada à interface.

Toda cor e toda fonte da interface saem daqui. Os motivos de cada escolha estão em
`docs/plans/notas-ui.md`.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import NamedTuple

import pygame

from xadrez.graphics import CellState
from xadrez.ui import drawing

DESIGN_SIZE = (1280, 720)
MIN_SCALE = 0.6
MAX_SCALE = 2.0
MIN_FONT_SIZE = 10

# Madeira, do mais fundo ao mais próximo da luz.
WALNUT_SHADOW = (23, 16, 11)
WALNUT = (42, 27, 18)
WALNUT_RAISED = (66, 44, 28)
WALNUT_EDGE = (108, 78, 46)

# Latão: o mesmo filete do tabuleiro. É a única cor de destaque do HUD.
BRASS_DARK = (143, 109, 51)
BRASS = (200, 161, 90)
BRASS_BRIGHT = (235, 203, 139)

# Papel e tinta: a planilha de anotação e tudo o que estiver sob a luz.
IVORY = (240, 228, 200)
PAPER = (233, 220, 190)
PAPER_RULE = (199, 182, 148)
PAPER_MARGIN = (186, 112, 92)
INK = (36, 23, 14)
INK_SOFT = (84, 58, 30)

TEXT_MUTED = (201, 184, 154)

# Alertas: a forma acompanha a cor, nunca só a cor (RNF04).
ALERT_ON_DARK = (255, 138, 112)
ALERT_ON_LIGHT = (140, 24, 14)
ALERT_PLATE = (150, 36, 26)
WARNING_ICON = (240, 150, 52)

LAMP_GLOW = (255, 186, 104)
DIM_VEIL = (14, 9, 6)

# O tema entra na matriz de cores: tons deslocados para o quente, como sob a luz do abajur.
BOARD_STATE_PALETTE = {
    CellState.LAST_MOVE: (198, 172, 84),
    CellState.PATH: (92, 172, 108),
    CellState.CAPTURE: (216, 78, 60),
    CellState.THREAT: (236, 138, 44),
    CellState.CHECK: (224, 44, 44),
    CellState.SELECTED: (244, 206, 96),
    CellState.CURSOR: (104, 170, 222),
}
STATE_TEXT_COLORS = {
    CellState.NONE: TEXT_MUTED,
    CellState.LAST_MOVE: (226, 202, 120),
    CellState.PATH: (130, 214, 146),
    CellState.CAPTURE: (255, 132, 112),
    CellState.THREAT: (255, 176, 90),
    CellState.CHECK: (255, 104, 104),
    CellState.SELECTED: (255, 226, 130),
    CellState.CURSOR: (140, 200, 250),
}

MARKER_PATH_COLOR = (34, 92, 54)
MARKER_CAPTURE_COLOR = (136, 26, 20)
MARKER_THREAT_COLOR = (122, 60, 8)
MARKER_CHECK_COLOR = (120, 14, 14)
MARKER_SELECTED_COLOR = (112, 78, 10)
MARKER_CURSOR_COLOR = (16, 52, 104)
MARKER_REFUSED_COLOR = (196, 40, 28)

THREAT_TINT = (255, 122, 34)
CHECK_TINT = (255, 28, 28)
MOVE_TRAIL_COLOR = (255, 214, 140)
FIREWORK_COLORS = ((255, 214, 110), (255, 112, 84), (128, 196, 255), (255, 240, 205))
NEUTRAL_FIREWORK_COLORS = ((150, 138, 116), (118, 104, 84))

ROLE_DISPLAY = "display"
ROLE_SERIF = "serif"
ROLE_LABEL = "label"
ROLE_NUMERIC = "numeric"
ROLE_MONO = "mono"

_SERIF_FAMILIES = (
    "palatinolinotype", "bookantiqua", "palatino", "p052", "urwpalladiol", "texgyrepagella",
    "georgia", "dejavuserif", "liberationserif", "timesnewroman",
)
_SANS_FAMILIES = (
    "franklingothicmedium", "helveticaneue", "avenirnext", "notosans", "dejavusans", "liberationsans",
    "tahoma", "verdana",
)
_MONO_FAMILIES = ("consolas", "menlo", "dejavusansmono", "liberationmono", "lucidaconsole", "couriernew")
_FONT_STACKS = {
    ROLE_DISPLAY: (_SERIF_FAMILIES, True),
    ROLE_SERIF: (_SERIF_FAMILIES, False),
    ROLE_LABEL: (_SANS_FAMILIES, False),
    ROLE_NUMERIC: (_SANS_FAMILIES, True),
    ROLE_MONO: (_MONO_FAMILIES, False),
}
# A fonte padrão do pygame desenha menor que as do sistema no mesmo tamanho nominal.
_DEFAULT_FONT_GROWTH = 1.25
_TABULAR_DIGITS = "0123456789"
_TEXT_CACHE_LIMIT = 1600
# Área de uso privado do Unicode: a fonte não tem, então sai o glifo de substituição dela.
_MISSING_GLYPH_PROBE = chr(0xE000)
_PLATE_CACHE_LIMIT = 320
_WRAP_CACHE_LIMIT = 256


class PlateStyle(NamedTuple):
    """Placa de cantos cortados, a forma comum do HUD: lembra as facetas das peças low-poly."""

    top: tuple[int, int, int]
    bottom: tuple[int, int, int]
    border: tuple[int, int, int] | None = None
    cut: int = 8


PLATE_LIT = PlateStyle((247, 224, 170), (222, 182, 110), BRASS_DARK, 10)
PLATE_SHADE = PlateStyle((50, 33, 22), (34, 22, 15), WALNUT_EDGE, 10)
PLATE_BUTTON = PlateStyle(WALNUT_RAISED, (50, 33, 21), WALNUT_EDGE, 6)
PLATE_BUTTON_HOVER = PlateStyle((92, 62, 38), (70, 47, 29), BRASS, 6)
PLATE_PRIMARY = PlateStyle((243, 214, 150), (214, 170, 96), BRASS_DARK, 6)
PLATE_PRIMARY_HOVER = PlateStyle((252, 232, 180), (232, 194, 122), BRASS, 6)
PLATE_DANGER = PlateStyle((142, 48, 34), (110, 34, 26), (190, 92, 70), 6)
PLATE_DANGER_HOVER = PlateStyle((172, 62, 44), (136, 44, 32), (226, 122, 96), 6)
PLATE_INPUT = PlateStyle(PAPER, (222, 206, 172), BRASS_DARK, 6)
PLATE_INPUT_FOCUS = PlateStyle((250, 240, 214), PAPER, BRASS, 6)
PLATE_KEYCAP = PlateStyle((238, 226, 198), (206, 190, 156), BRASS_DARK, 3)
PLATE_MODAL = PlateStyle((62, 41, 26), (38, 25, 17), BRASS, 14)
PLATE_LIGHT_TRAY = PlateStyle((238, 226, 198), (216, 200, 166), BRASS_DARK, 4)
PLATE_DARK_TRAY = PlateStyle((70, 46, 30), (52, 34, 22), BRASS_DARK, 4)
PLATE_NOTICE_TURN = PlateStyle((62, 41, 26), (42, 28, 18), BRASS, 8)
PLATE_NOTICE_WARNING = PlateStyle((247, 224, 170), (226, 190, 120), BRASS_DARK, 8)
PLATE_NOTICE_DANGER = PlateStyle((176, 50, 36), ALERT_PLATE, (236, 150, 124), 8)
PLATE_TAG_TURN = PlateStyle((60, 40, 24), INK, None, 4)
PLATE_TAG_CHECK = PlateStyle((176, 50, 36), ALERT_PLATE, None, 4)
PLATE_DEBUG = PlateStyle((30, 20, 14), (22, 15, 10), WALNUT_EDGE, 6)
PLATE_PAPER = PlateStyle(PAPER, (224, 210, 178), PAPER_RULE, 1)
PLATE_DISABLED = PlateStyle((50, 34, 22), (42, 28, 18), WALNUT_RAISED, 6)


def window_scale(size: tuple[int, int]) -> float:
    """Fator entre a janela e o tamanho de projeto. A menor proporção manda, para tudo caber."""
    ratio = min(size[0] / DESIGN_SIZE[0], size[1] / DESIGN_SIZE[1])
    return max(MIN_SCALE, min(ratio, MAX_SCALE))


def _find_font_path(role: str) -> str | None:
    families, is_bold = _FONT_STACKS[role]
    for family in families:
        path = pygame.font.match_font(family, bold=is_bold)
        if path:
            return path
    return None


class Theme:
    """Fontes, texto renderizado e placas, com cache: `font.render` é caro demais para cada quadro."""

    def __init__(self) -> None:
        self.scale = 1.0
        self._font_paths: dict[str, str | None] = {}
        self._fonts: dict[tuple[str, int], pygame.font.Font] = {}
        self._texts: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._glyphs: dict[tuple, bool] = {}
        self._plates: dict[tuple, pygame.Surface] = {}
        self._grounds: dict[tuple[int, int], pygame.Surface] = {}
        self._wrapped: dict[tuple, tuple[str, ...]] = {}

    def set_window_size(self, size: tuple[int, int]) -> None:
        self.scale = window_scale(size)
        self._grounds.clear()

    def px(self, value: float) -> int:
        """Converte uma medida do tamanho de projeto para pixels desta janela."""
        return max(1, round(value * self.scale))

    def font(self, role: str, size: int) -> pygame.font.Font:
        size = max(size, MIN_FONT_SIZE)
        font = self._fonts.get((role, size))
        if font is None:
            font = self._fonts[(role, size)] = self._load_font(role, size)
        return font

    def _load_font(self, role: str, size: int) -> pygame.font.Font:
        if role not in self._font_paths:
            self._font_paths[role] = _find_font_path(role)
        path = self._font_paths[role]
        try:
            if path is not None:
                font = pygame.font.Font(path, size)
                # Arquivo de fonte corrompido abre sem reclamar e só falha ao desenhar.
                font.render("A", True, (0, 0, 0))
                return font
        except (OSError, pygame.error):
            self._font_paths[role] = None
        font = pygame.font.Font(None, round(size * _DEFAULT_FONT_GROWTH))
        font.set_bold(_FONT_STACKS[role][1])
        return font

    def text(self, content: str, role: str, size: int, color: tuple) -> pygame.Surface:
        key = (content, role, size, color)
        surface = self._texts.get(key)
        if surface is not None:
            self._texts.move_to_end(key)
            return surface
        font = self.font(role, size)
        # Texto sem largura (vazio ou só com seletor de variação) faz o `render` levantar erro.
        surface = font.render(content if font.size(content)[0] > 0 else " ", True, color)
        return self._remember_text(key, surface)

    def _remember_text(self, key: tuple, surface: pygame.Surface) -> pygame.Surface:
        self._texts[key] = surface
        if len(self._texts) > _TEXT_CACHE_LIMIT:
            self._texts.popitem(last=False)
        return surface

    def text_fit(self, content: str, role: str, size: int, color: tuple, max_width: int) -> pygame.Surface:
        """Diminui a fonte até o texto caber. No limite, corta com reticências, mas não vaza."""
        fitted_size = self._size_that_fits(content, role, size, max_width)
        font = self.font(role, fitted_size)
        if font.size(content)[0] <= max_width:
            return self.text(content, role, fitted_size, color)
        return self.text(_ellipsize(content, font, max_width), role, fitted_size, color)

    def _size_that_fits(self, content: str, role: str, size: int, max_width: int) -> int:
        minimum = max(MIN_FONT_SIZE, round(size * 0.66))
        while size > minimum and self.font(role, size).size(content)[0] > max_width:
            size -= 1
        return size

    def wrap(self, content: str, role: str, size: int, max_width: int) -> tuple[str, ...]:
        """Quebra o texto em linhas que cabem na largura. Quebra de linha do texto é respeitada."""
        key = (content, role, size, max_width)
        lines = self._wrapped.get(key)
        if lines is None:
            if len(self._wrapped) >= _WRAP_CACHE_LIMIT:
                self._wrapped.clear()
            font = self.font(role, size)
            lines = self._wrapped[key] = tuple(
                line for paragraph in content.split("\n") for line in _wrap_paragraph(paragraph, font, max(max_width, 1))
            )
        return lines

    def tabular(self, content: str, role: str, size: int, color: tuple) -> pygame.Surface:
        """Números em células de largura igual, para o relógio não tremer quando um dígito muda."""
        key = ("tabular", content, role, size, color)
        surface = self._texts.get(key)
        if surface is not None:
            self._texts.move_to_end(key)
            return surface
        return self._remember_text(key, self._render_tabular(content, role, size, color))

    def _render_tabular(self, content: str, role: str, size: int, color: tuple) -> pygame.Surface:
        font = self.font(role, size)
        cell = max(font.size(digit)[0] for digit in _TABULAR_DIGITS)
        widths = [cell if char in _TABULAR_DIGITS else font.size(char)[0] for char in content]
        surface = pygame.Surface((max(sum(widths), 1), font.get_height()), pygame.SRCALPHA)
        x = 0
        for char, width in zip(content, widths):
            glyph = self.text(char, role, size, color)
            surface.blit(glyph, (x + (width - glyph.get_width()) // 2, 0))
            x += width
        return surface

    def has_glyph(self, char: str, role: str, size: int) -> bool:
        """Diz se a fonte desenha o caractere, para não aceitar nome que viraria quadradinho.

        `font.metrics` devolve as medidas do glifo de substituição, então não serve para saber. A
        comparação é com o desenho de um caractere que nenhuma fonte de texto comum tem.
        """
        key = (char, role, size)
        if key not in self._glyphs:
            self._glyphs[key] = _draws_own_glyph(self.font(role, size), char)
        return self._glyphs[key]

    def plate(self, size: tuple[int, int], style: PlateStyle) -> pygame.Surface:
        key = (size, style, self.scale)
        plate = self._plates.get(key)
        if plate is None:
            if len(self._plates) >= _PLATE_CACHE_LIMIT:
                self._plates.clear()
            plate = drawing.render_plate(size, style.top, style.bottom, style.border, self.px(style.cut))
            self._plates[key] = plate
        return plate

    def panel_ground(self, size: tuple[int, int]) -> pygame.Surface:
        """Chão de nogueira dos painéis, pronto: gerar a textura custa dezenas de milissegundos."""
        ground = self._grounds.get(size)
        if ground is None:
            ground = self._grounds[size] = drawing.render_panel_ground(size)
            drawing.draw_inlay_line(ground, 0, ground.get_height(), self.px(2), WALNUT_SHADOW, BRASS)
        return ground

    def outline(self, size: tuple[int, int], color: tuple, cut: int) -> pygame.Surface:
        key = ("outline", size, color, cut, self.scale)
        outline = self._plates.get(key)
        if outline is None:
            outline = self._plates[key] = drawing.render_outline(size, color, self.px(cut), self.px(2))
        return outline


def _draws_own_glyph(font: pygame.font.Font, char: str) -> bool:
    if char.isspace():
        return True
    metrics = font.metrics(char)
    if not metrics or metrics[0] is None or font.size(char)[0] == 0:
        return False
    return _glyph_pixels(font, char) != _glyph_pixels(font, _MISSING_GLYPH_PROBE)


def _glyph_pixels(font: pygame.font.Font, char: str) -> bytes:
    return pygame.image.tobytes(font.render(char, False, (255, 255, 255)), "RGBA")


def _wrap_paragraph(paragraph: str, font: pygame.font.Font, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in paragraph.split():
        candidate = f"{current} {word}" if current else word
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        pieces = _split_long_word(word, font, max_width)
        lines.extend(pieces[:-1])
        current = pieces[-1]
    lines.append(current)
    return lines


def _split_long_word(word: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Uma palavra maior que a linha, como o FEN em janela estreita, é cortada onde couber."""
    pieces: list[str] = []
    current = ""
    for char in word:
        if current and font.size(current + char)[0] > max_width:
            pieces.append(current)
            current = ""
        current += char
    pieces.append(current)
    return pieces


def _ellipsize(content: str, font: pygame.font.Font, max_width: int) -> str:
    for end in range(len(content) - 1, 0, -1):
        candidate = f"{content[:end].rstrip()}..."
        if font.size(candidate)[0] <= max_width:
            return candidate
    return "..."
