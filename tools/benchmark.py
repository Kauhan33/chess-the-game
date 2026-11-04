"""Mede o custo real de um quadro da cena cheia em 1280x720, sem janela (RNF01).

Cena: 32 peças, sombras, matriz de cores pulsando, marcadores, cerca de 300 partículas e
uma peça animada. Dois cenários: câmera parada (o caso comum) e câmera girando (o pior caso).

Uso: python tools/benchmark.py [--frames 600]
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pygame

from xadrez.graphics import (
    EBONY,
    FACING_BLACK,
    FACING_WHITE,
    IVORY,
    MARKER_CORNERS,
    MARKER_DOT,
    MARKER_RING,
    MARKER_TRIANGLE,
    Camera,
    CellState,
    ColorMatrix,
    ParticleSystem,
    PieceAnimation,
    Renderer3D,
    build_piece_meshes,
    piece_matrix,
    square_to_world,
)

WIDTH, HEIGHT = 1280, 720
DELTA_TIME = 1.0 / 60.0
ORBIT_SPEED = math.radians(30)
TARGET_PARTICLES = 340
BACK_RANK = ("rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook")
MOVING_SQUARE = (1, 0)
MOVE_ROUTE = ((1, 0), (2, 2), (4, 3), (2, 2))
THREATENED_SQUARES = {(5, 7), (2, 0)}
MARKERS = (
    (4, 3, MARKER_DOT, (40, 110, 66)), (4, 4, MARKER_DOT, (40, 110, 66)), (2, 3, MARKER_DOT, (40, 110, 66)),
    (6, 3, MARKER_DOT, (40, 110, 66)), (3, 4, MARKER_DOT, (40, 110, 66)), (5, 4, MARKER_DOT, (40, 110, 66)),
    (3, 6, MARKER_RING, (150, 30, 24)), (5, 6, MARKER_RING, (150, 30, 24)),
    (1, 4, MARKER_CORNERS, (20, 60, 120)), (5, 7, MARKER_TRIANGLE, (130, 66, 8)),
)


def initial_position() -> list[tuple[str, int, int, bool]]:
    pieces = []
    for file, kind in enumerate(BACK_RANK):
        pieces += [(kind, file, 0, True), ("pawn", file, 1, True), (kind, file, 7, False), ("pawn", file, 6, False)]
    return pieces


def build_color_matrix() -> ColorMatrix:
    matrix = ColorMatrix()
    matrix.set(4, 7, CellState.CHECK)
    matrix.set_many(THREATENED_SQUARES, CellState.THREAT)
    matrix.set(4, 2, CellState.SELECTED)
    matrix.set_many([(m[0], m[1]) for m in MARKERS[:6]], CellState.PATH)
    matrix.set_many([(3, 6), (5, 6)], CellState.CAPTURE)
    matrix.set_many([(4, 1), (2, 2)], CellState.LAST_MOVE)
    matrix.set(1, 4, CellState.CURSOR)
    return matrix


class BenchmarkScene:
    """Estado da cena que muda quadro a quadro, igual ao que a Interface fará em jogo."""

    def __init__(self, camera: Camera):
        self.camera = camera
        self.renderer = Renderer3D(camera)
        self.meshes = build_piece_meshes()
        self.static_pieces = [p for p in initial_position() if (p[1], p[2]) != MOVING_SQUARE]
        self.matrix = build_color_matrix()
        self.particles = ParticleSystem(seed=7)
        self.time = 0.0
        self.route_index = 0
        self.animation = self._next_animation()

    def _next_animation(self) -> PieceAnimation:
        origin = MOVE_ROUTE[self.route_index % len(MOVE_ROUTE)]
        target = MOVE_ROUTE[(self.route_index + 1) % len(MOVE_ROUTE)]
        self.route_index += 1
        return PieceAnimation(origin, target, duration=0.6, arc_height=0.9, facing=FACING_WHITE)

    def _keep_particles_alive(self) -> None:
        missing = TARGET_PARTICLES - self.particles.alive_count
        if missing >= 60:
            position = square_to_world(*MOVE_ROUTE[self.route_index % len(MOVE_ROUTE)])
            self.particles.capture_burst(position, (240, 170, 80))
        else:
            self.particles.trail(self.animation.position, (255, 214, 140))

    def update(self) -> None:
        self.time += DELTA_TIME
        self.animation.update(DELTA_TIME)
        if self.animation.is_done:
            self.animation = self._next_animation()
        self._keep_particles_alive()
        self.particles.update(DELTA_TIME)

    def draw(self, screen: pygame.Surface) -> None:
        renderer = self.renderer
        renderer.begin(screen)
        renderer.draw_board(self.matrix.rgb(self.time))
        pulse = 0.25 + 0.2 * math.sin(self.time * 7.0)
        for kind, file, rank, is_white in self.static_pieces:
            facing, color = (FACING_WHITE, IVORY) if is_white else (FACING_BLACK, EBONY)
            threat = (file, rank) in THREATENED_SQUARES
            renderer.add_mesh(self.meshes[kind], piece_matrix(file, rank, facing), color,
                              tint=(255, 110, 30) if threat else None, tint_amount=pulse if threat else 0.0)
        renderer.add_mesh(self.meshes["knight"], self.animation.model_matrix(), IVORY)
        for marker in MARKERS:
            renderer.add_marker(*marker)
        renderer.add_particles(self.particles)
        renderer.flush()


def run_scenario(screen: pygame.Surface, frames: int, is_orbiting: bool) -> dict:
    camera = Camera((0, 0, WIDTH, HEIGHT))
    scene = BenchmarkScene(camera)
    samples = np.zeros(frames)
    polygons = np.zeros(frames, dtype=np.int64)
    particles = np.zeros(frames, dtype=np.int64)
    # Quadros de aquecimento: enchem os caches, como a primeira exibição da partida.
    warmup = 30
    for frame in range(-warmup, frames):
        scene.update()
        if is_orbiting:
            camera.orbit_by(ORBIT_SPEED * DELTA_TIME)
        start = time.perf_counter()
        scene.draw(screen)
        elapsed = time.perf_counter() - start
        if frame >= 0:
            samples[frame] = elapsed
            polygons[frame] = scene.renderer.polygons_drawn
            particles[frame] = scene.particles.alive_count
    return {"samples": samples * 1000.0, "polygons": polygons, "particles": particles}


def measure_camera_stops(screen: pygame.Surface, stops: int = 20) -> np.ndarray:
    """Quadros logo após a câmera parar: é quando as camadas e os sprites são refeitos.

    Devolve (paradas, quadros) em ms: cada coluna é o enésimo quadro depois da parada.
    """
    camera = Camera((0, 0, WIDTH, HEIGHT))
    scene = BenchmarkScene(camera)
    frames_per_stop = 6
    costs = np.zeros((stops, frames_per_stop))
    for stop in range(stops):
        camera.orbit_by(math.radians(3.0))
        scene.update()
        scene.draw(screen)
        for frame in range(frames_per_stop):
            scene.update()
            start = time.perf_counter()
            scene.draw(screen)
            costs[stop, frame] = time.perf_counter() - start
    return costs * 1000.0


def report(name: str, result: dict) -> None:
    samples = result["samples"]
    print(f"\n{name}")
    print(f"  quadros medidos:     {len(samples)}")
    print(f"  média:               {samples.mean():6.2f} ms")
    print(f"  p95:                 {np.percentile(samples, 95):6.2f} ms")
    print(f"  p99:                 {np.percentile(samples, 99):6.2f} ms")
    print(f"  máximo:              {samples.max():6.2f} ms")
    print(f"  quadros por segundo: {1000.0 / samples.mean():6.0f} possíveis")
    print(f"  polígonos rasterizados por quadro: média {result['polygons'].mean():.0f}, máximo {result['polygons'].max()}")
    print(f"  partículas vivas: média {result['particles'].mean():.0f}, mínimo {result['particles'].min()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=600)
    args = parser.parse_args()
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    report("Câmera parada", run_scenario(screen, args.frames, is_orbiting=False))
    report("Câmera girando", run_scenario(screen, args.frames, is_orbiting=True))
    stops = measure_camera_stops(screen)
    print("\nQuadros logo após a câmera parar (camada e sprites sendo refeitos)")
    for frame in range(stops.shape[1]):
        print(f"  {frame + 1}º quadro: média {stops[:, frame].mean():6.2f} ms, máximo {stops[:, frame].max():6.2f} ms")
    pygame.quit()


if __name__ == "__main__":
    main()
