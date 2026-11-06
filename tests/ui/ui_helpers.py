"""Atalhos dos testes da interface. Tudo passa por eventos: nenhum teste joga pelo motor direto."""
import random
import time

import pygame

from xadrez.core import Color, Difficulty, Square, TimeControl, legal_moves
from xadrez.net import ClientSession, HostSession, NetTimings
from xadrez.ui import GameMode, MatchOptions
from xadrez.ui.autoplay import Autoplayer, click_point, post_mouse_move
from xadrez.ui.match import OPPONENT_CPU, OPPONENT_LOCAL

# Partida curta e completa: capturas, xeques, roque grande e mate no lance 17.
FULL_GAME = (
    "e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 "
    "c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8"
)
SCHOLARS_MATE = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
ENDING_SECONDS = 3.0
# Prazo só de falha: o teste segue assim que a condição vale, então a folga não o deixa mais lento.
WAIT_SECONDS = 60.0
FRAME_SECONDS = 1.0 / 60.0
LOCALHOST = "127.0.0.1"
# Sinal de vida real, com o ciclo da sessão rápido: uma pausa do CI não pode virar queda de conexão.
QUICK = NetTimings(tick=0.002)


def cell(name):
    return tuple(Square.from_name(name))


def start_game(app, fen=None, time_control=TimeControl.RAPID_10, auto_rotate=True, names=("Jogador 1", "Jogador 2"),
               mode=GameMode.TRAINING, opponent_kind=OPPONENT_LOCAL, difficulty=Difficulty.MEDIUM, human_color=Color.WHITE):
    """Abre a partida como o menu abriria e espera a câmera assentar."""
    options = MatchOptions(names[0], names[1], time_control, auto_rotate, mode, opponent_kind, difficulty, human_color)
    app.scene.next_scene = app.game_scene(options.create_engine(fen), options)
    player = Autoplayer(app)
    player.frames(1)
    player.settle()
    return app.scene, player


def start_cpu_game(app, difficulty=Difficulty.EASY, human_color=Color.WHITE, **options):
    return start_game(app, opponent_kind=OPPONENT_CPU, difficulty=difficulty, human_color=human_color, **options)


def open_cpu_game(app, difficulty=Difficulty.EASY, human_color=Color.BLACK, fen=None, time_control=TimeControl.RAPID_10,
                  mode=GameMode.TRAINING):
    """Abre a partida sem esperar a câmera: quando a CPU começa, o teste quer vê-la pensando."""
    options = MatchOptions("Jogador 1", "Jogador 2", time_control, False, mode, OPPONENT_CPU, difficulty, human_color)
    app.scene.next_scene = app.game_scene(options.create_engine(fen), options)
    app.step(0.0)
    return app.scene, Autoplayer(app)


def wait_for_cpu(app, scene, limit=WAIT_SECONDS):
    """Espera a jogada da CPU. Com a thread viva o relógio do jogo não anda, porque aqui o quadro é mais rápido que o real."""
    deadline = time.monotonic() + limit
    while scene.cpu.is_thinking:
        assert time.monotonic() < deadline, "a CPU não respondeu no prazo"
        if scene.cpu._job.thread.is_alive():
            time.sleep(0.001)
            app.step(0.0)
        else:
            app.step(FRAME_SECONDS)


def play_random_move(player, scene, rng):
    move = rng.choice(legal_moves(scene.engine.board))
    player.click_square(tuple(move.origin))
    player.click_square(tuple(move.target))
    if scene.modals:
        player.press(pygame.K_1)
    player.settle()


def new_rng(seed=3):
    return random.Random(seed)


def hud_button(scene, label):
    return next(button for button in scene.hud.buttons if button.label == label)


def resign_by_buttons(player, scene):
    player.click_widget(hud_button(scene, "Desistir"))
    player.click_widget(scene.modals[-1].buttons[0])


def click(player, name):
    player.click_square(cell(name))


def hover(player, name):
    post_mouse_move(click_point(player.view, cell(name)))
    player.frames(1)


def move_mouse_off_board(player):
    post_mouse_move((player.app.size[0] - 2, 2))
    player.frames(1)


def state_at(scene, name):
    return scene.view.matrix.state_at(*cell(name))


def resize(player, size):
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
    player.frames(1)


def finish_with_mate(player):
    player.play_all(SCHOLARS_MATE)
    player.seconds(ENDING_SECONDS)


class LoopbackNetwork:
    """Sessões reais em 127.0.0.1 e porta livre: quem entra na sala usa a porta da última que abriu."""

    def __init__(self, timings=QUICK):
        self.timings = timings
        self.opened = []
        self.last_host = None

    def host(self, name, time_control, mode="training"):
        self.last_host = self._track(HostSession(name, time_control, port=0, bind=LOCALHOST, timings=self.timings, mode=mode))
        return self.last_host

    def client(self, name, code):
        port = self.last_host.port if self.last_host is not None else 9
        return self._track(ClientSession(name, code, port=port, timeout=5.0, timings=self.timings))

    def _track(self, session):
        self.opened.append(session)
        return session

    def close_all(self):
        for session in self.opened:
            session.close()


def drive(apps, condition, limit=WAIT_SECONDS):
    """Quadros nos dois jogos até a condição valer. Os dois dividem a fila de eventos, então um de cada vez."""
    deadline = time.monotonic() + limit
    while not condition():
        assert time.monotonic() < deadline, "a condição não aconteceu no prazo"
        for app in apps:
            app.step(FRAME_SECONDS)
        time.sleep(0.0005)
