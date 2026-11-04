"""Gera, sem janela, os prints reais de cada tela em docs/img/.

Cada tela é alcançada por eventos reais de mouse e teclado, como em uma partida de verdade.

Uso: python tools/capturar_telas.py [--size 1280x720] [--out docs/img] [--only tela_menu,tela_xeque]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame

from xadrez.core import TimeControl
from xadrez.ui import App, MatchOptions
from xadrez.ui.autoplay import Autoplayer, post_mouse_move

SEED = 7
OPTIONS = MatchOptions("Jogador 1", "Jogador 2", TimeControl.RAPID_10, auto_rotate=True)
MIDDLE_GAME = "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5c6 d7c6 f3e5 d8d4 e5f3 d4d6 e1g1 c8g4"
PATHS_LINE = "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6"
THREAT_LINE = "e2e4 e7e5 g1f3 b8c6 f1c4"
CHECK_LINE = "e2e4 d7d5 f1b5"
SCHOLARS_MATE = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
PROMOTION_FEN = "r3k2r/1P3ppp/8/8/8/8/5PPP/4K2R w K - 0 1"


def start_match(app: App, fen: str | None = None, options: MatchOptions = OPTIONS) -> Autoplayer:
    app.scene.next_scene = app.game_scene(options.create_engine(fen), options)
    player = Autoplayer(app)
    player.frames(1)
    player.settle()
    return player


def think(player: Autoplayer, seconds: float) -> None:
    player.seconds(seconds)


def rest_mouse(player: Autoplayer) -> None:
    """Tira o mouse de cima do tabuleiro, para o cursor não aparecer onde não interessa."""
    post_mouse_move((player.app.size[0] - 2, player.app.size[1] // 2))
    player.frames(2)


def capture_menu(app: App) -> None:
    Autoplayer(app).seconds(0.6)


def capture_help(app: App) -> None:
    player = start_match(app)
    player.press(pygame.K_h)
    player.frames(2)


def capture_game(app: App) -> None:
    player = start_match(app)
    think(player, 7.4)
    player.play_all(MIDDLE_GAME)
    think(player, 12.0)
    rest_mouse(player)


def capture_paths(app: App) -> None:
    player = start_match(app)
    player.play_all(PATHS_LINE)
    think(player, 3.0)
    player.click_square((1, 4))
    player.frames(3)
    rest_mouse(player)


def capture_threat(app: App) -> None:
    player = start_match(app)
    player.play_all(THREAT_LINE)
    rest_mouse(player)
    player.frames(8)


def capture_check(app: App) -> None:
    player = start_match(app)
    player.play_all(CHECK_LINE)
    rest_mouse(player)
    player.frames(8)


def capture_pause(app: App) -> None:
    player = start_match(app)
    player.play_all(MIDDLE_GAME)
    rest_mouse(player)
    player.press(pygame.K_p)
    player.frames(2)


def capture_promotion(app: App) -> None:
    player = start_match(app, PROMOTION_FEN)
    player.click_square((1, 6))
    player.click_square((1, 7))
    player.frames(2)


def capture_victory(app: App) -> None:
    player = start_match(app)
    think(player, 2.0)
    player.play_all(SCHOLARS_MATE)
    player.seconds(3.6)


def capture_draw(app: App) -> None:
    player = start_match(app)
    player.play_all(MIDDLE_GAME)
    player.press(pygame.K_p)
    scene = app.scene
    player.click_widget(scene.modals[-1].buttons[2])
    player.click_widget(scene.modals[-1].buttons[0])
    player.seconds(2.4)


def capture_didactic(app: App) -> None:
    player = start_match(app)
    player.play_all(THREAT_LINE)
    player.press(pygame.K_F4)
    player.frames(3)
    player.click_square((6, 7))
    player.frames(10)


def capture_performance(app: App) -> None:
    """Único print em tempo real: o FPS do painel F3 precisa ser medido, não calculado."""
    player = start_match(app)
    player.play_all(THREAT_LINE)
    rest_mouse(player)
    player.press(pygame.K_F3)
    Autoplayer(app, app.run_frame).seconds(1.5)


SCREENS = {
    "tela_menu": capture_menu,
    "tela_partida": capture_game,
    "tela_caminhos": capture_paths,
    "tela_ameaca": capture_threat,
    "tela_xeque": capture_check,
    "tela_pausa": capture_pause,
    "tela_promocao": capture_promotion,
    "tela_vitoria": capture_victory,
    "tela_empate": capture_draw,
    "tela_didatico": capture_didactic,
    "tela_ajuda": capture_help,
    "tela_desempenho": capture_performance,
}


def parse_size(text: str) -> tuple[int, int]:
    width, height = text.lower().split("x")
    return int(width), int(height)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=parse_size, default=(1280, 720))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "img")
    parser.add_argument("--only", default=None, help="Nomes das telas separados por vírgula.")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    names = args.only.split(",") if args.only else list(SCREENS)
    for name in names:
        app = App(args.size, seed=SEED)
        pygame.event.clear()
        SCREENS[name](app)
        path = args.out / f"{name}.png"
        pygame.image.save(app.screen, str(path))
        print("salvo", path)
    pygame.quit()


if __name__ == "__main__":
    main()
