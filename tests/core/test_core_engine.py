"""Fachada GameEngine: turnos, erros de jogada, relatório da jogada e peças sob ameaça."""
import pytest
from core_helpers import IndexLikeInteger, play_all, sq, target_names

from xadrez.core import (
    STARTING_FEN,
    Color,
    EndReason,
    GameEngine,
    GameResult,
    GameState,
    Move,
    MoveError,
    MoveOutcome,
    PieceType,
    Square,
)


@pytest.mark.ct("CT-01")
def test_new_engine_starts_on_the_official_position():
    engine = GameEngine()
    assert engine.board.to_fen() == STARTING_FEN
    assert engine.state is GameState.IN_PROGRESS
    assert engine.result is None
    assert engine.history == []
    assert engine.players[Color.WHITE].name == "Jogador 1"
    assert engine.players[Color.BLACK].name == "Jogador 2"


@pytest.mark.ct("CT-02")
def test_white_starts_and_turns_alternate():
    engine = GameEngine()
    assert engine.turn is Color.WHITE
    assert engine.current_player is engine.players[Color.WHITE]
    play_all(engine, "e2e4")
    assert engine.turn is Color.BLACK
    assert engine.current_player is engine.players[Color.BLACK]
    play_all(engine, "e7e5")
    assert engine.turn is Color.WHITE
    assert engine.board.fullmove_number == 2
    assert engine.history == ["e4", "e5"]


@pytest.mark.ct("CT-03")
def test_move_out_of_turn_is_refused():
    engine = GameEngine()
    outcome = engine.play(sq("e7"), sq("e5"))
    assert not outcome.ok
    assert outcome.error is MoveError.NOT_YOUR_TURN
    assert engine.board.to_fen() == STARTING_FEN
    assert engine.turn is Color.WHITE
    assert engine.history == []


@pytest.mark.ct("CT-03")
def test_same_side_cannot_move_twice():
    engine = GameEngine()
    play_all(engine, "e2e4")
    assert engine.play(sq("d2"), sq("d4")).error is MoveError.NOT_YOUR_TURN
    assert engine.turn is Color.BLACK


@pytest.mark.ct("CT-03")
def test_enemy_piece_has_no_moves_out_of_turn():
    engine = GameEngine()
    assert engine.legal_moves_from(sq("e7")) == []
    assert target_names(engine.legal_moves_from(sq("e2"))) == {"e3", "e4"}


def test_empty_square_reports_no_piece():
    engine = GameEngine()
    assert engine.play(sq("e4"), sq("e5")).error is MoveError.NO_PIECE


GARBAGE_SQUARES = [
    *(None, "e2", 5, 1.5, [], {}),
    *((1,), (1, 2, 3), (1.5, 2), ("a", "b")),
    *((8, 0), (4, 8), (-1, 0), Square(9, 9)),
]


@pytest.mark.parametrize("origin", [*GARBAGE_SQUARES, object()], ids=str)
def test_invalid_origin_never_raises_and_changes_nothing(origin):
    engine = GameEngine()
    outcome = engine.play(origin, sq("e4"))
    assert isinstance(outcome, MoveOutcome)
    assert outcome.error is MoveError.NO_PIECE
    assert engine.board.to_fen() == STARTING_FEN
    assert engine.history == []


@pytest.mark.parametrize("target", [*GARBAGE_SQUARES, object()], ids=str)
def test_invalid_target_never_raises_and_changes_nothing(target):
    engine = GameEngine()
    outcome = engine.play(sq("e2"), target)
    assert outcome.error is MoveError.ILLEGAL_MOVE
    assert engine.board.to_fen() == STARTING_FEN


def test_play_accepts_plain_tuples_and_integer_like_values():
    engine = GameEngine()
    assert engine.play((4, 1), (4, 3)).ok
    assert engine.play((IndexLikeInteger(4), IndexLikeInteger(6)), (IndexLikeInteger(4), IndexLikeInteger(4))).ok
    assert engine.history == ["e4", "e5"]


def test_queries_accept_invalid_squares_without_raising():
    engine = GameEngine()
    assert engine.legal_moves_from(None) == []
    assert engine.legal_moves_from((9, 9)) == []
    assert engine.attackers_of("e4") == []
    assert engine.is_promotion_move(None, None) is False


def test_failed_move_outcome_is_empty():
    outcome = GameEngine().play(sq("e4"), sq("e5"))
    assert outcome == MoveOutcome(ok=False, error=MoveError.NO_PIECE)
    assert outcome.move is None
    assert outcome.san == ""
    assert outcome.result is None


def test_successful_move_outcome_details():
    engine = GameEngine()
    pawn = engine.board.piece_at(sq("e2"))
    outcome = engine.play(sq("e2"), sq("e4"))
    assert outcome.ok
    assert outcome.error is None
    assert outcome.move == Move(sq("e2"), sq("e4"), is_double_push=True)
    assert outcome.piece is pawn
    assert outcome.captured is None
    assert outcome.captured_square is None
    assert outcome.rook_path is None
    assert outcome.promoted_to is None
    assert not outcome.gives_check
    assert outcome.result is None
    assert outcome.san == "e4"


def test_capture_outcome_reports_the_captured_piece_and_square():
    engine = GameEngine()
    play_all(engine, "e2e4", "d7d5")
    victim = engine.board.piece_at(sq("d5"))
    outcome = engine.play(sq("e4"), sq("d5"))
    assert outcome.captured is victim
    assert outcome.captured_square == sq("d5")


def test_engine_loads_a_position_from_fen():
    fen = "4k3/8/8/8/8/8/4P3/4K3 b - - 3 9"
    engine = GameEngine(fen=fen)
    assert engine.board.to_fen() == fen
    assert engine.turn is Color.BLACK


@pytest.mark.parametrize("fen", ["", "not a fen", "8/8/8/8/8/8/8/8 w - - 0 1"])
def test_engine_with_malformed_fen_raises_value_error(fen):
    with pytest.raises(ValueError):
        GameEngine(fen=fen)


def test_custom_player_names():
    engine = GameEngine("Primeiro", "Segundo")
    assert engine.players[Color.WHITE].name == "Primeiro"
    assert engine.players[Color.BLACK].name == "Segundo"
    assert engine.players[Color.WHITE].color is Color.WHITE


def test_attackers_of_occupied_square_uses_the_enemies_of_the_occupant():
    engine = GameEngine(fen="4k3/8/8/2n5/8/3P4/8/R3K3 w - - 0 1")
    assert engine.attackers_of(sq("d3")) == [sq("c5")]
    assert engine.attackers_of(sq("c5")) == []
    assert engine.attackers_of(sq("a1")) == []


def test_attackers_of_empty_square_uses_the_opponent_of_the_side_to_move():
    engine = GameEngine(fen="4k3/8/8/2n5/8/3P4/8/R3K3 w - - 0 1")
    assert engine.attackers_of(sq("b3")) == [sq("c5")]


@pytest.mark.ct("CT-19")
def test_threatened_pieces_lists_attacked_pieces_of_that_color():
    engine = GameEngine(fen="4k3/8/2n5/8/3R4/8/8/4K2B w - - 0 1")
    assert engine.threatened_pieces(Color.WHITE) == [sq("d4")]
    assert engine.threatened_pieces(Color.BLACK) == [sq("c6")]


@pytest.mark.ct("CT-19")
def test_threatened_pieces_at_the_start_is_empty():
    engine = GameEngine()
    assert engine.threatened_pieces(Color.WHITE) == []
    assert engine.threatened_pieces(Color.BLACK) == []


@pytest.mark.ct("CT-19")
def test_threatened_pieces_does_not_count_the_king():
    engine = GameEngine(fen="4r1k1/8/8/8/8/8/8/4K3 w - - 0 1")
    assert engine.in_check
    assert engine.threatened_pieces(Color.WHITE) == []


@pytest.mark.ct("CT-19")
def test_blocked_attack_is_not_a_threat():
    engine = GameEngine(fen="4k3/8/8/4r3/4n3/8/4R3/4K3 w - - 0 1")
    assert engine.threatened_pieces(Color.WHITE) == []


@pytest.mark.ct("CT-19")
def test_defended_piece_is_still_threatened():
    engine = GameEngine(fen="4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    assert engine.threatened_pieces(Color.WHITE) == [sq("e4")]
    assert engine.threatened_pieces(Color.BLACK) == [sq("d5")]


@pytest.mark.ct("CT-19")
def test_pawn_capturable_en_passant_is_threatened():
    engine = GameEngine(fen="4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1")
    assert engine.threatened_pieces(Color.WHITE) == []
    play_all(engine, "e2e4")
    assert engine.threatened_pieces(Color.WHITE) == [sq("e4")]


@pytest.mark.ct("CT-19")
def test_threat_of_en_passant_ends_with_the_window():
    engine = GameEngine(fen="4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1")
    play_all(engine, "e2e4", "e8e7", "e1e2")
    assert sq("e4") not in engine.threatened_pieces(Color.WHITE)


@pytest.mark.ct("CT-19")
def test_illegal_en_passant_is_not_a_threat():
    engine = GameEngine(fen="8/8/8/K2pP2r/8/8/8/4k3 w - d6 0 2")
    assert engine.threatened_pieces(Color.BLACK) == []


@pytest.mark.ct("CT-19")
def test_en_passant_victim_is_listed_once_even_with_two_capturers_or_a_direct_attack():
    two_capturers = GameEngine(fen="4k3/8/8/8/3pPp2/8/8/4K2B b - e3 0 2")
    assert two_capturers.threatened_pieces(Color.WHITE) == [sq("e4")]
    attacked_too = GameEngine(fen="4k3/8/5n2/8/3pP3/8/8/4K3 b - e3 0 2")
    assert attacked_too.threatened_pieces(Color.WHITE) == [sq("e4")]


@pytest.mark.ct("CT-19")
def test_threat_query_does_not_change_the_game():
    engine = GameEngine(fen="4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1")
    play_all(engine, "e2e4")
    fen = engine.board.to_fen()
    engine.threatened_pieces(Color.WHITE)
    engine.threatened_pieces(Color.BLACK)
    assert engine.board.to_fen() == fen
    assert engine.board.en_passant_target == sq("e3")


def test_promotion_is_reported_in_history():
    engine = GameEngine(fen="k7/4P3/8/8/8/8/8/4K3 w - - 0 1")
    outcome = engine.play(sq("e7"), sq("e8"), PieceType.QUEEN)
    assert outcome.san == "e8=Q+"
    assert engine.history == ["e8=Q+"]


def test_take_back_restores_the_position_exactly():
    engine = GameEngine()
    play_all(engine, "e2e4", "d7d5")
    fen = engine.final_fen
    play_all(engine, "e4d5")
    assert engine.players[Color.WHITE].captured
    engine.take_back_last_move()
    assert engine.final_fen == fen
    assert engine.history == ["e4", "d5"]
    assert engine.players[Color.WHITE].captured == []
    assert engine.turn is Color.WHITE


def test_take_back_reopens_a_finished_game_and_removes_the_point():
    engine = GameEngine()
    play_all(engine, "f2f3", "e7e5", "g2g4", "d8h4")
    assert engine.result.reason is EndReason.CHECKMATE
    engine.take_back_last_move()
    assert engine.result is None and engine.state is GameState.IN_PROGRESS
    assert engine.players[Color.BLACK].match_points == 0.0
    assert engine.legal_moves_from(Square.from_name("d8"))


def test_take_back_removes_the_half_point_of_a_draw():
    engine = GameEngine(fen="4k3/8/8/8/8/8/4q3/4K3 w - - 0 1")
    assert engine.play(Square.from_name("e1"), Square.from_name("e2")).result.reason is EndReason.INSUFFICIENT_MATERIAL
    engine.take_back_last_move()
    assert all(player.match_points == 0.0 for player in engine.players.values())
    assert engine.result is None


def test_take_back_does_not_count_the_repetition():
    engine = GameEngine()
    shuffle = "g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1"
    play_all(engine, *shuffle.split())
    engine.play(Square.from_name("f6"), Square.from_name("g8"))
    assert engine.result.reason is EndReason.THREEFOLD_REPETITION
    engine.take_back_last_move()
    assert engine.result is None
    assert engine.play(Square.from_name("f6"), Square.from_name("g8")).result.reason is EndReason.THREEFOLD_REPETITION


def test_take_back_undoes_a_single_move_and_refuses_without_one():
    engine = GameEngine()
    with pytest.raises(IndexError):
        engine.take_back_last_move()
    play_all(engine, "e2e4")
    engine.take_back_last_move()
    with pytest.raises(IndexError):
        engine.take_back_last_move()


def test_finish_with_does_not_change_a_finished_game():
    engine = GameEngine()
    decided = engine.finish_with(GameResult(Color.WHITE, EndReason.TIMEOUT))
    assert decided.reason is EndReason.TIMEOUT and engine.state is GameState.FINISHED
    assert engine.finish_with(GameResult(None, EndReason.AGREEMENT)) == decided
    assert engine.players[Color.WHITE].match_points == 1.0
