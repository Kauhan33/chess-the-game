"""Apoio dos ataques da versão 1.1: fixtures e atalhos. Não tem teste próprio.

Mora aqui, e não em um `conftest.py`, para os ataques não mudarem nada nas outras pastas de teste. Cada arquivo faz
`from test_ataque_v11_apoio import *` para receber as fixtures, inclusive as `autouse`.

- Toda pasta de dados é temporária: nada toca as contas de verdade.
- A rede é sempre `127.0.0.1`, em porta livre.
- Nenhuma thread de CPU ou de rede pode sobrar depois de um teste, e o `setswitchinterval` tem de voltar ao original.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np
import pygame
import pytest

_UI_TESTS = str(Path(__file__).resolve().parents[1] / "ui")
if _UI_TESTS not in sys.path:
    sys.path.insert(0, _UI_TESTS)

from ui_helpers import LoopbackNetwork, cell, drive  # noqa: E402

from xadrez.core import Color, Square, TimeControl  # noqa: E402
from xadrez.data.paths import DATA_DIR_ENV  # noqa: E402
from xadrez.net.session import THREAD_NAME_PREFIX  # noqa: E402
from xadrez.ui import App, GameMode, GameOverScene, GameScene, LobbyScene, MatchOptions  # noqa: E402
from xadrez.ui.autoplay import Autoplayer, click_point, post_click, post_key, post_mouse_move, post_text  # noqa: E402
from xadrez.ui.cpu_player import THREAD_NAME  # noqa: E402
from xadrez.ui.match import OPPONENT_CPU, OPPONENT_LOCAL  # noqa: E402

FRAME = 1.0 / 60.0
NET_SEGMENT = 2
GAME_THREAD_PREFIXES = (THREAD_NAME, THREAD_NAME_PREFIX)


def game_threads():
    return [thread for thread in threading.enumerate() if thread.name.startswith(GAME_THREAD_PREFIXES)]


def wait_threads_gone(limit=15.0):
    deadline = time.monotonic() + limit
    while game_threads() and time.monotonic() < deadline:
        time.sleep(0.005)
    return game_threads()


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def nothing_left_behind():
    """Sem thread viva e com o intervalo de troca de thread de volta: vale para todo ataque, em qualquer saída."""
    interval = sys.getswitchinterval()
    yield
    left = wait_threads_gone()
    assert not left, f"thread ficou viva depois do teste: {left}"
    assert sys.getswitchinterval() == interval, "setswitchinterval não voltou ao valor original"


@pytest.fixture
def app():
    application = App(seed=11)
    pygame.event.clear()
    yield application
    application.scene.shutdown()
    pygame.event.clear()


@pytest.fixture
def network():
    loopback = LoopbackNetwork()
    yield loopback
    loopback.close_all()


def make_app(network=None, seed=1, size=(1280, 720), require_login=False):
    application = App(size=size, seed=seed, network=network, require_login=require_login)
    pygame.event.clear()
    return application


@pytest.fixture
def host_app(network):
    application = make_app(network, 1)
    yield application
    application.scene.shutdown()


@pytest.fixture
def guest_app(network):
    application = make_app(network, 2)
    yield application
    application.scene.shutdown()


def open_game(app, fen=None, time_control=TimeControl.RAPID_10, mode=GameMode.MATCH, names=("Ana", "Bia"),
              auto_rotate=False, opponent_kind=OPPONENT_LOCAL, difficulty=None, human_color=Color.WHITE, settle=True):
    """Abre a partida como o menu abriria, com todas as opções à mão."""
    kwargs = {} if difficulty is None else {"difficulty": difficulty}
    options = MatchOptions(names[0], names[1], time_control, auto_rotate, mode, opponent_kind, human_color=human_color, **kwargs)
    app.scene.next_scene = app.game_scene(options.create_engine(fen), options)
    player = Autoplayer(app)
    player.frames(1)
    if settle and opponent_kind != OPPONENT_CPU:
        player.settle()
    return app.scene, player


def press_at(position, button=1):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=button))


def release_at(position, button=1):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=position, button=button))


def move_to(position, buttons=(1, 0, 0), rel=(0, 0)):
    post_mouse_move(position, rel, buttons)


def point_of(view, name):
    return click_point(view, cell(name))


def key(player, code):
    player.press(code)


def surface_array(surface, rect=None):
    target = surface if rect is None else surface.subsurface(rect)
    return pygame.surfarray.array3d(target).copy()


def diff_box(first, second):
    """Caixa `(x0, y0, x1, y1)` dos pixels que mudaram entre duas matrizes de tela, ou None se forem idênticas."""
    changed = np.any(first != second, axis=2)
    if not changed.any():
        return None
    xs, ys = np.nonzero(changed)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def changed_pixels_outside(first, second, keep_out):
    """Quantos pixels mudaram fora das caixas `keep_out`, na lista `(x0, y0, x1, y1)`."""
    changed = np.any(first != second, axis=2)
    for x0, y0, x1, y1 in keep_out:
        changed[max(x0, 0):max(x1, 0) + 1, max(y0, 0):max(y1, 0) + 1] = False
    return int(changed.sum())


def square_screen_box(view, name, height=1.6, margin=14):
    """Caixa em pixels de tudo que a peça de uma casa pode pintar, da sombra ao topo."""
    x, _, z = _square_world(name)
    points = np.array([(x + dx, y, z + dz) for dx in (-0.62, 0.62) for dz in (-0.62, 0.62) for y in (0.0, height)], dtype=float)
    pixels, _ = view.camera.project(points)
    return (int(pixels[:, 0].min()) - margin, int(pixels[:, 1].min()) - margin,
            int(pixels[:, 0].max()) + margin, int(pixels[:, 1].max()) + margin)


def _square_world(name):
    from xadrez.graphics import square_to_world
    return square_to_world(*cell(name))


class Table:
    """Duas telas reais em rede, em turnos: cada ação passa pelo `App` de quem joga."""

    def __init__(self, host_app, guest_app):
        self.host_app, self.guest_app = host_app, guest_app
        self.apps = (host_app, guest_app)
        self.host_player, self.guest_player = Autoplayer(host_app), Autoplayer(guest_app)

    @property
    def host(self):
        return self.host_app.scene

    @property
    def guest(self):
        return self.guest_app.scene

    def player_of_turn(self):
        return self.host_player if self.host.engine.turn is self.host.local_color else self.guest_player

    def settle(self):
        drive(self.apps, self._is_settled)

    def _is_settled(self):
        scenes = (self.host, self.guest)
        return all(isinstance(scene, GameScene) for scene in scenes) and all(
            not scene.view.is_flying and not scene.view.is_camera_moving and not scene.net.link.inbox for scene in scenes
        )

    def play(self, uci):
        ply = len(self.host.engine.history)
        player = self.player_of_turn()
        player.click_square(cell(uci[:2]))
        player.click_square(cell(uci[2:4]))
        if len(uci) > 4:
            player.choose_promotion(uci[4])
        host, guest = self.host, self.guest
        drive(self.apps, lambda: len(host.engine.history) == len(guest.engine.history) == ply + 1)
        if host.engine.result is None:
            self.settle()

    def play_all(self, moves):
        for uci in moves.split():
            self.play(uci)

    def both_over(self):
        return isinstance(self.host, GameOverScene) and isinstance(self.guest, GameOverScene)

    def run_until_both_over(self, limit=30.0):
        drive(self.apps, self.both_over, limit)

    def steps(self, count, dt=FRAME):
        for _ in range(count):
            for application in self.apps:
                application.step(dt)


def open_room(app, time_control=None):
    player = Autoplayer(app)
    menu = app.scene
    player.click_segment(menu.opponent_selector, NET_SEGMENT)
    if time_control is not None:
        menu.time_selector.options.append(("Teste", time_control))
        menu.time_selector.select(len(menu.time_selector.options) - 1)
    player.click_widget(menu.create_room_button)
    assert isinstance(app.scene, LobbyScene)
    return app.scene


def join_room(app, code):
    player = Autoplayer(app)
    menu = app.scene
    player.click_segment(menu.opponent_selector, NET_SEGMENT)
    player.click_widget(menu.join_room_button)
    lobby = app.scene
    assert isinstance(lobby, LobbyScene)
    post_text(code)
    player.frames(1)
    player.press(pygame.K_RETURN)
    return lobby


def connected_table(host_app, guest_app, time_control=None):
    lobby = open_room(host_app, time_control)
    join_room(guest_app, lobby.code)
    table = Table(host_app, guest_app)
    table.settle()
    return table


def connect_raw(app, network, time_control=None, name="Crua"):
    """Uma tela de um lado e, do outro, só a sessão: o teste manda o que uma tela nunca mandaria."""
    lobby = open_room(app, time_control)
    raw = network.client(name, lobby.code)
    raw.start()
    player = Autoplayer(app)
    deadline = time.monotonic() + 30.0
    while not isinstance(app.scene, GameScene):
        assert time.monotonic() < deadline, "a partida não começou"
        player.frames(1)
    player.settle()
    return app.scene, player, raw


def wait_until(app, condition, limit=30.0, dt=0.0):
    """Quadros de tempo zero: o relógio e as animações ficam parados até a mensagem chegar."""
    deadline = time.monotonic() + limit
    while not condition():
        assert time.monotonic() < deadline, "a condição não aconteceu no prazo"
        time.sleep(0.0005)
        app.step(dt)


def fast_forward_clock(scene, color, seconds_left):
    """Deixa o relógio de `color` com `seconds_left`, sem esperar: só para montar o cenário."""
    clock = scene.engine.clock
    clock._remaining[color] = seconds_left


__all__ = [name for name in globals() if not name.startswith("__")]
