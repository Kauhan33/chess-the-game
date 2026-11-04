"""Joga por eventos reais do pygame, como um jogador faria.

Serve à demonstração automática, ao benchmark, à captura de telas e aos testes. O pixel de cada
clique sai de `Camera.project`, então continua certo em qualquer ângulo ou tamanho de janela.
"""
from __future__ import annotations

import numpy as np
import pygame

from xadrez.graphics import square_to_world
from xadrez.ui.board_view import BoardView

_HEIGHT_FRACTIONS = (0.72, 0.55, 0.85, 0.4, 0.25)
_FLOOR_OFFSETS = ((0.0, 0.0), (0.0, 0.28), (0.0, -0.28), (0.28, 0.0), (-0.28, 0.0), (0.28, 0.28), (-0.28, -0.28))


def _project(view: BoardView, point: tuple[float, float, float]) -> tuple[int, int]:
    pixels, _ = view.camera.project(np.array([point], dtype=float))
    return round(float(pixels[0, 0])), round(float(pixels[0, 1]))


def _candidate_points(view: BoardView, square: tuple[int, int]) -> list[tuple[float, float, float]]:
    x, _, z = square_to_world(*square)
    height = view.piece_height_at(square)
    if height > 0.0:
        return [(x, height * fraction, z) for fraction in _HEIGHT_FRACTIONS]
    return [(x + dx, 0.0, z + dz) for dx, dz in _FLOOR_OFFSETS]


def click_point(view: BoardView, square: tuple[int, int], pick=None) -> tuple[int, int]:
    """Pixel que aciona a casa neste ângulo de câmera: acha um ponto visível da peça ou da casa.

    `pick` é quem responde qual casa um pixel aciona. O padrão é o volume das peças, sem seleção.
    """
    answer = view.pick if pick is None else pick
    candidates = [_project(view, point) for point in _candidate_points(view, square)]
    for pixel in candidates:
        if answer(pixel) == tuple(square):
            return pixel
    return candidates[0]


def post_mouse_move(position: tuple[int, int], rel: tuple[int, int] = (0, 0),
                    buttons: tuple[int, int, int] = (0, 0, 0)) -> None:
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=position, rel=rel, buttons=buttons))


def post_mouse_down(position: tuple[int, int], button: int = 1) -> None:
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=button))


def post_mouse_up(position: tuple[int, int], button: int = 1) -> None:
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=position, button=button))


def post_click(position: tuple[int, int], button: int = 1) -> None:
    post_mouse_move(position)
    post_mouse_down(position, button)
    post_mouse_up(position, button)


def post_key(key: int, mod: int = 0) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode="", scancode=0))
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key, mod=mod, unicode="", scancode=0))


def post_text(text: str) -> None:
    pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=text))


class Autoplayer:
    """Roteiro de partida: clica nas casas, espera as animações e segue, sem chamar o motor direto.

    `run_frame` desenha um quadro. O padrão é o `App.step` com tempo fixo, sem relógio real. A
    demonstração automática passa um que também espera o relógio e mostra o quadro na janela.
    """

    FRAME_SECONDS = 1.0 / 60.0
    _SETTLE_LIMIT_FRAMES = 900

    def __init__(self, app, run_frame=None):
        self.app = app
        self._run_frame = run_frame if run_frame is not None else lambda: app.step(self.FRAME_SECONDS)

    @property
    def view(self) -> BoardView:
        return self.app.scene.view

    def frames(self, count: int) -> None:
        for _ in range(count):
            self._run_frame()

    def seconds(self, duration: float) -> None:
        self.frames(round(duration / self.FRAME_SECONDS))

    def settle(self) -> None:
        """Avança até a peça pousar e a câmera parar."""
        for _ in range(self._SETTLE_LIMIT_FRAMES):
            if not self.view.is_flying and not self.view.is_camera_moving:
                return
            self._run_frame()
        raise TimeoutError("A animação não terminou no limite de quadros.")

    def click_square(self, square: tuple[int, int]) -> None:
        pick = getattr(self.app.scene, "pick_at", None)
        post_click(click_point(self.view, tuple(square), pick))
        self.frames(1)

    def click_widget(self, widget) -> None:
        post_click(widget.rect.center)
        self.frames(1)

    def press(self, key: int, mod: int = 0) -> None:
        post_key(key, mod)
        self.frames(1)

    def type_text(self, text: str) -> None:
        post_text(text)
        self.frames(1)

    def play(self, uci: str) -> None:
        """Joga pelo mouse um lance como "e2e4", ou "a7a8q" na promoção, e espera a animação."""
        self.click_square(_cell(uci[:2]))
        self.click_square(_cell(uci[2:4]))
        if len(uci) > 4:
            self.choose_promotion(uci[4])
        self.settle()

    def play_all(self, moves: str) -> None:
        for uci in moves.split():
            self.play(uci)

    def choose_promotion(self, letter: str) -> None:
        dialog = self.app.scene.modals[-1]
        index = [kind.symbol.lower() for kind in dialog.kinds].index(letter)
        self.click_widget(dialog.buttons[index])


def _cell(name: str) -> tuple[int, int]:
    return "abcdefgh".index(name[0]), int(name[1]) - 1
