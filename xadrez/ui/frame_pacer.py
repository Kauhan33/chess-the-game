"""Controle de framerate: 60 FPS medidos em segundos, não em milissegundos inteiros."""
from __future__ import annotations

import time

_SLEEP_MARGIN_SECONDS = 0.002
_FPS_SMOOTHING = 0.05
_MIN_ELAPSED_SECONDS = 1e-6


class FramePacer:
    """Segura cada quadro até o seu prazo, com período de exatamente 1/fps segundo.

    `pygame.time.Clock.tick(60)` trabalha em milissegundos inteiros, e o sono do sistema acorda
    atrasado: medido em janela real, isso deu 59,1 FPS. Aqui cada prazo parte do prazo anterior,
    não de "agora", então um atraso pequeno é compensado no quadro seguinte em vez de se acumular.
    O sono vai até pouco antes do prazo e o resto é espera ativa, porque o sono não é preciso.
    """

    def __init__(self, fps: int, now=time.perf_counter, sleep=time.sleep):
        self.period = 1.0 / fps
        self.fps = float(fps)
        self._now = now
        self._sleep = sleep
        self._last_frame = now()
        self._deadline = self._last_frame + self.period

    def wait(self) -> float:
        """Espera o prazo do quadro e devolve o tempo real, em segundos, desde o quadro anterior."""
        remaining = self._deadline - self._now()
        if remaining > _SLEEP_MARGIN_SECONDS:
            self._sleep(remaining - _SLEEP_MARGIN_SECONDS)
        while self._now() < self._deadline:
            pass
        current = self._now()
        elapsed = max(current - self._last_frame, _MIN_ELAPSED_SECONDS)
        self._last_frame = current
        self._schedule_next(current)
        self.fps += (1.0 / elapsed - self.fps) * _FPS_SMOOTHING
        return elapsed

    def _schedule_next(self, current: float) -> None:
        self._deadline += self.period
        # Atraso de mais de um quadro (janela arrastada) não vira rajada para "recuperar" o tempo.
        if self._deadline < current:
            self._deadline = current + self.period
