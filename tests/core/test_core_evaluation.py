"""Avaliação da CPU: simétrica entre as cores e coerente com o que um jogador esperaria."""
import pytest

from xadrez.core import Board
from xadrez.core.evaluation import MAX_PHASE, evaluate
from xadrez.core.search_board import SearchBoard


def score_of(fen):
    return evaluate(SearchBoard.from_board(Board.from_fen(fen)))


def mirrored(fen):
    """Troca as cores e vira o tabuleiro: é a mesma posição, vista pelo outro lado."""
    placement, turn, castling, en_passant, *counters = fen.split()
    flipped = "/".join(row.swapcase() for row in reversed(placement.split("/")))
    new_turn = "b" if turn == "w" else "w"
    new_castling = "".join(sorted(castling.swapcase())) if castling != "-" else "-"
    new_en_passant = "-" if en_passant == "-" else f"{en_passant[0]}{9 - int(en_passant[1])}"
    return " ".join([flipped, new_turn, new_castling, new_en_passant, *counters])


@pytest.mark.parametrize(
    "fen",
    [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 9",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    ],
)
def test_mirrored_position_gets_the_same_score(fen):
    assert score_of(fen) == score_of(mirrored(fen))


def test_score_is_from_the_point_of_view_of_who_moves():
    white_up_a_queen = "4k3/8/8/8/8/8/8/3QK3"
    assert score_of(f"{white_up_a_queen} w - - 0 1") > 800
    assert score_of(f"{white_up_a_queen} b - - 0 1") < -800


def test_material_counts_more_than_position():
    assert score_of("4k3/8/8/8/8/8/P7/N3K3 w - - 0 1") > score_of("4k3/8/8/8/8/8/P7/4K3 w - - 0 1")


def test_knight_is_better_in_the_center_than_on_the_rim():
    center = "4k3/8/8/8/3N4/8/PPPPPPPP/4K3 w - - 0 1"
    rim = "4k3/8/8/8/N7/8/PPPPPPPP/4K3 w - - 0 1"
    assert score_of(center) > score_of(rim)


def test_king_hides_in_the_middlegame_and_centralizes_in_the_endgame():
    middlegame_castled = "rnbq1rk1/pppppppp/8/8/8/8/PPPPPPPP/RNBQ1RK1 w - - 0 1"
    middlegame_exposed = "rnbq1rk1/pppppppp/8/8/4K3/8/PPPPPPPP/RNBQ1R2 w - - 0 1"
    assert score_of(middlegame_castled) > score_of(middlegame_exposed)
    endgame_corner = "6k1/8/8/8/8/8/P7/K7 w - - 0 1"
    endgame_center = "6k1/8/8/8/3K4/8/P7/8 w - - 0 1"
    assert score_of(endgame_center) > score_of(endgame_corner)


def test_advanced_pawn_is_worth_more_in_the_endgame():
    assert score_of("4k3/P7/8/8/8/8/8/4K3 w - - 0 1") > score_of("4k3/8/8/8/8/8/P7/4K3 w - - 0 1") + 50


def test_bishop_pair_gets_a_bonus_for_both_colors():
    with_pair = "2b1kb2/8/8/8/8/8/8/2B1KB2 w - - 0 1"
    assert score_of(with_pair) == score_of(mirrored(with_pair))
    assert score_of("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1") > 2 * 330
    assert score_of("2b1kb2/8/8/8/8/8/8/4K3 b - - 0 1") > 2 * 330


@pytest.mark.parametrize(
    "fen",
    ["4k3/8/8/8/8/8/8/4K3 w - - 0 1", "4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", "4k3/8/8/8/8/8/8/1N2K3 b - - 0 1"],
)
def test_material_that_cannot_mate_is_scored_as_a_draw(fen):
    assert score_of(fen) == 0


def test_lone_pawn_still_counts_even_with_low_phase():
    assert score_of("4k3/8/8/8/8/8/P7/4K3 w - - 0 1") > 100


def test_phase_above_the_maximum_after_promotions_is_clamped():
    """Com damas extras, a fase passa do máximo. A nota tem de continuar sendo a do meio-jogo puro."""
    board = SearchBoard.from_board(Board.from_fen("QQQ1k1QQ/8/8/8/8/8/QQ6/4K3 b - - 0 1"))
    assert board.phase > MAX_PHASE
    assert evaluate(board) == -board.midgame + 10


def test_passed_pawn_is_worth_more_than_a_blocked_one():
    passed = "4k3/8/8/4P3/8/8/8/4K3 w - - 0 1"
    opposed = "4k3/3p4/8/4P3/8/8/8/4K3 w - - 0 1"
    assert score_of(passed) > score_of(opposed) + 100


def test_passed_pawn_bonus_grows_as_it_advances_for_both_colors():
    white_far = score_of("4k3/8/8/8/8/P7/8/4K3 w - - 0 1")
    white_near = score_of("4k3/8/P7/8/8/8/8/4K3 w - - 0 1")
    assert white_near - white_far > 60
    black_far = score_of("4k3/8/p7/8/8/8/8/4K3 b - - 0 1")
    black_near = score_of("4k3/8/8/8/8/p7/8/4K3 b - - 0 1")
    assert black_near - black_far > 60


def test_isolated_and_doubled_pawns_lose_points():
    healthy = "4k3/8/8/8/8/8/PP6/4K3 w - - 0 1"
    isolated = "4k3/8/8/8/8/8/P1P5/4K3 w - - 0 1"
    doubled = "4k3/8/8/8/8/P7/P7/4K3 w - - 0 1"
    assert score_of(healthy) > score_of(isolated)
    assert score_of(healthy) > score_of(doubled)


def test_pawn_structure_is_computed_once_per_pawn_arrangement():
    board = SearchBoard.from_board(Board.from_fen("4k3/8/8/8/8/8/PP6/R3K3 w - - 0 1"))
    evaluate(board)
    assert len(board.pawn_cache) == 1
    rook_move = 0 | 3 << 6
    board.make(rook_move)
    evaluate(board)
    assert len(board.pawn_cache) == 1
    board.unmake()
    pawn_move = 8 | 16 << 6
    board.make(pawn_move)
    evaluate(board)
    assert len(board.pawn_cache) == 2
