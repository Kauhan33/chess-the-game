"""Ataque às regras (`xadrez.core`) com um gerador de lances independente do motor.

CT-50: partidas aleatórias com semente, conferindo cada posição contra um gerador e um detector de ataque escritos à parte.
CT-51: bordas de promoção, en passant e roque que os testes do motor não combinam entre si.
CT-52: precedência entre os fins de jogo no mesmo lance: mate, 50 lances, afogamento e repetição.
CT-53: tripla repetição com direito de roque perdido e en passant que muda a posição.
CT-54: material insuficiente surgindo por captura e por promoção subpotente.
CT-55: relógio, desistência e placar da série: tempo contra rei só, pausa, pontos e revanche.
CT-56: entradas absurdas no motor e FEN maliciosos nunca derrubam nem alteram a partida.
"""
from __future__ import annotations

import math
import random
from collections import Counter

import pytest

from xadrez.core import (
    Board,
    Color,
    EndReason,
    GameEngine,
    GameState,
    MoveError,
    PieceType,
    Square,
    TimeControl,
    legal_moves,
    move_to_san,
)

FILES = "abcdefgh"
ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
KNIGHT_JUMPS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))


def sq(name: str) -> Square:
    return Square.from_name(name)


# Modelo independente: uma posição é um dicionário {(file, rank): letra FEN}. Nada vem do motor além do texto FEN.


def parse_fen(fen: str) -> dict:
    placement, turn, castling, ep, half, full = fen.split()
    pieces = {}
    for row_index, row in enumerate(placement.split("/")):
        rank, file = 7 - row_index, 0
        for char in row:
            if char.isdigit():
                file += int(char)
            else:
                pieces[(file, rank)] = char
                file += 1
    target = None if ep == "-" else (FILES.index(ep[0]), int(ep[1]) - 1)
    return {"pieces": pieces, "white": turn == "w", "rights": set(castling) - {"-"}, "ep": target,
            "half": int(half), "full": int(full)}


def is_white(letter: str) -> bool:
    return letter.isupper()


def attacked_by(pieces: dict, square: tuple, by_white: bool) -> bool:
    """Caminhada em raios a partir da casa: não usa `Board.is_attacked` nem as tabelas de `pieces.py`."""
    file, rank = square
    for dx, dy in ROOK_DIRS + BISHOP_DIRS:
        step = 1
        while True:
            at = (file + dx * step, rank + dy * step)
            if not (0 <= at[0] < 8 and 0 <= at[1] < 8):
                break
            found = pieces.get(at)
            if found is not None:
                if is_white(found) == by_white:
                    kind = found.upper()
                    if kind == "Q" or (kind == "R" and (dx == 0 or dy == 0)) or (kind == "B" and dx != 0 and dy != 0):
                        return True
                    if kind == "K" and step == 1:
                        return True
                break
            step += 1
    for dx, dy in KNIGHT_JUMPS:
        found = pieces.get((file + dx, rank + dy))
        if found is not None and found.upper() == "N" and is_white(found) == by_white:
            return True
    # Peão branco ataca para cima, então o atacante está uma fileira abaixo da casa.
    pawn_rank = rank - 1 if by_white else rank + 1
    pawn = "P" if by_white else "p"
    return pieces.get((file - 1, pawn_rank)) == pawn or pieces.get((file + 1, pawn_rank)) == pawn


def find_king(pieces: dict, white: bool) -> tuple:
    letter = "K" if white else "k"
    kings = [at for at, found in pieces.items() if found == letter]
    assert len(kings) == 1, f"rei {letter}: {kings}"
    return kings[0]


def pseudo_moves(state: dict) -> list:
    """Lances como (origem, destino, promoção, casa capturada ou None, jogada especial)."""
    pieces, white = state["pieces"], state["white"]
    moves = []
    for at, letter in pieces.items():
        if is_white(letter) != white:
            continue
        kind = letter.upper()
        if kind == "P":
            moves += _pawn_moves(state, at, white)
        elif kind == "N":
            moves += _step_moves(pieces, at, white, KNIGHT_JUMPS)
        elif kind == "K":
            moves += _step_moves(pieces, at, white, ROOK_DIRS + BISHOP_DIRS)
            moves += _castling_moves(state, at, white)
        else:
            dirs = {"R": ROOK_DIRS, "B": BISHOP_DIRS, "Q": ROOK_DIRS + BISHOP_DIRS}[kind]
            moves += _slide_moves(pieces, at, white, dirs)
    return moves


def _step_moves(pieces, at, white, offsets):
    moves = []
    for dx, dy in offsets:
        to = (at[0] + dx, at[1] + dy)
        if 0 <= to[0] < 8 and 0 <= to[1] < 8 and (to not in pieces or is_white(pieces[to]) != white):
            moves.append((at, to, None, to if to in pieces else None, None))
    return moves


def _slide_moves(pieces, at, white, dirs):
    moves = []
    for dx, dy in dirs:
        step = 1
        while True:
            to = (at[0] + dx * step, at[1] + dy * step)
            if not (0 <= to[0] < 8 and 0 <= to[1] < 8):
                break
            if to in pieces:
                if is_white(pieces[to]) != white:
                    moves.append((at, to, None, to, None))
                break
            moves.append((at, to, None, None, None))
            step += 1
    return moves


def _pawn_moves(state, at, white):
    pieces = state["pieces"]
    forward = 1 if white else -1
    last_rank = 7 if white else 0
    start_rank = 1 if white else 6
    moves = []

    def add(to, captured, special=None):
        if to[1] == last_rank:
            for kind in "QRBN":
                moves.append((at, to, kind, captured, special))
        else:
            moves.append((at, to, None, captured, special))

    one = (at[0], at[1] + forward)
    if one not in pieces:
        add(one, None)
        two = (at[0], at[1] + 2 * forward)
        if at[1] == start_rank and two not in pieces:
            moves.append((at, two, None, None, "double"))
    for dx in (-1, 1):
        to = (at[0] + dx, at[1] + forward)
        if not 0 <= to[0] < 8:
            continue
        if to in pieces and is_white(pieces[to]) != white:
            add(to, to)
        elif to == state["ep"] and to not in pieces:
            moves.append((at, to, None, (to[0], at[1]), "ep"))
    return moves


def _castling_moves(state, at, white):
    pieces, rights = state["pieces"], state["rights"]
    rank = 0 if white else 7
    if at != (4, rank) or attacked_by(pieces, at, not white):
        return []
    moves = []
    rook = "R" if white else "r"
    if ("K" if white else "k") in rights and pieces.get((7, rank)) == rook:
        if (5, rank) not in pieces and (6, rank) not in pieces and not attacked_by(pieces, (5, rank), not white):
            moves.append((at, (6, rank), None, None, "castle"))
    if ("Q" if white else "q") in rights and pieces.get((0, rank)) == rook:
        if all((file, rank) not in pieces for file in (1, 2, 3)) and not attacked_by(pieces, (3, rank), not white):
            moves.append((at, (2, rank), None, None, "castle"))
    return moves


def apply_model(state: dict, move: tuple) -> dict:
    origin, target, promotion, captured, special = move
    pieces = dict(state["pieces"])
    mover = pieces.pop(origin)
    if captured is not None:
        pieces.pop(captured)
    if promotion is not None:
        mover = promotion if state["white"] else promotion.lower()
    pieces[target] = mover
    if special == "castle":
        rank = origin[1]
        rook_from, rook_to = ((7, rank), (5, rank)) if target[0] == 6 else ((0, rank), (3, rank))
        pieces[rook_to] = pieces.pop(rook_from)
    return {"pieces": pieces, "white": not state["white"]}


def model_legal_moves(state: dict) -> list:
    white = state["white"]
    legal = []
    for move in pseudo_moves(state):
        after = apply_model(state, move)
        if not attacked_by(after["pieces"], find_king(after["pieces"], white), not white):
            legal.append(move)
    return legal


def move_key(origin, target, promotion) -> tuple:
    return tuple(origin), tuple(target), None if promotion is None else promotion.symbol


def model_threats(state: dict, color_white: bool) -> set:
    """Peças da cor atacadas, sem o rei, mais o peão que pode ser capturado en passant agora."""
    pieces = state["pieces"]
    threatened = {
        at for at, letter in pieces.items()
        if is_white(letter) == color_white and letter.upper() != "K" and attacked_by(pieces, at, not color_white)
    }
    if state["white"] != color_white:
        threatened |= {move[3] for move in model_legal_moves(state) if move[4] == "ep"}
    return threatened


def model_position_key(state: dict) -> tuple:
    legal_ep = any(move[4] == "ep" for move in model_legal_moves(state))
    return (frozenset(state["pieces"].items()), state["white"], frozenset(state["rights"]),
            state["ep"] if legal_ep else None)


def model_insufficient(pieces: dict) -> bool:
    others = [(at, letter) for at, letter in pieces.items() if letter.upper() != "K"]
    if not others:
        return True
    if len(others) == 1:
        return others[0][1].upper() in "BN"
    return all(letter.upper() == "B" for _, letter in others) and len({(a[0] + a[1]) % 2 for a, _ in others}) == 1


def san_matches(state: dict, san: str) -> list:
    """Interpreta SAN sem usar o gerador de SAN do motor e devolve os lances legais que ela descreve."""
    text = san.rstrip("+#")
    legal = model_legal_moves(state)
    pieces = state["pieces"]
    if text in ("O-O", "O-O-O"):
        file = 6 if text == "O-O" else 2
        return [m for m in legal if m[4] == "castle" and m[1][0] == file]
    promotion = None
    if "=" in text:
        text, promotion = text.split("=")
    target = (FILES.index(text[-2]), int(text[-1]) - 1)
    text = text[:-2].replace("x", "")
    kind = text[0] if text and text[0] in "NBRQK" else "P"
    hint = text[1:] if kind != "P" else text
    matches = []
    for move in legal:
        if move[1] != target or move[2] != promotion or pieces[move[0]].upper() != kind:
            continue
        name = f"{FILES[move[0][0]]}{move[0][1] + 1}"
        if all(char in name for char in hint):
            matches.append(move)
    return matches


def check_invariants(engine: GameEngine) -> dict:
    """Confere a posição atual inteira. Levanta AssertionError com o FEN da posição, se algo divergir."""
    board = engine.board
    fen = board.to_fen()
    state = parse_fen(fen)
    pieces = state["pieces"]
    assert sum(letter == "K" for letter in pieces.values()) == 1, fen
    assert sum(letter == "k" for letter in pieces.values()) == 1, fen
    assert all(letter.upper() != "P" or at[1] not in (0, 7) for at, letter in pieces.items()), fen
    assert tuple(board.king_square(Color.WHITE)) == find_king(pieces, True), fen
    assert tuple(board.king_square(Color.BLACK)) == find_king(pieces, False), fen

    idle_king = find_king(pieces, not state["white"])
    assert not attacked_by(pieces, idle_king, state["white"]), f"rei de quem não joga está em xeque: {fen}"

    engine_moves = {move_key(m.origin, m.target, m.promotion) for m in legal_moves(board)}
    model_moves = model_legal_moves(state)
    model_keys = {(m[0], m[1], m[2]) for m in model_moves}
    assert engine_moves == model_keys, f"{fen}\nsó no motor: {engine_moves - model_keys}\nsó no modelo: {model_keys - engine_moves}"

    assert Board.from_fen(fen).to_fen() == fen, f"FEN não fecha a ida e volta: {fen}"

    in_check = attacked_by(pieces, find_king(pieces, state["white"]), not state["white"])
    assert engine.in_check == in_check, fen

    for color in Color:
        threats = {tuple(s) for s in engine.threatened_pieces(color)}
        assert threats == model_threats(state, color is Color.WHITE), f"{color}: {fen}"

    _check_san_of_all_moves(engine, state, model_moves)
    return state


def _check_san_of_all_moves(engine, state, model_moves):
    board = engine.board
    sans = []
    for move in legal_moves(board):
        before = board.to_fen()
        san = move_to_san(board, move)
        assert board.to_fen() == before, f"move_to_san alterou o tabuleiro: {before}"
        sans.append(san)
        found = san_matches(state, san)
        assert [(m[0], m[1], m[2]) for m in found] == [move_key(move.origin, move.target, move.promotion)], (
            f"SAN {san!r} em {before} descreve {found}"
        )
        after = apply_model(state, _model_move_for(model_moves, move))
        opponent_in_check = attacked_by(after["pieces"], find_king(after["pieces"], after["white"]), state["white"])
        assert san.endswith(("+", "#")) == opponent_in_check, f"sufixo de xeque de {san} em {before}"
    assert len(set(sans)) == len(sans), f"SAN repetida em {board.to_fen()}: {Counter(sans).most_common(3)}"


def _model_move_for(model_moves, move):
    key = move_key(move.origin, move.target, move.promotion)
    return next(m for m in model_moves if (m[0], m[1], m[2]) == key)


def snapshot(board: Board) -> tuple:
    return (
        tuple(tuple(column) for column in board.grid), board.turn, board.castling_rights, board.en_passant_target,
        board.halfmove_clock, board.fullmove_number, dict(board._king_squares), len(board._applied),
    )


def choose_move(rng: random.Random, board: Board, moves: list):
    """Sorteio com tendência a capturas e peões: chega a finais, promoções e empates bem mais rápido."""
    weights = []
    for move in moves:
        weight = 1.0
        if board.piece_at(move.target) is not None or move.is_en_passant:
            weight += 3.0
        if move.promotion is not None:
            weight += 2.0
        if board.piece_at(move.origin).kind is PieceType.PAWN:
            weight += 1.0
        if move.is_castling:
            weight += 6.0
        weights.append(weight)
    return rng.choices(moves, weights)[0]


def play_checked_game(seed: int, fen: str | None, max_plies: int, stats: Counter) -> None:
    rng = random.Random(seed)
    engine = GameEngine(fen=fen)
    counts = Counter()
    state = parse_fen(engine.board.to_fen())
    counts[model_position_key(state)] += 1
    rights_before = set(state["rights"])
    half_before = state["half"]
    for _ in range(max_plies):
        if engine.result is not None:
            break
        state = check_invariants(engine)
        moves = legal_moves(engine.board)
        before = snapshot(engine.board)
        for move in moves:
            engine.board.apply(move)
            engine.board.undo()
        assert snapshot(engine.board) == before, f"apply/undo não restaurou: {engine.board.to_fen()}"

        move = choose_move(rng, engine.board, moves)
        captured_before = len(engine.current_player.captured)
        mover = engine.current_player
        was_pawn = engine.board.piece_at(move.origin).kind is PieceType.PAWN
        outcome = engine.play(move.origin, move.target, move.promotion)
        assert outcome.ok, f"{move.uci} recusado com {outcome.error} em {before}"
        stats["plies"] += 1
        stats["promotion"] += move.promotion is not None
        stats["en_passant"] += move.is_en_passant
        stats["castling"] += move.is_castling
        stats["capture"] += outcome.captured is not None
        assert len(mover.captured) == captured_before + (outcome.captured is not None)

        state = parse_fen(engine.board.to_fen())
        assert state["rights"] <= rights_before, f"direito de roque voltou: {engine.board.to_fen()}"
        rights_before = set(state["rights"])
        expected_half = 0 if was_pawn or outcome.captured is not None else half_before + 1
        assert state["half"] == expected_half, engine.board.to_fen()
        half_before = expected_half
        counts[model_position_key(state)] += 1
        _check_ending(engine, state, counts, stats)
    stats["games"] += 1


def _check_ending(engine, state, counts, stats):
    """Confere o resultado do motor contra a dedução independente, na precedência combinada."""
    model_moves = model_legal_moves(state)
    pieces = state["pieces"]
    in_check = attacked_by(pieces, find_king(pieces, state["white"]), not state["white"])
    expected = None
    if not model_moves:
        expected = EndReason.CHECKMATE if in_check else EndReason.STALEMATE
    elif model_insufficient(pieces):
        expected = EndReason.INSUFFICIENT_MATERIAL
    elif counts[model_position_key(state)] >= 3:
        expected = EndReason.THREEFOLD_REPETITION
    elif state["half"] >= 100:
        expected = EndReason.FIFTY_MOVES
    actual = None if engine.result is None else engine.result.reason
    assert actual is expected, f"motor {actual}, esperado {expected}: {engine.board.to_fen()}"
    if expected is not None:
        stats[expected.name] += 1
        winner = None
        if expected is EndReason.CHECKMATE:
            winner = Color.BLACK if state["white"] else Color.WHITE
        assert engine.result.winner is winner


# Posições de partida que forçam roques, en passant, promoções e finais em poucos lances.
SEED_FENS = [
    None,
    "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "8/PPPP1k2/8/8/8/8/2K1pppp/8 w - - 0 1",
    "8/1P4k1/8/8/8/8/1p4K1/8 b - - 0 1",
    "4k3/8/8/8/8/8/4P3/4K2R w K - 0 1",
    "k7/6p1/8/5P2/8/8/8/K7 b - - 0 1",
    "4k3/pp4pp/8/2PpP3/2pP1p2/8/PP4PP/4K3 w - d6 0 2",
    "n1n5/PPPk4/8/8/8/8/4Kppp/5N1N b - - 0 1",
]


@pytest.mark.ct("CT-50")
@pytest.mark.parametrize("seed", range(6))
def test_ataque_partidas_aleatorias_conferem_com_modelo_independente(seed):
    stats = Counter()
    for index, fen in enumerate(SEED_FENS):
        play_checked_game(seed * 1000 + index, fen, max_plies=60, stats=stats)
    assert stats["plies"] > 200


@pytest.mark.ct("CT-50")
@pytest.mark.slow
def test_ataque_partidas_aleatorias_longas_conferem_com_modelo_independente():
    stats = Counter()
    for seed in range(30):
        for index, fen in enumerate(SEED_FENS):
            play_checked_game(seed * 977 + index, fen, max_plies=240, stats=stats)
    print(dict(stats))
    assert stats["plies"] > 20000
    assert stats["promotion"] and stats["en_passant"] and stats["castling"]
    assert stats["CHECKMATE"] and stats["STALEMATE"] and stats["INSUFFICIENT_MATERIAL"]


# Promoção --------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-51")
def test_ataque_promocao_com_captura_xeque_e_mate_no_mesmo_lance():
    engine = GameEngine(fen="4r1k1/3P1ppp/8/8/8/8/8/4K3 w - - 0 1")
    outcome = engine.play(sq("d7"), sq("e8"), PieceType.QUEEN)
    assert outcome.ok and outcome.san == "dxe8=Q#"
    assert outcome.captured.kind is PieceType.ROOK and outcome.promoted_to is PieceType.QUEEN
    assert outcome.gives_check and outcome.result.reason is EndReason.CHECKMATE
    assert engine.players[Color.WHITE].material_score == 5
    assert engine.players[Color.WHITE].match_points == 1.0
    assert engine.board.piece_at(sq("e8")).kind is PieceType.QUEEN


@pytest.mark.ct("CT-51")
def test_ataque_promocao_a_cavalo_com_captura_que_nao_da_mate():
    engine = GameEngine(fen="4r1k1/3P1ppp/8/8/8/8/8/4K3 w - - 0 1")
    outcome = engine.play(sq("d7"), sq("e8"), PieceType.KNIGHT)
    assert outcome.ok and outcome.san == "dxe8=N" and outcome.result is None and not outcome.gives_check


@pytest.mark.ct("CT-51")
@pytest.mark.parametrize("bad", [PieceType.KING, PieceType.PAWN, "Q", 1, object()])
def test_ataque_promocao_invalida_nao_altera_nada(bad):
    engine = GameEngine(fen="4r1k1/3P1ppp/8/8/8/8/8/4K3 w - - 0 1")
    before = engine.board.to_fen()
    outcome = engine.play(sq("d7"), sq("e8"), bad)
    assert not outcome.ok and outcome.error is MoveError.ILLEGAL_MOVE
    assert engine.board.to_fen() == before and engine.history == []


@pytest.mark.ct("CT-51")
def test_ataque_promocao_cravada_recusa_antes_de_pedir_a_peca():
    engine = GameEngine(fen="1r2k3/P7/8/8/8/8/8/K7 w - - 0 1")
    assert engine.play(sq("a7"), sq("b8")).error is MoveError.PROMOTION_REQUIRED
    pinned = GameEngine(fen="4k3/KP5r/8/8/8/8/8/8 w - - 0 1")
    assert pinned.play(sq("b7"), sq("b8")).error is MoveError.LEAVES_KING_IN_CHECK
    assert not pinned.is_promotion_move(sq("b7"), sq("b8"))


# En passant ------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-51")
def test_ataque_en_passant_que_expoe_o_rei_na_fileira():
    engine = GameEngine(fen="8/8/8/K2pP2r/8/8/8/4k3 w - d6 0 2")
    targets = [tuple(m.target) for m in engine.legal_moves_from(sq("e5"))]
    assert tuple(sq("d6")) not in targets
    assert engine.play(sq("e5"), sq("d6")).error is MoveError.LEAVES_KING_IN_CHECK


@pytest.mark.ct("CT-51")
def test_ataque_en_passant_que_expoe_o_rei_na_diagonal():
    engine = GameEngine(fen="8/7k/8/8/3pP3/8/8/1B2K3 b - e3 0 1")
    assert tuple(sq("e3")) not in [tuple(m.target) for m in engine.legal_moves_from(sq("d4"))]
    assert engine.play(sq("d4"), sq("e3")).error is MoveError.LEAVES_KING_IN_CHECK
    assert {tuple(s) for s in engine.threatened_pieces(Color.WHITE)} == set()


@pytest.mark.ct("CT-51")
def test_ataque_en_passant_e_a_unica_defesa_do_xeque():
    engine = GameEngine(fen="8/8/7R/k7/pP6/3B4/8/1R2K3 b - b3 0 1")
    assert engine.result is None, "en passant é legal, a posição não é mate"
    moves = legal_moves(engine.board)
    assert [m.uci for m in moves] == ["a4b3"] and moves[0].is_en_passant
    outcome = engine.play(sq("a4"), sq("b3"))
    assert outcome.ok and outcome.san == "axb3" and outcome.captured_square == sq("b4")
    assert engine.board.piece_at(sq("b4")) is None and engine.players[Color.BLACK].material_score == 1


@pytest.mark.ct("CT-51")
def test_ataque_en_passant_nao_resolve_xeque_de_outra_peca():
    engine = GameEngine(fen="3rk3/8/8/1pP5/8/8/8/3K4 w - b6 0 1")
    assert engine.in_check
    assert engine.play(sq("c5"), sq("b6")).error is MoveError.LEAVES_KING_IN_CHECK


@pytest.mark.ct("CT-51")
def test_ataque_en_passant_some_depois_de_um_lance():
    engine = GameEngine(fen="4k3/8/8/1pP5/8/8/8/4K3 w - b6 0 1")
    assert engine.play(sq("e1"), sq("e2")).ok
    assert engine.play(sq("e8"), sq("e7")).ok
    assert engine.play(sq("c5"), sq("b6")).error is MoveError.ILLEGAL_MOVE


# Roque -----------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-51")
def test_ataque_roque_com_torre_capturada_e_outra_chegando_na_casa_original():
    engine = GameEngine(fen="4k3/6b1/8/8/8/1R6/8/R3K3 b Q - 0 1")
    for origin, target in (("g7", "a1"), ("b3", "b1"), ("a1", "d4"), ("b1", "a1"), ("e8", "e7")):
        assert engine.play(sq(origin), sq(target)).ok, f"{origin}{target} em {engine.board.to_fen()}"
    assert engine.board.piece_at(sq("a1")).kind is PieceType.ROOK
    assert "Q" not in engine.board.castling_rights
    assert tuple(sq("c1")) not in [tuple(m.target) for m in engine.legal_moves_from(sq("e1"))]
    assert engine.play(sq("e1"), sq("c1")).error is MoveError.ILLEGAL_MOVE


@pytest.mark.ct("CT-51")
def test_ataque_roque_com_torre_que_saiu_e_voltou_nao_recupera_direito():
    engine = GameEngine(fen="4k3/8/8/8/8/8/8/4K2R w K - 0 1")
    for origin, target in (("h1", "h2"), ("e8", "e7"), ("h2", "h1"), ("e7", "e8")):
        assert engine.play(sq(origin), sq(target)).ok
    assert engine.board.castling_rights == frozenset()
    assert engine.play(sq("e1"), sq("g1")).error is MoveError.ILLEGAL_MOVE


@pytest.mark.ct("CT-51")
@pytest.mark.parametrize("fen, origin, target, allowed", [
    ("4k3/8/8/8/8/5r2/8/4K2R w K - 0 1", "e1", "g1", False),  # f1 passa livre, mas é atacada? f3 ataca f1.
    ("4k3/8/8/8/8/6r1/8/4K2R w K - 0 1", "e1", "g1", False),  # a chegada g1 é atacada.
    ("4k3/8/8/8/8/7r/8/4K2R w K - 0 1", "e1", "g1", True),  # só a torre é atacada: pode.
    ("4k3/8/8/8/8/1r6/8/R3K3 w Q - 0 1", "e1", "c1", True),  # b1 atacada: o rei não passa por ela.
    ("4k3/8/8/8/8/r7/8/R3K3 w Q - 0 1", "e1", "c1", True),  # a torre é atacada: pode.
    ("4k3/8/8/8/8/3r4/8/R3K3 w Q - 0 1", "e1", "c1", False),  # d1 atacada: o rei atravessa.
    ("4k3/8/8/8/8/4r3/8/R3K3 w Q - 0 1", "e1", "c1", False),  # rei em xeque.
    ("4k3/8/8/8/8/8/8/RN2K3 w Q - 0 1", "e1", "c1", False),  # b1 ocupada.
])
def test_ataque_roque_casas_atacadas_e_bloqueio(fen, origin, target, allowed):
    engine = GameEngine(fen=fen)
    assert engine.play(sq(origin), sq(target)).ok is allowed


# Precedência dos fins de jogo ------------------------------------------------------------------------


@pytest.mark.ct("CT-52")
def test_ataque_mate_no_lance_que_completa_os_50_lances():
    engine = GameEngine(fen="6k1/5ppp/8/8/8/8/8/4R1K1 w - - 99 80")
    outcome = engine.play(sq("e1"), sq("e8"))
    assert outcome.result.reason is EndReason.CHECKMATE and outcome.result.winner is Color.WHITE
    assert engine.players[Color.WHITE].match_points == 1.0 and engine.players[Color.BLACK].match_points == 0.0


@pytest.mark.ct("CT-52")
def test_ataque_afogamento_no_lance_que_completa_os_50_lances():
    engine = GameEngine(fen="7k/8/5K2/6Q1/8/8/8/8 w - - 99 80")
    outcome = engine.play(sq("g5"), sq("g6"))
    assert outcome.result.reason is EndReason.STALEMATE and outcome.result.is_draw


@pytest.mark.ct("CT-52")
def test_ataque_captura_no_lance_100_zera_e_nao_empata():
    engine = GameEngine(fen="4k3/8/8/8/8/8/1p6/1R2K2R w - - 99 80")
    outcome = engine.play(sq("b1"), sq("b2"))
    assert outcome.result is None and engine.board.halfmove_clock == 0


@pytest.mark.ct("CT-52")
def test_ataque_peao_no_lance_100_zera_e_nao_empata():
    engine = GameEngine(fen="4k3/8/8/8/8/8/P7/4K2R w - - 99 80")
    assert engine.play(sq("a2"), sq("a3")).result is None


@pytest.mark.ct("CT-52")
def test_ataque_fim_no_lance_100_sem_captura_e_empate_50_lances():
    engine = GameEngine(fen="4k3/8/8/8/8/8/P7/4K2R w - - 99 80")
    outcome = engine.play(sq("h1"), sq("h2"))
    assert outcome.result.reason is EndReason.FIFTY_MOVES
    assert engine.play(sq("e8"), sq("e7")).error is MoveError.GAME_NOT_ACTIVE


@pytest.mark.ct("CT-52")
def test_ataque_repeticao_e_50_lances_no_mesmo_lance_empatam_uma_vez_so():
    engine = GameEngine(fen="4k3/8/8/8/8/8/P7/4K2R w - - 92 80")
    cycle = (("h1", "h2"), ("e8", "e7"), ("h2", "h1"), ("e7", "e8"))
    last = None
    for origin, target in cycle * 2:
        last = engine.play(sq(origin), sq(target))
        assert last.ok
    assert engine.result is not None
    assert last.result.reason is EndReason.THREEFOLD_REPETITION
    assert engine.players[Color.WHITE].match_points == 0.5 and engine.players[Color.BLACK].match_points == 0.5


@pytest.mark.ct("CT-52")
@pytest.mark.parametrize("fen, reason", [
    ("7k/5Q2/5K2/8/8/8/8/8 b - - 0 1", EndReason.STALEMATE),
    ("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1", EndReason.CHECKMATE),
    ("8/8/8/8/8/8/8/k1K5 w - - 0 1", EndReason.INSUFFICIENT_MATERIAL),
    ("4k3/8/8/8/8/8/P7/4K3 w - - 100 80", EndReason.FIFTY_MOVES),
])
def test_ataque_fen_que_ja_nasce_encerrada(fen, reason):
    engine = GameEngine(fen=fen)
    assert engine.state is GameState.FINISHED and engine.result.reason is reason
    assert engine.play(sq("a2"), sq("a3")).error is MoveError.GAME_NOT_ACTIVE
    assert engine.tick(1.0) is None


# Repetição --------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-53")
def test_ataque_repeticao_conta_direito_de_roque_perdido():
    """A disposição inicial reaparece nos lances 4 e 8. Se os direitos não contassem, o lance 8 empataria."""
    engine = GameEngine(fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    cycle = (("h1", "h2"), ("h8", "h7"), ("h2", "h1"), ("h7", "h8"))
    outcomes = [engine.play(sq(origin), sq(target)) for origin, target in cycle * 2]
    assert all(outcome.ok and outcome.result is None for outcome in outcomes)
    assert engine.board.castling_rights == frozenset("Qq")
    # O que empata é a posição do segundo meio-lance do ciclo, a primeira já sem K e k: 2, 6 e 10.
    assert engine.play(sq("h1"), sq("h2")).result is None
    last = engine.play(sq("h8"), sq("h7"))
    assert last.result.reason is EndReason.THREEFOLD_REPETITION and len(engine.history) == 10


@pytest.mark.ct("CT-53")
def test_ataque_repeticao_conta_a_posicao_inicial():
    engine = GameEngine()
    moves = (("g1", "f3"), ("g8", "f6"), ("f3", "g1"), ("f6", "g8")) * 2
    last = None
    for origin, target in moves:
        last = engine.play(sq(origin), sq(target))
    assert last.result.reason is EndReason.THREEFOLD_REPETITION and len(engine.history) == 8


@pytest.mark.ct("CT-53")
def test_ataque_repeticao_en_passant_legal_muda_a_posicao():
    """Depois do avanço com en passant possível, a mesma disposição não é a mesma posição."""
    engine = GameEngine(fen="4k3/8/8/8/2p5/8/3P4/4K3 w - - 0 1")
    assert engine.play(sq("d2"), sq("d4")).ok
    key_with_ep = engine._position_counts.copy()
    assert engine.board.en_passant_target == sq("d3")
    for origin, target in (("e8", "e7"), ("e1", "e2"), ("e7", "e8"), ("e2", "e1")):
        assert engine.play(sq(origin), sq(target)).ok
    # A disposição do avanço voltou, com as pretas na vez, mas sem o en passant.
    assert engine.board.to_fen().split()[:2] == ["4k3/8/8/8/2pP4/8/8/4K3", "b"]
    assert max(engine._position_counts.values()) == 1
    assert len(key_with_ep) == 2


@pytest.mark.ct("CT-53")
def test_ataque_repeticao_en_passant_ilegal_nao_muda_a_posicao():
    """Peão cravado: o alvo existe no FEN, mas não há jogada, então a posição se repete."""
    engine = GameEngine(fen="4K3/8/8/8/k1p4R/8/3P4/8 w - - 0 1")
    assert engine.play(sq("d2"), sq("d4")).ok
    assert engine.board.en_passant_target == sq("d3")
    assert not [m for m in legal_moves(engine.board) if m.is_en_passant], "c4xd3 abriria a fileira sobre o rei preto"
    for origin, target in (("a4", "a5"), ("e8", "e7"), ("a5", "a4"), ("e7", "e8")):
        assert engine.play(sq(origin), sq(target)).ok
    assert max(engine._position_counts.values()) == 2


# Material insuficiente --------------------------------------------------------------------------------


@pytest.mark.ct("CT-54")
@pytest.mark.parametrize("fen, origin, target, promotion, insufficient", [
    ("8/P7/8/8/8/8/8/k6K w - - 0 1", "a7", "a8", PieceType.BISHOP, True),
    ("8/P7/8/8/8/8/8/k6K w - - 0 1", "a7", "a8", PieceType.KNIGHT, True),
    ("8/P7/8/8/8/8/8/k6K w - - 0 1", "a7", "a8", PieceType.ROOK, False),
    ("8/P7/8/8/8/8/8/k6K w - - 0 1", "a7", "a8", PieceType.QUEEN, False),
    ("7b/P7/8/8/8/8/8/k6K w - - 0 1", "a7", "a8", PieceType.BISHOP, False),  # a8 clara e h8 escura.
    ("6b1/P7/8/8/8/8/8/k6K w - - 0 1", "a7", "a8", PieceType.BISHOP, True),  # a8 e g8, ambas claras.
    ("6n1/P7/8/8/8/8/8/k6K w - - 0 1", "a7", "a8", PieceType.BISHOP, False),  # bispo contra cavalo.
])
def test_ataque_material_insuficiente_por_promocao(fen, origin, target, promotion, insufficient):
    engine = GameEngine(fen=fen)
    outcome = engine.play(sq(origin), sq(target), promotion)
    assert outcome.ok
    reason = None if outcome.result is None else outcome.result.reason
    assert (reason is EndReason.INSUFFICIENT_MATERIAL) is insufficient


@pytest.mark.ct("CT-54")
def test_ataque_material_insuficiente_por_captura():
    engine = GameEngine(fen="8/8/8/8/8/8/1r6/kN5K b - - 0 1")
    outcome = engine.play(sq("a1"), sq("b1"))
    assert outcome.ok and outcome.result is None, "sobra torre preta"
    assert engine.play(sq("h1"), sq("g1")).ok
    engine = GameEngine(fen="8/8/8/8/8/8/8/kN5K b - - 0 1")
    assert engine.result.reason is EndReason.INSUFFICIENT_MATERIAL
    engine = GameEngine(fen="8/8/8/8/8/4k3/2r5/1N1K4 w - - 0 1")
    outcome = engine.play(sq("d1"), sq("c2"))
    assert outcome.result.reason is EndReason.INSUFFICIENT_MATERIAL and outcome.captured.kind is PieceType.ROOK


@pytest.mark.ct("CT-54")
def test_ataque_material_insuficiente_por_captura_de_peao_en_passant():
    engine = GameEngine(fen="4k3/8/8/1pP5/8/8/8/4K3 w - b6 0 1")
    outcome = engine.play(sq("c5"), sq("b6"))
    assert outcome.ok and outcome.result is None, "sobra o peão que capturou"
    engine = GameEngine(fen="8/8/2k5/1pP5/8/8/8/3K4 w - b6 0 1")
    assert engine.play(sq("c5"), sq("b6")).ok
    outcome = engine.play(sq("c6"), sq("b6"))
    assert outcome.result.reason is EndReason.INSUFFICIENT_MATERIAL


# Relógio, desistência e série ------------------------------------------------------------------------


@pytest.mark.ct("CT-55")
def test_ataque_tempo_esgotado_contra_so_rei_empata():
    engine = GameEngine(time_control=TimeControl.BLITZ_5, fen="k7/8/8/8/8/8/P7/7K w - - 0 1")
    result = engine.tick(300.0)
    assert result.is_draw and result.reason is EndReason.TIMEOUT
    assert engine.players[Color.WHITE].match_points == engine.players[Color.BLACK].match_points == 0.5
    assert engine.tick(10.0) is None


@pytest.mark.ct("CT-55")
def test_ataque_tempo_esgotado_de_quem_so_tem_rei_perde():
    engine = GameEngine(time_control=TimeControl.BLITZ_5, fen="k7/8/8/8/8/8/P7/7K b - - 0 1")
    result = engine.tick(300.0)
    assert result.winner is Color.WHITE and engine.players[Color.WHITE].match_points == 1.0


@pytest.mark.ct("CT-55")
def test_ataque_tempo_exato_e_fracao_antes():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    assert engine.tick(299.999999) is None
    assert engine.clock.remaining(Color.WHITE) > 0
    assert engine.tick(1e-6) is not None
    assert engine.result.winner is Color.BLACK


@pytest.mark.ct("CT-55")
@pytest.mark.parametrize("dt", [0.0, -1.0, -math.inf, math.nan])
def test_ataque_dt_absurdo_nao_mexe_no_relogio(dt):
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    assert engine.tick(dt) is None
    assert engine.clock.remaining(Color.WHITE) == 300.0 and engine.clock.elapsed(Color.WHITE) == 0.0


@pytest.mark.ct("CT-55")
def test_ataque_pausa_congela_e_desistir_na_pausa_conta_uma_vez():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.pause()
    assert engine.tick(9999.0) is None and engine.clock.remaining(Color.WHITE) == 300.0
    assert engine.play(sq("e2"), sq("e4")).error is MoveError.GAME_NOT_ACTIVE
    engine.resign()
    assert engine.state is GameState.FINISHED and engine.players[Color.BLACK].match_points == 1.0
    engine.resume()
    assert engine.state is GameState.FINISHED
    engine.pause()
    assert engine.state is GameState.FINISHED


@pytest.mark.ct("CT-55")
def test_ataque_pontos_da_serie_nunca_contam_duas_vezes():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.resign(Color.WHITE)
    first = engine.result
    assert engine.resign(Color.BLACK) is first
    assert engine.agree_draw() is first
    assert engine.tick(1000.0) is None
    assert engine.players[Color.BLACK].match_points == 1.0 and engine.players[Color.WHITE].match_points == 0.0


@pytest.mark.ct("CT-55")
def test_ataque_restart_no_meio_nao_da_pontos_e_limpa_tudo():
    engine = GameEngine(time_control=TimeControl.BLITZ_5)
    engine.tick(10.0)
    engine.play(sq("e2"), sq("e4"))
    engine.play(sq("d7"), sq("d5"))
    engine.play(sq("e4"), sq("d5"))
    engine.restart()
    assert engine.board.to_fen() == Board.initial().to_fen() and engine.history == []
    assert engine.clock.remaining(Color.WHITE) == 300.0 and engine.players[Color.WHITE].captured == []
    assert engine.players[Color.WHITE].match_points == 0.0 and engine.state is GameState.IN_PROGRESS
    assert engine.turn is Color.WHITE and engine.result is None


@pytest.mark.ct("CT-55")
def test_ataque_revanche_varias_vezes_troca_cores_e_soma_certo():
    engine = GameEngine("Ana", "Bia", TimeControl.BLITZ_5)
    expected = {"Ana": 0.0, "Bia": 0.0}
    for game in range(7):
        white_name = "Ana" if game % 2 == 0 else "Bia"
        black_name = "Bia" if game % 2 == 0 else "Ana"
        assert engine.players[Color.WHITE].name == white_name and engine.players[Color.WHITE].color is Color.WHITE
        assert engine.players[Color.BLACK].name == black_name and engine.players[Color.BLACK].color is Color.BLACK
        engine.resign(Color.WHITE)
        expected[black_name] += 1.0
        assert {p.name: p.match_points for p in engine.players.values()} == expected
        engine.rematch()
    assert engine.state is GameState.IN_PROGRESS and engine.history == []


@pytest.mark.ct("CT-55")
def test_ataque_fen_com_pretas_primeiro_no_motor():
    engine = GameEngine("Ana", "Bia", TimeControl.BLITZ_5, fen="4k3/8/8/8/8/8/4P3/4K3 b - - 3 10")
    assert engine.turn is Color.BLACK and engine.current_player.name == "Bia"
    engine.tick(5.0)
    assert engine.clock.remaining(Color.BLACK) == 295.0 and engine.clock.remaining(Color.WHITE) == 300.0
    assert engine.play(sq("e2"), sq("e4")).error is MoveError.NOT_YOUR_TURN
    assert engine.play(sq("e8"), sq("e7")).ok
    assert engine.board.fullmove_number == 11
    engine.rematch()
    assert engine.turn is Color.BLACK and engine.board.fullmove_number == 10
    assert engine.current_player.name == "Ana", "na revanche as cores trocam, e a FEN continua com as pretas primeiro"


@pytest.mark.ct("CT-55")
def test_ataque_dt_infinito_nao_esgota_relogio_sem_limite():
    engine = GameEngine()
    assert engine.tick(math.inf) is None


@pytest.mark.ct("CT-55")
def test_ataque_restart_em_fen_encerrada_nao_soma_pontos_de_novo():
    engine = GameEngine(fen="8/8/8/8/8/8/8/k1K5 w - - 0 1")
    first = engine.players[Color.WHITE].match_points
    engine.restart()
    engine.restart()
    assert engine.players[Color.WHITE].match_points == first


# Entradas absurdas ------------------------------------------------------------------------------------


@pytest.mark.ct("CT-56")
@pytest.mark.parametrize("origin, target", [
    (None, None), ("e2", "e4"), (12, 34), ((), ()), ((4,), (4, 3)), ((4, 1, 0), (4, 3)), ((1.0, 1.0), (1.0, 2.0)),
    ((-1, 0), (0, 0)), ((8, 8), (0, 0)), ((2**70, 0), (0, 0)), ({}, {}), (object(), object()), ([4, 1], "e4"),
])
def test_ataque_jogada_com_entrada_absurda_vira_erro(origin, target):
    engine = GameEngine()
    before = engine.board.to_fen()
    outcome = engine.play(origin, target)
    assert not outcome.ok and outcome.error is not None
    assert engine.board.to_fen() == before and engine.history == []
    assert engine.legal_moves_from(origin) == [] or isinstance(origin, list)
    assert engine.is_promotion_move(origin, target) is False
    assert engine.attackers_of(origin) == [] or isinstance(origin, list)


@pytest.mark.ct("CT-56")
@pytest.mark.parametrize("fen", [
    "", "   ", "8/8/8/8/8/8/8/8 w - - 0 1", "k7/8/8/8/8/8/8/K7", "k7/8/8/8/8/8/8/K7 x - - 0 1",
    "k7/8/8/8/8/8/8/K7 w ? - 0 1", "k7/8/8/8/8/8/8/K7 w - z9 0 1", "k7/8/8/8/8/8/8/K7 w - - -1 1",
    "k7/8/8/8/8/8/8/K7 w - - 0 0", "k7/8/8/8/8/8/8/K7 w - - a 1", "k7/8/8/8/8/8/8/K7 w - - \u0663 1",
    "k8/8/8/8/8/8/8/K7 w - - 0 1", "k6/8/8/8/8/8/8/K7 w - - 0 1", "k7/8/8/8/8/8/8/K7/8 w - - 0 1",
    "kK6/8/8/8/8/8/8/8 w - - 0 1", "kk6/8/8/8/8/8/8/K7 w - - 0 1", "k7/8/8/8/8/8/8/KK6 w - - 0 1",
    "kP6/8/8/8/8/8/8/K7 w - - 0 1", "k7/8/8/8/8/8/8/Kp6 w - - 0 1", "k7/8/8/8/8/8/8/K7 w KQkq - 0 1",
    "k7/8/8/8/8/8/8/K7 w KK - 0 1", "k7/8/8/8/8/8/8/K7 w - e3 0 1", "k7/8/8/8/8/8/8/K7 w - e6 0 1",
    "kX6/8/8/8/8/8/8/K7 w - - 0 1", "k7/8/8/8/8/8/8/ÇK6 w - - 0 1", "k0/8/8/8/8/8/8/K7 w - - 0 1",
    "k9/8/8/8/8/8/8/K7 w - - 0 1", "k6R/8/8/8/8/8/8/4K3 w - - 0 1", None,
])
def test_ataque_fen_malformada_levanta_valueerror_claro(fen):
    if fen is None:
        with pytest.raises(ValueError):
            Board.from_fen(fen)
        return
    with pytest.raises(ValueError):
        GameEngine(fen=fen)


@pytest.mark.ct("CT-56")
def test_ataque_fen_com_direitos_em_qualquer_ordem_normaliza():
    board = Board.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w qkQK - 0 1")
    assert board.to_fen() == "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"


@pytest.mark.ct("CT-56")
def test_ataque_undo_sem_lances_falha_com_erro_claro():
    with pytest.raises(IndexError):
        Board.initial().undo()
