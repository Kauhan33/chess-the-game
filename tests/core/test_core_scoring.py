"""Pontuação de material, placar da série, reinício e revanche."""
import pytest
from core_helpers import play_all, sq

from xadrez.core import STARTING_FEN, Color, EndReason, GameEngine, GameState, Player, PieceType, TimeControl

FOOLS_MATE = ("f2f3", "e7e5", "g2g4", "d8h4")
SCHOLARS_MATE = ("e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "g8f6", "h5f7")


def test_new_player_starts_empty():
    player = Player("Jogador", Color.WHITE)
    assert player.match_points == 0
    assert player.captured == []
    assert player.material_score == 0


def test_players_do_not_share_the_captured_list():
    first, second = Player("A", Color.WHITE), Player("B", Color.BLACK)
    first.captured.append(PieceType.PAWN)
    assert second.captured == []


@pytest.mark.ct("CT-08")
def test_capture_adds_the_value_of_the_piece_to_the_material_score():
    engine = GameEngine()
    play_all(engine, "e2e4", "d7d5", "e4d5")
    white = engine.players[Color.WHITE]
    assert white.captured == [PieceType.PAWN]
    assert white.material_score == 1
    assert engine.players[Color.BLACK].material_score == 0
    assert engine.material_balance() == 1


@pytest.mark.ct("CT-08")
def test_captures_by_both_sides_update_the_balance():
    engine = GameEngine()
    play_all(engine, "e2e4", "d7d5", "e4d5", "d8d5")
    assert engine.players[Color.BLACK].captured == [PieceType.PAWN]
    assert engine.material_balance() == 0
    play_all(engine, "b1c3", "d5d2", "c1d2")
    assert engine.players[Color.WHITE].material_score == 10
    assert engine.players[Color.BLACK].material_score == 2
    assert engine.material_balance() == 8


@pytest.mark.ct("CT-08")
@pytest.mark.parametrize(
    "victim_letter, points",
    [("p", 1), ("n", 3), ("b", 3), ("r", 5), ("q", 9)],
)
def test_each_kind_of_piece_is_worth_its_points(victim_letter, points):
    engine = GameEngine(fen=f"k7/8/8/3{victim_letter}4/8/8/8/3RK3 w - - 0 1")
    outcome = engine.play(sq("d1"), sq("d5"))
    assert outcome.ok
    assert engine.players[Color.WHITE].material_score == points


@pytest.mark.ct("CT-08")
def test_quiet_move_does_not_change_the_score():
    engine = GameEngine()
    play_all(engine, "g1f3")
    assert engine.players[Color.WHITE].material_score == 0
    assert engine.material_balance() == 0


@pytest.mark.ct("CT-08")
def test_black_lead_gives_a_negative_balance():
    engine = GameEngine(fen="k7/8/8/8/8/3r4/P2P4/4K3 b - - 0 1")
    play_all(engine, "d3d2")
    assert engine.players[Color.BLACK].material_score == 1
    assert engine.players[Color.WHITE].material_score == 0
    assert engine.material_balance() == -1


@pytest.mark.ct("CT-08")
def test_en_passant_counts_one_point():
    engine = GameEngine(fen="4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
    play_all(engine, "e5d6")
    assert engine.players[Color.WHITE].material_score == 1


@pytest.mark.ct("CT-18")
def test_win_is_worth_one_point():
    engine = GameEngine()
    play_all(engine, *SCHOLARS_MATE)
    assert engine.players[Color.WHITE].match_points == 1
    assert engine.players[Color.BLACK].match_points == 0


@pytest.mark.ct("CT-18")
def test_draw_is_worth_half_a_point_each():
    engine = GameEngine()
    engine.agree_draw()
    assert engine.players[Color.WHITE].match_points == 0.5
    assert engine.players[Color.BLACK].match_points == 0.5


@pytest.mark.ct("CT-18")
def test_points_are_given_only_once_per_game():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    play_all(engine, *FOOLS_MATE)
    result = engine.result
    assert engine.resign(Color.BLACK) == result
    assert engine.agree_draw() == result
    engine.tick(1000)
    engine.pause()
    engine.resume()
    assert engine.result == result
    assert engine.players[Color.BLACK].match_points == 1
    assert engine.players[Color.WHITE].match_points == 0


@pytest.mark.ct("CT-18")
def test_resignation_gives_the_point_to_the_opponent():
    engine = GameEngine()
    engine.resign(Color.BLACK)
    assert engine.players[Color.WHITE].match_points == 1
    assert engine.players[Color.BLACK].match_points == 0


@pytest.mark.ct("CT-18")
def test_series_score_follows_the_player_across_color_changes():
    engine = GameEngine("Primeiro", "Segundo")
    first, second = engine.players[Color.WHITE], engine.players[Color.BLACK]
    play_all(engine, *SCHOLARS_MATE)
    assert (first.match_points, second.match_points) == (1, 0)
    engine.rematch()
    assert engine.players[Color.BLACK] is first
    play_all(engine, *FOOLS_MATE)
    assert (first.match_points, second.match_points) == (2, 0)
    engine.rematch()
    engine.agree_draw()
    assert (first.match_points, second.match_points) == (2.5, 0.5)


@pytest.mark.ct("CT-21")
def test_restart_returns_to_the_start_and_keeps_colors_and_score():
    engine = GameEngine("Primeiro", "Segundo", TimeControl.BLITZ_5)
    first, second = engine.players[Color.WHITE], engine.players[Color.BLACK]
    play_all(engine, *SCHOLARS_MATE)
    engine.restart()
    assert engine.board.to_fen() == STARTING_FEN
    assert engine.state is GameState.IN_PROGRESS
    assert engine.result is None
    assert engine.history == []
    assert engine.players[Color.WHITE] is first
    assert engine.players[Color.BLACK] is second
    assert first.match_points == 1
    assert first.captured == []
    assert first.material_score == 0
    assert engine.material_balance() == 0
    assert engine.clock.remaining(Color.WHITE) == 300


@pytest.mark.ct("CT-21")
def test_rematch_swaps_colors_and_keeps_score():
    engine = GameEngine("Primeiro", "Segundo")
    first, second = engine.players[Color.WHITE], engine.players[Color.BLACK]
    play_all(engine, *SCHOLARS_MATE)
    engine.rematch()
    assert engine.players[Color.WHITE] is second
    assert engine.players[Color.BLACK] is first
    assert second.color is Color.WHITE
    assert first.color is Color.BLACK
    assert first.match_points == 1
    assert second.match_points == 0
    assert first.captured == []
    assert engine.board.to_fen() == STARTING_FEN
    assert engine.state is GameState.IN_PROGRESS
    assert engine.turn is Color.WHITE
    assert engine.current_player is second


@pytest.mark.ct("CT-21")
def test_unfinished_game_gives_no_points_on_restart_or_rematch():
    engine = GameEngine()
    play_all(engine, "e2e4", "d7d5", "e4d5")
    engine.restart()
    assert all(player.match_points == 0 for player in engine.players.values())
    play_all(engine, "e2e4")
    engine.rematch()
    assert all(player.match_points == 0 for player in engine.players.values())


@pytest.mark.ct("CT-21")
def test_restart_clears_the_position_counts_for_repetition():
    engine = GameEngine()
    play_all(engine, "g1f3", "g8f6", "f3g1", "f6g8")
    engine.restart()
    outcome = play_all(engine, "g1f3", "g8f6", "f3g1", "f6g8")
    assert outcome.result is None
    assert engine.state is GameState.IN_PROGRESS


@pytest.mark.ct("CT-21")
def test_restart_releases_a_paused_game():
    engine = GameEngine()
    engine.pause()
    engine.restart()
    assert engine.state is GameState.IN_PROGRESS


@pytest.mark.ct("CT-21")
def test_restart_returns_to_the_fen_given_to_the_engine():
    fen = "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"
    engine = GameEngine(fen=fen)
    play_all(engine, "e2e4")
    engine.restart()
    assert engine.board.to_fen() == fen
    engine.rematch()
    assert engine.board.to_fen() == fen


@pytest.mark.ct("CT-21")
def test_new_game_after_restart_plays_to_a_new_result():
    engine = GameEngine()
    play_all(engine, *FOOLS_MATE)
    engine.restart()
    outcome = play_all(engine, *SCHOLARS_MATE)
    assert outcome.result.reason is EndReason.CHECKMATE
    assert engine.players[Color.WHITE].match_points == 1
    assert engine.players[Color.BLACK].match_points == 1
