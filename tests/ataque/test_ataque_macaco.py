"""Macaco: eventos aleatórios com semente pelo `App.step`, sem janela, conferindo invariantes a cada quadro.

CT-57: nada levanta exceção, o histórico só tem lances legais, a pausa congela tudo e só há uma cena ativa.

O macaco não recebe NaN, roda gigante nem caracteres de largura zero: esses já têm teste próprio (QA-01, QA-12, QA-13).
Sem esse corte, a versão atual cairia na primeira ocorrência e o resto do ataque não rodaria.
"""
from __future__ import annotations

import random

import pygame
import pytest

from xadrez.core import Board, Color, GameState, legal_moves, move_to_san
from xadrez.ui import App, GameOverScene, GameScene, MenuScene
from xadrez.ui.autoplay import click_point

KEYS = [
    pygame.K_p, pygame.K_r, pygame.K_t, pygame.K_v, pygame.K_h, pygame.K_F1, pygame.K_F3, pygame.K_F4, pygame.K_ESCAPE,
    pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_TAB, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT,
    pygame.K_RIGHT, pygame.K_BACKSPACE, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_a, pygame.K_DELETE,
    pygame.K_HOME, pygame.K_END, pygame.K_0, pygame.K_F12, pygame.K_LSHIFT, pygame.K_KP1,
]
TEXTS = [
    "a", "Z", "Ç", "ç", "ã", "é", "João", "\U0001f600", "\u265e", "\x00", "\x07", "\n", "\t", "\r", "\x7f", "\u200b", "\u202e",
    "\ud83d", "W" * 40, "Ç" * 40, " ", "     ", "x" * 5000, "\ufdfa", "\U0001d54f", "\ud55c\uae00", "\u0645\u0631\u062d\u0628\u0627", "e\u0301", "\u0301" * 8,
    "%s%d{0}", "../..", "' OR 1=1", "\uffff", "\U0010ffff", "\ufe0f", "\U0001F336\ufe0f", "\u034f",
]
DTS = [1 / 60] * 20 + [0.0, 0.0, 0.1, 0.5, 5.0, 1e9, -1.0, 1 / 240, float("nan")]
SIZES = [(1, 1), (50, 2000), (3000, 200), (1280, 720), (640, 360), (200, 200), (2, 900), (1920, 1080), (800, 600),
         (320, 240), (1000, 1)]


class HistoryReplay:
    """Refaz em um tabuleiro próprio cada SAN do histórico: lance fora das regras não encontra par."""

    def __init__(self, engine):
        self.engine = engine
        self.board = Board.from_fen(engine._start_fen)
        self.count = 0

    def check(self):
        history = self.engine.history
        if len(history) < self.count:
            self.board = Board.from_fen(self.engine._start_fen)
            self.count = 0
        while self.count < len(history):
            san = history[self.count]
            matches = [m for m in legal_moves(self.board) if move_to_san(self.board, m) == san]
            assert len(matches) == 1, f"{san!r} não é legal em {self.board.to_fen()}"
            self.board.apply(matches[0])
            self.count += 1
        assert self.board.to_fen() == self.engine.board.to_fen()


class Monkey:
    def __init__(self, seed, resize_chance=0.35):
        self.rng = random.Random(seed)
        self.resize_chance = resize_chance

    def position(self, app):
        rng, scene = self.rng, app.scene
        width, height = app.size
        choice = rng.random()
        if choice < 0.35:
            rects = self._widgets(scene)
            if rects:
                return rng.choice(rects).center
        if choice < 0.8 and isinstance(scene, (GameScene, GameOverScene)):
            x, y, w, h = scene.view.camera.viewport
            return rng.randint(x + w // 8, x + max(w * 7 // 8, 1)), rng.randint(y + h // 10, y + max(h * 9 // 10, 1))
        if choice < 0.95:
            return rng.randint(0, max(width - 1, 0)), rng.randint(0, max(height - 1, 0))
        return rng.randint(-50, width + 50), rng.randint(-50, height + 50)

    @staticmethod
    def _widgets(scene):
        if isinstance(scene, GameScene):
            if not scene.modals:
                return [button.rect for button in scene.hud.buttons]
            top = scene.modals[-1]
            rects = [button.rect for button in getattr(top, "buttons", [])]
            close = getattr(top, "_close_button", None)
            return rects + ([close.rect] if close is not None else [])
        rects = [widget.rect for widget in scene.focus.widgets]
        if isinstance(scene, MenuScene) and scene.modal is not None:
            rects.append(scene.modal._close_button.rect)
        return rects

    def click(self, position, button=1):
        return [
            pygame.event.Event(pygame.MOUSEMOTION, pos=position, rel=(0, 0), buttons=(0, 0, 0)),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=button),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=position, button=button),
        ]

    def legal_play(self, app):
        """Em parte das vezes ele joga de verdade: sem isso, nunca sai da posição inicial."""
        scene = app.scene
        if not isinstance(scene, GameScene):
            return []
        if scene.modals:
            if self.rng.random() < 0.6:
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0)]
            return []
        if scene.engine.result is not None or scene.view.is_flying:
            return []
        move = self.rng.choice(legal_moves(scene.engine.board))
        events = []
        for square in (tuple(move.origin), tuple(move.target)):
            events += self.click(click_point(scene.view, square))
        return events

    def one(self, app):
        rng = self.rng
        if rng.random() < 0.45:
            play = self.legal_play(app)
            if play:
                return play
        roll = rng.random()
        if roll < 0.30:
            return self.click(self.position(app), rng.choice((1, 1, 1, 1, 3, 2, 4, 5)))
        if roll < 0.40:
            return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=self.position(app), button=rng.choice((1, 3)))]
        if roll < 0.50:
            return [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=self.position(app), button=rng.choice((1, 3)))]
        if roll < 0.60:
            return [pygame.event.Event(
                pygame.MOUSEMOTION, pos=self.position(app), rel=(rng.randint(-400, 400), rng.randint(-400, 400)),
                buttons=rng.choice(((0, 0, 0), (0, 0, 1), (1, 0, 0), (1, 1, 1))),
            )]
        if roll < 0.66:
            return [pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=rng.choice((-30, -3, -1, 1, 3, 30)), flipped=False)]
        if roll < 0.92:
            key = rng.choice(KEYS)
            mod = rng.choice((0, 0, 0, pygame.KMOD_SHIFT, pygame.KMOD_CTRL))
            return [pygame.event.Event(kind, key=key, mod=mod, unicode="", scancode=0)
                    for kind in (pygame.KEYDOWN, pygame.KEYUP)]
        if roll < 0.975:
            return [pygame.event.Event(pygame.TEXTINPUT, text=rng.choice(TEXTS))]
        if rng.random() < self.resize_chance:
            size = rng.choice(SIZES)
            return [pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1])]
        return []

    def frame_events(self, app):
        events = []
        for _ in range(self.rng.choice((0, 0, 1, 1, 1, 2, 3, 6))):
            events += self.one(app)
        return events


def game_snapshot(app):
    scene = app.scene
    if not isinstance(scene, GameScene):
        return None
    clock = scene.engine.clock
    return scene, scene.is_frozen, scene.engine.board.to_fen(), (clock.remaining(Color.WHITE), clock.remaining(Color.BLACK))


def check_invariants(app, before, had_events, replays):
    scene = app.scene
    assert isinstance(scene, (MenuScene, GameScene, GameOverScene))
    assert scene.next_scene is None, "a troca de cena é aplicada no mesmo quadro"
    assert len(app.theme._texts) <= 1600
    if isinstance(scene, (GameScene, GameOverScene)):
        assert scene.view.particles.alive_count <= scene.view.particles.capacity
    if not isinstance(scene, GameScene):
        return
    engine, view = scene.engine, scene.view
    replay = replays.setdefault(id(engine), HistoryReplay(engine))
    replay.check()
    fen = engine.board.to_fen()
    clocks = (engine.clock.remaining(Color.WHITE), engine.clock.remaining(Color.BLACK))
    if before and before[0] is scene and before[1] and scene.is_frozen:
        if not had_events:
            assert fen == before[2], "tabuleiro mudou com sobreposição aberta"
            assert clocks == before[3], "relógio mudou com sobreposição aberta"
        elif engine.history:
            assert fen == before[2], "tabuleiro mudou com sobreposição aberta"
    if engine.state is GameState.PAUSED:
        assert scene.is_frozen, "motor em pausa sem sobreposição que congele"
    if engine.state is GameState.IN_PROGRESS:
        assert not scene.is_frozen, "sobreposição congela a tela com o motor em andamento"
    if scene.selection is None:
        assert view.lifted_square is None
    else:
        piece = engine.board.piece_at(scene.selection)
        assert piece is not None and piece.color is engine.turn, f"seleção inválida {scene.selection} em {fen}"
        assert view.lifted_square == tuple(scene.selection)
    if scene.cursor is not None:
        assert 0 <= scene.cursor[0] < 8 and 0 <= scene.cursor[1] < 8
    assert sum(type(modal).__name__ == "PromotionDialog" for modal in scene.modals) <= 1
    assert len(scene.modals) <= 3, "sobreposições empilhadas demais"


def run_monkey(seed, frames):
    """Roda o macaco e devolve quantos quadros passou em cada cena e quantos lances jogou."""
    app = App(seed=seed)
    pygame.event.clear()
    monkey = Monkey(seed)
    replays = {}
    stats = {"menu": 0, "game": 0, "over": 0, "played": 0}
    last_moves = 0
    for frame in range(frames):
        before = game_snapshot(app)
        events = monkey.frame_events(app)
        for event in events:
            pygame.event.post(event)
        dt = monkey.rng.choice(DTS)
        try:
            app.step(dt)
            check_invariants(app, before, bool(events), replays)
        except Exception as error:
            pytest.fail(f"macaco caiu: semente {seed}, quadro {frame}, dt {dt}, eventos {events}: {error!r}")
        scene = app.scene
        if isinstance(scene, MenuScene):
            stats["menu"] += 1
        elif isinstance(scene, GameOverScene):
            stats["over"] += 1
        else:
            stats["game"] += 1
            moves = len(scene.engine.history)
            stats["played"] += max(moves - last_moves, 0)
            last_moves = moves
    pygame.event.clear()
    return stats


@pytest.mark.ct("CT-57")
def test_ataque_macaco_curto_nao_derruba_nem_quebra_invariante():
    totals = {"menu": 0, "game": 0, "over": 0, "played": 0}
    for seed in (10, 12, 13):
        for key, value in run_monkey(seed, 2200).items():
            totals[key] += value
    assert totals["played"] > 100, f"o macaco precisa jogar de verdade: {totals}"
    assert totals["menu"] > 0 and totals["game"] > 0


@pytest.mark.ct("CT-57")
@pytest.mark.slow
def test_ataque_macaco_longo_nao_derruba_nem_quebra_invariante():
    totals = {"menu": 0, "game": 0, "over": 0, "played": 0}
    for seed in range(100, 110):
        for key, value in run_monkey(seed, 5000).items():
            totals[key] += value
    print(totals)
    assert totals["played"] > 1000 and totals["over"] > 0 and totals["menu"] > 0
