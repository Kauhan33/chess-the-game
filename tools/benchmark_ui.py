"""Mede o quadro completo do jogo (App.step com HUD, eventos e cena 3D), sem janela (RNF01).

A partida é jogada por eventos reais, com o mouse passando sobre as casas entre um lance e outro.
Não inclui `display.flip`: para isso existe `tools/demo_automatica.py`, em janela real.

Metas: câmera parada com média até 10 ms e p99 abaixo de 16,6 ms.

Uso: python tools/benchmark_ui.py [--seconds 10] [--size 1280x720]
"""
from __future__ import annotations

import argparse
import gc
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pygame

from xadrez.core import Color, Difficulty, TimeControl, legal_moves
from xadrez.ui import App, MatchOptions
from xadrez.ui.autoplay import Autoplayer, click_point, post_key, post_mouse_move
from xadrez.ui.match import OPPONENT_CPU

SEED = 3
FRAME_SECONDS = 1.0 / 60.0
MEAN_BUDGET_MS = 10.0
P99_BUDGET_MS = 16.6
DEFAULT_MEASURE_SECONDS = 10.0
THINK_SECONDS = 0.5
MATE_ANIMATION_SECONDS = 2.0
# Partida curta e completa: capturas, xeques, roque grande e mate no lance 17.
FULL_GAME = (
    "e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 "
    "c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8"
)


class FrameRecorder:
    """Cronometra cada `App.step`. É o `run_frame` do Autoplayer."""

    def __init__(self, app: App):
        self.app = app
        self.samples: list[float] = []

    def __call__(self) -> None:
        started = time.perf_counter()
        self.app.step(FRAME_SECONDS)
        self.samples.append((time.perf_counter() - started) * 1000.0)


def start_match(app: App, auto_rotate: bool) -> None:
    options = MatchOptions("Jogador 1", "Jogador 2", TimeControl.CLASSIC_30, auto_rotate)
    app.scene.next_scene = app.game_scene(options.create_engine(), options)
    app.step(FRAME_SECONDS)


def warm_caches(player: Autoplayer) -> None:
    """Primeiros quadros: camadas e sprites nascem aqui, como no primeiro segundo de uma partida real."""
    player.seconds(0.5)


def wander_mouse(player: Autoplayer, square: tuple[int, int], frames: int) -> None:
    for _ in range(frames):
        post_mouse_move(click_point(player.view, square))
        player.frames(1)


def play_scripted_game(player: Autoplayer) -> None:
    """Joga a partida inteira, do primeiro lance até o rei terminar de cair."""
    think_frames = round(THINK_SECONDS / FRAME_SECONDS)
    for uci in FULL_GAME.split():
        wander_mouse(player, ("abcdefgh".index(uci[2]), int(uci[3]) - 1), think_frames // 2)
        player.frames(think_frames - think_frames // 2)
        player.play(uci)
    player.seconds(MATE_ANIMATION_SECONDS)


def measure_full_game(size: tuple[int, int], auto_rotate: bool) -> np.ndarray:
    app = App(size, seed=SEED)
    pygame.event.clear()
    start_match(app, auto_rotate)
    recorder = FrameRecorder(app)
    player = Autoplayer(app, recorder)
    warm_caches(player)
    recorder.samples.clear()
    gc.collect()
    play_scripted_game(player)
    return np.array(recorder.samples)


def measure_continuous_orbit(size: tuple[int, int], seconds: float) -> np.ndarray:
    """Pior caso: o jogador arrasta a câmera sem parar, com a cena toda sendo redesenhada por polígonos."""
    app = App(size, seed=SEED)
    pygame.event.clear()
    start_match(app, auto_rotate=False)
    recorder = FrameRecorder(app)
    player = Autoplayer(app, recorder)
    warm_caches(player)
    recorder.samples.clear()
    for _ in range(round(seconds / FRAME_SECONDS)):
        app.scene.view.drag_orbit(4, 0)
        recorder()
    return np.array(recorder.samples)


def measure_victory_screen(size: tuple[int, int], seconds: float) -> np.ndarray:
    app = App(size, seed=SEED)
    pygame.event.clear()
    start_match(app, auto_rotate=False)
    player = Autoplayer(app)
    player.play_all("e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7")
    player.seconds(2.5)
    recorder = FrameRecorder(app)
    for _ in range(round(seconds / FRAME_SECONDS)):
        recorder()
    return np.array(recorder.samples)


def measure_cpu_thinking(size: tuple[int, int], seconds: float) -> np.ndarray:
    """A CPU Hardcore pensa em outra thread e a câmera está parada: é o que o RNF09 pede.

    Cada lance dela leva cerca de 4 s, então o tempo do quadro é real, sem pular: o `dt` é fixo só para o relógio.
    """
    app = App(size, seed=SEED)
    pygame.event.clear()
    options = MatchOptions("Jogador 1", "Jogador 2", TimeControl.UNLIMITED, False, opponent_kind=OPPONENT_CPU,
                           difficulty=Difficulty.HARDCORE, human_color=Color.WHITE)
    app.scene.next_scene = app.game_scene(options.create_engine(), options)
    app.step(FRAME_SECONDS)
    scene = app.scene
    player = Autoplayer(app)
    player.play("e2e4")
    post_mouse_move((size[0] - 2, 2))
    samples: list[float] = []
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        if not scene.cpu.is_thinking:
            player.settle()
            play_any_move(player, scene)
            continue
        started = time.perf_counter()
        app.step(FRAME_SECONDS)
        samples.append((time.perf_counter() - started) * 1000.0)
    scene.shutdown()
    return np.array(samples)


def play_any_move(player: Autoplayer, scene) -> None:
    move = next(iter(legal_moves(scene.engine.board)))
    player.click_square(tuple(move.origin))
    player.click_square(tuple(move.target))
    if scene.modals:
        post_key(pygame.K_1)
        player.frames(1)
    post_mouse_move((player.app.size[0] - 2, 2))
    player.settle()


def report(name: str, samples: np.ndarray) -> None:
    print(f"\n{name}")
    print(f"  quadros medidos: {len(samples)}")
    print(f"  média:  {samples.mean():6.2f} ms")
    print(f"  p95:    {np.percentile(samples, 95):6.2f} ms")
    print(f"  p99:    {np.percentile(samples, 99):6.2f} ms")
    print(f"  máximo: {samples.max():6.2f} ms")
    over_budget = int((samples > 1000.0 / 60.0).sum())
    print(f"  acima de 16,67 ms: {over_budget} quadros ({over_budget / len(samples):.2%})")


def parse_size(text: str) -> tuple[int, int]:
    width, height = text.lower().split("x")
    return int(width), int(height)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=DEFAULT_MEASURE_SECONDS)
    parser.add_argument("--size", type=parse_size, default=(1280, 720))
    args = parser.parse_args()
    print(f"Janela {args.size[0]}x{args.size[1]}, sem display.flip")
    parked = measure_full_game(args.size, auto_rotate=False)
    report("Partida inteira com câmera parada (giro por turno desligado)", parked)
    report("Partida inteira com giro por turno", measure_full_game(args.size, auto_rotate=True))
    report("Câmera em giro contínuo (pior caso)", measure_continuous_orbit(args.size, args.seconds))
    report("Tela de vitória com fogos", measure_victory_screen(args.size, args.seconds))
    report("CPU Hardcore pensando, câmera parada", measure_cpu_thinking(args.size, args.seconds))
    is_within_budget = parked.mean() <= MEAN_BUDGET_MS and np.percentile(parked, 99) < P99_BUDGET_MS
    verdict = "dentro" if is_within_budget else "FORA"
    print(f"\nMeta de câmera parada (média até {MEAN_BUDGET_MS:g} ms, p99 abaixo de {P99_BUDGET_MS:g} ms): {verdict}")
    pygame.quit()


if __name__ == "__main__":
    main()
