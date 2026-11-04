"""Relógio, controle de tempo, derrota por tempo e pausa."""
import math

import pytest
from core_helpers import play_all, sq

from xadrez.core import ChessClock, Color, EndReason, GameEngine, GameState, MoveError, TimeControl


def test_time_control_presets():
    assert TimeControl.UNLIMITED.is_unlimited
    assert TimeControl.BLITZ_5.minutes == 5
    assert TimeControl.RAPID_10.minutes == 10
    assert TimeControl.CLASSIC_30.minutes == 30
    assert not TimeControl.BLITZ_5.is_unlimited


@pytest.mark.parametrize("minutes, increment", [(-1, 0), (5, -1)])
def test_time_control_rejects_negative_values(minutes, increment):
    with pytest.raises(ValueError):
        TimeControl(minutes, increment)


def test_unlimited_clock_counts_elapsed_and_never_runs_out():
    clock = ChessClock(TimeControl.UNLIMITED)
    clock.tick(Color.WHITE, 1_000_000)
    assert clock.elapsed(Color.WHITE) == 1_000_000
    assert clock.remaining(Color.WHITE) == math.inf
    assert not clock.is_flagged(Color.WHITE)
    assert clock.elapsed(Color.BLACK) == 0


def test_limited_clock_counts_down_and_stops_at_zero():
    clock = ChessClock(TimeControl.BLITZ_5)
    assert clock.remaining(Color.WHITE) == 300
    clock.tick(Color.WHITE, 100.5)
    assert clock.remaining(Color.WHITE) == pytest.approx(199.5)
    assert clock.elapsed(Color.WHITE) == pytest.approx(100.5)
    assert clock.remaining(Color.BLACK) == 300
    clock.tick(Color.WHITE, 1000)
    assert clock.remaining(Color.WHITE) == 0
    assert clock.is_flagged(Color.WHITE)
    assert not clock.is_flagged(Color.BLACK)


@pytest.mark.parametrize("dt", [0, -5, float("nan")])
def test_tick_ignores_time_that_is_not_positive(dt):
    clock = ChessClock(TimeControl.BLITZ_5)
    clock.tick(Color.WHITE, dt)
    assert clock.remaining(Color.WHITE) == 300
    assert clock.elapsed(Color.WHITE) == 0


def test_increment_is_added_to_the_remaining_time():
    clock = ChessClock(TimeControl(1, 2))
    clock.add_increment(Color.WHITE)
    assert clock.remaining(Color.WHITE) == 62


def test_default_clock_is_unlimited():
    assert ChessClock().time_control is TimeControl.UNLIMITED


def test_engine_uses_the_chosen_time_control():
    engine = GameEngine(time_control=TimeControl.RAPID_10)
    assert engine.clock.remaining(Color.WHITE) == 600
    assert engine.clock.remaining(Color.BLACK) == 600


def test_tick_runs_the_clock_of_the_side_to_move():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    assert engine.tick(10) is None
    assert engine.clock.remaining(Color.WHITE) == 290
    assert engine.clock.remaining(Color.BLACK) == 300
    play_all(engine, "e2e4")
    engine.tick(20)
    assert engine.clock.remaining(Color.WHITE) == 290
    assert engine.clock.remaining(Color.BLACK) == 280


def test_engine_applies_the_increment_to_the_side_that_moved():
    engine = GameEngine(time_control=TimeControl(5, 3))
    engine.tick(10)
    play_all(engine, "e2e4")
    assert engine.clock.remaining(Color.WHITE) == 293
    assert engine.clock.remaining(Color.BLACK) == 300


def test_refused_move_does_not_earn_the_increment():
    engine = GameEngine(time_control=TimeControl(5, 3))
    assert not engine.play(sq("e2"), sq("e5")).ok
    assert engine.clock.remaining(Color.WHITE) == 300


def test_unlimited_game_never_ends_on_time():
    engine = GameEngine()
    assert engine.tick(10_000_000) is None
    assert engine.state is GameState.IN_PROGRESS
    assert engine.clock.elapsed(Color.WHITE) == 10_000_000


@pytest.mark.ct("CT-16")
def test_running_out_of_time_loses_the_game():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    assert engine.tick(299) is None
    result = engine.tick(1)
    assert result.winner is Color.BLACK
    assert result.reason is EndReason.TIMEOUT
    assert engine.result == result
    assert engine.state is GameState.FINISHED
    assert engine.players[Color.BLACK].match_points == 1
    assert engine.players[Color.WHITE].match_points == 0


@pytest.mark.ct("CT-16")
def test_black_can_lose_on_time_too():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    play_all(engine, "e2e4")
    assert engine.tick(300).winner is Color.WHITE


@pytest.mark.ct("CT-16")
def test_running_out_of_time_against_a_lone_king_is_a_draw():
    engine = GameEngine(time_control=TimeControl.BLITZ_5, fen="4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    result = engine.tick(300)
    assert result.is_draw
    assert result.reason is EndReason.TIMEOUT
    assert engine.players[Color.WHITE].match_points == 0.5
    assert engine.players[Color.BLACK].match_points == 0.5


@pytest.mark.ct("CT-16")
def test_lone_king_loses_on_time_when_the_opponent_has_material():
    engine = GameEngine(time_control=TimeControl.BLITZ_5, fen="4k3/8/8/8/8/8/4P3/4K3 b - - 0 1")
    assert engine.tick(300).winner is Color.WHITE


@pytest.mark.ct("CT-16")
def test_no_moves_are_accepted_after_time_runs_out():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.tick(300)
    assert engine.play(sq("e2"), sq("e4")).error is MoveError.GAME_NOT_ACTIVE


@pytest.mark.ct("CT-16")
def test_tick_does_nothing_after_the_game_ended():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.tick(300)
    elapsed = engine.clock.elapsed(Color.WHITE)
    assert engine.tick(50) is None
    assert engine.clock.elapsed(Color.WHITE) == elapsed
    assert engine.players[Color.BLACK].match_points == 1

    finished_by_resignation = GameEngine(time_control=TimeControl.BLITZ_5)
    finished_by_resignation.resign()
    assert finished_by_resignation.tick(1000) is None
    assert finished_by_resignation.clock.remaining(Color.WHITE) == 300


@pytest.mark.ct("CT-20")
def test_pause_freezes_the_clock():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.tick(10)
    engine.pause()
    assert engine.state is GameState.PAUSED
    assert engine.tick(100) is None
    assert engine.clock.remaining(Color.WHITE) == 290
    assert engine.clock.elapsed(Color.WHITE) == 10


@pytest.mark.ct("CT-20")
def test_time_cannot_run_out_during_a_pause():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.pause()
    engine.tick(10_000)
    assert engine.state is GameState.PAUSED
    assert engine.result is None


@pytest.mark.ct("CT-20")
def test_pause_refuses_moves_and_hides_legal_moves():
    engine = GameEngine()
    engine.pause()
    outcome = engine.play(sq("e2"), sq("e4"))
    assert outcome.error is MoveError.GAME_NOT_ACTIVE
    assert engine.legal_moves_from(sq("e2")) == []
    assert not engine.is_promotion_move(sq("e2"), sq("e4"))
    assert engine.board.piece_at(sq("e2")) is not None
    assert engine.history == []


@pytest.mark.ct("CT-20")
def test_resume_returns_to_normal():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.pause()
    engine.resume()
    assert engine.state is GameState.IN_PROGRESS
    assert engine.play(sq("e2"), sq("e4")).ok
    engine.tick(5)
    assert engine.clock.remaining(Color.BLACK) == 295


@pytest.mark.ct("CT-20")
def test_pause_and_resume_do_not_reopen_a_finished_game():
    engine = GameEngine()
    engine.resign()
    engine.pause()
    assert engine.state is GameState.FINISHED
    engine.resume()
    assert engine.state is GameState.FINISHED


@pytest.mark.ct("CT-20")
def test_resume_without_pause_changes_nothing():
    engine = GameEngine()
    engine.resume()
    assert engine.state is GameState.IN_PROGRESS
