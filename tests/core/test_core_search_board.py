"""Tabuleiro compacto da CPU: tem de obedecer às mesmas regras que o motor já provado por perft.

Três provas independentes: os valores publicados de perft, a comparação jogada a jogada com
`rules.legal_moves` em partidas aleatórias, e a conferência das contas incrementais contra o recálculo.
"""
import random

import pytest
from core_helpers import sq
from test_core_perft import DEEP_REFERENCE_COUNTS, ENDGAME_PINS, KIWIPETE, PROMOTIONS, REFERENCE_CASES

from xadrez.core import Board, Move, PieceType, legal_moves
from xadrez.core.evaluation import PAWN, QUEEN
from xadrez.core.search_board import (
    FLAG_CASTLING,
    FLAG_DOUBLE_PUSH,
    FLAG_EN_PASSANT,
    FLAG_PROMOTE_QUEEN,
    FLAG_SHIFT,
    MOVE_MASK,
    SearchBoard,
    encode_move,
)

CASTLING_AND_PROMOTIONS = "r3k2r/P6p/8/8/8/8/p6P/R3K2R w KQkq - 0 1"
EN_PASSANT_READY = "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"


def compact(fen):
    return SearchBoard.from_board(Board.from_fen(fen))


def fast_perft(board, depth):
    if depth == 0:
        return 1
    in_check = board.in_check()
    total = 0
    for move in board.generate_moves():
        if board.try_make(move, in_check):
            total += fast_perft(board, depth - 1)
            board.unmake()
    return total


def legal_codes(board):
    in_check = board.in_check()
    codes = set()
    for move in board.generate_moves():
        if board.try_make(move, in_check):
            board.unmake()
            codes.add(move)
    return codes


def state_of(board):
    return (
        list(board.squares), board.side, board.castling, board.en_passant, board.halfmove, list(board.kings),
        board.midgame, board.endgame, board.phase, board.key, board.pawn_key, list(board.counts),
    )


def assert_same_position(fast, reference):
    """O que a busca atualizou aos poucos tem de ser igual ao que se obtém montando do zero."""
    assert state_of(fast) == state_of(SearchBoard.from_board(reference))


@pytest.mark.ct("CT-70")
@pytest.mark.parametrize("fen, depth, nodes", REFERENCE_CASES)
def test_fast_board_matches_published_perft(fen, depth, nodes):
    assert fast_perft(compact(fen), depth) == nodes


@pytest.mark.ct("CT-70")
@pytest.mark.slow
@pytest.mark.parametrize("fen, depth, nodes", DEEP_REFERENCE_COUNTS)
def test_fast_board_matches_deep_published_perft(fen, depth, nodes):
    assert fast_perft(compact(fen), depth) == nodes


@pytest.mark.ct("CT-70")
@pytest.mark.parametrize("fen", [KIWIPETE, ENDGAME_PINS, PROMOTIONS, CASTLING_AND_PROMOTIONS, EN_PASSANT_READY])
@pytest.mark.parametrize("seed", range(3))
def test_random_games_agree_move_by_move_with_the_rules(fen, seed):
    rng = random.Random(seed)
    reference = Board.from_fen(fen)
    fast = SearchBoard.from_board(reference)
    for _ in range(60):
        legal = legal_moves(reference)
        assert {encode_move(move) for move in legal} == legal_codes(fast)
        if not legal:
            return
        move = rng.choice(legal)
        before = state_of(fast)
        fast.make(encode_move(move))
        fast.unmake()
        assert state_of(fast) == before
        fast.make(encode_move(move))
        reference.apply(move)
        assert_same_position(fast, reference)


def test_tactical_moves_are_the_captures_and_queen_promotions():
    for fen in (KIWIPETE, PROMOTIONS, CASTLING_AND_PROMOTIONS, EN_PASSANT_READY):
        reference = Board.from_fen(fen)
        fast = SearchBoard.from_board(reference)
        expected = {
            encode_move(move)
            for move in legal_moves(reference)
            if move.is_en_passant or move.promotion is PieceType.QUEEN or reference.piece_at(move.target) is not None
        }
        # Promoção com captura para peça menor fica de fora: a dama quase sempre é a melhor escolha.
        expected = {code for code in expected if not 4 <= code >> FLAG_SHIFT <= 6}
        assert legal_tactical(fast) == expected


def legal_tactical(board):
    in_check = board.in_check()
    codes = set()
    for move in board.generate_tactical_moves():
        if board.try_make(move, in_check):
            board.unmake()
            codes.add(move)
    return codes


@pytest.mark.parametrize(
    "move, flag",
    [
        (Move(sq("e2"), sq("e4"), is_double_push=True), FLAG_DOUBLE_PUSH),
        (Move(sq("e5"), sq("d6"), is_en_passant=True), FLAG_EN_PASSANT),
        (Move(sq("e1"), sq("g1"), is_castling=True), FLAG_CASTLING),
        (Move(sq("a7"), sq("a8"), promotion=PieceType.QUEEN), FLAG_PROMOTE_QUEEN),
        (Move(sq("a2"), sq("a3")), 0),
    ],
)
def test_encoded_move_keeps_squares_and_special_flag(move, flag):
    code = encode_move(move)
    assert code & 63 == move.origin.rank * 8 + move.origin.file
    assert code >> 6 & 63 == move.target.rank * 8 + move.target.file
    assert code >> FLAG_SHIFT == flag
    assert code <= MOVE_MASK


def test_en_passant_target_only_counts_when_a_pawn_can_capture():
    """Mesma regra de `position_key`: sem peão ao lado, as jogadas possíveis são as mesmas de sem alvo."""
    without_capturer = compact("4k3/8/8/8/4P3/8/8/4K3 b - e3 0 1")
    with_capturer = compact("4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1")
    assert without_capturer.en_passant == -1
    assert with_capturer.en_passant == 20


def play_quiet_moves(board, *moves):
    for origin, target in moves:
        board.make(encode_move(Move(sq(origin), sq(target))))


def test_same_position_reached_by_different_move_orders_shares_the_key():
    """É isso que faz a tabela de transposição funcionar: posição igual, nota já conhecida."""
    first = compact("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    second = compact("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    play_quiet_moves(first, ("g1", "f3"), ("g8", "f6"), ("b1", "c3"))
    play_quiet_moves(second, ("b1", "c3"), ("g8", "f6"), ("g1", "f3"))
    assert first.key == second.key


def test_side_to_move_and_castling_rights_change_the_key():
    position = "r3k2r/8/8/8/8/8/8/R3K2R {} {} - 0 1"
    assert compact(position.format("w", "KQkq")).key != compact(position.format("b", "KQkq")).key
    assert compact(position.format("w", "KQkq")).key != compact(position.format("w", "KQk")).key


def test_repetition_is_seen_through_the_game_history():
    reference = Board.from_fen("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    fast = SearchBoard.from_board(reference)
    start_key = fast.key
    for name, target in (("a1", "a2"), ("e8", "d8"), ("a2", "a1")):
        fast.make(encode_move(Move(sq(name), sq(target))))
        assert not fast.is_rule_draw()
    assert fast.key != start_key
    fast.make(encode_move(Move(sq("d8"), sq("e8"))))
    assert fast.key == start_key
    assert fast.is_rule_draw()


def test_seeded_history_counts_as_previous_positions():
    fast = compact("4k3/8/8/8/8/8/8/R3K3 w - - 4 10")
    assert not fast.is_rule_draw()
    fast.seed_history([fast.key, 111, 222, 333])
    assert fast.is_rule_draw()


def test_fifty_move_rule_is_a_draw():
    assert compact("4k3/8/8/8/8/8/8/R3K3 w - - 100 80").is_rule_draw()
    assert not compact("4k3/8/8/8/8/8/8/R3K3 w - - 99 80").is_rule_draw()


def test_material_helpers():
    assert compact("4k3/8/8/8/8/8/8/R3K3 w - - 0 1").has_no_pawns()
    assert not compact("4k3/p7/8/8/8/8/8/4K3 w - - 0 1").has_no_pawns()
    assert not compact("4k3/8/8/8/8/8/P7/4K3 w - - 0 1").has_no_pawns()


def test_defended_by_pawn_looks_at_the_side_not_to_move():
    white_to_move = compact("4k3/2p5/3p4/8/8/8/8/4K3 w - - 0 1")
    assert white_to_move.defended_by_pawn(sq_index("d6"))
    assert not white_to_move.defended_by_pawn(sq_index("e6"))


def sq_index(name):
    square = sq(name)
    return square.rank * 8 + square.file


def test_has_legal_move_detects_mate_and_stalemate():
    assert compact("4k3/8/8/8/8/8/8/R3K3 b - - 0 1").has_legal_move()
    assert not compact("R5k1/5ppp/8/8/8/8/8/4K3 b - - 0 1").has_legal_move()
    assert not compact("7k/5Q2/5K2/8/8/8/8/8 b - - 0 1").has_legal_move()


def test_promotion_is_undone_back_to_a_pawn():
    board = compact("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    origin = sq_index("a7")
    target = sq_index("a8")
    before = state_of(board)
    board.make(origin | target << 6 | FLAG_PROMOTE_QUEEN << FLAG_SHIFT)
    assert board.squares[target] == QUEEN
    assert board.counts[PAWN] == 0
    board.unmake()
    assert state_of(board) == before


def test_castling_is_refused_when_the_rook_is_gone():
    """Direito sobrando sem torre só acontece em tabuleiro montado à mão, mas a geração não pode falhar."""
    reference = Board.from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    reference.remove(sq("h1"))
    reference.remove(sq("a1"))
    board = SearchBoard.from_board(reference)
    assert not any(move >> FLAG_SHIFT == FLAG_CASTLING for move in board.generate_moves())
