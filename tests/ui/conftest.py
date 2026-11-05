"""Fixtures da interface: o jogo inteiro roda sem janela, dirigido por eventos reais e `App.step`."""
import threading
import time

import pygame
import pytest

from xadrez.data.paths import DATA_DIR_ENV
from xadrez.net.session import THREAD_NAME_PREFIX
from xadrez.ui import App
from xadrez.ui.autoplay import Autoplayer
from xadrez.ui.cpu_player import THREAD_NAME

_THREAD_EXIT_SECONDS = 15.0
_GAME_THREAD_PREFIXES = (THREAD_NAME, THREAD_NAME_PREFIX)


def game_threads():
    return [thread for thread in threading.enumerate() if thread.name.startswith(_GAME_THREAD_PREFIXES)]


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Nenhum teste pode tocar as contas de verdade: a pasta de dados de cada teste é temporária."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))


@pytest.fixture(autouse=True)
def no_game_thread_left_behind():
    """Nenhuma thread de CPU ou de rede pode sobrar depois de um teste."""
    yield
    deadline = time.monotonic() + _THREAD_EXIT_SECONDS
    while game_threads() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not game_threads(), f"thread ficou viva depois do teste: {game_threads()}"


@pytest.fixture
def app():
    application = App(seed=11)
    pygame.event.clear()
    yield application
    application.scene.shutdown()
    pygame.event.clear()


@pytest.fixture
def player(app):
    return Autoplayer(app)
