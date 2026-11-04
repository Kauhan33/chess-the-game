"""Gera os wireframes de baixa fidelidade das três telas exigidas, em tons de cinza.

Uso: python tools/gerar_wireframes.py
Resultado: docs/img/wireframes/. As áreas seguem o layout real em 1280x720, mas sem cor nem acabamento:
o wireframe mostra a organização da tela. O visual final está nos prints de docs/img/.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "docs" / "img" / "wireframes"
SIZE = (1280, 720)
BOARD_AREA_WIDTH = 960
FORM_LEFT = 800
FONT_NAMES = "segoeui,dejavusans,liberationsans,arial"

PAPER = (250, 250, 250)
AREA = (232, 232, 232)
BOX = (214, 214, 214)
STRONG_BOX = (176, 176, 176)
LINE = (70, 70, 70)
TEXT = (30, 30, 30)
HINT = (110, 110, 110)
BOARD_CELLS = 8
LABEL_SIZE = 25
SMALL_SIZE = 21


class Sketch:
    """Folha de desenho com as poucas formas que um wireframe precisa."""

    def __init__(self) -> None:
        self.surface = pygame.Surface(SIZE)
        self.surface.fill(PAPER)
        self._fonts: dict[tuple[int, bool], pygame.font.Font] = {}

    def _font(self, size: int, bold: bool) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont(FONT_NAMES, size, bold=bold)
        return self._fonts[key]

    def text(self, content: str, center: tuple[int, int], size: int = LABEL_SIZE, bold: bool = False,
             color: tuple = TEXT) -> None:
        image = self._font(size, bold).render(content, True, color)
        self.surface.blit(image, image.get_rect(center=center))

    def box(self, rect: tuple[int, int, int, int], label: str = "", fill: tuple = BOX, size: int = LABEL_SIZE,
            bold: bool = False) -> None:
        area = pygame.Rect(rect)
        pygame.draw.rect(self.surface, fill, area)
        pygame.draw.rect(self.surface, LINE, area, 2)
        for index, line in enumerate(label.split("\n")):
            offset = (index - (label.count("\n")) / 2) * (size + 6)
            self.text(line, (area.centerx, round(area.centery + offset)), size, bold)

    def field(self, rect: tuple[int, int, int, int], caption: str, content: str) -> None:
        x, y, _, _ = rect
        image = self._font(SMALL_SIZE, False).render(caption, True, HINT)
        self.surface.blit(image, (x, y - image.get_height() - 1))
        self.box(rect, content, size=SMALL_SIZE + 1)

    def board(self, area: tuple[int, int, int, int]) -> None:
        """Tabuleiro 8x8 em perspectiva: basta um trapézio com a grade para indicar a área jogável."""
        x, y, width, height = area
        top_inset = width * 0.14
        left_edge = [(x + top_inset * (1 - row / BOARD_CELLS), y + height * row / BOARD_CELLS)
                     for row in range(BOARD_CELLS + 1)]
        right_edge = [(x + width - left[0] + x, left[1]) for left in left_edge]
        for row in range(BOARD_CELLS):
            for column in range(BOARD_CELLS):
                if (row + column) % 2 == 0:
                    pygame.draw.polygon(self.surface, STRONG_BOX, self._cell(left_edge, right_edge, row, column))
        for left, right in zip(left_edge, right_edge):
            pygame.draw.line(self.surface, LINE, left, right, 2)
        for column in range(BOARD_CELLS + 1):
            top = self._lerp(left_edge[0], right_edge[0], column / BOARD_CELLS)
            bottom = self._lerp(left_edge[-1], right_edge[-1], column / BOARD_CELLS)
            pygame.draw.line(self.surface, LINE, top, bottom, 2)

    def _cell(self, left_edge: list, right_edge: list, row: int, column: int) -> list:
        return [
            self._lerp(left_edge[row], right_edge[row], column / BOARD_CELLS),
            self._lerp(left_edge[row], right_edge[row], (column + 1) / BOARD_CELLS),
            self._lerp(left_edge[row + 1], right_edge[row + 1], (column + 1) / BOARD_CELLS),
            self._lerp(left_edge[row + 1], right_edge[row + 1], column / BOARD_CELLS),
        ]

    @staticmethod
    def _lerp(start: tuple, end: tuple, t: float) -> tuple[float, float]:
        return start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t

    def player_card(self, top: int, name: str, is_active: bool) -> None:
        """Placa de jogador: nome, pontos, relógio e capturas. A placa da vez é mais escura."""
        left, width = 976, 292
        self.box((left, top, width, 152), fill=STRONG_BOX if is_active else BOX)
        self.text(name, (left + 92, top + 22), SMALL_SIZE + 1, bold=True)
        self.text("Pontuação", (left + 236, top + 22), SMALL_SIZE - 1)
        self.text("Cronômetro", (left + 88, top + 72), LABEL_SIZE + 3, bold=True)
        if is_active:
            self.box((left + 182, top + 56, 98, 32), "Joga agora", size=SMALL_SIZE - 4, fill=PAPER)
        self.box((left + 12, top + 112, 268, 30), "Peças capturadas", size=SMALL_SIZE - 3, fill=PAPER)

    def save(self, name: str) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{name}.png"
        pygame.image.save(self.surface, str(path))
        print("salvo", path)


def draw_menu() -> None:
    sketch = Sketch()
    sketch.box((0, 0, FORM_LEFT, SIZE[1]), fill=AREA)
    sketch.text("Cena 3D ao vivo", (FORM_LEFT // 2, 320), 34, bold=True)
    sketch.text("peças low-poly, com a câmera girando devagar", (FORM_LEFT // 2, 366), LABEL_SIZE, color=HINT)
    x, width = 832, 418
    half = (width - 14) // 2
    sketch.text("Título do jogo", (x + width // 2, 46), 38, bold=True)
    sketch.text("Frase de apresentação", (x + width // 2, 96), SMALL_SIZE, color=HINT)
    sketch.field((x, 142, half, 44), "Brancas", "Nome do Jogador 1")
    sketch.field((x + half + 14, 142, half, 44), "Pretas", "Nome do Jogador 2")
    sketch.field((x, 216, width, 44), "Tempo por jogador", "<  Seleção de modo: tempo  >")
    sketch.field((x, 290, width, 44), "Câmera", "<  Seleção de modo: câmera  >")
    sketch.box((x, 352, width, 54), "Iniciar partida", fill=STRONG_BOX, bold=True)
    sketch.box((x, 415, width, 36), "Ver todos os controles", size=SMALL_SIZE)
    sketch.box((x, 466, width, 150), "Resumo dos controles\nmouse e teclado", size=SMALL_SIZE, fill=PAPER)
    sketch.save("wireframe_menu")


def draw_match() -> None:
    sketch = Sketch()
    sketch.box((0, 0, BOARD_AREA_WIDTH, SIZE[1]), fill=AREA)
    sketch.board((110, 110, 740, 520))
    sketch.box((270, 12, 420, 42), "Indicador de vez e avisos", fill=PAPER, bold=True)
    sketch.text("Área jogável: tabuleiro 3D", (BOARD_AREA_WIDTH // 2, 670), LABEL_SIZE, bold=True)
    sketch.player_card(12, "Jogador 2", is_active=False)
    sketch.box((976, 172, 292, 290), "Planilha de lances\nem notação SAN", size=SMALL_SIZE + 1, fill=PAPER)
    sketch.player_card(470, "Jogador 1", is_active=True)
    for (x, y), label in zip(((976, 630), (1124, 630), (976, 672), (1124, 672)),
                             ("Pausar", "Giro", "Vista padrão", "Ajuda")):
        sketch.box((x, y, 144, 36), label, size=SMALL_SIZE - 2)
    sketch.save("wireframe_partida")


def draw_game_over() -> None:
    sketch = Sketch()
    sketch.box((0, 0, BOARD_AREA_WIDTH, SIZE[1]), fill=AREA)
    sketch.board((130, 110, 700, 490))
    sketch.text("Posição final com fogos de vitória", (BOARD_AREA_WIDTH // 2, 650), LABEL_SIZE, bold=True)
    x, width = 976, 292
    sketch.box((x, 100, width, 216), fill=STRONG_BOX)
    sketch.text("1 - 0", (x + width // 2, 150), 48, bold=True)
    sketch.text("Vencedor", (x + width // 2, 218), 28, bold=True)
    sketch.text("Motivo do fim", (x + width // 2, 262), SMALL_SIZE + 1)
    sketch.text("Número de lances", (x + width // 2, 290), SMALL_SIZE - 2)
    sketch.box((x, 328, width, 124), "Placar da série\nJogador 1 e Jogador 2", size=SMALL_SIZE + 1)
    sketch.box((x, 464, width, 54), "Revanche com cores trocadas", size=SMALL_SIZE - 2, fill=STRONG_BOX, bold=True)
    sketch.box((x, 527, width, 44), "Voltar ao menu", size=SMALL_SIZE + 1)
    sketch.save("wireframe_fim_de_jogo")


def main() -> None:
    pygame.init()
    draw_menu()
    draw_match()
    draw_game_over()
    pygame.quit()


if __name__ == "__main__":
    main()
