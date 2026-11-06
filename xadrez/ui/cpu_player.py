"""CPU adversária fora do quadro: `choose_move` roda em uma thread, e a tela nunca espera por ela.

Decisão e medições em `docs/plans/2026-11-03-xadrez-design.md`, seção 10.2. O tabuleiro é copiado aqui, na
thread principal, antes de a busca começar, porque `legal_moves_from` faz `apply` e `undo` temporários no
tabuleiro real. Cada busca é um `_SearchJob` próprio: a jogada de uma busca cancelada nunca chega a ninguém.
"""
from __future__ import annotations

import logging
import math
import random
import sys
import threading
import time
from typing import Callable

from xadrez.core import Board, Difficulty, Move, choose_move, legal_moves

THREAD_NAME = "chess-cpu"
SEARCH_SWITCH_INTERVAL = 0.0002
_BUSY_NAP_SECONDS = 0.001
_JOIN_SECONDS = 2.0
_REMAINING_DIVISOR = 25.0
_INCREMENT_SHARE = 0.75
_MAX_SHARE_OF_REMAINING = 0.5
# Jogada instantânea parece defeito: Easy e Medium respondem em milissegundos.
_MINIMUM_THINK_SECONDS = {Difficulty.EASY: 0.5, Difficulty.MEDIUM: 0.5}

_log = logging.getLogger(__name__)


class _FastThreadSwitching:
    """Intervalo curto de troca entre threads enquanto houver alguma busca viva, e o original de volta depois.

    Com o intervalo padrão, a busca segura o interpretador por 5 ms de cada vez e a tela cai para 9,5 FPS.
    Uma busca cancelada pode terminar depois de a próxima começar, por isso a contagem.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self._original = 0.0

    def __enter__(self) -> None:
        with self._lock:
            if self._active == 0:
                self._original = sys.getswitchinterval()
                sys.setswitchinterval(SEARCH_SWITCH_INTERVAL)
            self._active += 1

    def __exit__(self, *_: object) -> None:
        with self._lock:
            self._active -= 1
            if self._active == 0:
                sys.setswitchinterval(self._original)


_fast_switching = _FastThreadSwitching()


def search_budget(remaining: float, increment: float) -> float | None:
    """Tempo máximo para um lance, sempre menos do que resta: o incremento só chega depois dele. Sem relógio, só vale o limite do nível."""
    if math.isinf(remaining):
        return None
    return min(remaining / _REMAINING_DIVISOR + increment * _INCREMENT_SHARE, remaining * _MAX_SHARE_OF_REMAINING)


class _SearchJob:
    def __init__(self, board: Board, difficulty: Difficulty, rng: random.Random, is_busy: Callable[[], bool],
                 max_seconds: float | None):
        self.board = board
        self.difficulty = difficulty
        self.rng = rng
        self.is_busy = is_busy
        self.max_seconds = max_seconds
        self.stop = threading.Event()
        self.move: Move | None = None
        self.error: Exception | None = None
        self.waited = 0.0
        minimum = _MINIMUM_THINK_SECONDS.get(difficulty, 0.0)
        self.minimum_wait = minimum if max_seconds is None else min(minimum, max_seconds)
        self.thread = threading.Thread(target=self._run, name=THREAD_NAME, daemon=True)

    def _run(self) -> None:
        with _fast_switching:
            try:
                self.move = choose_move(self.board, self.difficulty, self.rng, self._should_stop, self.max_seconds)
            except Exception as error:
                # Sem isto, a exceção morreria com a thread, e a partida esperaria para sempre uma jogada.
                _log.exception("A busca da CPU falhou")
                self.error = error

    def _should_stop(self) -> bool:
        if self.stop.is_set():
            return True
        # Câmera girando ou peça voando: a tela precisa do interpretador mais do que a busca.
        if self.is_busy():
            time.sleep(_BUSY_NAP_SECONDS)
        return self.stop.is_set()

    def begin(self) -> None:
        try:
            self.thread.start()
        except RuntimeError as error:
            self.error = error

    def cancel(self) -> None:
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(_JOIN_SECONDS)

    def any_legal_move(self) -> Move | None:
        """Jogada de emergência. A cópia é só desta busca, que já terminou, então a thread principal pode usá-la."""
        moves = legal_moves(self.board)
        return self.rng.choice(moves) if moves else None


class CpuPlayer:
    """`start` começa a pensar; `poll`, a cada quadro, entrega a jogada uma vez; `cancel` descarta tudo."""

    def __init__(self, difficulty: Difficulty, rng: random.Random | None = None,
                 is_busy: Callable[[], bool] = lambda: False):
        self.difficulty = difficulty
        self._rng = rng if rng is not None else random.Random()
        self._is_busy = is_busy
        self._job: _SearchJob | None = None
        self.last_error: Exception | None = None

    @property
    def is_thinking(self) -> bool:
        return self._job is not None

    def start(self, board: Board, remaining: float = math.inf, increment: float = 0.0) -> None:
        self.cancel()
        # Um gerador para cada busca: uma busca cancelada que ainda termina não disputa o próximo número com a seguinte.
        rng = random.Random(self._rng.getrandbits(64))
        self._job = _SearchJob(board.copy(), self.difficulty, rng, self._is_busy, search_budget(remaining, increment))
        self._job.begin()

    def poll(self, dt: float) -> Move | None:
        """A jogada pronta, depois da espera mínima visível. Se a busca falhou, uma jogada legal qualquer."""
        job = self._job
        if job is None:
            return None
        job.waited += dt
        if job.thread.is_alive() or job.waited < job.minimum_wait:
            return None
        self._job = None
        self.last_error = job.error
        return job.move if job.error is None else job.any_legal_move()

    def cancel(self) -> None:
        job, self._job = self._job, None
        if job is not None:
            job.cancel()
