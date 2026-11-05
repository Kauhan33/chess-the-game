"""Acréscimos da versão 1.1 ao motor: tempos com incremento, abandono, FEN final e cópia do tabuleiro."""
import pytest
from core_helpers import play_all, sq

from xadrez.core import (
    STARTING_FEN,
    Board,
    Color,
    EndReason,
    GameEngine,
    GameState,
    Move,
    MoveError,
    Queen,
    TimeControl,
)


@pytest.mark.ct("CT-77")
def test_new_time_controls_have_the_right_values():
    assert (TimeControl.BLITZ_3_2.minutes, TimeControl.BLITZ_3_2.increment) == (3, 2)
    assert (TimeControl.CLASSIC_15_10.minutes, TimeControl.CLASSIC_15_10.increment) == (15, 10)
    assert not TimeControl.BLITZ_3_2.is_unlimited
    assert not TimeControl.CLASSIC_15_10.is_unlimited


@pytest.mark.ct("CT-77")
def test_old_presets_stay_as_they_were():
    assert TimeControl.UNLIMITED.is_unlimited
    assert (TimeControl.BLITZ_5.minutes, TimeControl.BLITZ_5.increment) == (5, 0)
    assert (TimeControl.RAPID_10.minutes, TimeControl.RAPID_10.increment) == (10, 0)
    assert (TimeControl.CLASSIC_30.minutes, TimeControl.CLASSIC_30.increment) == (30, 0)


@pytest.mark.ct("CT-77")
@pytest.mark.parametrize(
    "time_control, start, increment",
    [(TimeControl.BLITZ_3_2, 180, 2), (TimeControl.CLASSIC_15_10, 900, 10)],
)
def test_increment_is_earned_on_each_move_by_who_moved(time_control, start, increment):
    engine = GameEngine(time_control=time_control)
    assert engine.clock.remaining(Color.WHITE) == start
    engine.tick(5)
    play_all(engine, "e2e4")
    assert engine.clock.remaining(Color.WHITE) == start - 5 + increment
    assert engine.clock.remaining(Color.BLACK) == start
    engine.tick(1)
    play_all(engine, "e7e5")
    assert engine.clock.remaining(Color.BLACK) == start - 1 + increment
    assert engine.clock.remaining(Color.WHITE) == start - 5 + increment


@pytest.mark.ct("CT-77")
def test_increment_can_keep_a_player_alive_past_the_initial_time():
    engine = GameEngine(time_control=TimeControl.BLITZ_3_2)
    for _ in range(40):
        for uci in ("g1f3", "g8f6", "f3g1", "f6g8"):
            if engine.result is not None:
                break
            engine.tick(4)
            play_all(engine, uci)
    assert engine.result.reason is EndReason.THREEFOLD_REPETITION
    assert engine.clock.remaining(Color.WHITE) > 0


def test_abandonment_reason_has_a_label():
    assert EndReason.ABANDONMENT.label == "Adversário desconectou"


def test_abandoning_loses_and_counts_in_the_series():
    engine = GameEngine()
    result = engine.abandon(Color.WHITE)
    assert result.winner is Color.BLACK
    assert result.reason is EndReason.ABANDONMENT
    assert engine.result == result
    assert engine.state is GameState.FINISHED
    assert engine.players[Color.BLACK].match_points == 1
    assert engine.players[Color.WHITE].match_points == 0
    assert engine.play(sq("e2"), sq("e4")).error is MoveError.GAME_NOT_ACTIVE


def test_abandoning_is_allowed_during_a_pause():
    engine = GameEngine()
    engine.pause()
    assert engine.abandon(Color.BLACK).winner is Color.WHITE
    assert engine.state is GameState.FINISHED


def test_abandoning_a_finished_game_changes_nothing():
    engine = GameEngine()
    resigned = engine.resign(Color.WHITE)
    assert engine.abandon(Color.BLACK) == resigned
    assert engine.result.reason is EndReason.RESIGNATION
    assert engine.players[Color.BLACK].match_points == 1
    assert engine.players[Color.WHITE].match_points == 0


def test_abandoning_a_position_born_finished_keeps_its_result():
    engine = GameEngine(fen="R5k1/5ppp/8/8/8/8/8/4K3 b - - 0 1")
    assert engine.abandon(Color.WHITE).reason is EndReason.CHECKMATE


def test_final_fen_follows_the_game_and_survives_the_end():
    engine = GameEngine()
    assert engine.final_fen == STARTING_FEN
    play_all(engine, "e2e4")
    assert engine.final_fen == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    fen = engine.final_fen
    engine.resign()
    assert engine.final_fen == fen


def test_start_fen_is_kept_through_the_game():
    assert GameEngine().start_fen == STARTING_FEN
    fen = "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"
    engine = GameEngine(fen=fen)
    play_all(engine, "e2e4")
    assert engine.start_fen == fen


def test_board_copy_keeps_the_history_and_can_be_undone_alone():
    engine = GameEngine()
    play_all(engine, "e2e4", "e7e5")
    original = engine.board
    clone = original.copy()
    assert clone.to_fen() == original.to_fen()
    assert clone.undoable_moves == original.undoable_moves == 2
    clone.undo()
    assert clone.undoable_moves == 1
    assert original.undoable_moves == 2
    assert clone.to_fen() != original.to_fen()
    clone.undo()
    assert clone.to_fen() == STARTING_FEN


def test_changing_a_board_copy_does_not_touch_the_original():
    original = Board.from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    clone = original.copy()
    clone.place(sq("d4"), Queen(Color.WHITE))
    assert original.piece_at(sq("d4")) is None
    clone.apply(Move(sq("e1"), sq("f1")))
    assert original.king_square(Color.WHITE) == sq("e1")
    assert clone.king_square(Color.WHITE) == sq("f1")
    assert original.turn is Color.WHITE
