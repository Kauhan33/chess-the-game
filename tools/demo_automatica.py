"""Abre uma janela real e joga sozinho, em velocidade real, até a tela de vitória.

Serve de medição real de FPS (inclui `display.flip`) e de plano B na apresentação. Encerra sozinho
e imprime as estatísticas dos quadros. Esc ou fechar a janela interrompe e imprime o que já mediu.

Uso: python tools/demo_automatica.py [--longa] [--size 1280x720]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pygame

from xadrez.ui.app import App
from xadrez.ui.autoplay import Autoplayer, post_click, post_text
from xadrez.ui.game_over_scene import GameOverScene

SHORT_GAME = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
LONG_GAME = (
    "e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 "
    "c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8"
)
THINK_SECONDS = 0.7
MENU_SECONDS = 1.5
VICTORY_SECONDS = 5.0


class Interrupted(Exception):
    """O espectador apertou Esc ou fechou a janela."""


class RealTimeFrames:
    """Um quadro em tempo real, medindo o trabalho (`step` + `flip`) e o intervalo entre quadros."""

    def __init__(self, app: App):
        self.app = app
        self.work_ms: list[float] = []
        self.interval_ms: list[float] = []
        self._previous = time.perf_counter()

    def __call__(self) -> None:
        if self._has_stop_request():
            raise Interrupted
        dt = self.app.pacer.wait()
        self.app.fps = self.app.pacer.fps
        started = time.perf_counter()
        self.app.step(dt)
        pygame.display.flip()
        finished = time.perf_counter()
        self.work_ms.append((finished - started) * 1000.0)
        self.interval_ms.append((finished - self._previous) * 1000.0)
        self._previous = finished

    def _has_stop_request(self) -> bool:
        return bool(pygame.event.peek(pygame.QUIT)) or any(
            event.key == pygame.K_ESCAPE for event in pygame.event.get(pygame.KEYDOWN, pump=True)
        )


def run_demo(player: Autoplayer, moves: str) -> None:
    app = player.app
    menu = app.scene
    player.seconds(MENU_SECONDS)
    post_text("Jogador 1")
    player.seconds(0.2)
    post_click(menu.start_button.rect.center)
    player.frames(2)
    player.settle()
    for uci in moves.split():
        player.seconds(THINK_SECONDS)
        player.play(uci)
    while not isinstance(app.scene, GameOverScene):
        player.frames(1)
    player.seconds(VICTORY_SECONDS)


def report(frames: RealTimeFrames) -> None:
    work = np.array(frames.work_ms[1:])
    interval = np.array(frames.interval_ms[1:])
    if len(work) == 0:
        print("Nenhum quadro medido.")
        return
    print(f"\nQuadros: {len(work)} em {interval.sum() / 1000.0:.1f} s, janela real, com display.flip")
    print(f"FPS médio: {1000.0 / interval.mean():.1f}")
    print(f"Intervalo entre quadros: média {interval.mean():.2f} ms, p95 {np.percentile(interval, 95):.2f} ms, "
          f"p99 {np.percentile(interval, 99):.2f} ms, máximo {interval.max():.2f} ms")
    print(f"Trabalho por quadro (step + flip): média {work.mean():.2f} ms, p95 {np.percentile(work, 95):.2f} ms, "
          f"p99 {np.percentile(work, 99):.2f} ms, máximo {work.max():.2f} ms")
    late = int((interval > 1000.0 / 60.0 * 1.5).sum())
    print(f"Quadros atrasados (mais de 25 ms de intervalo): {late} ({late / len(interval):.2%})")


def parse_size(text: str) -> tuple[int, int]:
    width, height = text.lower().split("x")
    return int(width), int(height)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--longa", action="store_true", help="Joga a partida de 17 lances, em vez da de 4.")
    parser.add_argument("--size", type=parse_size, default=(1280, 720))
    args = parser.parse_args()
    app = App(args.size, seed=5)
    app.preload()
    frames = RealTimeFrames(app)
    try:
        run_demo(Autoplayer(app, frames), LONG_GAME if args.longa else SHORT_GAME)
    except Interrupted:
        print("Demonstração interrompida.")
    report(frames)
    pygame.quit()


if __name__ == "__main__":
    main()
