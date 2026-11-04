"""Empates: afogamento, material insuficiente, regra dos 50 lances e tripla repetição."""
import pytest
from core_helpers import play_all, sq

from xadrez.core import (
    STARTING_FEN,
    Board,
    Color,
    EndReason,
    GameEngine,
    GameState,
    MoveError,
    has_insufficient_material,
    is_checkmate,
    is_stalemate,
    position_key,
)


@pytest.mark.ct("CT-14")
def test_stalemate_ends_the_game_as_a_draw():
    engine = GameEngine(fen="7k/8/6K1/8/8/8/8/5Q2 w - - 0 1")
    outcome = engine.play(sq("f1"), sq("f7"))
    assert outcome.ok
    assert not outcome.gives_check
    assert outcome.result.winner is None
    assert outcome.result.reason is EndReason.STALEMATE
    assert engine.state is GameState.FINISHED
    assert is_stalemate(engine.board)
    assert not is_checkmate(engine.board)
    assert engine.history == ["Qf7"]


@pytest.mark.ct("CT-14")
def test_shortest_known_stalemate_game_end_to_end():
    engine = GameEngine()
    outcome = play_all(
        engine,
        *("e2e3", "a7a5", "d1h5", "a8a6", "h5a5", "h7h5", "h2h4", "a6h6", "a5c7", "f7f6"),
        *("c7d7", "e8f7", "d7b7", "d8d3", "b7b8", "d3h7", "b8c8", "f7g6", "c8e6"),
    )
    assert outcome.result.reason is EndReason.STALEMATE
    assert outcome.result.is_draw
    assert engine.history[-1] == "Qe6"
    assert engine.history[10] == "Qxd7+"


@pytest.mark.ct("CT-14")
def test_stalemate_requires_no_check():
    assert not is_stalemate(Board.from_fen("7k/8/6K1/8/8/8/8/5Q2 b - - 0 1"))
    assert not is_stalemate(Board.initial())
    assert is_stalemate(Board.from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"))


@pytest.mark.ct("CT-14")
def test_game_loaded_on_a_stalemate_is_already_finished():
    engine = GameEngine(fen="7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert engine.state is GameState.FINISHED
    assert engine.result.reason is EndReason.STALEMATE


@pytest.mark.ct("CT-15")
@pytest.mark.parametrize(
    "fen, expected",
    [
        ("4k3/8/8/8/8/8/8/4K3 w - - 0 1", True),
        ("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", True),
        ("2b1k3/8/8/8/8/8/8/4K3 w - - 0 1", True),
        ("4k3/8/8/8/8/8/8/1N2K3 w - - 0 1", True),
        ("1n2k3/8/8/8/8/8/8/4K3 w - - 0 1", True),
        ("5b1k/8/8/8/8/8/8/K1B5 w - - 0 1", True),
        ("2b4k/8/8/8/8/8/8/K1B5 w - - 0 1", False),
        ("1n5k/8/8/8/8/8/8/K1B5 w - - 0 1", False),
        ("1n5k/8/8/8/8/8/8/KN6 w - - 0 1", False),
        ("7k/8/8/8/8/8/8/KNN5 w - - 0 1", False),
        ("7k/8/8/8/8/8/8/KBB5 w - - 0 1", False),
        ("6k1/8/8/8/8/8/1B6/K1B5 w - - 0 1", True),
        ("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", False),
        ("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", False),
        ("4k3/8/8/8/8/8/8/3QK3 w - - 0 1", False),
        (STARTING_FEN, False),
    ],
    ids=[
        "k-k",
        "kb-k",
        "k-kb",
        "kn-k",
        "k-kn",
        "kb-kb-same-color",
        "kb-kb-opposite-color",
        "kb-kn",
        "kn-kn",
        "knn-k",
        "kbb-k-opposite-colors",
        "kbb-k-same-color",
        "pawn",
        "rook",
        "queen",
        "start",
    ],
)
def test_insufficient_material_cases(fen, expected):
    assert has_insufficient_material(Board.from_fen(fen)) is expected


@pytest.mark.ct("CT-15")
def test_capture_leaving_only_kings_ends_the_game():
    engine = GameEngine(fen="4k3/8/8/8/8/8/4r3/4K3 w - - 0 1")
    outcome = engine.play(sq("e1"), sq("e2"))
    assert outcome.result.reason is EndReason.INSUFFICIENT_MATERIAL
    assert outcome.result.is_draw


@pytest.mark.ct("CT-15")
def test_fifty_move_rule_draws_automatically_at_one_hundred_halfmoves():
    engine = GameEngine(fen="7k/8/6K1/8/8/8/8/5Q2 w - - 99 80")
    outcome = engine.play(sq("f1"), sq("e1"))
    assert engine.board.halfmove_clock == 100
    assert outcome.result.reason is EndReason.FIFTY_MOVES
    assert outcome.result.is_draw


@pytest.mark.ct("CT-15")
def test_fifty_move_rule_does_not_fire_before_one_hundred_halfmoves():
    engine = GameEngine(fen="7k/8/6K1/8/8/8/8/5Q2 w - - 98 80")
    outcome = engine.play(sq("f1"), sq("e1"))
    assert outcome.result is None
    assert engine.state is GameState.IN_PROGRESS


@pytest.mark.ct("CT-15")
def test_checkmate_takes_precedence_over_fifty_moves():
    engine = GameEngine(fen="7k/8/6K1/8/8/8/8/5Q2 w - - 99 80")
    outcome = engine.play(sq("f1"), sq("f8"))
    assert engine.board.halfmove_clock == 100
    assert outcome.result.reason is EndReason.CHECKMATE
    assert outcome.result.winner is Color.WHITE
    assert engine.players[Color.WHITE].match_points == 1


@pytest.mark.ct("CT-15")
def test_pawn_move_or_capture_on_the_last_halfmove_resets_the_count():
    pawn_move = GameEngine(fen="4k3/8/8/8/8/8/4P3/4K3 w - - 99 80")
    assert pawn_move.play(sq("e2"), sq("e3")).result is None
    capture = GameEngine(fen="4k3/8/4p3/3p4/8/2N5/8/4K3 w - - 99 80")
    assert capture.play(sq("c3"), sq("d5")).result is None
    assert capture.board.halfmove_clock == 0


@pytest.mark.ct("CT-15")
def test_threefold_repetition_draws_on_the_third_occurrence():
    engine = GameEngine()
    shuffle = ("g1f3", "g8f6", "f3g1", "f6g8")
    play_all(engine, *shuffle)
    assert engine.state is GameState.IN_PROGRESS
    outcome = play_all(engine, *shuffle)
    assert outcome.result.reason is EndReason.THREEFOLD_REPETITION
    assert outcome.result.is_draw
    assert engine.play(sq("e2"), sq("e4")).error is MoveError.GAME_NOT_ACTIVE


@pytest.mark.ct("CT-15")
def test_repetition_does_not_need_to_be_consecutive():
    engine = GameEngine()
    play_all(engine, "g1f3", "g8f6", "f3g1", "f6g8")
    play_all(engine, "b1c3", "b8c6", "c3b1")
    assert engine.state is GameState.IN_PROGRESS
    outcome = play_all(engine, "c6b8")
    assert outcome.result.reason is EndReason.THREEFOLD_REPETITION


@pytest.mark.ct("CT-15")
def test_repetition_distinguishes_who_is_to_move():
    white_to_move = Board.from_fen("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    black_to_move = Board.from_fen("4k3/8/8/8/8/8/8/R3K3 b - - 0 1")
    assert position_key(white_to_move) != position_key(black_to_move)


@pytest.mark.ct("CT-15")
def test_repetition_distinguishes_castling_rights():
    """As peças voltam às casas da posição inicial, mas sem o direito de roque ela não se repete.

    Ao fim do segundo ciclo a disposição apareceu três vezes, e só duas contam. Quem chega à terceira
    ocorrência primeiro é a posição logo depois de h1-h2, que já nasceu sem o direito.
    """
    engine = GameEngine(fen="4k3/8/8/8/8/8/8/4K2R w K - 0 1")
    play_all(engine, "h1h2", "e8e7", "h2h1", "e7e8")
    play_all(engine, "h1h2", "e8e7", "h2h1", "e7e8")
    assert engine.state is GameState.IN_PROGRESS
    outcome = play_all(engine, "h1h2")
    assert outcome.result.reason is EndReason.THREEFOLD_REPETITION


@pytest.mark.ct("CT-15")
def test_en_passant_target_without_legal_capture_does_not_change_the_position():
    """Depois de e2-e4 o FEN marca e3, mas ninguém pode capturar: a posição é igual às repetições."""
    engine = GameEngine()
    play_all(engine, "e2e4")
    assert engine.board.en_passant_target == sq("e3")
    play_all(engine, "g8f6", "g1f3", "f6g8", "f3g1")
    play_all(engine, "g8f6", "g1f3", "f6g8")
    assert engine.state is GameState.IN_PROGRESS
    outcome = play_all(engine, "f3g1")
    assert outcome.result.reason is EndReason.THREEFOLD_REPETITION


@pytest.mark.ct("CT-15")
def test_legal_en_passant_makes_the_position_different():
    """Aqui o peão de d4 pode capturar: a posição logo após e2-e4 não conta como repetição."""
    engine = GameEngine(fen="4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1")
    play_all(engine, "e2e4", "e8d8", "e1d1", "d8e8", "d1e1")
    play_all(engine, "e8d8", "e1d1", "d8e8", "d1e1")
    assert engine.state is GameState.IN_PROGRESS
    outcome = play_all(engine, "e8d8")
    assert outcome.result.reason is EndReason.THREEFOLD_REPETITION


@pytest.mark.ct("CT-15")
def test_en_passant_that_would_expose_the_king_does_not_change_the_position():
    pinned = Board.from_fen("8/8/8/K2pP2r/8/8/8/4k3 w - d6 0 2")
    assert position_key(pinned).endswith(" -")
    free = Board.from_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
    assert position_key(free).endswith(" d6")


@pytest.mark.ct("CT-15")
def test_position_key_ignores_the_move_counters():
    assert position_key(Board.from_fen("4k3/8/8/8/8/8/4P3/4K3 w - - 3 9")) == position_key(
        Board.from_fen("4k3/8/8/8/8/8/4P3/4K3 w - - 7 50")
    )


@pytest.mark.ct("CT-15")
def test_agreed_draw_ends_the_game():
    engine = GameEngine()
    result = engine.agree_draw()
    assert result.is_draw
    assert result.reason is EndReason.AGREEMENT
    assert engine.state is GameState.FINISHED


def test_resignation_defaults_to_the_side_to_move():
    engine = GameEngine()
    play_all(engine, "e2e4")
    result = engine.resign()
    assert result.winner is Color.WHITE
    assert result.reason is EndReason.RESIGNATION


def test_resignation_of_a_named_color():
    engine = GameEngine()
    result = engine.resign(Color.WHITE)
    assert result.winner is Color.BLACK
    assert engine.result == result


def test_resignation_is_accepted_while_paused():
    engine = GameEngine()
    engine.pause()
    assert engine.resign().reason is EndReason.RESIGNATION
    assert engine.state is GameState.FINISHED
