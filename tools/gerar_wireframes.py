"""Gera os wireframes de baixa fidelidade das telas exigidas e das telas da versão 1.1, em tons de cinza.

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
FORM_X = 832
FORM_WIDTH = 418
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

    def segments(self, top: int, caption: str, labels: tuple[str, ...], active: int) -> None:
        """Controle segmentado: todas as opções à vista, com a escolhida mais escura."""
        x, width = FORM_X, FORM_WIDTH
        self.small_caption(x, top - 24, caption)
        step = width / len(labels)
        for index, label in enumerate(labels):
            area = (round(x + index * step), top, round(step) - 4, 40)
            self.box(area, label, fill=STRONG_BOX if index == active else BOX, size=SMALL_SIZE - 2)

    def small_caption(self, x: int, y: int, caption: str) -> None:
        self.surface.blit(self._font(SMALL_SIZE - 3, False).render(caption, True, HINT), (x, y))

    def note(self, top: int, content: str) -> None:
        self.small_caption(FORM_X, top, content)

    def table_scene(self) -> None:
        """A mesa ao fundo, a mesma em todas as telas fora da partida."""
        self.box((0, 0, FORM_LEFT, SIZE[1]), fill=AREA)
        self.text("Mesa 3D ao vivo", (FORM_LEFT // 2, 320), 34, bold=True)
        self.text("a mesma em todas as telas fora da partida", (FORM_LEFT // 2, 366), LABEL_SIZE, color=HINT)

    def save(self, name: str) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{name}.png"
        pygame.image.save(self.surface, str(path))
        print("salvo", path)


def _menu_header(sketch: Sketch, active_opponent: int, active_tab_label: str = "Jogar") -> None:
    x, width = FORM_X, FORM_WIDTH
    half = width // 2
    sketch.text("Título do jogo", (x + width // 2, 34), 34, bold=True)
    sketch.note(68, "Quem está jogando, e o botão de conta")
    for index, label in enumerate(("Jogar", "Meu histórico")):
        sketch.box((x + index * half, 92, half, 34), label, size=SMALL_SIZE - 2, bold=label == active_tab_label,
                   fill=STRONG_BOX if label == active_tab_label else BOX)
    if active_tab_label == "Jogar":
        sketch.segments(160, "Adversário", ("2 jogadores", "CPU", "Rede local"), active_opponent)
        sketch.segments(226, "Modo", ("Treinamento", "Partida"), 0)
        sketch.note(270, "Frase que explica o modo escolhido")


def _menu_footer(sketch: Sketch) -> None:
    sketch.box((FORM_X, 672, 312, 34), "Ver todos os controles", size=SMALL_SIZE - 3)
    sketch.box((FORM_X + 326, 672, 92, 34), "Sair", size=SMALL_SIZE - 3)


def draw_menu() -> None:
    sketch = Sketch()
    sketch.table_scene()
    x, width = FORM_X, FORM_WIDTH
    half = (width - 14) // 2
    _menu_header(sketch, 0)
    sketch.field((x, 336, half, 40), "Brancas", "Nome do Jogador 1")
    sketch.field((x + half + 14, 336, half, 40), "Pretas", "Nome do Jogador 2")
    sketch.field((x, 402, width, 40), "Tempo por jogador", "<  Seleção: tempo  >")
    sketch.field((x, 468, width, 40), "Câmera", "<  Seleção: câmera  >")
    sketch.box((x, 522, width, 50), "Iniciar partida", fill=STRONG_BOX, bold=True)
    _menu_footer(sketch)
    sketch.save("wireframe_menu")


def draw_menu_cpu() -> None:
    sketch = Sketch()
    sketch.table_scene()
    x, width = FORM_X, FORM_WIDTH
    _menu_header(sketch, 1)
    sketch.segments(336, "Nível", ("Easy", "Medium", "Hard", "Hardcore"), 0)
    sketch.note(380, "Frase que explica o nível escolhido")
    sketch.segments(446, "Sua cor", ("Brancas", "Pretas", "Sorteio"), 0)
    sketch.field((x, 512, width, 40), "Tempo por jogador", "<  Seleção: tempo  >")
    sketch.box((x, 566, width, 50), "Iniciar partida", fill=STRONG_BOX, bold=True)
    _menu_footer(sketch)
    sketch.save("wireframe_menu_cpu")


def draw_login() -> None:
    sketch = Sketch()
    sketch.table_scene()
    x, width = FORM_X, FORM_WIDTH
    sketch.text("Título do jogo", (x + width // 2, 46), 38, bold=True)
    sketch.note(88, "Para que serve a conta")
    half = width // 2
    sketch.box((x, 142, half - 2, 40), "Entrar", size=SMALL_SIZE - 2, fill=STRONG_BOX)
    sketch.box((x + half + 2, 142, half - 2, 40), "Criar conta", size=SMALL_SIZE - 2)
    sketch.field((x, 208, width, 44), "Usuário", "De 3 a 16 caracteres")
    sketch.field((x, 278, width, 44), "Senha", "Pontos, nunca o texto")
    sketch.note(330, "Erro, com triângulo e texto, sem mudar o resto de lugar")
    sketch.box((x, 380, width, 52), "Entrar", fill=STRONG_BOX, bold=True)
    sketch.box((x, 462, width, 44), "Jogar como convidado", size=SMALL_SIZE)
    sketch.note(514, "Como convidado, as partidas não ficam guardadas")
    sketch.note(546, "As contas ficam só neste computador")
    sketch.box((x, 598, width, 36), "Sair do jogo", size=SMALL_SIZE - 2)
    sketch.save("wireframe_login")


def draw_room() -> None:
    sketch = Sketch()
    sketch.table_scene()
    x, width = FORM_X, FORM_WIDTH
    sketch.text("Criar sala em rede", (x + width // 2, 40), 34, bold=True)
    sketch.note(104, "Passe este código para quem vai jogar com você")
    sketch.box((x, 130, width, 104), "Código da sala\nde 7 caracteres", fill=STRONG_BOX, size=32, bold=True)
    sketch.box((x, 248, width, 46), "Copiar convite", size=SMALL_SIZE)
    sketch.note(306, "Tempo escolhido e a cor de quem criou a sala")
    sketch.note(332, "Modo e tempo valem para os dois, na mesma rede local")
    sketch.text("Aguardando adversário...", (x + width // 2, 378), LABEL_SIZE, bold=True)
    sketch.box((x, 422, width, 42), "Cancelar e voltar", size=SMALL_SIZE)
    sketch.save("wireframe_sala")


def draw_join_room() -> None:
    sketch = Sketch()
    sketch.table_scene()
    x, width = FORM_X, FORM_WIDTH
    sketch.text("Entrar em uma sala", (x + width // 2, 40), 34, bold=True)
    sketch.note(104, "Digite o código que o outro jogador passou")
    sketch.field((x, 160, width, 56), "Código da sala", "7 letras e números")
    sketch.box((x, 230, width, 50), "Entrar na sala", fill=STRONG_BOX, bold=True)
    sketch.note(298, "Conectando, ou o erro em português, com triângulo")
    sketch.box((x, 372, width, 42), "Cancelar e voltar", size=SMALL_SIZE)
    sketch.save("wireframe_entrar_sala")


def draw_history() -> None:
    sketch = Sketch()
    sketch.table_scene()
    x, width = FORM_X, FORM_WIDTH
    _menu_header(sketch, 0, "Meu histórico")
    for index, label in enumerate(("Partidas", "Vitórias", "Derrotas", "Empates")):
        sketch.box((x + index * 106, 142, 100, 58), label, size=SMALL_SIZE - 4)
    for row in range(7):
        top = 212 + row * 63
        sketch.box((x, top, width - 10, 58), "Resultado, adversário e data\nmodo, cor, lances e duração", size=SMALL_SIZE - 5)
    _menu_footer(sketch)
    sketch.box((26, 26, 748, 668), fill=PAPER)
    sketch.text("Resultado contra o adversário", (400, 60), 30, bold=True)
    sketch.text("Motivo do fim", (400, 96), SMALL_SIZE)
    sketch.box((50, 120, 700, 60), "Data, tempo, modo, cor, lances e duração", size=SMALL_SIZE - 2, fill=AREA)
    sketch.box((50, 192, 700, 340), "Lances da partida em SAN\ncom rolagem pela roda do mouse", size=SMALL_SIZE, fill=PAPER)
    sketch.box((50, 544, 700, 60), "Posição final em FEN", size=SMALL_SIZE - 2, fill=AREA)
    sketch.box((50, 630, 340, 40), "Copiar PGN", size=SMALL_SIZE - 2, fill=STRONG_BOX)
    sketch.box((410, 630, 340, 40), "Fechar", size=SMALL_SIZE - 2)
    sketch.save("wireframe_historico")


HUD_BUTTONS = ("Pausar", "Giro", "Vista padrão", "Ajuda", "Virar", "Copiar PGN")


def _match_panel(sketch: Sketch) -> None:
    sketch.player_card(12, "Jogador 2", is_active=False)
    sketch.box((976, 172, 292, 200), "Planilha de lances\nem notação SAN", size=SMALL_SIZE + 1, fill=PAPER)
    sketch.small_caption(976, 378, "Modo e tempo da partida")
    sketch.player_card(404, "Jogador 1", is_active=True)
    for index, label in enumerate(HUD_BUTTONS):
        row, column = divmod(index, 2)
        sketch.box((976 + column * 148, 566 + row * 37, 144, 32), label, size=SMALL_SIZE - 4)
    sketch.box((976, 677, 292, 32), "Desistir", size=SMALL_SIZE - 4)


def draw_match() -> None:
    sketch = Sketch()
    sketch.box((0, 0, BOARD_AREA_WIDTH, SIZE[1]), fill=AREA)
    sketch.board((110, 110, 740, 520))
    sketch.box((270, 12, 420, 42), "Indicador de vez e avisos", fill=PAPER, bold=True)
    sketch.text("Área jogável: tabuleiro 3D", (BOARD_AREA_WIDTH // 2, 670), LABEL_SIZE, bold=True)
    _match_panel(sketch)
    sketch.save("wireframe_partida")


def draw_match_mode() -> None:
    sketch = Sketch()
    sketch.box((0, 0, BOARD_AREA_WIDTH, SIZE[1]), fill=AREA)
    sketch.board((110, 110, 740, 520))
    sketch.box((270, 12, 420, 42), "De quem é a vez, sem aviso de xeque", fill=PAPER, bold=True, size=SMALL_SIZE)
    sketch.box((130, 640, 700, 66), "Só peça selecionada, cursor e último lance\nsem caminhos, capturas, ameaças ou xeque", fill=PAPER, size=SMALL_SIZE)
    _match_panel(sketch)
    sketch.save("wireframe_modo_partida")


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
    sketch.box((x, 527, 142, 44), "Voltar ao menu", size=SMALL_SIZE - 3)
    sketch.box((x + 150, 527, 142, 44), "Copiar PGN", size=SMALL_SIZE - 3)
    sketch.save("wireframe_fim_de_jogo")


def main() -> None:
    pygame.init()
    draw_login()
    draw_menu()
    draw_menu_cpu()
    draw_room()
    draw_join_room()
    draw_history()
    draw_match()
    draw_match_mode()
    draw_game_over()
    pygame.quit()


if __name__ == "__main__":
    main()
