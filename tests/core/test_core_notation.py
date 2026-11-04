"""Notação SAN nos casos difíceis: desambiguação, captura, xeque, mate, roque e promoção."""
import pytest
from core_helpers import play_all, sq

from xadrez.core import Board, GameEngine, PieceType, legal_moves, move_to_san


def san_of(fen, uci):
    """Escreve em SAN a jogada legal da posição que corresponde ao código UCI."""
    board = Board.from_fen(fen)
    move = next(move for move in legal_moves(board) if move.uci == uci)
    san = move_to_san(board, move)
    assert board.to_fen() == fen
    return san


@pytest.mark.parametrize(
    "fen, uci, expected",
    [
        ("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", "e2e4", "e4"),
        ("4k3/8/8/8/8/8/8/1N2K3 w - - 0 1", "b1c3", "Nc3"),
        ("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1", "e4d5", "exd5"),
        ("4k3/8/8/3p4/8/2N5/8/4K3 w - - 0 1", "c3d5", "Nxd5"),
        ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", "e5d6", "exd6"),
    ],
    ids=["pawn", "piece", "pawn-capture", "piece-capture", "en-passant"],
)
def test_basic_notation(fen, uci, expected):
    assert san_of(fen, uci) == expected


@pytest.mark.parametrize(
    "fen, uci, expected",
    [
        ("4k3/8/8/8/8/5N2/8/1N2K3 w - - 0 1", "b1d2", "Nbd2"),
        ("4k3/8/8/8/8/5N2/8/1N2K3 w - - 0 1", "f3d2", "Nfd2"),
        ("4k3/8/8/R7/8/8/8/R3K3 w - - 0 1", "a1a3", "R1a3"),
        ("4k3/8/8/R7/8/8/8/R3K3 w - - 0 1", "a5a3", "R5a3"),
        ("8/k7/8/8/4Q2Q/1K6/8/7Q w - - 0 1", "h4e1", "Qh4e1"),
        ("8/k7/8/8/4Q2Q/1K6/8/7Q w - - 0 1", "e4e1", "Qee1"),
        ("8/k7/8/8/4Q2Q/1K6/8/7Q w - - 0 1", "h1e1", "Q1e1"),
        ("4k3/8/8/3p4/8/2N1N3/8/4K3 w - - 0 1", "c3d5", "Ncxd5"),
    ],
    ids=["file-b", "file-f", "rank-1", "rank-5", "both", "file-e", "rank-1-queen", "with-capture"],
)
def test_disambiguation(fen, uci, expected):
    assert san_of(fen, uci) == expected


def test_pinned_rival_does_not_require_disambiguation():
    assert san_of("4r1k1/8/8/8/8/8/4N3/1N2K3 w - - 0 1", "b1c3") == "Nc3"


def test_rival_of_another_kind_does_not_require_disambiguation():
    assert san_of("4k3/8/8/8/8/8/1B6/RN2K3 w - - 0 1", "b1c3") == "Nc3"


@pytest.mark.parametrize(
    "fen, uci, expected",
    [
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1", "O-O"),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1c1", "O-O-O"),
        ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1", "e8g8", "O-O"),
        ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1", "e8c8", "O-O-O"),
        ("3k4/8/8/8/8/8/8/R3K3 w Q - 0 1", "e1c1", "O-O-O+"),
        ("5k2/8/8/8/8/8/8/4K2R w K - 0 1", "e1g1", "O-O+"),
    ],
)
def test_castling_notation(fen, uci, expected):
    assert san_of(fen, uci) == expected


@pytest.mark.parametrize(
    "fen, uci, expected",
    [
        ("7k/4P3/8/8/8/8/8/4K3 w - - 0 1", "e7e8q", "e8=Q+"),
        ("7k/4P3/8/8/8/8/8/4K3 w - - 0 1", "e7e8r", "e8=R+"),
        ("7k/4P3/8/8/8/8/8/4K3 w - - 0 1", "e7e8b", "e8=B"),
        ("7k/4P3/8/8/8/8/8/4K3 w - - 0 1", "e7e8n", "e8=N"),
        ("5r1k/4P1pp/8/8/8/8/8/4K3 w - - 0 1", "e7f8q", "exf8=Q#"),
        ("5r1k/4P1pp/8/8/8/8/8/4K3 w - - 0 1", "e7f8n", "exf8=N"),
        ("4k3/8/8/8/8/8/p7/1R2K3 b - - 0 1", "a2b1q", "axb1=Q+"),
    ],
)
def test_promotion_notation(fen, uci, expected):
    assert san_of(fen, uci) == expected


@pytest.mark.parametrize(
    "fen, uci, expected",
    [
        ("6k1/8/8/8/8/8/8/R3K3 w - - 0 1", "a1a8", "Ra8+"),
        ("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1", "a1a8", "Ra8#"),
        ("7k/8/6K1/8/8/8/8/5Q2 w - - 0 1", "f1f8", "Qf8#"),
        ("7k/8/6K1/8/8/8/8/5Q2 w - - 0 1", "f1f7", "Qf7"),
    ],
    ids=["check", "mate", "mate-with-king-help", "stalemate-has-no-suffix"],
)
def test_check_and_mate_suffixes(fen, uci, expected):
    assert san_of(fen, uci) == expected


def test_history_of_a_real_opening():
    engine = GameEngine()
    play_all(engine, "e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5c6", "d7c6", "e1g1")
    assert engine.history == ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Bxc6", "dxc6", "O-O"]


def test_history_records_only_accepted_moves():
    engine = GameEngine()
    engine.play(sq("e2"), sq("e5"))
    engine.play(sq("e7"), sq("e5"))
    engine.play(sq("e2"), sq("e4"))
    assert engine.history == ["e4"]


def test_history_records_a_promotion_with_capture():
    engine = GameEngine(fen="1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    engine.play(sq("a7"), sq("b8"), PieceType.KNIGHT)
    assert engine.history == ["axb8=N"]
