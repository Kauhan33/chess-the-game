"""Perft: conta as posições alcançáveis e compara com os valores de referência publicados.

Um único erro em roque, en passant, promoção ou cravada muda a contagem. Se o total não bater,
quem está errado é o motor: o valor de referência não se altera.
"""
import pytest

from xadrez.core import STARTING_FEN, Board, leaves_king_in_check, legal_moves, perft

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
ENDGAME_PINS = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
PROMOTIONS = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
CASTLING_BUGS = "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"
# A 3ª fileira é `P1NP1N2`. Com `P1NP1N1P` haveria nove peões brancos e a contagem de referência não vale.
SYMMETRIC_MIDDLEGAME = "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"

REFERENCE_COUNTS = [
    (STARTING_FEN, [20, 400, 8902, 197281]),
    (KIWIPETE, [48, 2039, 97862]),
    (ENDGAME_PINS, [14, 191, 2812, 43238]),
    (PROMOTIONS, [6, 264, 9467]),
    (CASTLING_BUGS, [44, 1486, 62379]),
    (SYMMETRIC_MIDDLEGAME, [46, 2079, 89890]),
]

# Além das profundidades da especificação: demoram mais e por isso levam a marca `slow`.
DEEP_REFERENCE_COUNTS = [
    (PROMOTIONS, 4, 422333),
    (ENDGAME_PINS, 5, 674624),
    (CASTLING_BUGS, 4, 2103487),
    (KIWIPETE, 4, 4085603),
]


REFERENCE_CASES = [
    pytest.param(fen, depth, nodes, id=f"{fen.split()[0][:12]}-d{depth}")
    for fen, counts in REFERENCE_COUNTS
    for depth, nodes in enumerate(counts, start=1)
]


@pytest.mark.ct("CT-17")
@pytest.mark.parametrize("fen, depth, nodes", REFERENCE_CASES)
def test_perft_matches_reference(fen, depth, nodes):
    board = Board.from_fen(fen)
    assert perft(board, depth) == nodes
    assert board.to_fen() == fen


@pytest.mark.ct("CT-17")
@pytest.mark.slow
@pytest.mark.parametrize(
    "fen, depth, nodes",
    [pytest.param(*case, id=f"{case[0].split()[0][:12]}-d{case[1]}") for case in DEEP_REFERENCE_COUNTS],
)
def test_deep_perft_matches_reference(fen, depth, nodes):
    board = Board.from_fen(fen)
    assert perft(board, depth) == nodes
    assert board.to_fen() == fen


def test_perft_of_depth_zero_is_one_position():
    assert perft(Board.initial(), 0) == 1


def test_fast_legality_filter_agrees_with_testing_every_move():
    """O filtro rápido só pode economizar trabalho: a lista final tem de ser a do teste completo."""
    for fen, _ in REFERENCE_COUNTS:
        board = Board.from_fen(fen)
        for move in legal_moves(board):
            board.apply(move)
            complete = {
                candidate.uci
                for square, piece in list(board.pieces(board.turn))
                for candidate in piece.pseudo_legal_moves(board, square)
                if not leaves_king_in_check(board, candidate)
            }
            assert {candidate.uci for candidate in legal_moves(board)} == complete
            board.undo()
