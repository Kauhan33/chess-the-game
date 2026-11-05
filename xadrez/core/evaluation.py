"""Avaliação estática usada pela CPU: material, tabelas de posição (piece-square) e estrutura de peões.

Dá uma nota à posição sem olhar lances futuros. As tabelas dizem quanto cada peça vale em cada casa:
cavalo no centro vale mais que na borda, peão vale mais perto de promover. Elas seguem a ideia da
"Simplified Evaluation Function", de Tomasz Michniewski, com valores ajustados aqui.

O rei precisa de dois comportamentos opostos: esconder-se no meio-jogo e ir para o centro no final.
Por isso há uma tabela de cada fase, e a nota final é a mistura das duas conforme o material em jogo
(avaliação "afilada"). `SearchBoard` mantém as duas somas ao aplicar cada jogada, então avaliar um nó
não precisa percorrer o tabuleiro, e é isso que torna a avaliação barata em Python puro.

A estrutura de peões precisa olhar um peão em relação aos outros, o que nenhuma tabela expressa. Como
os peões mudam pouco de um nó para outro, a nota fica guardada pela chave deles e quase nunca é refeita.
Em 284 partidas a 0,15 s por lance entre a versão com e sem esse termo, a com ele fez 55,6% dos pontos.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .search_board import SearchBoard

WHITE, BLACK = 1, -1
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = 1, 2, 3, 4, 5, 6
_PIECE_CODES = (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING)

_SQUARE_COUNT = 64
_FILES_PER_RANK = 8

# Centésimos de peão. O peão vale mais no final porque cada um deles ameaça virar dama.
_MIDGAME_VALUE = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900, KING: 0}
_ENDGAME_VALUE = {PAWN: 120, KNIGHT: 300, BISHOP: 320, ROOK: 520, QUEEN: 920, KING: 0}

MAX_PHASE = 24
_PHASE_WEIGHT = {KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4}

_BISHOP_PAIR_BONUS = 30
# Peão passado: nenhum peão inimigo na frente, nem nas colunas vizinhas. Índice: fileiras já avançadas.
_PASSED_MIDGAME = (0, 0, 5, 10, 20, 35, 60, 0)
_PASSED_ENDGAME = (0, 10, 15, 30, 50, 80, 120, 0)
# Peão isolado, sem vizinho para protegê-lo, e peão dobrado, que atrapalha o outro da mesma coluna.
_ISOLATED_MIDGAME, _ISOLATED_ENDGAME = 10, 15
_DOUBLED_MIDGAME, _DOUBLED_ENDGAME = 5, 10
# Quem está na vez costuma ter uma pequena vantagem: a avaliação reconhece isso para não oscilar a
# cada lance entre profundidades pares e ímpares.
_TEMPO_BONUS = 10

# Nas tabelas abaixo, a primeira linha é a 8ª fileira e a coluna da esquerda é a coluna a, como no
# tabuleiro visto pelas brancas. As pretas usam a mesma tabela espelhada.
_PAWN_MIDGAME = (
      0,   0,   0,   0,   0,   0,   0,   0,
     50,  50,  50,  50,  50,  50,  50,  50,
     10,  10,  20,  30,  30,  20,  10,  10,
      5,   5,  10,  25,  25,  10,   5,   5,
      0,   0,   0,  20,  20,   0,   0,   0,
      5,  -5, -10,   0,   0, -10,  -5,   5,
      5,  10,  10, -20, -20,  10,  10,   5,
      0,   0,   0,   0,   0,   0,   0,   0,
)
# No final, peão avançado é quase peça nova: o valor cresce cada vez mais rápido até a promoção.
_PAWN_ENDGAME = (
      0,   0,   0,   0,   0,   0,   0,   0,
     90,  90,  90,  90,  90,  90,  90,  90,
     55,  55,  55,  55,  55,  55,  55,  55,
     30,  30,  30,  30,  30,  30,  30,  30,
     15,  15,  15,  15,  15,  15,  15,  15,
      5,   5,   5,   5,   5,   5,   5,   5,
      5,   5,   5,   5,   5,   5,   5,   5,
      0,   0,   0,   0,   0,   0,   0,   0,
)
_KNIGHT = (
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
)
_BISHOP = (
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
)
_ROOK = (
      0,   0,   0,   0,   0,   0,   0,   0,
      5,  10,  10,  10,  10,  10,  10,   5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
      0,   0,   0,   5,   5,   0,   0,   0,
)
_QUEEN = (
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20,
)
_KING_MIDGAME = (
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20,
)
_KING_ENDGAME = (
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
)

_MIDGAME_SHAPE = {
    PAWN: _PAWN_MIDGAME, KNIGHT: _KNIGHT, BISHOP: _BISHOP, ROOK: _ROOK, QUEEN: _QUEEN, KING: _KING_MIDGAME,
}
_ENDGAME_SHAPE = {
    PAWN: _PAWN_ENDGAME, KNIGHT: _KNIGHT, BISHOP: _BISHOP, ROOK: _ROOK, QUEEN: _QUEEN, KING: _KING_ENDGAME,
}


def _by_piece_code(values: dict[int, object], empty: object, black_of) -> list:
    """Monta uma lista indexada pelo código da peça, positivo para as brancas e negativo para as pretas.

    O índice negativo do Python é o que faz isso funcionar: com 13 posições, `lista[-3]` é a décima
    primeira. Assim, branca e preta usam a mesma expressão, sem nenhum `if` no caminho mais executado.
    """
    table = [empty] * (2 * KING + 1)
    for code, value in values.items():
        table[code] = value
        table[-code] = black_of(value)
    return table


def _square_values(shape: tuple[int, ...], base: int) -> list[int]:
    """Converte a tabela visual para o índice `fileira * 8 + coluna`, com a1 = 0 e h8 = 63."""
    return [shape[(_FILES_PER_RANK - 1 - square // 8) * 8 + square % 8] + base for square in range(_SQUARE_COUNT)]


def _mirrored_negative(values: list[int]) -> list[int]:
    """Para as pretas, a nota troca de sinal e a fileira se inverte: a 2ª delas é a 7ª das brancas."""
    return [-values[square ^ 56] for square in range(_SQUARE_COUNT)]


def _piece_square_table(shapes: dict[int, tuple[int, ...]], bases: dict[int, int]) -> list:
    white = {code: _square_values(shapes[code], bases[code]) for code in _PIECE_CODES}
    return _by_piece_code(white, [0] * _SQUARE_COUNT, _mirrored_negative)


MIDGAME_TABLE = _piece_square_table(_MIDGAME_SHAPE, _MIDGAME_VALUE)
ENDGAME_TABLE = _piece_square_table(_ENDGAME_SHAPE, _ENDGAME_VALUE)
PHASE_WEIGHT = _by_piece_code(_PHASE_WEIGHT, 0, lambda weight: weight)


def _square_mask(files: range, ranks: range) -> int:
    return sum(1 << (rank * 8 + file) for rank in ranks for file in files if 0 <= file < 8)


# Conjuntos de casas como bits de um inteiro: testar "há peão inimigo aqui?" vira um único `&`.
_FILE_MASKS = [_square_mask(range(file, file + 1), range(8)) for file in range(8)]
_NEIGHBOR_FILE_MASKS = [
    _square_mask(range(file - 1, file), range(8)) | _square_mask(range(file + 1, file + 2), range(8))
    for file in range(8)
]
# Indexada pelo lado: `tabela[1]` é das brancas e `tabela[-1]`, o último elemento, das pretas.
_PASSED_SPAN = [
    None,
    [_square_mask(range(square % 8 - 1, square % 8 + 2), range(square // 8 + 1, 8)) for square in range(_SQUARE_COUNT)],
    [_square_mask(range(square % 8 - 1, square % 8 + 2), range(0, square // 8)) for square in range(_SQUARE_COUNT)],
]


def _score_pawn_side(squares: list[int], own: int, enemy: int, side: int) -> tuple[int, int]:
    midgame = endgame = 0
    for square in squares:
        file = square % 8
        if not enemy & _PASSED_SPAN[side][square]:
            advanced = square // 8 if side == WHITE else 7 - square // 8
            midgame += _PASSED_MIDGAME[advanced]
            endgame += _PASSED_ENDGAME[advanced]
        if not own & _NEIGHBOR_FILE_MASKS[file]:
            midgame -= _ISOLATED_MIDGAME
            endgame -= _ISOLATED_ENDGAME
        if (own & _FILE_MASKS[file]).bit_count() > 1:
            midgame -= _DOUBLED_MIDGAME
            endgame -= _DOUBLED_ENDGAME
    return midgame, endgame


def _score_pawn_structure(board: SearchBoard) -> tuple[int, int]:
    """Soma do meio-jogo e do final, pelo ponto de vista das brancas. Só roda quando os peões mudam."""
    white = [square for square, piece in enumerate(board.squares) if piece == PAWN]
    black = [square for square, piece in enumerate(board.squares) if piece == -PAWN]
    white_mask = sum(1 << square for square in white)
    black_mask = sum(1 << square for square in black)
    white_midgame, white_endgame = _score_pawn_side(white, white_mask, black_mask, WHITE)
    black_midgame, black_endgame = _score_pawn_side(black, black_mask, white_mask, BLACK)
    return white_midgame - black_midgame, white_endgame - black_endgame


def evaluate(board: SearchBoard) -> int:
    """Nota da posição em centésimos de peão, do ponto de vista de quem está na vez."""
    phase = board.phase
    if phase <= 1 and board.has_no_pawns():
        # Rei contra rei, ou rei e uma peça menor contra rei: ninguém consegue dar mate.
        return 0
    if phase > MAX_PHASE:
        phase = MAX_PHASE
    structure = board.pawn_cache.get(board.pawn_key)
    if structure is None:
        structure = board.pawn_cache[board.pawn_key] = _score_pawn_structure(board)
    blended = (board.midgame + structure[0]) * phase + (board.endgame + structure[1]) * (MAX_PHASE - phase)
    counts = board.counts
    if counts[BISHOP] >= 2:
        blended += _BISHOP_PAIR_BONUS * MAX_PHASE
    if counts[-BISHOP] >= 2:
        blended -= _BISHOP_PAIR_BONUS * MAX_PHASE
    # O lado entra antes da divisão inteira: como ela arredonda para baixo, dividir antes daria notas
    # diferentes para a mesma posição vista pelas brancas e pelas pretas.
    return blended * board.side // MAX_PHASE + _TEMPO_BONUS
