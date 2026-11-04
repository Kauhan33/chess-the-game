"""Atalhos dos testes da interface. Tudo passa por eventos: nenhum teste joga pelo motor direto."""
import pygame

from xadrez.core import Square, TimeControl
from xadrez.ui import MatchOptions
from xadrez.ui.autoplay import Autoplayer, click_point, post_mouse_move

# Partida curta e completa: capturas, xeques, roque grande e mate no lance 17.
FULL_GAME = (
    "e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 "
    "c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8"
)
SCHOLARS_MATE = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
ENDING_SECONDS = 3.0


def cell(name):
    return tuple(Square.from_name(name))


def start_game(app, fen=None, time_control=TimeControl.RAPID_10, auto_rotate=True, names=("Jogador 1", "Jogador 2")):
    """Abre a partida como o menu abriria e espera a câmera assentar."""
    options = MatchOptions(names[0], names[1], time_control, auto_rotate)
    app.scene.next_scene = app.game_scene(options.create_engine(fen), options)
    player = Autoplayer(app)
    player.frames(1)
    player.settle()
    return app.scene, player


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
