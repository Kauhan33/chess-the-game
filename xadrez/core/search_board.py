"""Tabuleiro compacto da CPU: as mesmas regras de `Board`, numa forma feita para velocidade.

`Board` é o tabuleiro do jogo: fácil de ler, com objetos para peças, casas e jogadas. Uma busca precisa
visitar dezenas de milhares de posições por segundo, e criar esses objetos custaria caro demais em
Python puro. Aqui tudo é inteiro:

- Casa: `fileira * 8 + coluna`, com a1 = 0 e h8 = 63.
- Peça: 1 a 6 (peão a rei), positiva para as brancas e negativa para as pretas. Vazia é 0.
- Lado: `WHITE` = 1 e `BLACK` = -1. Assim, `peça * lado` é positivo só para as peças de quem joga.
- Jogada: `origem | alvo << 6 | marca << 12`, um único inteiro de 15 bits.

As jogadas geradas são pseudolegais. `try_make` as testa ao aplicar, com o mesmo atalho de `rules.py`:
só precisa olhar o rei quando a peça está alinhada com ele.

A corretude é provada pelos mesmos valores de perft usados no motor (`test_core_search_board.py`).
Além disso, `choose_move` só devolve jogadas que `rules.legal_moves` também aceita.
"""
from __future__ import annotations

import random

from .board import Board
from .evaluation import (
    BISHOP,
    BLACK,
    ENDGAME_TABLE,
    KING,
    KNIGHT,
    MIDGAME_TABLE,
    PAWN,
    PHASE_WEIGHT,
    QUEEN,
    ROOK,
    WHITE,
)
from .move import Move
from .types import Color, PieceType

_SQUARE_COUNT = 64
SQUARE_MASK = 63
TARGET_SHIFT = 6
FLAG_SHIFT = 12
MOVE_MASK = (1 << 15) - 1
# A história do "de onde para onde" usa só a origem e o alvo, os 12 bits baixos da jogada.
FROM_TO_MASK = (1 << 12) - 1

FLAG_DOUBLE_PUSH = 1
FLAG_EN_PASSANT = 2
FLAG_CASTLING = 3
# Da marca 4 em diante é promoção, e a peça nova é `marca - 2`: 4 cavalo, 5 bispo, 6 torre e 7 dama.
FLAG_PROMOTE_KNIGHT = 4
FLAG_PROMOTE_QUEEN = 7
_FLAG_TO_PROMOTED_KIND = 2

_PIECE_CODE = {
    PieceType.PAWN: PAWN, PieceType.KNIGHT: KNIGHT, PieceType.BISHOP: BISHOP,
    PieceType.ROOK: ROOK, PieceType.QUEEN: QUEEN, PieceType.KING: KING,
}
_PROMOTION_FLAG = {PieceType.KNIGHT: 4, PieceType.BISHOP: 5, PieceType.ROOK: 6, PieceType.QUEEN: 7}

_RIGHT_BITS = {"K": 1, "Q": 2, "k": 4, "q": 8}
_ALL_RIGHTS = 15

A1, B1, C1, D1, E1, F1, G1, H1 = range(8)
A8, B8, C8, D8, E8, F8, G8, H8 = range(56, 64)

# Direitos que sobrevivem a uma jogada que sai de cada casa ou chega nela: o rei ou a torre se moveu,
# ou a torre foi capturada na casa de origem. É a mesma ideia de `_RIGHTS_LOST_AT` em `board.py`.
_RIGHTS_KEPT = [_ALL_RIGHTS] * _SQUARE_COUNT
for _square, _lost in ((E1, 3), (H1, 1), (A1, 2), (E8, 12), (H8, 4), (A8, 8)):
    _RIGHTS_KEPT[_square] = _ALL_RIGHTS ^ _lost

# Cada entrada: bit do direito, casa de chegada do rei, casas que precisam estar vazias e casa
# atravessada pelo rei. Roque grande exige b1 vazia, mas ela pode estar atacada: o rei não passa lá.
_WHITE_CASTLES = ((1, E1, G1, (F1, G1), F1), (2, E1, C1, (B1, C1, D1), D1))
_BLACK_CASTLES = ((4, E8, G8, (F8, G8), F8), (8, E8, C8, (B8, C8, D8), D8))
_CASTLES = [(), _WHITE_CASTLES, _BLACK_CASTLES]
_ROOK_HOME = {G1: H1, C1: A1, G8: H8, C8: A8}
_ROOK_TARGET = {G1: F1, C1: D1, G8: F8, C8: D8}


def _file_of(square: int) -> int:
    return square & 7


def _rank_of(square: int) -> int:
    return square >> 3


def _shifted(square: int, file_step: int, rank_step: int) -> int | None:
    file, rank = _file_of(square) + file_step, _rank_of(square) + rank_step
    return rank * 8 + file if 0 <= file < 8 and 0 <= rank < 8 else None


def _jump_targets(square: int, steps: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    targets = (_shifted(square, *step) for step in steps)
    return tuple(target for target in targets if target is not None)


def _ray(square: int, file_step: int, rank_step: int) -> tuple[int, ...]:
    squares = []
    current = _shifted(square, file_step, rank_step)
    while current is not None:
        squares.append(current)
        current = _shifted(current, file_step, rank_step)
    return tuple(squares)


def _rays_from(square: int, directions: tuple[tuple[int, int], ...]) -> tuple[tuple[int, ...], ...]:
    rays = (_ray(square, *direction) for direction in directions)
    return tuple(ray for ray in rays if ray)


def _is_aligned(square: int, other: int) -> bool:
    file_distance = abs(_file_of(square) - _file_of(other))
    rank_distance = abs(_rank_of(square) - _rank_of(other))
    return file_distance == 0 or rank_distance == 0 or file_distance == rank_distance


_ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
_DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_KNIGHT_STEPS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))

# Geometria calculada uma vez, ao importar: consultar uma tupla é bem mais barato que testar bordas.
_SQUARES = range(_SQUARE_COUNT)
_KNIGHT_TARGETS = [_jump_targets(square, _KNIGHT_STEPS) for square in _SQUARES]
_KING_TARGETS = [_jump_targets(square, _ORTHOGONAL + _DIAGONAL) for square in _SQUARES]
_ROOK_RAYS = [_rays_from(square, _ORTHOGONAL) for square in _SQUARES]
_BISHOP_RAYS = [_rays_from(square, _DIAGONAL) for square in _SQUARES]
_SLIDER_RAYS = {
    BISHOP: _BISHOP_RAYS,
    ROOK: _ROOK_RAYS,
    QUEEN: [_rays_from(square, _ORTHOGONAL + _DIAGONAL) for square in _SQUARES],
}
# Indexadas pelo lado: `tabela[1]` é das brancas e `tabela[-1]`, o último elemento, das pretas.
_PAWN_CAPTURES = [
    None,
    [_jump_targets(square, ((-1, 1), (1, 1))) for square in _SQUARES],
    [_jump_targets(square, ((-1, -1), (1, -1))) for square in _SQUARES],
]
_PAWN_START_RANK = [None, 1, 6]
_PAWN_LAST_STEP_RANK = [None, 6, 1]
_ALIGNED = [[_is_aligned(square, other) for other in _SQUARES] for square in _SQUARES]

# Chaves de Zobrist: um número aleatório por peça em cada casa. A chave da posição é o XOR dos números
# do que está no tabuleiro, então mover uma peça custa só dois XOR. A semente é fixa para a mesma
# posição sempre dar a mesma chave, e a busca continuar determinística.
_KEY_BITS = 64
_key_source = random.Random(20261103)


def _new_key() -> int:
    return _key_source.getrandbits(_KEY_BITS)


_PIECE_KEYS = [[_new_key() for _ in _SQUARES] for _ in range(2 * KING + 1)]
_SIDE_KEY = _new_key()
_CASTLING_KEYS = [_new_key() for _ in range(_ALL_RIGHTS + 1)]
# A posição extra guarda zero: `en_passant == -1`, sem alvo, pega esse último elemento e não muda a chave.
_EN_PASSANT_KEYS = [_new_key() for _ in _SQUARES] + [0]

_NO_EN_PASSANT = -1
_MIN_PLIES_TO_REPEAT = 4
_FIFTY_MOVES_IN_HALFMOVES = 100


def encode_move(move: Move) -> int:
    """Converte a jogada do motor para o inteiro usado na busca."""
    flag = 0
    if move.promotion is not None:
        flag = _PROMOTION_FLAG[move.promotion]
    elif move.is_double_push:
        flag = FLAG_DOUBLE_PUSH
    elif move.is_en_passant:
        flag = FLAG_EN_PASSANT
    elif move.is_castling:
        flag = FLAG_CASTLING
    origin = move.origin.rank * 8 + move.origin.file
    target = move.target.rank * 8 + move.target.file
    return origin | target << TARGET_SHIFT | flag << FLAG_SHIFT


class SearchBoard:
    """Posição com aplicar, desfazer e avaliação incremental. Não guarda nada que a busca não use."""

    __slots__ = (
        "squares", "side", "castling", "en_passant", "halfmove", "kings",
        "midgame", "endgame", "phase", "key", "pawn_key", "pawn_cache", "counts", "_undo", "_keys",
    )

    def __init__(self) -> None:
        self.squares = [0] * _SQUARE_COUNT
        self.side = WHITE
        self.castling = 0
        self.en_passant = _NO_EN_PASSANT
        self.halfmove = 0
        # Indexada pelo lado, como as tabelas: `kings[1]` são as brancas e `kings[-1]`, as pretas.
        self.kings = [0, 0, 0]
        self.midgame = 0
        self.endgame = 0
        self.phase = 0
        self.key = 0
        # Chave só dos peões: a estrutura deles muda pouco, e `evaluation.py` guarda a nota por essa chave.
        self.pawn_key = 0
        self.pawn_cache: dict[int, tuple[int, int]] = {}
        self.counts = [0] * (2 * KING + 1)
        self._undo: list[tuple[int, ...]] = []
        self._keys: list[int] = []

    @classmethod
    def from_board(cls, board: Board) -> SearchBoard:
        """Copia a posição de um `Board`, que precisa ter um rei de cada cor."""
        instance = cls()
        for square, piece in board.pieces():
            sign = WHITE if piece.color is Color.WHITE else BLACK
            instance._put(square.rank * 8 + square.file, _PIECE_CODE[piece.kind] * sign)
        instance.side = WHITE if board.turn is Color.WHITE else BLACK
        instance.castling = sum(_RIGHT_BITS[right] for right in board.castling_rights)
        instance.halfmove = board.halfmove_clock
        instance.key ^= _CASTLING_KEYS[instance.castling]
        if instance.side == BLACK:
            instance.key ^= _SIDE_KEY
        target = board.en_passant_target
        if target is not None:
            instance._set_en_passant(target.rank * 8 + target.file, instance.side)
        return instance

    def _put(self, square: int, piece: int) -> None:
        self.squares[square] = piece
        self.midgame += MIDGAME_TABLE[piece][square]
        self.endgame += ENDGAME_TABLE[piece][square]
        self.phase += PHASE_WEIGHT[piece]
        self.key ^= _PIECE_KEYS[piece][square]
        self.counts[piece] += 1
        if piece == PAWN or piece == -PAWN:
            self.pawn_key ^= _PIECE_KEYS[piece][square]
        if piece == KING or piece == -KING:
            self.kings[1 if piece > 0 else -1] = square

    def _set_en_passant(self, target: int, capturing_side: int) -> None:
        """Só registra o alvo se houver peão capaz de capturar, como `position_key` no motor.

        Sem isso, a posição logo depois de um avanço duplo teria chave diferente de outra idêntica
        em tudo, e a busca deixaria de reconhecer as repetições e transposições entre as duas.
        """
        pawn = capturing_side * PAWN
        squares = self.squares
        for origin in _PAWN_CAPTURES[-capturing_side][target]:
            if squares[origin] == pawn:
                self.en_passant = target
                self.key ^= _EN_PASSANT_KEYS[target]
                return

    def seed_history(self, keys: list[int]) -> None:
        """Informa as posições anteriores da partida, da mais antiga para a mais nova."""
        self._keys = list(keys)

    def in_check(self) -> bool:
        side = self.side
        return self.attacked(self.kings[side], -side)

    def attacked(self, square: int, by_side: int) -> bool:
        """Olha a partir da casa, nas linhas por onde um atacante poderia chegar: é mais barato que
        perguntar a cada peça inimiga, e para no primeiro atacante."""
        squares = self.squares
        knight = by_side * KNIGHT
        for origin in _KNIGHT_TARGETS[square]:
            if squares[origin] == knight:
                return True
        pawn = by_side * PAWN
        for origin in _PAWN_CAPTURES[-by_side][square]:
            if squares[origin] == pawn:
                return True
        if self.kings[by_side] in _KING_TARGETS[square]:
            return True
        queen = by_side * QUEEN
        rook = by_side * ROOK
        for ray in _ROOK_RAYS[square]:
            for origin in ray:
                occupant = squares[origin]
                if occupant:
                    if occupant == rook or occupant == queen:
                        return True
                    break
        bishop = by_side * BISHOP
        for ray in _BISHOP_RAYS[square]:
            for origin in ray:
                occupant = squares[origin]
                if occupant:
                    if occupant == bishop or occupant == queen:
                        return True
                    break
        return False

    def defended_by_pawn(self, square: int) -> bool:
        """Diz se um peão de quem não joga protege a casa: entrar nela com peça cara costuma ser perda."""
        side = self.side
        squares = self.squares
        pawn = -side * PAWN
        for origin in _PAWN_CAPTURES[side][square]:
            if squares[origin] == pawn:
                return True
        return False

    def generate_moves(self) -> list[int]:
        """Todas as jogadas pseudolegais do lado da vez."""
        squares = self.squares
        side = self.side
        moves: list[int] = []
        add = moves.append
        for origin, piece in enumerate(squares):
            kind = piece * side
            if kind <= 0:
                continue
            if kind == PAWN:
                self._add_pawn_moves(origin, moves)
            elif kind == KNIGHT or kind == KING:
                for target in _KNIGHT_TARGETS[origin] if kind == KNIGHT else _KING_TARGETS[origin]:
                    if squares[target] * side <= 0:
                        add(origin | target << TARGET_SHIFT)
            else:
                for ray in _SLIDER_RAYS[kind][origin]:
                    for target in ray:
                        occupant = squares[target]
                        if not occupant:
                            add(origin | target << TARGET_SHIFT)
                            continue
                        if occupant * side < 0:
                            add(origin | target << TARGET_SHIFT)
                        break
        if self.castling:
            self._add_castling_moves(moves)
        return moves

    def _add_pawn_moves(self, origin: int, moves: list[int]) -> None:
        squares = self.squares
        side = self.side
        promotes = origin >> 3 == _PAWN_LAST_STEP_RANK[side]
        ahead = origin + 8 * side
        if not squares[ahead]:
            if promotes:
                _add_promotions(origin, ahead, moves)
            else:
                moves.append(origin | ahead << TARGET_SHIFT)
                beyond = ahead + 8 * side
                if origin >> 3 == _PAWN_START_RANK[side] and not squares[beyond]:
                    moves.append(origin | beyond << TARGET_SHIFT | FLAG_DOUBLE_PUSH << FLAG_SHIFT)
        for target in _PAWN_CAPTURES[side][origin]:
            if squares[target] * side < 0:
                if promotes:
                    _add_promotions(origin, target, moves)
                else:
                    moves.append(origin | target << TARGET_SHIFT)
            elif target == self.en_passant:
                moves.append(origin | target << TARGET_SHIFT | FLAG_EN_PASSANT << FLAG_SHIFT)

    def _add_castling_moves(self, moves: list[int]) -> None:
        """A casa de chegada do rei fica para `try_make`, como em qualquer outra jogada de rei."""
        side = self.side
        squares = self.squares
        rook = side * ROOK
        checked = False
        for right, king_home, king_target, between, crossed in _CASTLES[side]:
            if not self.castling & right or squares[_ROOK_HOME[king_target]] != rook:
                continue
            if any(squares[square] for square in between):
                continue
            if not checked:
                if self.attacked(king_home, -side):
                    return
                checked = True
            if not self.attacked(crossed, -side):
                moves.append(king_home | king_target << TARGET_SHIFT | FLAG_CASTLING << FLAG_SHIFT)

    def generate_tactical_moves(self) -> list[int]:
        """Só capturas e promoções a dama: o que muda o material e por isso interessa à quiescence."""
        squares = self.squares
        side = self.side
        moves: list[int] = []
        add = moves.append
        for origin, piece in enumerate(squares):
            kind = piece * side
            if kind <= 0:
                continue
            if kind == PAWN:
                self._add_pawn_tactics(origin, moves)
            elif kind == KNIGHT or kind == KING:
                for target in _KNIGHT_TARGETS[origin] if kind == KNIGHT else _KING_TARGETS[origin]:
                    if squares[target] * side < 0:
                        add(origin | target << TARGET_SHIFT)
            else:
                for ray in _SLIDER_RAYS[kind][origin]:
                    for target in ray:
                        occupant = squares[target]
                        if occupant:
                            if occupant * side < 0:
                                add(origin | target << TARGET_SHIFT)
                            break
        return moves

    def _add_pawn_tactics(self, origin: int, moves: list[int]) -> None:
        squares = self.squares
        side = self.side
        queen_flag = FLAG_PROMOTE_QUEEN << FLAG_SHIFT if origin >> 3 == _PAWN_LAST_STEP_RANK[side] else 0
        if queen_flag and not squares[origin + 8 * side]:
            moves.append(origin | (origin + 8 * side) << TARGET_SHIFT | queen_flag)
        for target in _PAWN_CAPTURES[side][origin]:
            if squares[target] * side < 0:
                moves.append(origin | target << TARGET_SHIFT | queen_flag)
            elif target == self.en_passant:
                moves.append(origin | target << TARGET_SHIFT | FLAG_EN_PASSANT << FLAG_SHIFT)

    def has_legal_move(self) -> bool:
        in_check = self.in_check()
        for move in self.generate_moves():
            if self.try_make(move, in_check):
                self.unmake()
                return True
        return False

    def try_make(self, move: int, in_check: bool) -> bool:
        """Aplica a jogada pseudolegal. Se ela deixar o próprio rei em xeque, desfaz e devolve False.

        Fora de xeque, só pode expor o rei a peça alinhada com ele; o resto dispensa o teste de ataque,
        que é a parte cara. O próprio rei sempre precisa do teste, e o en passant também, porque tira
        duas peças da mesma fileira de uma vez.
        """
        side = self.side
        king = self.kings[side]
        origin = move & SQUARE_MASK
        must_verify = in_check or origin == king or _ALIGNED[king][origin] or move >> FLAG_SHIFT == FLAG_EN_PASSANT
        self.make(move)
        if must_verify and self.attacked(self.kings[side], -side):
            self.unmake()
            return False
        return True

    def make(self, move: int) -> None:
        """Aplica a jogada, atualizando em poucas contas as somas da avaliação e a chave da posição.

        Longa de propósito: é a função mais executada da busca, e cada chamada a mais custaria caro.
        """
        squares = self.squares
        origin = move & SQUARE_MASK
        target = move >> TARGET_SHIFT & SQUARE_MASK
        piece = squares[origin]
        captured = squares[target]
        key = self.key
        self._undo.append((move, captured, self.castling, self.en_passant, self.halfmove,
                           self.midgame, self.endgame, self.phase, self.pawn_key))
        self._keys.append(key)
        piece_keys = _PIECE_KEYS[piece]
        key ^= _SIDE_KEY ^ _EN_PASSANT_KEYS[self.en_passant] ^ piece_keys[origin] ^ piece_keys[target]
        midgame_values = MIDGAME_TABLE[piece]
        endgame_values = ENDGAME_TABLE[piece]
        midgame = self.midgame + midgame_values[target] - midgame_values[origin]
        endgame = self.endgame + endgame_values[target] - endgame_values[origin]
        squares[origin] = 0
        squares[target] = piece
        halfmove = self.halfmove + 1
        if captured:
            key ^= _PIECE_KEYS[captured][target]
            midgame -= MIDGAME_TABLE[captured][target]
            endgame -= ENDGAME_TABLE[captured][target]
            self.phase -= PHASE_WEIGHT[captured]
            self.counts[captured] -= 1
            halfmove = 0
            if captured == PAWN or captured == -PAWN:
                self.pawn_key ^= _PIECE_KEYS[captured][target]
        if piece == PAWN or piece == -PAWN:
            halfmove = 0
            self.pawn_key ^= piece_keys[origin] ^ piece_keys[target]
        rights = self.castling
        if rights:
            remaining = rights & _RIGHTS_KEPT[origin] & _RIGHTS_KEPT[target]
            if remaining != rights:
                key ^= _CASTLING_KEYS[rights] ^ _CASTLING_KEYS[remaining]
                self.castling = remaining
        side = self.side
        if piece == KING or piece == -KING:
            self.kings[side] = target
        self.en_passant = _NO_EN_PASSANT
        self.halfmove = halfmove
        self.midgame = midgame
        self.endgame = endgame
        self.key = key
        self.side = -side
        flag = move >> FLAG_SHIFT
        if flag:
            self._make_special(flag, origin, target, side)

    def _make_special(self, flag: int, origin: int, target: int, side: int) -> None:
        if flag >= FLAG_PROMOTE_KNIGHT:
            self._swap_piece(target, side * PAWN, side * (flag - _FLAG_TO_PROMOTED_KIND))
        elif flag == FLAG_DOUBLE_PUSH:
            self._set_en_passant((origin + target) >> 1, -side)
        elif flag == FLAG_EN_PASSANT:
            self._take(target - 8 * side, -side * PAWN)
        else:
            self._slide_rook(_ROOK_HOME[target], _ROOK_TARGET[target], side * ROOK)

    def _swap_piece(self, square: int, old: int, new: int) -> None:
        self.squares[square] = new
        self.midgame += MIDGAME_TABLE[new][square] - MIDGAME_TABLE[old][square]
        self.endgame += ENDGAME_TABLE[new][square] - ENDGAME_TABLE[old][square]
        self.key ^= _PIECE_KEYS[old][square] ^ _PIECE_KEYS[new][square]
        self.pawn_key ^= _PIECE_KEYS[old][square]
        self.phase += PHASE_WEIGHT[new]
        self.counts[old] -= 1
        self.counts[new] += 1

    def _take(self, square: int, piece: int) -> None:
        self.squares[square] = 0
        self.midgame -= MIDGAME_TABLE[piece][square]
        self.endgame -= ENDGAME_TABLE[piece][square]
        self.key ^= _PIECE_KEYS[piece][square]
        self.pawn_key ^= _PIECE_KEYS[piece][square]
        self.counts[piece] -= 1

    def _slide_rook(self, origin: int, target: int, rook: int) -> None:
        self.squares[origin] = 0
        self.squares[target] = rook
        self.midgame += MIDGAME_TABLE[rook][target] - MIDGAME_TABLE[rook][origin]
        self.endgame += ENDGAME_TABLE[rook][target] - ENDGAME_TABLE[rook][origin]
        self.key ^= _PIECE_KEYS[rook][origin] ^ _PIECE_KEYS[rook][target]

    def unmake(self) -> None:
        """Desfaz a última jogada. As somas e a chave voltam prontas: nada é recalculado."""
        (move, captured, self.castling, self.en_passant, self.halfmove,
         self.midgame, self.endgame, self.phase, self.pawn_key) = self._undo.pop()
        self.key = self._keys.pop()
        side = self.side = -self.side
        squares = self.squares
        origin = move & SQUARE_MASK
        target = move >> TARGET_SHIFT & SQUARE_MASK
        piece = squares[target]
        flag = move >> FLAG_SHIFT
        if flag >= FLAG_PROMOTE_KNIGHT:
            self.counts[piece] -= 1
            piece = side * PAWN
            self.counts[piece] += 1
        elif flag == FLAG_EN_PASSANT:
            squares[target - 8 * side] = -side * PAWN
            self.counts[-side * PAWN] += 1
        elif flag == FLAG_CASTLING:
            squares[_ROOK_HOME[target]] = side * ROOK
            squares[_ROOK_TARGET[target]] = 0
        squares[origin] = piece
        squares[target] = captured
        if captured:
            self.counts[captured] += 1
        if piece == KING or piece == -KING:
            self.kings[side] = origin

    def is_rule_draw(self) -> bool:
        """Empate pela regra dos 50 lances ou por repetição, contando as posições anteriores da partida.

        Basta a posição aparecer uma segunda vez para valer como empate: quem pode repetir uma vez
        pode repetir de novo, e isso poupa a busca de explorar o mesmo ciclo.
        """
        halfmove = self.halfmove
        if halfmove < _MIN_PLIES_TO_REPEAT:
            return False
        if halfmove >= _FIFTY_MOVES_IN_HALFMOVES:
            return True
        keys = self._keys
        key = self.key
        newest = len(keys) - _MIN_PLIES_TO_REPEAT
        oldest = max(len(keys) - halfmove, 0)
        for index in range(newest, oldest - 1, -2):
            if keys[index] == key:
                return True
        return False

    def has_no_pawns(self) -> bool:
        counts = self.counts
        return not counts[PAWN] and not counts[-PAWN]


def _add_promotions(origin: int, target: int, moves: list[int]) -> None:
    base = origin | target << TARGET_SHIFT
    for flag in range(FLAG_PROMOTE_KNIGHT, FLAG_PROMOTE_QUEEN + 1):
        moves.append(base | flag << FLAG_SHIFT)
