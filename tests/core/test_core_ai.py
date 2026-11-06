"""CPU: jogada sempre legal, táticas básicas, erros do nível fácil, cancelamento e limite de tempo."""
import functools
import pickle
import random
import threading
import time
from dataclasses import replace

import pytest
from core_helpers import play_all, sq

from xadrez.core import (
    STARTING_FEN,
    Board,
    Color,
    Difficulty,
    GameEngine,
    Pawn,
    PieceType,
    SearchReport,
    analyze,
    choose_move,
    is_checkmate,
    legal_moves,
)
from xadrez.core import ai as ai_module
from xadrez.core.search_board import SearchBoard

MIDGAME = "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 9"
TACTICAL_MIDGAME = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"

# Limite curto para o Hardcore: estes testes conferem o comportamento, não a força.
FAST = 0.05
LEVELS_WITH_LIMIT = [
    (Difficulty.EASY, None),
    (Difficulty.MEDIUM, None),
    (Difficulty.HARD, None),
    (Difficulty.HARDCORE, FAST),
]
STRONG_LEVELS = [(Difficulty.MEDIUM, None), (Difficulty.HARD, None), (Difficulty.HARDCORE, 0.3)]

SPECIAL_POSITIONS = {
    "inicial": STARTING_FEN,
    "meio-jogo": MIDGAME,
    "kiwipete": TACTICAL_MIDGAME,
    "promocao": "8/P6k/8/8/8/8/8/K7 w - - 0 1",
    "promocao-preta": "k7/8/8/8/8/8/p6K/8 b - - 0 1",
    "promocao-com-captura": "1n5k/P7/8/8/8/8/8/K7 w - - 0 1",
    "roques": "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "roques-pretas": "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    "en-passant": "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2",
    "en-passant-cravado": "8/8/8/KPp4r/8/8/8/7k w - c6 0 2",
    "em-xeque": "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1",
    "xeque-duplo": "4k3/8/8/8/1b6/5n2/8/4K3 w - - 0 1",
    "cravada": "4k3/4r3/8/8/8/8/4B3/4K2R w K - 0 1",
    "uma-jogada": "7k/8/5K2/6Q1/8/8/8/8 b - - 0 1",
    "poucas-jogadas": "k7/8/1K6/8/8/8/8/7R b - - 0 1",
    "final-de-peoes": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "promocoes-mutuas": "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
}


@functools.lru_cache(maxsize=None)
def random_game_positions(count, seed):
    """Posições variadas de partidas aleatórias, sem as que já terminaram."""
    rng = random.Random(seed)
    positions = []
    while len(positions) < count:
        board = Board.initial()
        for _ in range(rng.randrange(4, 120)):
            moves = legal_moves(board)
            if not moves:
                break
            board.apply(rng.choice(moves))
        if legal_moves(board):
            positions.append(board.to_fen())
    return positions


def think(fen, level, limit, seed=1):
    return choose_move(Board.from_fen(fen), level, random.Random(seed), max_seconds=limit)


def play_and_check_queen(board, move):
    """Aplica o lance e diz se a dama de quem jogou ficou de graça para o adversário.

    De graça é: o adversário pode capturá-la já no próximo lance, com peça mais barata ou sem que haja
    recaptura. Quem acabou de capturar a dama inimiga está trocando damas, e isso não é entregar.
    """
    color = board.turn
    victim = board.piece_at(move.captured_square)
    traded_queens = victim is not None and victim.kind is PieceType.QUEEN
    board.apply(move)
    queen = next((square for square, piece in board.pieces(color) if piece.kind is PieceType.QUEEN), None)
    capturers = [reply.origin for reply in legal_moves(board) if reply.target == queen]
    if traded_queens or queen is None or not capturers:
        return False
    cheaper = any(board.piece_at(origin).kind is not PieceType.QUEEN for origin in capturers)
    return cheaper or not board.attackers_of(queen, color)


def ends_in_mate_in_one(board, move):
    board.apply(move)
    mated = is_checkmate(board)
    board.undo()
    return mated


def forces_mate_in_two(board, move):
    """Prova por força bruta: depois do lance, toda resposta do adversário permite mate imediato."""
    board.apply(move)
    replies = legal_moves(board)
    forced = bool(replies)
    for reply in replies:
        board.apply(reply)
        forced = forced and any(ends_in_mate_in_one(board, follow_up) for follow_up in legal_moves(board))
        board.undo()
    board.undo()
    return forced


def test_difficulty_labels_and_descriptions():
    assert [level.label for level in Difficulty] == ["Easy", "Medium", "Hard", "Hardcore"]
    assert all(level.description for level in Difficulty)
    assert Difficulty.EASY.value == "Easy"


@pytest.mark.ct("CT-70")
@pytest.mark.parametrize("level, limit", LEVELS_WITH_LIMIT, ids=lambda value: getattr(value, "label", None))
@pytest.mark.parametrize("name", SPECIAL_POSITIONS)
def test_move_is_legal_and_board_is_untouched_in_special_positions(name, level, limit):
    fen = SPECIAL_POSITIONS[name]
    board = Board.from_fen(fen)
    move = choose_move(board, level, random.Random(5), max_seconds=limit)
    assert move in legal_moves(board)
    assert board.to_fen() == fen


@pytest.mark.ct("CT-70")
@pytest.mark.parametrize("level, limit", LEVELS_WITH_LIMIT, ids=lambda value: getattr(value, "label", None))
def test_move_is_legal_across_dozens_of_random_positions(level, limit):
    for fen in random_game_positions(40, seed=11):
        board = Board.from_fen(fen)
        move = choose_move(board, level, random.Random(3), max_seconds=limit)
        assert move in legal_moves(board), fen
        assert board.to_fen() == fen


@pytest.mark.ct("CT-70")
def test_game_history_of_the_board_is_kept():
    engine = GameEngine()
    play_all(engine, "g1f3", "g8f6", "f3g1", "f6g8")
    before = engine.board.undoable_moves
    fen = engine.final_fen
    choose_move(engine.board, Difficulty.HARD, random.Random(1))
    assert engine.board.undoable_moves == before
    assert engine.final_fen == fen
    assert engine.board.halfmove_clock == 4


@pytest.mark.ct("CT-70")
@pytest.mark.parametrize("fen", ["R5k1/5ppp/8/8/8/8/8/4K3 b - - 0 1", "7k/5Q2/5K2/8/8/8/8/8 b - - 0 1"])
@pytest.mark.parametrize("level", list(Difficulty))
def test_position_without_legal_moves_raises_a_clear_error(fen, level):
    with pytest.raises(ValueError, match="jogada legal"):
        choose_move(Board.from_fen(fen), level)


@pytest.mark.ct("CT-70")
def test_single_legal_move_answers_without_searching():
    report = analyze(Board.from_fen(SPECIAL_POSITIONS["uma-jogada"]), Difficulty.HARDCORE)
    assert report.move.uci == "h8h7"
    assert report.nodes == 0
    assert report.seconds < 0.1


@pytest.mark.ct("CT-70")
@pytest.mark.parametrize("level", list(Difficulty))
def test_promotion_comes_with_the_piece_already_chosen(level):
    """As quatro promoções são jogadas diferentes: a escolhida tem de ser uma delas, com a peça definida."""
    board = Board.from_fen("8/P5k1/8/8/8/8/8/K7 w - - 0 1")
    legal = legal_moves(board)
    assert sum(move.promotion is not None for move in legal) == 4
    for seed in range(5):
        assert choose_move(board, level, random.Random(seed), max_seconds=FAST) in legal


@pytest.mark.ct("CT-70")
@pytest.mark.parametrize("level, limit", STRONG_LEVELS, ids=lambda value: getattr(value, "label", None))
def test_promotes_to_queen_when_waiting_would_lose_the_pawn(level, limit):
    board = Board.from_fen("8/P1k5/8/8/8/8/8/K7 w - - 0 1")
    for seed in range(5):
        move = choose_move(board, level, random.Random(seed), max_seconds=limit)
        assert move.uci == "a7a8q", f"semente {seed}"


@pytest.mark.ct("CT-70")
def test_hard_promotes_at_once_even_when_nothing_can_stop_the_pawn():
    """Com o rei preto longe, promover agora ou depois dá nota parecida, mas ninguém adia isso de propósito."""
    board = Board.from_fen("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    for seed in range(20):
        assert choose_move(board, Difficulty.HARD, random.Random(seed)).uci == "a7a8q", f"semente {seed}"


@pytest.mark.ct("CT-70")
def test_position_built_by_hand_without_kings_still_gets_a_legal_move():
    """O motor aceita tabuleiro montado à mão, e a busca presume um rei de cada cor: não pode quebrar."""
    board = Board()
    board.place(sq("e2"), Pawn(Color.WHITE))
    move = choose_move(board, Difficulty.HARD, random.Random(1))
    assert move in legal_moves(board)


@pytest.mark.ct("CT-70")
def test_default_rng_is_created_when_none_is_given():
    assert choose_move(Board.initial(), Difficulty.EASY) in legal_moves(Board.initial())


@pytest.mark.ct("CT-70")
def test_board_and_move_survive_pickle_so_the_search_can_run_in_another_process():
    engine = GameEngine()
    play_all(engine, "e2e4", "e7e5", "g1f3")
    copy = pickle.loads(pickle.dumps(engine.board))
    assert copy.to_fen() == engine.final_fen
    assert copy.undoable_moves == 3
    move = choose_move(copy, Difficulty.MEDIUM, random.Random(2))
    assert pickle.loads(pickle.dumps(move)) == move


MATE_IN_ONE = {
    "pastor": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
    "corredor": "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
    "corredor-pretas": "3r2k1/8/8/8/8/8/5PPP/6K1 b - - 0 1",
    "promocao": "7k/P7/6K1/8/8/8/8/8 w - - 0 1",
    "abafado": "6rk/6pp/7N/8/8/8/8/6K1 w - - 0 1",
    "dama-e-rei": "k7/8/1K6/8/8/8/7Q/8 w - - 0 1",
}


@pytest.mark.ct("CT-71")
@pytest.mark.parametrize("level, limit", STRONG_LEVELS, ids=lambda value: getattr(value, "label", None))
@pytest.mark.parametrize("name", MATE_IN_ONE)
def test_finds_mate_in_one(name, level, limit):
    board = Board.from_fen(MATE_IN_ONE[name])
    for seed in range(5):
        move = choose_move(board, level, random.Random(seed), max_seconds=limit)
        assert ends_in_mate_in_one(board, move), f"{name}: {move.uci}, semente {seed}"


@pytest.mark.ct("CT-71")
def test_noise_never_hides_mate_from_medium():
    board = Board.from_fen(MATE_IN_ONE["corredor"])
    moves = {choose_move(board, Difficulty.MEDIUM, random.Random(seed)).uci for seed in range(30)}
    assert moves == {"d1d8"}


@pytest.mark.ct("CT-71")
@pytest.mark.parametrize("name", MATE_IN_ONE)
def test_easy_erra_de_proposito_mas_nao_perde_o_mate_em_um(name):
    board = Board.from_fen(MATE_IN_ONE[name])
    for seed in range(30):
        move = choose_move(board, Difficulty.EASY, random.Random(seed))
        assert ends_in_mate_in_one(board, move), f"{name}: {move.uci}, semente {seed}"


@pytest.mark.ct("CT-71")
@pytest.mark.parametrize("level", list(Difficulty))
def test_mate_on_the_fiftieth_move_wins_instead_of_drawing(level):
    """O mate tem prioridade: o lance que completaria os 50 lances, sendo mate, ganha a partida."""
    board = Board.from_fen("6k1/5ppp/8/8/8/8/8/3R2K1 w - - 99 80")
    assert choose_move(board, level, random.Random(1), max_seconds=0.3).uci == "d1d8"


MATE_IN_TWO = {
    "escada": "7k/8/8/8/8/8/R7/1R4K1 w - - 0 1",
    "sacrificio-de-dama": "r5k1/5ppp/8/8/8/1Q6/5PPP/1R4K1 w - - 0 1",
    "sacrificio-pretas": "1r4k1/5ppp/1q6/8/8/8/5PPP/R5K1 b - - 0 1",
    "mate-de-philidor": "5r1k/6pp/7N/8/8/1Q6/8/6K1 w - - 0 1",
}
MATE_LEVELS = [(Difficulty.HARD, None), (Difficulty.HARDCORE, 0.5)]


@pytest.mark.ct("CT-72")
@pytest.mark.parametrize("level, limit", MATE_LEVELS, ids=lambda value: getattr(value, "label", None))
@pytest.mark.parametrize("name", MATE_IN_TWO)
def test_finds_mate_in_two(name, level, limit):
    board = Board.from_fen(MATE_IN_TWO[name])
    for seed in range(4):
        move = choose_move(board, level, random.Random(seed), max_seconds=limit)
        assert forces_mate_in_two(board, move), f"{name}: {move.uci}, semente {seed}"


@pytest.mark.ct("CT-72")
@pytest.mark.parametrize("level, limit", MATE_LEVELS, ids=lambda value: getattr(value, "label", None))
def test_faster_mate_is_preferred_over_a_slower_one(level, limit):
    board = Board.from_fen("6k1/5ppp/8/8/8/8/R7/1R4K1 w - - 0 1")
    for seed in range(10):
        move = choose_move(board, level, random.Random(seed), max_seconds=limit)
        assert ends_in_mate_in_one(board, move), f"{move.uci}, semente {seed}"


@pytest.mark.ct("CT-72")
def test_report_scores_a_mate_by_distance():
    short = analyze(Board.from_fen(MATE_IN_ONE["corredor"]), Difficulty.HARD, random.Random(1))
    long = analyze(Board.from_fen(MATE_IN_TWO["escada"]), Difficulty.HARD, random.Random(1))
    assert short.score > long.score > ai_module._MATE_THRESHOLD


@pytest.mark.ct("CT-72")
def test_side_being_mated_delays_it_as_long_as_possible():
    """Kf8 leva mate no lance seguinte. Kh8 obriga a torre a esperar o rei: são dois meios-lances a mais."""
    board = Board.from_fen("6k1/R7/5K2/8/8/8/8/8 b - - 0 1")
    assert choose_move(board, Difficulty.HARD, random.Random(1)).uci == "g8h8"
    report = analyze(board, Difficulty.HARDCORE, random.Random(1), max_seconds=0.5)
    assert report.move.uci == "g8h8"
    assert report.score == -ai_module._MATE + 4


QUEEN_TRAPS = {
    "atacada-por-peao": "rnbqkbnr/ppp1pppp/8/3p4/4Q3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 3",
    "peao-protegido": "rnbqkbnr/ppp2ppp/3p4/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 3",
    "atacada-por-cavalo": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/4P3/2N5/PPPP1PPP/R1B1KBNR w KQkq - 4 4",
    "peca-protegida": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P2Q/2NP1N2/PPP2PPP/R1B1K2R w KQkq - 0 7",
    "pretas-atacada": "rnb1kbnr/pppp1ppp/8/4p3/4P2q/3P1N2/PPP2PPP/RNBQKB1R b KQkq - 0 3",
    "pretas-peao-protegido": "rnb1kbnr/pppp1ppp/8/4p2q/4P3/3P4/PPP2PPP/RNBQKBNR b KQkq - 0 3",
}


@pytest.mark.ct("CT-73")
@pytest.mark.parametrize("level, limit", STRONG_LEVELS, ids=lambda value: getattr(value, "label", None))
@pytest.mark.parametrize("name", QUEEN_TRAPS)
def test_queen_is_not_given_away(name, level, limit):
    fen = QUEEN_TRAPS[name]
    for seed in range(4):
        board = Board.from_fen(fen)
        move = choose_move(board, level, random.Random(seed), max_seconds=limit)
        assert not play_and_check_queen(board, move), f"{name}: {move.uci}, semente {seed}"


def had_a_way_to_keep_the_queen(board):
    """Dama pendurada só é erro se existia outro lance que a salvava: num garfo, não há o que fazer."""
    for move in legal_moves(board):
        hangs = play_and_check_queen(board, move)
        board.undo()
        if not hangs:
            return True
    return False


@pytest.mark.ct("CT-73")
@pytest.mark.slow
@pytest.mark.parametrize("level", [Difficulty.MEDIUM, Difficulty.HARD], ids=lambda level: level.label)
def test_queen_is_not_given_away_during_real_games(level):
    """Partidas inteiras contra o Easy: a cada lance, a dama não pode ficar de graça se havia como evitar."""
    rng = random.Random(31)
    for game in range(6):
        level_is_white = game % 2 == 0
        engine = GameEngine()
        while engine.result is None and len(engine.history) < 200:
            is_level_turn = (engine.turn is Color.WHITE) == level_is_white
            move = choose_move(engine.board, level if is_level_turn else Difficulty.EASY, rng)
            if is_level_turn:
                probe = engine.board.copy()
                if play_and_check_queen(probe, move):
                    probe.undo()
                    assert not had_a_way_to_keep_the_queen(probe), f"{move.uci} em {probe.to_fen()}"
            assert engine.play(move.origin, move.target, move.promotion).ok


def test_easy_grabs_a_free_queen_so_it_is_not_a_random_mover():
    board = Board.from_fen("r1b1kbnr/pppp1ppp/2n5/4p3/4P2q/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 1 4")
    captures = [choose_move(board, Difficulty.EASY, random.Random(seed)).uci for seed in range(100)]
    assert captures.count("f3h4") >= 90


def test_easy_really_leaves_the_queen_hanging_often():
    """Medido com semente: enxergando só o próprio lance, Easy não percebe a dama atacada."""
    fen = QUEEN_TRAPS["atacada-por-peao"]
    hanging = 0
    for seed in range(200):
        board = Board.from_fen(fen)
        hanging += play_and_check_queen(board, choose_move(board, Difficulty.EASY, random.Random(seed)))
    assert hanging >= 80, f"Easy deixou a dama pendurada só {hanging} vezes em 200"


def test_medium_never_hangs_that_same_queen():
    fen = QUEEN_TRAPS["atacada-por-peao"]
    for seed in range(50):
        board = Board.from_fen(fen)
        assert not play_and_check_queen(board, choose_move(board, Difficulty.MEDIUM, random.Random(seed)))


@pytest.mark.slow
def test_easy_beats_a_random_mover_most_of_the_time():
    rng = random.Random(7)
    points = 0.0
    for game in range(10):
        easy_is_white = game % 2 == 0
        engine = GameEngine()
        while engine.result is None and len(engine.history) < 300:
            if (engine.turn is Color.WHITE) == easy_is_white:
                move = choose_move(engine.board, Difficulty.EASY, rng)
            else:
                move = rng.choice(legal_moves(engine.board))
            assert engine.play(move.origin, move.target, move.promotion).ok
        winner = engine.result.winner if engine.result else None
        points += 0.5 if winner is None else float((winner is Color.WHITE) == easy_is_white)
    assert points >= 7


@pytest.mark.parametrize("level", [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD])
def test_same_seed_gives_the_same_move(level):
    for fen in (MIDGAME, TACTICAL_MIDGAME, STARTING_FEN):
        moves = {choose_move(Board.from_fen(fen), level, random.Random(99)).uci for _ in range(3)}
        assert len(moves) == 1


@pytest.mark.parametrize(
    "level, limit, least_distinct",
    [
        (Difficulty.EASY, None, 5),
        (Difficulty.MEDIUM, None, 3),
        (Difficulty.HARD, None, 2),
        (Difficulty.HARDCORE, 0.1, 2),
    ],
    ids=lambda value: getattr(value, "label", None),
)
def test_different_seeds_vary_the_opening(level, limit, least_distinct):
    moves = {think(STARTING_FEN, level, limit, seed).uci for seed in range(12)}
    assert len(moves) >= least_distinct, moves


def test_hard_varies_all_game_long_but_hardcore_only_in_the_opening():
    """O sorteio consome a semente. Depois da abertura, o Hardcore fica sempre com o melhor lance."""
    late_game = MIDGAME.replace(" 0 9", " 0 30")
    assert len({think(late_game, Difficulty.HARD, None, seed).uci for seed in range(6)}) >= 2

    late_rng = random.Random(1)
    before = late_rng.getstate()
    choose_move(Board.from_fen(late_game), Difficulty.HARDCORE, late_rng, max_seconds=FAST)
    assert late_rng.getstate() == before

    opening_rng = random.Random(1)
    before = opening_rng.getstate()
    choose_move(Board.initial(), Difficulty.HARDCORE, opening_rng, max_seconds=FAST)
    assert opening_rng.getstate() != before


def test_cpu_knows_the_game_history_and_takes_the_draw_when_losing():
    """Atrás em material, repetir a posição salva o empate. Sem olhar a partida, a busca não veria isso."""
    engine = GameEngine(fen="6k1/6p1/8/8/8/8/rr6/4Q1K1 w - - 0 1")
    play_all(engine, "e1e8", "g8h7", "e8h5", "h7g8")
    report = analyze(engine.board, Difficulty.HARD, random.Random(1))
    assert report.move.uci == "h5e8"
    assert report.score == 0


def test_cpu_ahead_in_material_avoids_repeating_the_position():
    engine = GameEngine(fen="7k/8/8/8/8/8/R7/K7 w - - 0 1")
    play_all(engine, "a2b2", "h8g8", "b2a2", "g8h8")
    for seed in range(10):
        assert choose_move(engine.board, Difficulty.HARD, random.Random(seed)).uci != "a2b2"


def test_cpu_ahead_in_material_avoids_the_fifty_move_draw():
    board = Board.from_fen("6k1/8/8/8/8/8/P6R/K7 w - - 99 80")
    for seed in range(5):
        assert choose_move(board, Difficulty.HARD, random.Random(seed)).uci in {"a2a3", "a2a4"}


def test_report_has_the_numbers_of_the_search():
    report = analyze(Board.from_fen(MIDGAME), Difficulty.HARD, random.Random(1))
    assert isinstance(report, SearchReport)
    assert report.depth == 3
    assert report.nodes > 100
    assert report.seconds > 0


def test_hardcore_goes_deeper_than_hard(monkeypatch):
    """Com o mesmo limite de nós, e não de tempo: em máquina lenta ou com cobertura, 1 s só chegava à profundidade 3."""
    node_limit = ai_module._LEVELS[Difficulty.HARD].node_limit
    level = replace(ai_module._LEVELS[Difficulty.HARDCORE], seconds=None, node_limit=node_limit)
    monkeypatch.setitem(ai_module._LEVELS, Difficulty.HARDCORE, level)
    hard = analyze(Board.from_fen(MIDGAME), Difficulty.HARD, random.Random(1))
    hardcore = analyze(Board.from_fen(MIDGAME), Difficulty.HARDCORE, random.Random(1))
    assert hardcore.depth > hard.depth


def test_node_limit_keeps_a_level_bounded_and_deterministic():
    level = ai_module._LEVELS[Difficulty.HARD]
    assert level.node_limit is not None
    reports = [analyze(Board.from_fen(TACTICAL_MIDGAME), Difficulty.HARD, random.Random(4)) for _ in range(2)]
    assert reports[0].nodes == reports[1].nodes <= level.node_limit + ai_module._POLL_MASK + 1
    assert reports[0].move == reports[1].move


@pytest.mark.ct("CT-75")
@pytest.mark.parametrize("level", list(Difficulty))
def test_cancelled_from_the_start_returns_a_legal_move_at_once(level):
    board = Board.from_fen(MIDGAME)
    started = time.perf_counter()
    report = analyze(board, level, random.Random(1), should_stop=lambda: True)
    assert time.perf_counter() - started < 0.1
    assert report.move in legal_moves(board)
    assert report.depth == 0


@pytest.mark.ct("CT-75")
@pytest.mark.parametrize("polls_until_stop", [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233])
@pytest.mark.parametrize("level", [Difficulty.MEDIUM, Difficulty.HARD, Difficulty.HARDCORE])
def test_cancelling_at_any_moment_still_gives_a_legal_move(level, polls_until_stop):
    board = Board.from_fen(TACTICAL_MIDGAME)
    polls = []

    def should_stop():
        polls.append(1)
        return len(polls) >= polls_until_stop

    move = choose_move(board, level, random.Random(1), should_stop=should_stop)
    assert move in legal_moves(board)
    assert board.to_fen() == TACTICAL_MIDGAME


@pytest.mark.ct("CT-75")
def test_cancelling_keeps_the_best_move_found_so_far():
    """Com tempo para várias voltas, parar no meio ainda devolve a resposta tática da volta anterior."""
    board = Board.from_fen("rnb1kbnr/pppp1ppp/8/4p3/4P2q/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 1 3")
    polls = []

    def should_stop():
        polls.append(1)
        return len(polls) >= 400

    assert choose_move(board, Difficulty.HARDCORE, random.Random(1), should_stop=should_stop).uci == "f3h4"


@pytest.mark.ct("CT-75")
def test_search_in_a_thread_stops_quickly_when_cancelled():
    board = Board.from_fen(MIDGAME)
    stop = threading.Event()
    answer = []
    finished_at = []

    def work():
        answer.append(choose_move(board, Difficulty.HARDCORE, random.Random(1), should_stop=stop.is_set))
        finished_at.append(time.perf_counter())

    thread = threading.Thread(target=work)
    thread.start()
    time.sleep(0.2)
    assert thread.is_alive()
    asked_at = time.perf_counter()
    stop.set()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert finished_at[0] - asked_at < 0.1
    assert answer[0] in legal_moves(board)
    assert board.to_fen() == MIDGAME


@pytest.mark.ct("CT-75")
@pytest.mark.parametrize("limit", [0.0, 0.01, 0.05, 0.2])
@pytest.mark.parametrize("level", list(Difficulty))
def test_max_seconds_is_a_hard_ceiling(level, limit):
    for fen in (MIDGAME, TACTICAL_MIDGAME):
        board = Board.from_fen(fen)
        started = time.perf_counter()
        move = choose_move(board, level, random.Random(1), max_seconds=limit)
        assert time.perf_counter() - started < limit + 0.1
        assert move in legal_moves(board)


@pytest.mark.ct("CT-75")
def test_negative_max_seconds_answers_at_once():
    board = Board.from_fen(MIDGAME)
    started = time.perf_counter()
    assert choose_move(board, Difficulty.HARDCORE, max_seconds=-5) in legal_moves(board)
    assert time.perf_counter() - started < 0.1


@pytest.mark.ct("CT-75")
def test_hardcore_uses_its_own_budget_when_max_seconds_is_larger():
    assert ai_module._time_budget(ai_module._LEVELS[Difficulty.HARDCORE], 100.0) == 4.0
    assert ai_module._time_budget(ai_module._LEVELS[Difficulty.HARDCORE], 1.5) == 1.5
    assert ai_module._time_budget(ai_module._LEVELS[Difficulty.HARDCORE], None) == 4.0
    assert ai_module._time_budget(ai_module._LEVELS[Difficulty.HARD], None) == float("inf")


@pytest.mark.ct("CT-75")
def test_should_stop_is_consulted_often():
    polls = []

    def should_stop():
        polls.append(time.perf_counter())
        return False

    board = Board.from_fen(MIDGAME)
    report = analyze(board, Difficulty.HARDCORE, random.Random(1), should_stop=should_stop, max_seconds=0.3)
    assert len(polls) >= report.nodes // (ai_module._POLL_MASK + 1)
    gaps = [later - earlier for earlier, later in zip(polls, polls[1:])]
    assert sorted(gaps)[len(gaps) // 2] < 0.02


def test_search_stops_going_deeper_at_the_ply_limit():
    """Sequências de xeque estendidas não podem crescer sem fim: no limite, a nota é a da avaliação."""
    level = ai_module._LEVELS[Difficulty.HARDCORE]
    board = SearchBoard.from_board(Board.from_fen(MIDGAME))
    search = ai_module._Search(board, level, 0, None, float("inf"))
    score = search._negamax(5, -ai_module._INFINITY, ai_module._INFINITY, ai_module._MAX_PLY)
    assert score == search._quiesce(-ai_module._INFINITY, ai_module._INFINITY, ai_module._MAX_PLY, False)


@pytest.mark.slow
@pytest.mark.parametrize("white, black", [(Difficulty.EASY, Difficulty.MEDIUM), (Difficulty.MEDIUM, Difficulty.EASY)])
def test_full_game_between_levels_ends_without_errors(white, black):
    engine = GameEngine(white.label, black.label)
    rng = random.Random(21)
    while engine.result is None and len(engine.history) < 300:
        level = white if engine.turn is Color.WHITE else black
        move = choose_move(engine.board, level, rng)
        assert engine.play(move.origin, move.target, move.promotion).ok
    assert engine.result is not None
