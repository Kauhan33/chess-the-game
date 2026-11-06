"""Macaco da versão 1.1: eventos com semente por todas as telas, com CPU em cada nível e um robô de verdade na rede.

CT-130: login, menu, histórico, sala, partida contra a CPU e em rede, e tela de fim, sem exceção, sem quebrar invariante e sem sobrar thread.

O robô é uma sessão real em 127.0.0.1. Ele joga lances legais e, de vez em quando, desiste, propõe empate, pede revanche, some ou manda lixo.
Em caso de falha, a mensagem traz a semente, o quadro e os eventos. Para reduzir, rode `run_monkey(semente, quadro + 1)`.
"""
from __future__ import annotations

import random
import sys
import time

import pygame
import pytest
from test_ataque_v11_apoio import *  # noqa: F403

from xadrez.core import Board, Color, Difficulty, EndReason, GameEngine, GameResult, GameState, TimeControl, legal_moves, move_to_san
from xadrez.data import HistoryStore, MatchRecord
from xadrez.data import accounts as accounts_module
from xadrez.net import ClientSession, DrawOffered, GameStart, HostSession, MoveReceived, NetTimings, NetworkError, PeerLeft, RematchRequested, parse_uci
from xadrez.net.room_code import encode_room_code
from xadrez.ui import LoginScene, MenuScene, cpu_player
from xadrez.ui.autoplay import click_point
from xadrez.ui.history_panel import HistoryList
from xadrez.ui.widgets import SegmentedControl, TextInput

SECRET = "ZZSENHAMACACOZZ"
ACCOUNT = "Macaco"
QUICK = NetTimings(tick=0.002)
ROOM_CODE = encode_room_code("127.0.0.1")
KEYS = [
    pygame.K_p, pygame.K_r, pygame.K_t, pygame.K_v, pygame.K_h, pygame.K_f, pygame.K_c, pygame.K_F1, pygame.K_F3, pygame.K_F4, pygame.K_F11,
    pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_TAB, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT,
    pygame.K_RIGHT, pygame.K_BACKSPACE, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_a, pygame.K_DELETE, pygame.K_PAGEUP,
    pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END, pygame.K_0, pygame.K_F12, pygame.K_LSHIFT,
]
TEXTS = [
    "a", "Z", "Ç", "ã", "João", ACCOUNT, ROOM_CODE, ROOM_CODE.lower(), "abc def", "\U0001f600", "\x00", "\x07", "\n", "\t", "\x7f", chr(0x200b), chr(0x202e),
    "W" * 40, " ", "     ", "x" * 500, "ﷺ", "한글", "مرحبا", "é", "́" * 8, "%s%d{0}", "../..", "' OR 1=1", chr(0xffff),
]
DTS = [1 / 60] * 24 + [0.0, 0.0, 0.1, 0.5, 5.0, 1e9, -1.0, 1 / 240, float("nan")]
SIZES = [(1, 1), (50, 2000), (3000, 200), (1280, 720), (640, 360), (200, 200), (1920, 1080), (800, 600), (1024, 640), (320, 240)]
HOSTILE_NAMES = ["W" * 16, "́" * 16, "\U0001f600" * 8, "ﷺ" * 16, "مرحبا", '"]', "Robô"]
GAME_SCENES = (LoginScene, MenuScene, LobbyScene, GameScene, GameOverScene)


class Robot:
    """O outro lado da rede: uma sessão real, com um motor próprio para saber o que é legal."""

    def __init__(self, session, rng):
        self.session = session
        self.rng = rng
        self.engine = None
        self.color = None
        self.is_gone = False
        self.has_published = False

    def tick(self):
        if self.is_gone:
            return
        for event in self.session.poll():
            self._receive(event)
        if self.engine is None or self.is_gone:
            return
        self._publish_result()
        roll = self.rng.random()
        if roll < 0.0004:
            self._leave()
        elif roll < 0.0008:
            self.session.send_move("a1a1", 0)
        elif roll < 0.0012 and self.session.is_authority:
            # A sala tem a palavra final, e pode decidir mesmo com um lance da tela a caminho.
            self.session.send_result(GameResult(self.color, EndReason.RESIGNATION), len(self.engine.history))
        elif roll < 0.0012:
            self.session.send_resign()
        elif roll < 0.003:
            self.session.send_draw_offer()
        elif roll < 0.004:
            self.session.send_rematch()
        elif roll < 0.12 and self.engine.result is None and self.engine.turn is self.color:
            move = self.rng.choice(legal_moves(self.engine.board))
            if self.engine.play(move.origin, move.target, move.promotion).ok:
                self.session.send_move(move.uci, self.rng.randint(0, 900000))

    def _publish_result(self):
        """A sala avisa quando o próprio tabuleiro encerrou a partida, como o jogo de verdade."""
        is_new_end = self.engine.result is not None and not self.has_published
        if self.session.is_authority and is_new_end:
            self.has_published = True
            self.session.send_result(self.engine.result, len(self.engine.history))

    def _receive(self, event):
        if isinstance(event, GameStart):
            self.engine = GameEngine(event.white, event.black, TimeControl(event.minutes, event.increment))
            self.color = event.your_color
            self.has_published = False
        elif isinstance(event, MoveReceived) and self.engine is not None:
            self.engine.play(*parse_uci(event.uci))
        elif isinstance(event, DrawOffered):
            self.session.send_draw_answer(self.rng.random() < 0.3)
        elif isinstance(event, RematchRequested) and self.rng.random() < 0.5:
            self.session.send_rematch()
        elif isinstance(event, (PeerLeft, NetworkError)):
            self.is_gone = True

    def _leave(self):
        self.is_gone = True
        self.session.send_bye()
        self.session.close()


class RobotNetwork:
    """Sessões reais em porta livre de 127.0.0.1. Cada sala aberta pela tela recebe um robô depois de um tempo."""

    def __init__(self, rng):
        self.rng = rng
        self.sessions = []
        self.robots = []
        self.waiting_hosts = []

    def host(self, name, time_control, mode):
        session = HostSession(name, time_control, port=0, bind="127.0.0.1", timings=QUICK, mode=mode)
        self.sessions.append(session)
        self.waiting_hosts.append(session)
        return session

    def client(self, name, code):
        room = HostSession(self.rng.choice(HOSTILE_NAMES), self.rng.choice((TimeControl.BLITZ_3_2, TimeControl.UNLIMITED, TimeControl(0.05))),
                           port=0, bind="127.0.0.1", timings=QUICK)
        room.start()
        self.sessions.append(room)
        self.robots.append(Robot(room, self.rng))
        session = ClientSession(name, code, port=room.port, timeout=0.5, timings=QUICK)
        self.sessions.append(session)
        return session

    def tick(self):
        for host in list(self.waiting_hosts):
            if host.port != 0 and self.rng.random() < 0.3:
                self.waiting_hosts.remove(host)
                client = ClientSession(self.rng.choice(HOSTILE_NAMES), "127.0.0.1", port=host.port, timings=QUICK)
                client.start()
                self.sessions.append(client)
                self.robots.append(Robot(client, self.rng))
        for robot in self.robots:
            robot.tick()

    def close_all(self):
        for session in self.sessions:
            session.close()


class Monkey:
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def targets(self, scene):
        if isinstance(scene, GameScene):
            if not scene.modals:
                return [button.rect.center for button in scene.hud.buttons]
            top = scene.modals[-1]
            rects = [button.rect.center for button in getattr(top, "buttons", [])]
            close = getattr(top, "_close_button", None)
            return rects + ([close.rect.center] if close is not None else [])
        if isinstance(scene, MenuScene) and scene.modal is not None:
            return [scene.modal._close_button.rect.center]
        points = []
        for widget in scene.focus.widgets:
            if isinstance(widget, SegmentedControl):
                points += [widget.segment_rect(index).center for index in range(len(widget.options))]
            elif isinstance(widget, HistoryList):
                points += [widget.row_rect(index).center for index in range(len(widget.records)) if widget.rect.collidepoint(widget.row_rect(index).center)]
            else:
                points.append(widget.rect.center)
        return points

    def position(self, app):
        rng, scene = self.rng, app.scene
        width, height = app.size
        choice = rng.random()
        if choice < 0.55:
            points = self.targets(scene)
            if points:
                return rng.choice(points)
        if choice < 0.8 and isinstance(scene, (GameScene, GameOverScene)):
            x, y, w, h = scene.view.camera.viewport
            return rng.randint(x + w // 8, x + max(w * 7 // 8, 1)), rng.randint(y + h // 10, y + max(h * 9 // 10, 1))
        return rng.randint(-20, width + 20), rng.randint(-20, height + 20)

    @staticmethod
    def click(position, button=1):
        return [
            pygame.event.Event(pygame.MOUSEMOTION, pos=position, rel=(0, 0), buttons=(0, 0, 0)),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=button),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=position, button=button),
        ]

    def legal_play(self, app):
        scene = app.scene
        if not isinstance(scene, GameScene):
            return []
        if scene.modals:
            if self.rng.random() < 0.5:
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0)]
            return []
        if scene.engine.result is not None or scene.view.is_flying or not scene.is_local_turn:
            return []
        move = self.rng.choice(legal_moves(scene.engine.board))
        origin, target = click_point(scene.view, tuple(move.origin)), click_point(scene.view, tuple(move.target))
        if self.rng.random() < 0.3:
            return [
                pygame.event.Event(pygame.MOUSEMOTION, pos=origin, rel=(0, 0), buttons=(0, 0, 0)),
                pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=origin, button=1),
                pygame.event.Event(pygame.MOUSEMOTION, pos=((origin[0] + target[0]) // 2, (origin[1] + target[1]) // 2), rel=(0, 0), buttons=(1, 0, 0)),
                pygame.event.Event(pygame.MOUSEMOTION, pos=target, rel=(0, 0), buttons=(1, 0, 0)),
                pygame.event.Event(pygame.MOUSEBUTTONUP, pos=target, button=1),
            ]
        return self.click(origin) + self.click(target)

    def typing(self, app):
        scene = app.scene
        focused = getattr(getattr(scene, "focus", None), "focused", None)
        if not isinstance(focused, TextInput):
            return self.rng.choice(TEXTS)
        if focused.is_secret:
            return SECRET
        if isinstance(scene, LobbyScene) and self.rng.random() < 0.7:
            return ROOM_CODE
        if isinstance(scene, LoginScene) and self.rng.random() < 0.7:
            return ACCOUNT
        return self.rng.choice(TEXTS)

    def one(self, app):
        rng = self.rng
        if rng.random() < 0.4:
            play = self.legal_play(app)
            if play:
                return play
        roll = rng.random()
        if roll < 0.34:
            return self.click(self.position(app), rng.choice((1, 1, 1, 1, 1, 3, 2, 4, 5)))
        if roll < 0.40:
            return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=self.position(app), button=rng.choice((1, 3)))]
        if roll < 0.46:
            return [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=self.position(app), button=rng.choice((1, 3)))]
        if roll < 0.56:
            return [pygame.event.Event(pygame.MOUSEMOTION, pos=self.position(app), rel=(rng.randint(-400, 400), rng.randint(-400, 400)),
                                       buttons=rng.choice(((0, 0, 0), (0, 0, 1), (1, 0, 0), (1, 1, 1))))]
        if roll < 0.60:
            return [pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=rng.choice((-30, -3, -1, 1, 3, 30)), flipped=False)]
        if roll < 0.84:
            code, mod = rng.choice(KEYS), rng.choice((0, 0, 0, pygame.KMOD_SHIFT, pygame.KMOD_CTRL))
            return [pygame.event.Event(kind, key=code, mod=mod, unicode="", scancode=0) for kind in (pygame.KEYDOWN, pygame.KEYUP)]
        if roll < 0.95:
            return [pygame.event.Event(pygame.TEXTINPUT, text=self.typing(app))]
        if rng.random() < 0.2:
            size = rng.choice(SIZES)
            return [pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1])]
        return []

    def frame_events(self, app):
        events = []
        for _ in range(self.rng.choice((0, 0, 1, 1, 1, 2, 3, 6))):
            events += self.one(app)
        # O foco pode mudar com os eventos anteriores do quadro: a senha só vale como primeiro evento, no campo certo.
        return [event for position, event in enumerate(events) if position == 0 or getattr(event, "text", "") != SECRET]


class HistoryReplay:
    """Refaz cada SAN em um tabuleiro próprio. Partida nova tem lista nova: reiniciar e jogar no mesmo quadro não engana a conta.

    A lista também encurta quando a sala não aceita o lance de quem entrou, e aí a conta recomeça.
    """

    def __init__(self, engine):
        self.engine = engine
        self.history = None
        self.board = None
        self.count = 0

    def check(self):
        history = self.engine.history
        if history is not self.history or len(history) < self.count:
            self.history = history
            self.board = Board.from_fen(self.engine.start_fen)
            self.count = 0
        while self.count < len(history):
            san = history[self.count]
            matches = [move for move in legal_moves(self.board) if move_to_san(self.board, move) == san]
            assert len(matches) == 1, f"{san!r} não é legal em {self.board.to_fen()}"
            self.board.apply(matches[0])
            self.count += 1
        assert self.board.to_fen() == self.engine.board.to_fen()


def secret_is_clean(theme):
    for mapping in (theme._texts, theme._wrapped):
        for entry in mapping:
            for part in entry:
                if isinstance(part, str) and SECRET in part:
                    return False
    return True


def check_invariants(app, replays):
    scene = app.scene
    assert isinstance(scene, GAME_SCENES)
    assert scene.next_scene is None, "a troca de cena é aplicada no mesmo quadro"
    assert len(app.theme._texts) <= 1600
    assert secret_is_clean(app.theme), "a senha entrou em um cache de texto"
    if isinstance(scene, MenuScene):
        assert scene.focus.widgets
    if isinstance(scene, (GameScene, GameOverScene)):
        assert scene.view.particles.alive_count <= scene.view.particles.capacity
    if not isinstance(scene, GameScene):
        return
    engine, view = scene.engine, scene.view
    replays.setdefault(id(engine), HistoryReplay(engine)).check()
    if engine.state is GameState.PAUSED:
        assert scene.is_frozen, "motor em pausa sem sobreposição que congele"
    if engine.state is GameState.IN_PROGRESS:
        assert not scene.is_frozen, "sobreposição congela a tela com o motor em andamento"
    if scene.selection is None:
        assert view.lifted_square is None
    else:
        piece = engine.board.piece_at(scene.selection)
        assert piece is not None and piece.color is engine.turn, f"seleção inválida em {engine.board.to_fen()}"
        assert scene.is_local_turn, "seleção na vez de quem não está na tela"
    if scene.hides_hints and engine.result is None:
        assert not view.tints, "tint de dica no modo Partida"
    assert sum(type(modal).__name__ == "PromotionDialog" for modal in scene.modals) <= 1
    assert len(scene.modals) <= 4, "sobreposições empilhadas demais"
    if scene.net is not None:
        assert not scene.is_frozen, "em rede, nada congela o relógio"


def seed_account(rng):
    accounts_module.AccountStore().create(ACCOUNT, SECRET)
    store = HistoryStore(ACCOUNT)
    outcomes = ("vitoria", "derrota", "empate")
    for index in range(50):
        store.add(MatchRecord(
            f"2026-01-{index % 28 + 1:02d}T10:00:00", rng.choice(HOSTILE_NAMES), "rede", None, "Brancas", outcomes[index % 3], "Xeque-mate", index,
            float(index), "Blitz 5", "Partida", '[White "a"]\n\n1. e4 e5 *\n', "8/8/8/8/8/8/8/8 w - - 0 1",
        ))


def run_monkey(seed, frames, monkeypatch, fast_cpu=True):
    """Roda o macaco e devolve quantos quadros ficou em cada lugar."""
    rng = random.Random(seed)
    # O PBKDF2 custa 0,17 s por tentativa, e o Hardcore, 4 s por lance. Aqui o que importa é a quantidade de caminhos.
    monkeypatch.setattr(accounts_module, "_PBKDF2_ITERATIONS", 1000)
    if fast_cpu:
        monkeypatch.setattr(cpu_player, "search_budget", lambda remaining, increment: 0.01)
    seed_account(rng)
    network = RobotNetwork(rng)
    app = App(seed=seed, require_login=True, network=network)
    pygame.event.clear()
    monkey = Monkey(seed)
    replays = {}
    stats = dict.fromkeys(("login", "menu", "history", "lobby", "game", "cpu", "net", "over", "played"), 0)
    levels = set()
    last_moves = stuck_frames = 0
    last_scene = None
    try:
        for frame in range(frames):
            events = monkey.frame_events(app)
            for event in events:
                pygame.event.post(event)
            dt = monkey.rng.choice(DTS)
            try:
                app.step(dt)
                network.tick()
                check_invariants(app, replays)
            except Exception as error:  # noqa: BLE001
                pytest.fail(f"macaco caiu: semente {seed}, quadro {frame}, dt {dt}, cena {type(app.scene).__name__}, eventos {events}: {error!r}")
            scene = app.scene
            if not app.running:
                scene.shutdown()
                app.running = True
                scene.next_scene = app.login_scene()
                app.step(0.0)
                scene = app.scene
            stuck_frames = stuck_frames + 1 if scene is last_scene else 0
            last_scene = scene
            if stuck_frames > 350 or (isinstance(scene, MenuScene) and rng.random() < 0.01):
                stuck_frames = 0
                _push_out(app, rng)
            _count(stats, levels, scene)
            if isinstance(scene, GameScene):
                moves = len(scene.engine.history)
                stats["played"] += max(moves - last_moves, 0)
                last_moves = moves
    finally:
        app.scene.shutdown()
        network.close_all()
        pygame.event.clear()
        # O macaco aperta F11. Sem fechar a janela, o próximo `set_mode` herdaria o tamanho da tela cheia, e os testes seguintes mudariam.
        pygame.display.quit()
    stats["levels"] = len(levels)
    assert not wait_threads_gone(10.0), "thread sobrando no fim do macaco"
    return stats


def _push_out(app, rng):
    """Sem isto, o macaco passaria o tempo todo na tela em que caiu: leva para outra, como um jogador que desiste."""
    scene = app.scene
    if isinstance(scene, GameScene):
        scene.shutdown()
        scene.next_scene = app.menu_scene()
    elif isinstance(scene, LobbyScene):
        scene.cancel()
    elif isinstance(scene, GameOverScene):
        scene.go_to_menu()
    elif isinstance(scene, MenuScene):
        roll = rng.random()
        if roll < 0.35:
            scene.opponent_selector.select(1)
            scene.difficulty_selector.select(rng.randrange(4))
            scene.color_selector.select(rng.randrange(3))
            scene.mode_selector.select(rng.randrange(2))
            scene.start_match()
        elif roll < 0.85 and app.network is not None:
            scene.opponent_selector.select(2)
            scene.mode_selector.select(rng.randrange(2))
            scene.create_room() if rng.random() < 0.6 else scene.join_room()
        else:
            scene.tab_bar.select(1)
    else:
        scene.play_as_guest() if rng.random() < 0.5 else _sign_in(app, scene)


def _sign_in(app, scene):
    app.account = ACCOUNT
    scene.next_scene = app.menu_scene()


def _count(stats, levels, scene):
    if isinstance(scene, LoginScene):
        stats["login"] += 1
    elif isinstance(scene, LobbyScene):
        stats["lobby"] += 1
    elif isinstance(scene, GameOverScene):
        stats["over"] += 1
    elif isinstance(scene, MenuScene):
        stats["menu"] += 1
        if scene.tab_bar.value == "historico":
            stats["history"] += 1
    else:
        stats["game"] += 1
        if scene.cpu is not None:
            stats["cpu"] += 1
            levels.add(scene.cpu.difficulty)
        if scene.net is not None:
            stats["net"] += 1


@pytest.mark.ct("CT-130")
def test_macaco_curto_percorre_todas_as_telas(monkeypatch):
    totals = {}
    for seed in (70, 71, 72):
        monkeypatch.setenv("CHESS_THE_GAME_DATA", _fresh_dir(seed))
        for key, value in run_monkey(seed, 1800, monkeypatch).items():
            totals[key] = totals.get(key, 0) + value
    assert totals["played"] > 50, f"o macaco precisa jogar de verdade: {totals}"
    for place in ("login", "menu", "lobby", "game", "cpu", "net", "over"):
        assert totals[place] > 0, f"o macaco não passou por {place}: {totals}"


def _fresh_dir(seed):
    import tempfile
    return tempfile.mkdtemp(prefix=f"macaco-{seed}-")


@pytest.mark.ct("CT-130")
@pytest.mark.slow
@pytest.mark.parametrize("seed", range(200, 216))
def test_macaco_longo_por_dezenas_de_milhares_de_quadros(monkeypatch, seed):
    monkeypatch.setenv("CHESS_THE_GAME_DATA", _fresh_dir(seed))
    stats = run_monkey(seed, 6000, monkeypatch, fast_cpu=seed % 4 != 0)
    print(seed, stats)
    assert stats["played"] > 0
