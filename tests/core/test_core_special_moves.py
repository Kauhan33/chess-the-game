"""Jogadas especiais: roque, en passant e promoção."""
import pytest
from core_helpers import play_all, sq, target_names

from xadrez.core import Board, Color, GameEngine, MoveError, PieceType, Queen, Square, legal_moves, legal_moves_from

ALL_CASTLING = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"


def assert_castling_refused(fen, target, error):
    engine = GameEngine(fen=fen)
    outcome = engine.play(sq("e1"), sq(target))
    assert not outcome.ok
    assert outcome.error is error
    assert engine.board.to_fen() == fen


@pytest.mark.ct("CT-09")
@pytest.mark.parametrize(
    "fen, king_origin, king_target, rook_origin, rook_target, san",
    [
        (ALL_CASTLING, "e1", "g1", "h1", "f1", "O-O"),
        (ALL_CASTLING, "e1", "c1", "a1", "d1", "O-O-O"),
        ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1", "e8", "g8", "h8", "f8", "O-O"),
        ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1", "e8", "c8", "a8", "d8", "O-O-O"),
    ],
    ids=["white-kingside", "white-queenside", "black-kingside", "black-queenside"],
)
def test_valid_castling_moves_king_and_rook(fen, king_origin, king_target, rook_origin, rook_target, san):
    engine = GameEngine(fen=fen)
    king = engine.board.piece_at(sq(king_origin))
    rook = engine.board.piece_at(sq(rook_origin))
    outcome = engine.play(sq(king_origin), sq(king_target))
    assert outcome.ok
    assert outcome.move.is_castling
    assert outcome.rook_path == (sq(rook_origin), sq(rook_target))
    assert outcome.san == san
    assert engine.board.piece_at(sq(king_target)) is king
    assert engine.board.piece_at(sq(rook_target)) is rook
    assert engine.board.piece_at(sq(king_origin)) is None
    assert engine.board.piece_at(sq(rook_origin)) is None
    assert engine.board.king_square(king.color) == sq(king_target)


@pytest.mark.ct("CT-09")
def test_castling_removes_only_the_rights_of_that_color():
    engine = GameEngine(fen=ALL_CASTLING)
    play_all(engine, "e1g1")
    assert engine.board.castling_rights == frozenset("kq")


@pytest.mark.ct("CT-09")
def test_castling_undo_restores_king_rook_and_rights():
    board = Board.from_fen(ALL_CASTLING)
    move = next(move for move in legal_moves(board) if move.is_castling)
    board.apply(move)
    board.undo()
    assert board.to_fen() == ALL_CASTLING


@pytest.mark.ct("CT-09")
def test_castling_is_forbidden_after_king_moved_and_returned():
    engine = GameEngine(fen=ALL_CASTLING)
    play_all(engine, "e1e2", "a8a7", "e2e1", "a7a8")
    assert engine.board.castling_rights == frozenset("k")
    assert engine.play(sq("e1"), sq("g1")).error is MoveError.ILLEGAL_MOVE
    assert engine.play(sq("e1"), sq("c1")).error is MoveError.ILLEGAL_MOVE


@pytest.mark.ct("CT-09")
def test_castling_is_forbidden_with_the_rook_that_moved_and_returned():
    engine = GameEngine(fen=ALL_CASTLING)
    play_all(engine, "h1h2", "a8a7", "h2h1", "a7a8")
    assert engine.board.castling_rights == frozenset("Qk")
    assert engine.play(sq("e1"), sq("g1")).error is MoveError.ILLEGAL_MOVE
    assert engine.play(sq("e1"), sq("c1")).ok


@pytest.mark.ct("CT-09")
@pytest.mark.parametrize("target", ["g1", "c1"])
def test_castling_is_forbidden_with_piece_between(target):
    assert_castling_refused("4k3/8/8/8/8/8/8/RN2K1NR w KQ - 0 1", target, MoveError.ILLEGAL_MOVE)


@pytest.mark.ct("CT-09")
def test_castling_is_forbidden_with_any_piece_on_queenside_path():
    for fen in ("4k3/8/8/8/8/8/8/R1B1K3 w Q - 0 1", "4k3/8/8/8/8/8/8/R2QK3 w Q - 0 1"):
        assert_castling_refused(fen, "c1", MoveError.ILLEGAL_MOVE)


@pytest.mark.ct("CT-09")
@pytest.mark.parametrize("target", ["g1", "c1"])
def test_castling_is_forbidden_while_in_check(target):
    assert_castling_refused("4k3/8/8/8/8/8/4r3/R3K2R w KQ - 0 1", target, MoveError.ILLEGAL_MOVE)


@pytest.mark.ct("CT-09")
@pytest.mark.parametrize(
    "fen, target",
    [
        ("4kr2/8/8/8/8/8/8/R3K2R w KQ - 0 1", "g1"),
        ("3rk3/8/8/8/8/8/8/R3K2R w KQ - 0 1", "c1"),
        ("4k3/8/8/8/8/8/6p1/R3K2R w KQ - 0 1", "g1"),
    ],
    ids=["rook-on-f1", "rook-on-d1", "pawn-attacks-f1"],
)
def test_castling_is_forbidden_passing_through_attacked_square(fen, target):
    assert_castling_refused(fen, target, MoveError.ILLEGAL_MOVE)


@pytest.mark.ct("CT-09")
@pytest.mark.parametrize(
    "fen, target",
    [
        ("4k1r1/8/8/8/8/8/8/R3K2R w KQ - 0 1", "g1"),
        ("2r1k3/8/8/8/8/8/8/R3K2R w KQ - 0 1", "c1"),
    ],
    ids=["arrives-g1", "arrives-c1"],
)
def test_castling_is_forbidden_arriving_on_attacked_square(fen, target):
    assert_castling_refused(fen, target, MoveError.LEAVES_KING_IN_CHECK)


@pytest.mark.ct("CT-09")
def test_queenside_castling_allows_attack_on_b1_because_king_does_not_cross_it():
    engine = GameEngine(fen="1r2k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert engine.board.is_attacked(sq("b1"), Color.BLACK)
    assert engine.play(sq("e1"), sq("c1")).ok


@pytest.mark.ct("CT-09")
def test_rook_itself_may_be_attacked_when_castling():
    engine = GameEngine(fen="r3k2r/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert engine.board.is_attacked(sq("h1"), Color.BLACK)
    assert engine.play(sq("e1"), sq("g1")).ok


@pytest.mark.ct("CT-09")
def test_capturing_rook_on_home_square_removes_the_right():
    engine = GameEngine(fen="r3k2r/8/8/8/8/8/6b1/R3K2R b KQkq - 0 1")
    play_all(engine, "g2h1")
    assert engine.board.castling_rights == frozenset("Qkq")


@pytest.mark.ct("CT-09")
def test_rook_capturing_rook_removes_the_rights_of_both_sides():
    engine = GameEngine(fen=ALL_CASTLING)
    play_all(engine, "h1h8")
    assert engine.board.to_fen() == "r3k2R/8/8/8/8/8/8/R3K3 b Qq - 0 1"


@pytest.mark.ct("CT-09")
def test_new_rook_on_home_square_does_not_recover_the_right():
    engine = GameEngine(fen="4k3/8/8/8/8/8/6b1/R3K2R b K - 0 1")
    play_all(engine, "g2h1", "a1a2", "h1c6", "a2h2", "e8d7", "h2h1", "d7d8")
    assert engine.board.castling_rights == frozenset()
    assert engine.play(sq("e1"), sq("g1")).error is MoveError.ILLEGAL_MOVE


def test_castling_generator_requires_the_rook_even_with_the_right_set():
    board = Board.from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    board.remove(sq("h1"))
    assert "g1" not in target_names(legal_moves_from(board, sq("e1")))
    assert "c1" in target_names(legal_moves_from(board, sq("e1")))


def test_castling_generator_requires_the_king_on_its_home_square():
    board = Board.from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    king = board.remove(sq("e1"))
    board.place(sq("d1"), king)
    assert not any(move.is_castling for move in legal_moves_from(board, sq("d1")))


@pytest.mark.ct("CT-10")
def test_en_passant_captures_the_pawn_beside_the_origin():
    engine = GameEngine()
    play_all(engine, "e2e4", "a7a6", "e4e5", "d7d5")
    assert engine.board.en_passant_target == sq("d6")
    victim = engine.board.piece_at(sq("d5"))
    outcome = engine.play(sq("e5"), sq("d6"))
    assert outcome.ok
    assert outcome.move.is_en_passant
    assert outcome.captured is victim
    assert outcome.captured_square == sq("d5")
    assert outcome.captured_square != outcome.move.target
    assert outcome.san == "exd6"
    assert engine.board.piece_at(sq("d5")) is None
    assert engine.board.piece_at(sq("d6")).kind is PieceType.PAWN
    assert engine.players[Color.WHITE].captured == [PieceType.PAWN]
    assert engine.board.halfmove_clock == 0


@pytest.mark.ct("CT-10")
def test_black_can_capture_en_passant_too():
    engine = GameEngine()
    play_all(engine, "a2a3", "d7d5", "a3a4", "d5d4", "e2e4")
    outcome = engine.play(sq("d4"), sq("e3"))
    assert outcome.ok
    assert outcome.captured_square == sq("e4")
    assert engine.board.piece_at(sq("e4")) is None


@pytest.mark.ct("CT-10")
def test_en_passant_window_closes_after_one_move():
    engine = GameEngine()
    play_all(engine, "e2e4", "a7a6", "e4e5", "d7d5", "h2h3", "h7h6")
    assert engine.board.en_passant_target is None
    assert engine.play(sq("e5"), sq("d6")).error is MoveError.ILLEGAL_MOVE


@pytest.mark.ct("CT-10")
def test_en_passant_requires_a_double_step():
    engine = GameEngine()
    play_all(engine, "e2e4", "d7d6", "e4e5", "h7h6", "h2h3", "d6d5")
    assert engine.board.en_passant_target is None
    assert engine.play(sq("e5"), sq("d6")).error is MoveError.ILLEGAL_MOVE


@pytest.mark.ct("CT-10")
def test_en_passant_that_exposes_king_along_the_rank_is_refused():
    """As duas peças saem da fileira ao mesmo tempo: nenhuma cravada comum detecta esse caso."""
    fen = "8/8/8/K2pP2r/8/8/8/4k3 w - d6 0 2"
    engine = GameEngine(fen=fen)
    outcome = engine.play(sq("e5"), sq("d6"))
    assert outcome.error is MoveError.LEAVES_KING_IN_CHECK
    assert engine.board.to_fen() == fen
    assert "d6" not in target_names(engine.legal_moves_from(sq("e5")))


@pytest.mark.ct("CT-10")
def test_en_passant_can_remove_the_pawn_that_gives_check():
    engine = GameEngine(fen="8/8/8/2k5/3Pp3/8/8/4K3 b - d3 0 1")
    assert engine.in_check
    assert engine.play(sq("e4"), sq("d3")).ok
    assert not engine.in_check


@pytest.mark.ct("CT-10")
def test_en_passant_target_belongs_only_to_the_side_to_move():
    """O peão em c7 alcança d6 pela geometria, mas o alvo foi deixado pela própria cor dele."""
    board = Board.from_fen("4k3/2p5/8/3p4/8/8/8/4K3 w - d6 0 2")
    assert target_names(legal_moves_from(board, sq("c7"))) == {"c6", "c5"}


@pytest.mark.ct("CT-11")
def test_promotion_without_choice_is_refused_and_changes_nothing():
    fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    engine = GameEngine(fen=fen)
    assert engine.is_promotion_move(sq("a7"), sq("a8"))
    outcome = engine.play(sq("a7"), sq("a8"))
    assert outcome.error is MoveError.PROMOTION_REQUIRED
    assert engine.board.to_fen() == fen


@pytest.mark.ct("CT-11")
@pytest.mark.parametrize("kind", [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT])
def test_promotion_replaces_pawn_with_chosen_piece(kind):
    engine = GameEngine(fen="4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    pawn = engine.board.piece_at(sq("a7"))
    outcome = engine.play(sq("a7"), sq("a8"), kind)
    assert outcome.ok
    assert outcome.promoted_to is kind
    assert outcome.piece is pawn
    assert engine.board.piece_at(sq("a8")).kind is kind
    assert engine.board.piece_at(sq("a8")).color is Color.WHITE
    assert engine.board.piece_at(sq("a7")) is None


@pytest.mark.ct("CT-11")
@pytest.mark.parametrize("invalid", [PieceType.KING, PieceType.PAWN, "queen", 9])
def test_promotion_to_invalid_piece_is_refused(invalid):
    fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    engine = GameEngine(fen=fen)
    outcome = engine.play(sq("a7"), sq("a8"), invalid)
    assert outcome.error is MoveError.ILLEGAL_MOVE
    assert engine.board.to_fen() == fen


@pytest.mark.ct("CT-11")
def test_promotion_choice_on_a_normal_move_is_refused():
    engine = GameEngine()
    assert engine.play(sq("e2"), sq("e4"), PieceType.QUEEN).error is MoveError.ILLEGAL_MOVE
    assert engine.board.piece_at(sq("e2")) is not None


@pytest.mark.ct("CT-11")
def test_promotion_by_capture_counts_the_captured_piece():
    engine = GameEngine(fen="1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    outcome = engine.play(sq("a7"), sq("b8"), PieceType.QUEEN)
    assert outcome.ok
    assert outcome.captured.kind is PieceType.ROOK
    assert engine.players[Color.WHITE].material_score == PieceType.ROOK.points
    assert isinstance(engine.board.piece_at(sq("b8")), Queen)


@pytest.mark.ct("CT-11")
def test_black_promotes_on_first_rank():
    engine = GameEngine(fen="4k3/8/8/8/8/8/p7/4K3 b - - 0 1")
    assert engine.play(sq("a2"), sq("a1"), PieceType.ROOK).ok
    assert engine.board.piece_at(Square(0, 0)).color is Color.BLACK


@pytest.mark.ct("CT-11")
def test_is_promotion_move_is_false_for_other_moves():
    engine = GameEngine(fen="4k3/P7/8/8/8/8/4P3/4K3 w - - 0 1")
    assert not engine.is_promotion_move(sq("e2"), sq("e4"))
    assert not engine.is_promotion_move(sq("a7"), sq("b8"))
    assert not engine.is_promotion_move((9, 9), sq("a8"))
    assert not engine.is_promotion_move(sq("a7"), None)


@pytest.mark.ct("CT-11")
@pytest.mark.parametrize("choice", [None, PieceType.QUEEN])
def test_pinned_pawn_reports_the_pin_before_asking_for_the_promotion(choice):
    """A interface só deve abrir o diálogo de promoção se a jogada puder acontecer."""
    engine = GameEngine(fen="8/K3P2r/8/2k5/8/8/8/8 w - - 0 1")
    assert not engine.is_promotion_move(sq("e7"), sq("e8"))
    assert engine.play(sq("e7"), sq("e8"), choice).error is MoveError.LEAVES_KING_IN_CHECK
