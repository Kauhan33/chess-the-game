"""Cena: uma tela do jogo. O `App` entrega eventos, avança o tempo e pede o desenho."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from xadrez.ui.app import App


class Scene(ABC):
    """Para trocar de tela, a cena preenche `next_scene`. O `App` faz a troca no fim do quadro."""

    def __init__(self, app: App) -> None:
        self.app = app
        self.next_scene: Scene | None = None

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None: ...

    @abstractmethod
    def update(self, dt: float) -> None: ...

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None: ...

    @abstractmethod
    def resize(self, size: tuple[int, int]) -> None:
        """Recalcula o layout. Precisa aguentar qualquer tamanho sem levantar exceção (RNF07)."""
