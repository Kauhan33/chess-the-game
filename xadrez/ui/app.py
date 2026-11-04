"""Aplicação: janela, relógio de 60 FPS e troca de cenas."""
from __future__ import annotations

import ctypes
import sys
import time

import pygame

from xadrez.core import GameEngine
from xadrez.graphics import IVORY, build_piece_meshes
from xadrez.ui.board_view import BoardView
from xadrez.ui.game_over_scene import GameOverScene
from xadrez.ui.game_scene import GameScene
from xadrez.ui.match import MatchOptions
from xadrez.ui.menu_scene import MenuScene
from xadrez.ui.scene import Scene
from xadrez.ui.theme import Theme

WINDOW_SIZE = (1280, 720)
WINDOW_TITLE = "Xadrez The Game"
FPS = 60
# Quadro mais longo que isso (janela arrastada, por exemplo) não pode virar salto de relógio e animação.
MAX_FRAME_SECONDS = 0.1
_FRAME_SMOOTHING = 0.1
_WINDOW_ICON_SIZE = 64


def _enable_dpi_awareness() -> None:
    """No Windows com escala de tela, sem isto a janela fica borrada e o mouse desalinhado."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


class App:
    def __init__(self, size: tuple[int, int] = WINDOW_SIZE, seed: int | None = None):
        _enable_dpi_awareness()
        pygame.init()
        self._flags = pygame.RESIZABLE
        self.seed = seed
        self.screen = pygame.display.set_mode(size, self._flags)
        self.size = self.screen.get_size()
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.theme = Theme()
        self.theme.set_window_size(self.size)
        self.meshes = build_piece_meshes()
        self.running = True
        self.fps = 0.0
        self.frame_ms = 0.0
        self.scene: Scene = self.menu_scene()
        self._set_window_icon()

    def _set_window_icon(self) -> None:
        icon = self.scene.renderer.render_icon(self.meshes["knight"], IVORY, _WINDOW_ICON_SIZE)
        pygame.display.set_icon(icon)

    # As cenas se chamam em ciclo (menu, partida e fim). Passar pelo App evita importação circular.

    def menu_scene(self, defaults: MatchOptions | None = None) -> MenuScene:
        return MenuScene(self, defaults)

    def game_scene(self, engine: GameEngine, options: MatchOptions, view: BoardView | None = None) -> GameScene:
        return GameScene(self, engine, options, view)

    def game_over_scene(self, engine: GameEngine, options: MatchOptions, view: BoardView) -> GameOverScene:
        return GameOverScene(self, engine, options, view)

    def step(self, dt: float) -> None:
        """Um quadro completo e determinístico: eventos, tempo e desenho. Quem chama controla o `dt`."""
        started = time.perf_counter()
        for event in pygame.event.get():
            self._dispatch(event)
        self._follow_window_size()
        self.scene.update(min(max(dt, 0.0), MAX_FRAME_SECONDS))
        self._apply_scene_change()
        self.scene.draw(self.screen)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.frame_ms += (elapsed_ms - self.frame_ms) * _FRAME_SMOOTHING

    def _dispatch(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self._apply_resize(event.size)
        else:
            self.scene.handle_event(event)

    def _apply_resize(self, requested: tuple[int, int]) -> None:
        size = (max(requested[0], 1), max(requested[1], 1))
        self.screen = pygame.display.get_surface()
        # Em janela real o SDL já redimensionou a superfície. Sem janela, quem muda é este set_mode.
        if self.screen.get_size() != size:
            self.screen = pygame.display.set_mode(size, self._flags)
        self._adopt_size(self.screen.get_size())

    def _follow_window_size(self) -> None:
        """Rede de segurança: alguns gerenciadores de janela mudam o tamanho sem gerar VIDEORESIZE."""
        surface = pygame.display.get_surface()
        if surface is not None and surface.get_size() != self.size:
            self.screen = surface
            self._adopt_size(surface.get_size())

    def _adopt_size(self, size: tuple[int, int]) -> None:
        self.size = size
        self.theme.set_window_size(size)
        self.scene.resize(size)

    def _apply_scene_change(self) -> None:
        if self.scene.next_scene is not None:
            self.scene = self.scene.next_scene
            self.scene.update(0.0)

    def run_frame(self) -> None:
        """Um quadro em tempo real: espera o relógio de 60 FPS, desenha e mostra na janela."""
        dt = self.clock.tick(FPS) / 1000.0
        self.fps = self.clock.get_fps()
        self.step(dt)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            self.run_frame()
        pygame.quit()
