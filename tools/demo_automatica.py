"""Abre uma janela real e joga sozinho, em velocidade real, até a tela de vitória.

Serve de medição real de FPS (inclui `display.flip`) e de plano B na apresentação. Encerra sozinho
e imprime as estatísticas dos quadros. Esc ou fechar a janela interrompe e imprime o que já mediu.

Com `--cpu hardcore`, o jogo é contra a CPU desse nível: os lances do lado de cá são sorteados e jogados pelo
mouse, e o relatório separa os quadros com a CPU pensando, que é o caso que o RNF09 mede.

Uso: python tools/demo_automatica.py [--longa] [--size 1280x720] [--cpu hardcore] [--lances 5]
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pygame

from xadrez.core import Color, Difficulty, TimeControl, legal_moves
from xadrez.ui.app import App
from xadrez.ui.autoplay import Autoplayer, post_click, post_mouse_move, post_text
from xadrez.ui.game_over_scene import GameOverScene
from xadrez.ui.game_scene import GameScene
from xadrez.ui.match import OPPONENT_CPU, MatchOptions

SHORT_GAME = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
LONG_GAME = (
    "e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 "
    "c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8"
)
THINK_SECONDS = 0.7
MENU_SECONDS = 1.5
VICTORY_SECONDS = 5.0
CPU_LEVELS = {level.label.lower(): level for level in Difficulty}
DEFAULT_CPU_MOVES = 5
FLIP_AFTER_FRAMES = 120


class Interrupted(Exception):
    """O espectador apertou Esc ou fechou a janela."""


class RealTimeFrames:
    """Um quadro em tempo real, medindo o trabalho (`step` + `flip`) e o intervalo entre quadros."""

    def __init__(self, app: App):
        self.app = app
        self.work_ms: list[float] = []
        self.interval_ms: list[float] = []
        self.thinking_interval_ms: list[float] = []
        self.moving_thinking_interval_ms: list[float] = []
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
        interval = (finished - self._previous) * 1000.0
        self.work_ms.append((finished - started) * 1000.0)
        self.interval_ms.append(interval)
        self._record_thinking(interval)
        self._previous = finished

    def _record_thinking(self, interval: float) -> None:
        scene = self.app.scene
        if not isinstance(scene, GameScene) or scene.cpu is None or not scene.cpu.is_thinking:
            return
        target = self.moving_thinking_interval_ms if scene.view.is_animating else self.thinking_interval_ms
        target.append(interval)

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


def run_cpu_demo(player: Autoplayer, level: Difficulty, move_count: int) -> None:
    """Partida contra a CPU: quem joga do lado de cá sorteia lances legais, com o mouse parado longe do tabuleiro."""
    app = player.app
    options = MatchOptions("Jogador 1", "Jogador 2", TimeControl.UNLIMITED, False, opponent_kind=OPPONENT_CPU,
                           difficulty=level, human_color=Color.WHITE)
    app.scene.next_scene = app.game_scene(options.create_engine(), options)
    player.frames(2)
    player.settle()
    scene = app.scene
    rng = random.Random(5)
    for _ in range(move_count):
        if scene.engine.result is not None:
            break
        _play_random_move(player, scene, rng)
        _wait_for_cpu(player, scene)
    scene.shutdown()


def _play_random_move(player: Autoplayer, scene: GameScene, rng: random.Random) -> None:
    player.settle()
    player.seconds(THINK_SECONDS)
    move = rng.choice(legal_moves(scene.engine.board))
    player.click_square(tuple(move.origin))
    player.click_square(tuple(move.target))
    if scene.modals:
        player.click_widget(scene.modals[-1].buttons[0])
    post_mouse_move((player.app.size[0] - 2, 2))
    player.settle()


def _wait_for_cpu(player: Autoplayer, scene: GameScene) -> None:
    """Metade do tempo com a câmera parada e, no meio do pensamento, uma virada do tabuleiro, para medir os dois casos."""
    elapsed_frames = 0
    while scene.cpu.is_thinking and scene.engine.result is None:
        player.frames(1)
        elapsed_frames += 1
        if elapsed_frames == FLIP_AFTER_FRAMES:
            post_click(next(button for button in scene.hud.buttons if button.label == "Virar").rect.center)


def _print_interval(name: str, samples: list[float]) -> None:
    if len(samples) < 2:
        print(f"{name}: sem quadros suficientes.")
        return
    values = np.array(samples[1:])
    print(f"{name}: {len(values)} quadros, FPS médio {1000.0 / values.mean():.1f}, intervalo médio {values.mean():.2f} ms, "
          f"p95 {np.percentile(values, 95):.2f} ms, p99 {np.percentile(values, 99):.2f} ms, máximo {values.max():.2f} ms")


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
    if frames.thinking_interval_ms or frames.moving_thinking_interval_ms:
        _print_interval("CPU pensando, câmera parada", frames.thinking_interval_ms)
        _print_interval("CPU pensando, com animação ou câmera em movimento", frames.moving_thinking_interval_ms)


def parse_size(text: str) -> tuple[int, int]:
    width, height = text.lower().split("x")
    return int(width), int(height)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--longa", action="store_true", help="Joga a partida de 17 lances, em vez da de 4.")
    parser.add_argument("--size", type=parse_size, default=(1280, 720))
    parser.add_argument("--cpu", choices=sorted(CPU_LEVELS), default=None, help="Joga contra a CPU desse nível.")
    parser.add_argument("--lances", type=int, default=DEFAULT_CPU_MOVES, help="Lances da partida contra a CPU.")
    args = parser.parse_args()
    app = App(args.size, seed=5)
    app.preload()
    frames = RealTimeFrames(app)
    try:
        if args.cpu is None:
            run_demo(Autoplayer(app, frames), LONG_GAME if args.longa else SHORT_GAME)
        else:
            run_cpu_demo(Autoplayer(app, frames), CPU_LEVELS[args.cpu], args.lances)
    except Interrupted:
        print("Demonstração interrompida.")
    report(frames)
    app.scene.shutdown()
    pygame.quit()


if __name__ == "__main__":
    main()
