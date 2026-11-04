"""Tipos básicos: cores, tipos de peça, casas, jogadas e os textos em português."""
import ast
from pathlib import Path

import pytest
from core_helpers import IndexLikeInteger, sq

import xadrez.core as core
from xadrez.core import Color, EndReason, GameResult, Move, MoveError, PieceType, Square
from xadrez.core.types import coerce_square

CORE_DIRECTORY = Path(core.__file__).parent


def test_color_opposite_and_label():
    assert Color.WHITE.opposite is Color.BLACK
    assert Color.BLACK.opposite is Color.WHITE
    assert Color.WHITE.label == "Brancas"
    assert Color.BLACK.label == "Pretas"


@pytest.mark.parametrize(
    "kind, value, points, symbol",
    [
        (PieceType.PAWN, "pawn", 1, "P"),
        (PieceType.KNIGHT, "knight", 3, "N"),
        (PieceType.BISHOP, "bishop", 3, "B"),
        (PieceType.ROOK, "rook", 5, "R"),
        (PieceType.QUEEN, "queen", 9, "Q"),
        (PieceType.KING, "king", 0, "K"),
    ],
)
def test_piece_type_attributes(kind, value, points, symbol):
    assert (kind.value, kind.points, kind.symbol) == (value, points, symbol)
    assert PieceType(value) is kind


def test_square_names_follow_board_convention():
    assert Square(0, 0).name == "a1"
    assert Square(7, 7).name == "h8"
    assert Square.from_name("e4") == Square(4, 3)


def test_a1_is_a_dark_square():
    assert sq("a1").is_dark
    assert not sq("a2").is_dark


@pytest.mark.parametrize(
    "square, expected",
    [(Square(0, 0), True), (Square(7, 7), True), (Square(8, 0), False), (Square(0, -1), False)],
)
def test_square_validity(square, expected):
    assert square.is_valid() is expected


@pytest.mark.parametrize("name", ["", "e", "e9", "i1", "e44", "E4", 42, None])
def test_square_from_malformed_name_raises(name):
    with pytest.raises(ValueError):
        Square.from_name(name)


def test_coerce_square_accepts_pairs_of_integers():
    assert coerce_square(Square(4, 1)) == Square(4, 1)
    assert isinstance(coerce_square((4, 1)), Square)
    assert coerce_square((IndexLikeInteger(4), IndexLikeInteger(1))) == Square(4, 1)


@pytest.mark.parametrize("value", [None, 5, "e2", (1,), (1, 2, 3), (1.5, 2), ("a", "b"), (8, 0), (0, -1), object()])
def test_coerce_square_rejects_everything_else(value):
    assert coerce_square(value) is None


def test_move_uci():
    assert Move(sq("e2"), sq("e4")).uci == "e2e4"
    assert Move(sq("a7"), sq("a8"), promotion=PieceType.KNIGHT).uci == "a7a8n"


def test_move_is_immutable_and_hashable():
    move = Move(sq("e2"), sq("e4"))
    assert move == Move(sq("e2"), sq("e4"))
    assert len({move, Move(sq("e2"), sq("e4"))}) == 1
    with pytest.raises(AttributeError):
        move.target = sq("e3")


def test_move_captured_square_differs_from_target_only_on_en_passant():
    assert Move(sq("e5"), sq("d6"), is_en_passant=True).captured_square == sq("d5")
    assert Move(sq("e5"), sq("d6")).captured_square == sq("d6")


def test_every_end_reason_has_a_label():
    assert EndReason.CHECKMATE.label == "Xeque-mate"
    assert all(reason.label for reason in EndReason)
    assert len({reason.label for reason in EndReason}) == len(EndReason)


def test_every_move_error_has_a_message():
    assert all(error.message for error in MoveError)
    assert len({error.message for error in MoveError}) == len(MoveError)


def test_game_result_reports_draws():
    assert GameResult(None, EndReason.STALEMATE).is_draw
    assert not GameResult(Color.WHITE, EndReason.CHECKMATE).is_draw


@pytest.mark.parametrize("source_file", sorted(CORE_DIRECTORY.glob("*.py")), ids=lambda path: path.name)
def test_source_parses_as_python_310(source_file):
    ast.parse(source_file.read_text(encoding="utf-8"), feature_version=(3, 10))


def test_public_api_is_reexported():
    assert all(hasattr(core, name) for name in core.__all__)
