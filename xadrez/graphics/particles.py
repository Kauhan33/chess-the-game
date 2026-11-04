"""Sistema de partículas vetorizado: estrutura de arrays, uma linha por partícula viva.

As `alive_count` primeiras linhas estão vivas. Ao morrer, a partícula é removida por
compactação, sem laço em Python.
"""
from __future__ import annotations

import math

import numpy as np

_FLOOR_NORMAL = np.array((0.0, 1.0, 0.0))
_DEFAULT_DRAG = 0.55


def _ranged(rng: np.random.Generator, value, count: int) -> np.ndarray:
    """Aceita valor fixo ou faixa (mínimo, máximo)."""
    if isinstance(value, (tuple, list)):
        return rng.uniform(value[0], value[1], count)
    return np.full(count, float(value))


class ParticleSystem:
    def __init__(self, capacity: int = 2000, gravity: float = -9.8, floor_y: float = 0.0,
                 restitution: float = 0.45, seed: int | None = None, drag: float = _DEFAULT_DRAG):
        self.capacity = capacity
        self.gravity = gravity
        self.floor_y = floor_y
        self.restitution = restitution
        self.drag = drag
        self.alive_count = 0
        self._rng = np.random.default_rng(seed)
        self._positions = np.zeros((capacity, 3))
        self._velocities = np.zeros((capacity, 3))
        self._colors = np.zeros((capacity, 3))
        self._base_sizes = np.zeros(capacity)
        self._ages = np.zeros(capacity)
        self._lifetimes = np.ones(capacity)

    @property
    def positions(self) -> np.ndarray:
        return self._positions[: self.alive_count]

    @property
    def velocities(self) -> np.ndarray:
        return self._velocities[: self.alive_count]

    @property
    def colors(self) -> np.ndarray:
        return self._colors[: self.alive_count]

    @property
    def sizes(self) -> np.ndarray:
        """Tamanho em unidades de mundo: a partícula encolhe até a metade ao envelhecer."""
        count = self.alive_count
        return self._base_sizes[:count] * (1.0 - 0.5 * self._ages[:count] / self._lifetimes[:count])

    @property
    def alphas(self) -> np.ndarray:
        """Fade de 1 a 0: a = 1 - (idade / vida)^2 mantém o brilho por mais tempo no início."""
        count = self.alive_count
        return 1.0 - (self._ages[:count] / self._lifetimes[:count]) ** 2

    def emit(self, position, count: int, color, speed, life, size, bias=(0.0, 0.0, 0.0)) -> None:
        """Emite até `count` partículas. O que passar da capacidade é descartado.

        A direção é uma normal 3D normalizada, que é uniforme na esfera. Somar `bias` antes
        de normalizar concentra o jato para aquele lado. `speed`, `life` e `size` aceitam
        faixa; `color` aceita uma cor ou uma por partícula.
        """
        count = min(count, self.capacity - self.alive_count)
        if count <= 0:
            return
        color = np.asarray(color, dtype=float)
        if color.ndim == 2:
            color = color[:count]
        directions = self._rng.standard_normal((count, 3))
        directions /= np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-9)
        directions += bias
        directions /= np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-9)
        start, end = self.alive_count, self.alive_count + count
        self._positions[start:end] = position
        self._velocities[start:end] = directions * _ranged(self._rng, speed, count)[:, None]
        self._colors[start:end] = color
        self._base_sizes[start:end] = _ranged(self._rng, size, count)
        self._ages[start:end] = 0.0
        self._lifetimes[start:end] = np.maximum(_ranged(self._rng, life, count), 1e-3)
        self.alive_count = end

    def capture_burst(self, position, color) -> None:
        """Explosão de captura: lascas na cor da peça e faíscas quentes por cima."""
        self.emit(position, 34, color, speed=(1.2, 3.8), life=(0.45, 0.95), size=(0.045, 0.085), bias=(0.0, 0.9, 0.0))
        self.emit(position, 26, (255, 196, 110), speed=(2.0, 4.6), life=(0.25, 0.6), size=(0.03, 0.05), bias=(0.0, 1.2, 0.0))

    def trail(self, position, color) -> None:
        """Rastro: poucas partículas lentas e de vida curta, emitidas a cada quadro."""
        self.emit(position, 2, color, speed=(0.05, 0.3), life=(0.22, 0.42), size=(0.03, 0.055))

    def victory_fireworks(self, position, colors) -> None:
        """Fogos: um estouro esférico em que cada partícula sorteia uma cor da lista."""
        count = 140
        palette = np.asarray(colors, dtype=float).reshape(-1, 3)
        chosen = palette[self._rng.integers(len(palette), size=count)]
        self.emit(position, count, chosen, speed=(2.5, 6.0), life=(0.9, 1.7), size=(0.05, 0.1), bias=(0.0, 0.2, 0.0))

    def update(self, dt: float) -> None:
        """Avança a simulação por Euler semi-implícito: velocidade primeiro, depois posição."""
        count = self.alive_count
        if count == 0 or dt <= 0.0:
            return
        velocities = self._velocities[:count]
        positions = self._positions[:count]
        velocities[:, 1] += self.gravity * dt
        # Arrasto proporcional à velocidade: dv/dt = -k v tem solução v(t) = v0 exp(-k t).
        velocities *= math.exp(-self.drag * dt)
        positions += velocities * dt
        self._bounce_on_floor(positions, velocities)
        self._ages[:count] += dt
        self._remove_dead()

    def _bounce_on_floor(self, positions: np.ndarray, velocities: np.ndarray) -> None:
        """Colisão com o piso por reflexão do vetor velocidade.

        v' = v - (1 + e)(v.n) n, em que e é a restituição. Com e = 1, a reflexão é perfeita
        (v - 2(v.n)n). Com e < 1, só a componente normal perde energia, a tangencial fica.
        """
        hits = np.flatnonzero((positions[:, 1] < self.floor_y) & (velocities[:, 1] < 0.0))
        if hits.size == 0:
            return
        normal_speed = velocities[hits] @ _FLOOR_NORMAL
        velocities[hits] -= (1.0 + self.restitution) * normal_speed[:, None] * _FLOOR_NORMAL
        positions[hits, 1] = self.floor_y

    def _remove_dead(self) -> None:
        count = self.alive_count
        survivors = np.flatnonzero(self._ages[:count] < self._lifetimes[:count])
        if survivors.size == count:
            return
        for array in (self._positions, self._velocities, self._colors, self._base_sizes, self._ages, self._lifetimes):
            array[: survivors.size] = array[survivors]
        self.alive_count = survivors.size
