"""Gera, sem janela, os prints reais de cada tela em docs/img/.

Cada tela é alcançada por eventos reais de mouse e teclado, como em uma partida de verdade. Nada aqui grava na
pasta de dados: o histórico do print fica em memória, e a sala em rede só escuta em 127.0.0.1, para o código
do print não revelar o endereço desta máquina.

Uso: python tools/capturar_telas.py [--size 1280x720] [--out docs/img] [--only tela_menu,tela_xeque]
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Uma pasta que não existe: o print do login errado consulta as contas e não pode ler as de verdade.
os.environ["CHESS_THE_GAME_DATA"] = str(ROOT / "build" / "sem-dados")

import pygame

from xadrez.core import Color, Difficulty, Square, TimeControl
from xadrez.data import HistoryStats
from xadrez.net import ClientSession, HostSession
from xadrez.ui import App, GameMode, MatchOptions
from xadrez.ui.autoplay import Autoplayer, post_click, post_key, post_mouse_move, post_text
from xadrez.ui.lobby_scene import ROLE_GUEST, ROLE_HOST
from xadrez.ui.match import OPPONENT_CPU
from xadrez.ui.match_record import build_record

SEED = 7
OPTIONS = MatchOptions("Jogador 1", "Jogador 2", TimeControl.RAPID_10, auto_rotate=True)
MIDDLE_GAME = "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5c6 d7c6 f3e5 d8d4 e5f3 d4d6 e1g1 c8g4"
PATHS_LINE = "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6"
THREAT_LINE = "e2e4 e7e5 g1f3 b8c6 f1c4"
CHECK_LINE = "e2e4 d7d5 f1b5"
SCHOLARS_MATE = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
FOOLS_MATE = "f2f3 e7e5 g2g4 d8h4"
PROMOTION_FEN = "r3k2r/1P3ppp/8/8/8/8/5PPP/4K2R w K - 0 1"
_LOOPBACK = "127.0.0.1"


class LoopbackNetwork:
    """Sala de verdade, só em 127.0.0.1 e em porta livre."""

    def __init__(self) -> None:
        self.port = 0

    def host(self, name: str, time_control: TimeControl) -> HostSession:
        session = HostSession(name, time_control, port=0, bind=_LOOPBACK)
        self.port = session.port
        return session

    def client(self, name: str, code: str) -> ClientSession:
        return ClientSession(name, code, port=self.port)


class MemoryHistory:
    """Histórico do print: partidas de verdade, jogadas no motor, sem gravar nada em disco."""

    def __init__(self, records: list) -> None:
        self._records = records

    def records(self) -> list:
        return self._records

    def stats(self) -> HistoryStats:
        outcomes = [record.outcome for record in self._records]
        return HistoryStats(len(outcomes), outcomes.count("vitoria"), outcomes.count("derrota"), outcomes.count("empate"))


def played_record(moves: str, played_at: str, seconds: float, options: MatchOptions, local_color: Color = Color.WHITE,
                  resign: Color | None = None):
    engine = options.create_engine(human_color=local_color)
    for uci in moves.split():
        engine.play(Square.from_name(uci[:2]), Square.from_name(uci[2:4]))
    if resign is not None:
        engine.resign(resign)
    elif engine.result is None:
        engine.agree_draw()
    return replace(build_record(engine, options, engine.players[local_color]), played_at=played_at, seconds=seconds)


def sample_records() -> list:
    hard = replace(OPTIONS, opponent_kind=OPPONENT_CPU, difficulty=Difficulty.HARD, mode=GameMode.MATCH,
                   time_control=TimeControl.BLITZ_3_2)
    easy = replace(OPTIONS, opponent_kind=OPPONENT_CPU, difficulty=Difficulty.EASY)
    return [
        played_record(SCHOLARS_MATE, "2026-11-05T19:42:00", 214.5, hard),
        played_record(FOOLS_MATE, "2026-11-05T19:30:00", 95.2, hard),
        played_record(MIDDLE_GAME, "2026-11-04T21:15:00", 842.0, OPTIONS),
        played_record(MIDDLE_GAME + " h2h3", "2026-11-04T20:40:00", 1320.0, easy, Color.BLACK, resign=Color.WHITE),
        played_record(PATHS_LINE, "2026-11-03T18:05:00", 480.0, OPTIONS, resign=Color.BLACK),
        played_record(THREAT_LINE, "2026-11-03T17:20:00", 305.0, easy, Color.BLACK, resign=Color.BLACK),
        played_record(CHECK_LINE, "2026-11-02T22:10:00", 77.0, OPTIONS),
        played_record(SCHOLARS_MATE, "2026-11-02T21:45:00", 188.0, OPTIONS),
    ]


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


def capture_login(app: App) -> None:
    player = Autoplayer(app)
    scene = app.scene
    post_text("Jogador 1")
    player.frames(1)
    player.click_widget(scene.password_input)
    post_text("senha de exemplo")
    player.seconds(0.6)


def capture_login_error(app: App) -> None:
    player = Autoplayer(app)
    scene = app.scene
    post_text("Jogador 1")
    player.frames(1)
    player.click_widget(scene.password_input)
    post_text("senha errada")
    player.frames(1)
    post_key(pygame.K_RETURN)
    player.seconds(0.6)


def capture_create_account(app: App) -> None:
    player = Autoplayer(app)
    scene = app.scene
    player.click_segment(scene.mode_selector, 1)
    player.seconds(0.6)


def capture_menu(app: App) -> None:
    Autoplayer(app).seconds(0.6)


def capture_menu_cpu(app: App) -> None:
    player = Autoplayer(app)
    menu = app.scene
    player.click_segment(menu.opponent_selector, 1)
    player.click_segment(menu.difficulty_selector, 2)
    player.seconds(0.6)


def capture_menu_network(app: App) -> None:
    player = Autoplayer(app)
    player.click_segment(app.scene.opponent_selector, 2)
    player.seconds(0.6)


def capture_room(app: App) -> None:
    app.scene.next_scene = app.lobby_scene(OPTIONS, ROLE_HOST)
    Autoplayer(app).seconds(0.8)


def capture_join_room(app: App) -> None:
    app.scene.next_scene = app.lobby_scene(OPTIONS, ROLE_GUEST)
    player = Autoplayer(app)
    player.frames(1)
    post_text("ABC")
    player.seconds(0.4)


def capture_game(app: App) -> None:
    player = start_match(app)
    think(player, 7.4)
    player.play_all(MIDDLE_GAME)
    think(player, 12.0)
    rest_mouse(player)


def capture_help(app: App) -> None:
    player = start_match(app)
    player.press(pygame.K_h)
    player.frames(2)


def capture_paths(app: App, options: MatchOptions = OPTIONS) -> None:
    player = start_match(app, options=options)
    player.play_all(PATHS_LINE)
    think(player, 3.0)
    player.click_square((1, 4))
    player.frames(3)
    rest_mouse(player)


def capture_match_mode(app: App) -> None:
    """A mesma posição de `tela_caminhos`, com a mesma peça selecionada: no modo Partida, nenhuma dica aparece."""
    capture_paths(app, replace(OPTIONS, mode=GameMode.MATCH))


def capture_cpu_thinking(app: App) -> None:
    options = replace(OPTIONS, opponent_kind=OPPONENT_CPU, difficulty=Difficulty.HARDCORE, human_color=Color.WHITE,
                      time_control=TimeControl.CLASSIC_15_10)
    player = start_match(app, options=options)
    player.play("e2e4")
    player.frames(20)
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


def _open_history_tab(app: App) -> tuple:
    records = sample_records()
    app.account = "Jogador 1"
    app.history_store = lambda: MemoryHistory(records)
    app.scene.next_scene = app.menu_scene()
    player = Autoplayer(app)
    player.frames(1)
    menu = app.scene
    player.click_segment(menu.tab_bar, 1)
    return menu, player


def capture_history(app: App) -> None:
    menu, player = _open_history_tab(app)
    rest_mouse(player)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(1)
    rest_mouse(player)
    player.seconds(0.4)


def capture_history_list(app: App) -> None:
    _, player = _open_history_tab(app)
    rest_mouse(player)
    player.seconds(0.4)


def capture_history_guest(app: App) -> None:
    player = Autoplayer(app)
    player.click_segment(app.scene.tab_bar, 1)
    rest_mouse(player)
    player.seconds(0.4)


SCREENS = {
    "tela_login": capture_login,
    "tela_login_erro": capture_login_error,
    "tela_criar_conta": capture_create_account,
    "tela_menu": capture_menu,
    "tela_menu_cpu": capture_menu_cpu,
    "tela_menu_rede": capture_menu_network,
    "tela_sala": capture_room,
    "tela_entrar_sala": capture_join_room,
    "tela_partida": capture_game,
    "tela_caminhos": capture_paths,
    "tela_modo_partida": capture_match_mode,
    "tela_cpu_pensando": capture_cpu_thinking,
    "tela_ameaca": capture_threat,
    "tela_xeque": capture_check,
    "tela_pausa": capture_pause,
    "tela_promocao": capture_promotion,
    "tela_vitoria": capture_victory,
    "tela_empate": capture_draw,
    "tela_didatico": capture_didactic,
    "tela_ajuda": capture_help,
    "tela_desempenho": capture_performance,
    "tela_historico": capture_history,
    "tela_historico_lista": capture_history_list,
    "tela_historico_convidado": capture_history_guest,
}
_LOGIN_SCREENS = {"tela_login", "tela_login_erro", "tela_criar_conta"}
_NETWORK_SCREENS = {"tela_sala", "tela_entrar_sala"}


def parse_size(text: str) -> tuple[int, int]:
    width, height = text.lower().split("x")
    return int(width), int(height)


def open_app(name: str, size: tuple[int, int]) -> App:
    network = LoopbackNetwork() if name in _NETWORK_SCREENS else None
    return App(size, seed=SEED, require_login=name in _LOGIN_SCREENS, network=network)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=parse_size, default=(1280, 720))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "img")
    parser.add_argument("--only", default=None, help="Nomes das telas separados por vírgula.")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    names = args.only.split(",") if args.only else list(SCREENS)
    for name in names:
        app = open_app(name, args.size)
        pygame.event.clear()
        SCREENS[name](app)
        path = args.out / f"{name}.png"
        pygame.image.save(app.screen, str(path))
        app.scene.shutdown()
        print("salvo", path)
    pygame.quit()


if __name__ == "__main__":
    main()
