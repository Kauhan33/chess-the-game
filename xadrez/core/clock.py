"""Controle de tempo e relógio de xadrez. Tudo em segundos, menos `TimeControl.minutes`."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

from .types import Color

_SECONDS_PER_MINUTE = 60


@dataclass(frozen=True)
class TimeControl:
    """Tempo inicial em minutos e incremento por lance em segundos. `minutes=0` significa sem limite."""

    minutes: float = 0
    increment: float = 0

    UNLIMITED: ClassVar[TimeControl]
    BLITZ_5: ClassVar[TimeControl]
    RAPID_10: ClassVar[TimeControl]
    CLASSIC_30: ClassVar[TimeControl]

    def __post_init__(self) -> None:
        if self.minutes < 0 or self.increment < 0:
            raise ValueError("O controle de tempo não aceita valores negativos")

    @property
    def is_unlimited(self) -> bool:
        return self.minutes == 0


TimeControl.UNLIMITED = TimeControl(0)
TimeControl.BLITZ_5 = TimeControl(5)
TimeControl.RAPID_10 = TimeControl(10)
TimeControl.CLASSIC_30 = TimeControl(30)


class ChessClock:
    """Sem limite, o relógio só soma o tempo decorrido. Com limite, faz também a contagem regressiva."""

    def __init__(self, time_control: TimeControl = TimeControl.UNLIMITED) -> None:
        self.time_control = time_control
        initial = math.inf if time_control.is_unlimited else time_control.minutes * _SECONDS_PER_MINUTE
        self._remaining = {color: initial for color in Color}
        self._elapsed = {color: 0.0 for color in Color}

    def remaining(self, color: Color) -> float:
        """Segundos restantes; `math.inf` no controle sem limite."""
        return self._remaining[color]

    def elapsed(self, color: Color) -> float:
        return self._elapsed[color]

    def tick(self, color: Color, dt: float) -> None:
        # `not dt > 0` também descarta NaN, que falharia em `dt <= 0` e corromperia o relógio.
        if not dt > 0:
            return
        self._elapsed[color] += dt
        self._remaining[color] = max(0.0, self._remaining[color] - dt)

    def add_increment(self, color: Color) -> None:
        self._remaining[color] += self.time_control.increment

    def is_flagged(self, color: Color) -> bool:
        return self._remaining[color] <= 0
