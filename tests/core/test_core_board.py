"""Tabuleiro: posição inicial, FEN, operações básicas e a pilha de desfazer."""
import pytest
from core_helpers import sq

from xadrez.core import (
    STARTING_FEN,
    Bishop,
    Board,
    Color,
    King,
    Move,
    Pawn,
    PieceType,
    Queen,
    Rook,
    Square,
    legal_moves,
)

BACK_RANK = [
    PieceType.ROOK,
    PieceType.KNIGHT,
    PieceType.BISHOP,
    PieceType.QUEEN,
    PieceType.KING,
    PieceType.BISHOP,
    PieceType.KNIGHT,
    PieceType.ROOK,
]

UNDO_POSITIONS = [
    STARTING_FEN,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2",
    "4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 2",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 7 30",
]


@pytest.mark.ct("CT-01")
def test_initial_position_has_official_setup():
    board = Board.initial()
    for file, kind in enumerate(BACK_RANK):
        assert board.piece_at(Square(file, 0)).kind is kind
        assert board.piece_at(Square(file, 0)).color is Color.WHITE
        assert board.piece_at(Square(file, 7)).kind is kind
        assert board.piece_at(Square(file, 7)).color is Color.BLACK
        assert board.piece_at(Square(file, 1)).kind is PieceType.PAWN
        assert board.piece_at(Square(file, 1)).color is Color.WHITE
        assert board.piece_at(Square(file, 6)).kind is PieceType.PAWN
        assert board.piece_at(Square(file, 6)).color is Color.BLACK
    assert all(board.piece_at(Square(file, rank)) is None for file in range(8) for rank in range(2, 6))


@pytest.mark.ct("CT-01")
def test_initial_position_state():
    board = Board.initial()
    assert board.to_fen() == STARTING_FEN
    assert board.turn is Color.WHITE
    assert board.castling_rights == frozenset("KQkq")
    assert board.en_passant_target is None
    assert (board.halfmove_clock, board.fullmove_number) == (0, 1)
    assert board.king_square(Color.WHITE) == sq("e1")
    assert board.king_square(Color.BLACK) == sq("e8")
    assert len(list(board.pieces())) == 32
    assert len(list(board.pieces(Color.WHITE))) == 16
    assert len(legal_moves(board)) == 20


@pytest.mark.parametrize(
    "fen",
    [
        STARTING_FEN,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 3 17",
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 99 80",
        "r3k3/8/8/8/8/8/8/4K2R b Kq - 12 40",
    ],
)
def test_fen_round_trip(fen):
    assert Board.from_fen(fen).to_fen() == fen


@pytest.mark.parametrize(
    "fen",
    [
        None,
        "",
        "not a fen",
        "8/8/8/8/8/8/8/8 w - - 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP w KQkq - 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN w KQkq - 0 1",
        "rnbqkbnr/pppppppp/9/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "rnbqkbnrr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "rnbqkbnx/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkx - 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KK - 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq e9 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - -1 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 0",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - x 1",
        "4k3/8/8/8/8/8/8/8 w - - 0 1",
        "4k2k/8/8/8/8/8/8/4K3 w - - 0 1",
        "P3k3/8/8/8/8/8/8/4K3 w - - 0 1",
        "4k3/8/8/8/8/8/8/p3K3 w - - 0 1",
        "4k3/8/8/8/8/8/8/4K3 w K - 0 1",
        "4k3/8/8/8/8/8/8/R3K3 w K - 0 1",
        "4k3/8/8/8/8/8/8/3K3R w K - 0 1",
        "4k3/8/8/8/8/8/8/4K3 w - e6 0 1",
        "4k3/8/8/4p3/8/8/8/4K3 b - e6 0 1",
        "4k3/8/4p3/4p3/8/8/8/4K3 w - e6 0 1",
        "4k3/4R3/8/8/8/8/8/4K3 w - - 0 1",
    ],
)
def test_malformed_or_impossible_fen_raises_value_error(fen):
    with pytest.raises(ValueError):
        Board.from_fen(fen)


def test_place_and_remove_update_the_grid_and_the_king_square():
    board = Board()
    king = King(Color.WHITE)
    board.place(sq("d4"), king)
    assert board.piece_at(sq("d4")) is king
    assert board.king_square(Color.WHITE) == sq("d4")
    assert board.remove(sq("d4")) is king
    assert board.piece_at(sq("d4")) is None
    assert board.king_square(Color.WHITE) is None
    assert board.remove(sq("d4")) is None


def test_placing_over_a_king_clears_its_square():
    board = Board()
    board.place(sq("d4"), King(Color.WHITE))
    board.place(sq("d4"), Rook(Color.WHITE))
    assert board.king_square(Color.WHITE) is None


def test_piece_at_off_board_returns_none():
    board = Board.initial()
    assert board.piece_at(Square(8, 0)) is None
    assert board.piece_at(Square(0, -1)) is None


def test_pieces_lists_each_piece_with_its_square():
    board = Board()
    white_rook, black_bishop = Rook(Color.WHITE), Bishop(Color.BLACK)
    board.place(sq("a1"), white_rook)
    board.place(sq("h8"), black_bishop)
    assert list(board.pieces(Color.WHITE)) == [(sq("a1"), white_rook)]
    assert list(board.pieces(Color.BLACK)) == [(sq("h8"), black_bishop)]
    assert len(list(board.pieces())) == 2


def test_attack_queries_count_pawn_diagonals_and_stop_at_blockers():
    board = Board.from_fen("4k3/8/8/8/8/8/1P6/R3K3 w - - 0 1")
    assert board.is_attacked(sq("c3"), Color.WHITE)
    assert board.is_attacked(sq("a3"), Color.WHITE)
    assert board.is_attacked(sq("a8"), Color.WHITE)
    assert not board.is_attacked(sq("b3"), Color.WHITE)
    assert board.attackers_of(sq("d1"), Color.WHITE) == [sq("a1"), sq("e1")]
    assert board.attackers_of(sq("h8"), Color.WHITE) == []


def test_apply_returns_details_of_the_capture():
    board = Board.from_fen("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    pawn = board.piece_at(sq("e4"))
    victim = board.piece_at(sq("d5"))
    applied = board.apply(Move(sq("e4"), sq("d5")))
    assert applied.piece is pawn
    assert applied.captured is victim
    assert applied.captured_square == sq("d5")


def test_apply_from_empty_square_raises():
    with pytest.raises(ValueError):
        Board.initial().apply(Move(sq("e4"), sq("e5")))


def test_undo_without_applied_moves_raises():
    with pytest.raises(IndexError):
        Board.initial().undo()


@pytest.mark.parametrize("fen", UNDO_POSITIONS)
def test_undo_restores_exact_state_after_every_legal_move(fen):
    board = Board.from_fen(fen)
    pieces_before = list(board.pieces())
    kings_before = [board.king_square(color) for color in Color]
    for move in legal_moves(board):
        board.apply(move)
        assert board.to_fen() != fen
        board.undo()
        assert board.to_fen() == fen
    assert list(board.pieces()) == pieces_before
    assert [board.king_square(color) for color in Color] == kings_before


def test_undo_walks_back_a_chain_of_moves_to_the_start():
    board = Board.initial()
    fens = [board.to_fen()]
    for origin, target in [("e2", "e4"), ("d7", "d5"), ("e4", "d5"), ("d8", "d5"), ("b1", "c3")]:
        move = next(move for move in legal_moves(board) if move.origin == sq(origin) and move.target == sq(target))
        board.apply(move)
        fens.append(board.to_fen())
    while len(fens) > 1:
        assert board.to_fen() == fens.pop()
        board.undo()
    assert board.to_fen() == STARTING_FEN


def test_counters_follow_fen_rules():
    board = Board.initial()
    board.apply(Move(sq("g1"), sq("f3")))
    assert (board.halfmove_clock, board.fullmove_number, board.turn) == (1, 1, Color.BLACK)
    board.apply(Move(sq("g8"), sq("f6")))
    assert (board.halfmove_clock, board.fullmove_number, board.turn) == (2, 2, Color.WHITE)
    board.apply(Move(sq("e2"), sq("e4"), is_double_push=True))
    assert (board.halfmove_clock, board.fullmove_number) == (0, 2)
    assert board.en_passant_target == sq("e3")


def test_capture_resets_halfmove_clock():
    board = Board.from_fen("4k3/8/8/3p4/8/2N5/8/4K3 w - - 40 60")
    board.apply(Move(sq("c3"), sq("d5")))
    assert board.halfmove_clock == 0


def test_promotion_replaces_the_pawn_and_undo_restores_the_same_pawn():
    board = Board.from_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    pawn = board.piece_at(sq("a7"))
    board.apply(Move(sq("a7"), sq("a8"), promotion=PieceType.QUEEN))
    assert isinstance(board.piece_at(sq("a8")), Queen)
    assert board.piece_at(sq("a8")).color is Color.WHITE
    board.undo()
    assert board.piece_at(sq("a7")) is pawn
    assert isinstance(pawn, Pawn)
    assert board.piece_at(sq("a8")) is None
