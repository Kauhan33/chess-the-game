"""Fixtures da interface: o jogo inteiro roda sem janela, dirigido por eventos reais e `App.step`."""
import pygame
import pytest

from xadrez.ui import App
from xadrez.ui.autoplay import Autoplayer


@pytest.fixture
def app():
    application = App(seed=11)
    pygame.event.clear()
    yield application
    pygame.event.clear()


@pytest.fixture
def player(app):
    return Autoplayer(app)
