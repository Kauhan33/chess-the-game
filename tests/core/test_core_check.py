"""Xeque, cravada e xeque-mate, incluindo partidas curtas de ponta a ponta."""
import pytest
from core_helpers import play_all, sq, target_names

from xadrez.core import (
    Board,
    Color,
    EndReason,
    GameEngine,
    GameState,
    MoveError,
    is_checkmate,
    is_in_check,
    is_stalemate,
    leaves_king_in_check,
    legal_moves,
    legal_moves_from,
)


@pytest.mark.ct("CT-12")
def test_pinned_knight_cannot_move():
    fen = "4r1k1/8/8/8/8/8/4N3/4K3 w - - 0 1"
    engine = GameEngine(fen=fen)
    assert engine.legal_moves_from(sq("e2")) == []
    assert engine.play(sq("e2"), sq("c3")).error is MoveError.LEAVES_KING_IN_CHECK
    assert engine.board.to_fen() == fen


@pytest.mark.ct("CT-12")
def test_exposing_the_king_is_a_different_error_from_an_illegal_pattern():
    engine = GameEngine(fen="4r1k1/8/8/8/8/8/4N3/4K3 w - - 0 1")
    assert engine.play(sq("e2"), sq("e4")).error is MoveError.ILLEGAL_MOVE
    assert engine.play(sq("e2"), sq("g3")).error is MoveError.LEAVES_KING_IN_CHECK


@pytest.mark.ct("CT-12")
def test_pinned_rook_moves_only_along_the_pin_line():
    board = Board.from_fen("4r1k1/8/8/8/8/4R3/8/4K3 w - - 0 1")
    assert target_names(legal_moves_from(board, sq("e3"))) == {"e2", "e4", "e5", "e6", "e7", "e8"}


@pytest.mark.ct("CT-12")
def test_pinned_bishop_moves_only_along_the_diagonal():
    board = Board.from_fen("6k1/8/8/8/7b/8/5B2/4K3 w - - 0 1")
    assert target_names(legal_moves_from(board, sq("f2"))) == {"g3", "h4"}


@pytest.mark.ct("CT-12")
def test_pinned_pawn_cannot_leave_the_file_of_the_pin_but_can_advance_on_it():
    board = Board.from_fen("4r1k1/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    assert target_names(legal_moves_from(board, sq("e4"))) == {"e5"}


@pytest.mark.ct("CT-12")
def test_king_cannot_step_onto_attacked_square():
    engine = GameEngine(fen="3r2k1/8/8/8/8/8/8/4K3 w - - 0 1")
    assert engine.play(sq("e1"), sq("d1")).error is MoveError.LEAVES_KING_IN_CHECK
    assert target_names(engine.legal_moves_from(sq("e1"))) == {"e2", "f1", "f2"}


@pytest.mark.ct("CT-12")
def test_king_cannot_retreat_along_the_line_of_the_checking_rook():
    """Quem cobre a casa atrás do rei é a torre: o rei não pode bloquear o raio saindo dele."""
    board = Board.from_fen("6k1/8/8/8/8/8/8/r3K3 w - - 0 1")
    targets = target_names(legal_moves_from(board, sq("e1")))
    assert "f1" not in targets
    assert "d1" not in targets
    assert targets == {"d2", "e2", "f2"}


@pytest.mark.ct("CT-12")
def test_king_cannot_capture_a_defended_piece():
    engine = GameEngine(fen="6k1/8/8/8/8/2n5/4r3/4K3 w - - 0 1")
    assert engine.play(sq("e1"), sq("e2")).error is MoveError.LEAVES_KING_IN_CHECK


@pytest.mark.ct("CT-12")
def test_kings_cannot_stand_adjacent():
    board = Board.from_fen("8/8/8/3k4/8/3K4/8/8 w - - 0 1")
    assert target_names(legal_moves_from(board, sq("d3"))) == {"c2", "c3", "d2", "e2", "e3"}


@pytest.mark.ct("CT-12")
def test_in_check_only_moves_that_resolve_it_are_legal():
    engine = GameEngine(fen="4r1k1/8/8/8/8/2N5/PP6/4K3 w - - 0 1")
    assert engine.in_check
    assert engine.play(sq("a2"), sq("a3")).error is MoveError.LEAVES_KING_IN_CHECK
    uci_moves = {move.uci for move in legal_moves(engine.board)}
    assert uci_moves == {"c3e2", "c3e4", "e1d1", "e1d2", "e1f1", "e1f2"}


@pytest.mark.ct("CT-12")
def test_double_check_forces_the_king_to_move():
    board = Board.from_fen("4k3/8/8/8/1b6/8/4r3/R3K3 w - - 0 1")
    assert len(board.attackers_of(sq("e1"), Color.BLACK)) == 2
    moves = legal_moves(board)
    assert moves
    assert all(move.origin == sq("e1") for move in moves)


def test_leaves_king_in_check_restores_the_board():
    fen = "4r1k1/8/8/8/8/8/4N3/4K3 w - - 0 1"
    board = Board.from_fen(fen)
    move = next(move for move in board.piece_at(sq("e2")).pseudo_legal_moves(board, sq("e2")))
    assert leaves_king_in_check(board, move)
    assert board.to_fen() == fen


def test_legal_moves_can_be_asked_for_the_side_not_to_move():
    board = Board.initial()
    assert len(legal_moves(board, Color.BLACK)) == 20
    assert board.turn is Color.WHITE
    assert board.to_fen() == Board.initial().to_fen()


def test_check_queries_without_kings_on_the_board():
    board = Board()
    assert not is_in_check(board, Color.WHITE)
    rook_board = Board.from_fen("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    rook_board.remove(sq("e1"))
    assert len(legal_moves_from(rook_board, sq("a1"))) > 0


def test_engine_reports_who_is_checking():
    engine = GameEngine(fen="4r1k1/8/8/8/8/8/8/4K3 w - - 0 1")
    assert engine.in_check
    assert engine.checked_king_square == sq("e1")
    assert engine.checking_pieces == [sq("e8")]


def test_engine_without_check_reports_nothing():
    engine = GameEngine()
    assert not engine.in_check
    assert engine.checked_king_square is None
    assert engine.checking_pieces == []


def test_move_that_gives_check_is_flagged_in_the_outcome():
    engine = GameEngine(fen="6k1/8/8/8/8/8/8/R3K3 w - - 0 1")
    outcome = engine.play(sq("a1"), sq("a8"))
    assert outcome.gives_check
    assert outcome.san == "Ra8+"
    assert engine.in_check
    assert engine.state is GameState.IN_PROGRESS


@pytest.mark.ct("CT-13")
def test_fools_mate_ends_the_game():
    engine = GameEngine()
    outcome = play_all(engine, "f2f3", "e7e5", "g2g4", "d8h4")
    assert outcome.gives_check
    assert outcome.result.winner is Color.BLACK
    assert outcome.result.reason is EndReason.CHECKMATE
    assert engine.result == outcome.result
    assert engine.state is GameState.FINISHED
    assert engine.history == ["f3", "e5", "g4", "Qh4#"]
    assert is_checkmate(engine.board)
    assert engine.checked_king_square == sq("e1")
    assert engine.checking_pieces == [sq("h4")]


@pytest.mark.ct("CT-13")
def test_scholars_mate_ends_the_game():
    engine = GameEngine()
    outcome = play_all(engine, "e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "g8f6", "h5f7")
    assert outcome.result.winner is Color.WHITE
    assert outcome.result.reason is EndReason.CHECKMATE
    assert engine.history == ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7#"]
    assert engine.players[Color.WHITE].material_score == 1


@pytest.mark.ct("CT-13")
def test_no_moves_are_accepted_after_checkmate():
    engine = GameEngine()
    play_all(engine, "f2f3", "e7e5", "g2g4", "d8h4")
    fen = engine.board.to_fen()
    assert engine.play(sq("a2"), sq("a3")).error is MoveError.GAME_NOT_ACTIVE
    assert engine.legal_moves_from(sq("a2")) == []
    assert engine.board.to_fen() == fen


@pytest.mark.ct("CT-13")
def test_back_rank_mate_from_a_fen():
    engine = GameEngine(fen="6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1")
    outcome = engine.play(sq("a1"), sq("a8"))
    assert outcome.san == "Ra8#"
    assert outcome.result.reason is EndReason.CHECKMATE


@pytest.mark.ct("CT-13")
def test_smothered_mate_with_a_knight():
    board = Board.from_fen("6rk/5Npp/8/8/8/8/8/4K3 b - - 0 1")
    assert is_checkmate(board)
    assert not is_stalemate(board)


@pytest.mark.ct("CT-13")
def test_check_with_an_escape_is_not_checkmate():
    checked = Board.from_fen("R5k1/8/8/8/8/8/8/4K3 b - - 0 1")
    assert is_in_check(checked)
    assert not is_checkmate(checked)


@pytest.mark.ct("CT-13")
def test_game_loaded_on_a_checkmate_is_already_finished():
    engine = GameEngine(fen="R5k1/5ppp/8/8/8/8/8/4K3 b - - 0 1")
    assert engine.state is GameState.FINISHED
    assert engine.result.winner is Color.WHITE
    assert engine.result.reason is EndReason.CHECKMATE
