"""Movimento das peças: padrões válidos, movimentos proibidos, colisão e salto do cavalo."""
import pytest
from core_helpers import play_all, sq, target_names

from xadrez.core import (
    Bishop,
    Board,
    Color,
    GameEngine,
    King,
    Knight,
    MoveError,
    Pawn,
    Piece,
    Queen,
    Rook,
    SlidingPiece,
    legal_moves_from,
)

ROOK_FROM_D4 = {
    *("d1", "d2", "d3", "d5", "d6", "d7", "d8"),
    *("a4", "b4", "c4", "e4", "f4", "g4", "h4"),
}
BISHOP_FROM_D4 = {
    *("a1", "b2", "c3", "e5", "f6", "g7", "h8"),
    *("a7", "b6", "c5", "e3", "f2", "g1"),
}
KNIGHT_FROM_D4 = {"b3", "b5", "c2", "c6", "e2", "e6", "f3", "f5"}
KING_FROM_D4 = {"c3", "c4", "c5", "d3", "d5", "e3", "e4", "e5"}


@pytest.mark.ct("CT-04")
@pytest.mark.parametrize(
    "fen, expected",
    [
        ("k7/8/8/8/3R4/8/8/7K w - - 0 1", ROOK_FROM_D4),
        ("k7/8/8/8/3B4/8/8/7K w - - 0 1", BISHOP_FROM_D4),
        ("k7/8/8/8/3Q4/8/8/7K w - - 0 1", ROOK_FROM_D4 | BISHOP_FROM_D4),
        ("k7/8/8/8/3N4/8/8/7K w - - 0 1", KNIGHT_FROM_D4),
        ("k7/8/8/8/3K4/8/8/8 w - - 0 1", KING_FROM_D4),
    ],
    ids=["rook", "bishop", "queen", "knight", "king"],
)
def test_piece_reaches_all_squares_of_its_pattern(fen, expected):
    assert target_names(legal_moves_from(Board.from_fen(fen), sq("d4"))) == expected


@pytest.mark.ct("CT-04")
def test_pawn_moves_one_or_two_squares_from_start():
    board = Board.initial()
    assert target_names(legal_moves_from(board, sq("e2"))) == {"e3", "e4"}
    assert target_names(legal_moves_from(board, sq("e7"))) == {"e6", "e5"}


@pytest.mark.ct("CT-04")
def test_pawn_moves_one_square_after_leaving_start():
    board = Board.from_fen("4k3/8/8/8/8/4P3/8/4K3 w - - 0 1")
    assert target_names(legal_moves_from(board, sq("e3"))) == {"e4"}


@pytest.mark.ct("CT-04")
def test_pawn_captures_diagonally_only_on_enemy_pieces():
    board = Board.from_fen("4k3/8/8/3p1P2/4P3/8/8/4K3 w - - 0 1")
    assert target_names(legal_moves_from(board, sq("e4"))) == {"e5", "d5"}


@pytest.mark.ct("CT-04")
def test_black_pawn_moves_down_the_board():
    board = Board.from_fen("4k3/8/8/8/3p4/4P3/8/4K3 b - - 0 1")
    assert target_names(legal_moves_from(board, sq("d4"))) == {"d3", "e3"}


@pytest.mark.ct("CT-04")
def test_each_piece_can_really_move_through_the_engine():
    engine = GameEngine()
    play_all(engine, "e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5", "f1c4", "c8g4", "g1f3", "b8c6", "a1b1")
    assert engine.history == ["e4", "d5", "exd5", "Qxd5", "Nc3", "Qa5", "Bc4", "Bg4", "Nf3", "Nc6", "Rb1"]
    assert engine.board.piece_at(sq("b1")).color is Color.WHITE


def test_empty_square_has_no_moves():
    assert legal_moves_from(Board.initial(), sq("e4")) == []


@pytest.mark.ct("CT-05")
@pytest.mark.parametrize(
    "fen, origin, target",
    [
        ("k7/7p/8/8/3R4/8/8/7K w - - 0 1", "d4", "e5"),
        ("k7/7p/8/8/3B4/8/8/7K w - - 0 1", "d4", "d5"),
        ("k7/7p/8/8/3Q4/8/8/7K w - - 0 1", "d4", "e6"),
        ("k7/7p/8/8/3N4/8/8/7K w - - 0 1", "d4", "d6"),
        ("k7/7p/8/8/3K4/8/8/8 w - - 0 1", "d4", "d6"),
        ("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", "e4", "e3"),
        ("4k3/8/8/8/8/4P3/8/4K3 w - - 0 1", "e3", "e5"),
        ("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", "e4", "f5"),
        ("4k3/8/8/4p3/4P3/8/8/4K3 w - - 0 1", "e4", "e5"),
        ("4k3/7p/8/8/8/8/4N3/4K3 w - - 0 1", "e1", "e2"),
        ("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", "a1", "e1"),
    ],
    ids=[
        "rook-diagonal",
        "bishop-straight",
        "queen-knight-jump",
        "knight-straight",
        "king-two-squares",
        "pawn-backward",
        "pawn-double-off-start",
        "pawn-diagonal-without-capture",
        "pawn-straight-capture",
        "king-captures-own",
        "rook-captures-own",
    ],
)
def test_forbidden_move_is_refused_without_changing_state(fen, origin, target):
    engine = GameEngine(fen=fen)
    outcome = engine.play(sq(origin), sq(target))
    assert not outcome.ok
    assert outcome.error is MoveError.ILLEGAL_MOVE
    assert engine.board.to_fen() == fen
    assert engine.history == []


@pytest.mark.parametrize("sliding_class", [Rook, Bishop, Queen])
def test_sliding_pieces_share_the_collision_base_class(sliding_class):
    assert issubclass(sliding_class, SlidingPiece)
    assert issubclass(SlidingPiece, Piece)


@pytest.mark.parametrize("leaping_class", [Knight, King, Pawn])
def test_other_pieces_do_not_slide(leaping_class):
    assert issubclass(leaping_class, Piece)
    assert not issubclass(leaping_class, SlidingPiece)


def test_piece_is_abstract():
    with pytest.raises(TypeError):
        Piece(Color.WHITE)


def test_piece_symbol_and_repr():
    assert Rook(Color.WHITE).symbol == "R"
    assert Rook(Color.BLACK).symbol == "r"
    assert repr(Knight(Color.BLACK)) == "Knight(BLACK)"


@pytest.mark.ct("CT-06")
def test_rook_stops_before_own_piece_and_on_enemy_piece():
    board = Board.from_fen("k7/8/3p4/8/1P1R4/8/8/7K w - - 0 1")
    targets = target_names(legal_moves_from(board, sq("d4")))
    assert "d6" in targets
    assert "d7" not in targets
    assert "b4" not in targets
    assert "a4" not in targets
    assert "c4" in targets


@pytest.mark.ct("CT-06")
def test_bishop_stops_at_first_piece_on_diagonal():
    board = Board.from_fen("k7/8/5p2/8/3B4/2P5/8/7K w - - 0 1")
    targets = target_names(legal_moves_from(board, sq("d4")))
    assert {"e5", "f6"} <= targets
    assert "g7" not in targets
    assert "c3" not in targets
    assert "b2" not in targets


@pytest.mark.ct("CT-06")
def test_queen_cannot_cross_pieces():
    board = Board.initial()
    assert legal_moves_from(board, sq("d1")) == []


@pytest.mark.ct("CT-06")
@pytest.mark.parametrize(
    "fen, origin, target",
    [
        ("k7/8/3p4/8/3R4/8/8/7K w - - 0 1", "d4", "d7"),
        ("k7/8/8/8/1P1R4/8/8/7K w - - 0 1", "d4", "a4"),
        ("k7/8/5p2/8/3B4/8/8/7K w - - 0 1", "d4", "g7"),
        ("1k6/8/8/3Q1p2/8/8/8/7K w - - 0 1", "d5", "g5"),
    ],
    ids=["rook-through-enemy", "rook-through-own", "bishop-through-enemy", "queen-through-enemy"],
)
def test_moving_through_a_piece_is_refused(fen, origin, target):
    outcome = GameEngine(fen=fen).play(sq(origin), sq(target))
    assert outcome.error is MoveError.ILLEGAL_MOVE


@pytest.mark.ct("CT-06")
def test_pawn_double_step_is_blocked_by_piece_on_either_square():
    blocked_at_first = Board.from_fen("4k3/8/8/8/8/4n3/4P3/4K3 w - - 0 1")
    blocked_at_second = Board.from_fen("4k3/8/8/8/4n3/8/4P3/4K3 w - - 0 1")
    assert legal_moves_from(blocked_at_first, sq("e2")) == []
    assert target_names(legal_moves_from(blocked_at_second, sq("e2"))) == {"e3"}


@pytest.mark.ct("CT-07")
def test_knight_jumps_over_pieces_at_the_start():
    engine = GameEngine()
    assert target_names(engine.legal_moves_from(sq("b1"))) == {"a3", "c3"}
    assert engine.play(sq("b1"), sq("c3")).ok
    assert engine.board.piece_at(sq("c3")).kind.value == "knight"


@pytest.mark.ct("CT-07")
def test_surrounded_knight_keeps_all_its_targets():
    board = Board.from_fen("k7/8/8/2ppp3/2pNp3/2ppp3/8/7K w - - 0 1")
    assert target_names(legal_moves_from(board, sq("d4"))) == KNIGHT_FROM_D4


@pytest.mark.ct("CT-07")
def test_knight_in_corner_has_two_targets():
    board = Board.from_fen("k7/8/8/8/8/8/8/N6K w - - 0 1")
    assert target_names(legal_moves_from(board, sq("a1"))) == {"b3", "c2"}
