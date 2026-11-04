"""Hierarquia de peças. Cada classe conhece só o próprio padrão de movimento.

As jogadas daqui são pseudolegais: seguem o padrão da peça, mas ainda não verificam se o próprio
rei fica em xeque. Esse filtro é de `rules.py`, porque a resposta é a mesma para todas as peças.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, NamedTuple, Sequence

from .move import Move
from .types import ALL_SQUARES, BOARD_SIZE, SQUARE_GRID, Color, PieceType, Square

if TYPE_CHECKING:
    from .board import Board

Offset = tuple[int, int]

ORTHOGONAL_DIRECTIONS: tuple[Offset, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL_DIRECTIONS: tuple[Offset, ...] = ((1, 1), (1, -1), (-1, 1), (-1, -1))
KNIGHT_JUMPS: tuple[Offset, ...] = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))

PAWN_FORWARD = {Color.WHITE: 1, Color.BLACK: -1}
PAWN_START_RANK = {Color.WHITE: 1, Color.BLACK: 6}
PAWN_PROMOTION_RANK = {Color.WHITE: 7, Color.BLACK: 0}
PROMOTION_KINDS = (PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT)

HOME_RANK = {Color.WHITE: 0, Color.BLACK: 7}
KING_HOME_FILE = 4


def _shifted(square: Square, offset: Offset) -> Square | None:
    file, rank = square[0] + offset[0], square[1] + offset[1]
    if 0 <= file < BOARD_SIZE and 0 <= rank < BOARD_SIZE:
        return SQUARE_GRID[file][rank]
    return None


def _ray(square: Square, direction: Offset) -> tuple[Square, ...]:
    squares = []
    current = _shifted(square, direction)
    while current is not None:
        squares.append(current)
        current = _shifted(current, direction)
    return tuple(squares)


def _jump_table(offsets: tuple[Offset, ...]) -> dict[Square, tuple[Square, ...]]:
    table = {}
    for square in ALL_SQUARES:
        targets = (_shifted(square, offset) for offset in offsets)
        table[square] = tuple(target for target in targets if target is not None)
    return table


def _pawn_advance_table(color: Color) -> dict[Square, tuple[Square, ...]]:
    """Casas à frente do peão, em ordem: uma, ou duas se ele ainda estiver na fileira inicial."""
    forward = PAWN_FORWARD[color]
    table = {}
    for square in ALL_SQUARES:
        steps = 2 if square.rank == PAWN_START_RANK[color] else 1
        ahead = (_shifted(square, (0, forward * step)) for step in range(1, steps + 1))
        table[square] = tuple(target for target in ahead if target is not None)
    return table


# Geometria calculada uma vez ao importar o módulo. As jogadas são geradas milhares de vezes por
# segundo, então consultar uma tabela evita repetir as contas e os testes de borda do tabuleiro.
_RAYS = {
    square: {direction: _ray(square, direction) for direction in ORTHOGONAL_DIRECTIONS + DIAGONAL_DIRECTIONS}
    for square in ALL_SQUARES
}
_KNIGHT_TARGETS = _jump_table(KNIGHT_JUMPS)
_KING_TARGETS = _jump_table(ORTHOGONAL_DIRECTIONS + DIAGONAL_DIRECTIONS)
_PAWN_ATTACKS = {color: _jump_table(((-1, PAWN_FORWARD[color]), (1, PAWN_FORWARD[color]))) for color in Color}
_PAWN_ADVANCES = {color: _pawn_advance_table(color) for color in Color}


class CastlingSide(NamedTuple):
    rook_file: int
    rook_target_file: int
    king_target_file: int
    files_between: tuple[int, ...]


_KINGSIDE = CastlingSide(rook_file=7, rook_target_file=5, king_target_file=6, files_between=(5, 6))
_QUEENSIDE = CastlingSide(rook_file=0, rook_target_file=3, king_target_file=2, files_between=(1, 2, 3))

# Para cada cor, a letra FEN do direito de roque e o lado do tabuleiro a que ela se refere.
CASTLING_SIDES = {
    Color.WHITE: {"K": _KINGSIDE, "Q": _QUEENSIDE},
    Color.BLACK: {"k": _KINGSIDE, "q": _QUEENSIDE},
}


def castling_rook_path(move: Move) -> tuple[Square, Square]:
    """Origem e destino da torre em um roque, deduzidos da casa onde o rei chega."""
    rank = move.target.rank
    side = _KINGSIDE if move.target.file == _KINGSIDE.king_target_file else _QUEENSIDE
    return SQUARE_GRID[side.rook_file][rank], SQUARE_GRID[side.rook_target_file][rank]


class Piece(ABC):
    """Peça de xadrez. Subclasses definem `kind` e as casas que atacam."""

    kind: ClassVar[PieceType]

    def __init__(self, color: Color) -> None:
        self.color = color

    @property
    def symbol(self) -> str:
        """Letra da peça em FEN: maiúscula para as brancas, minúscula para as pretas."""
        return self.kind.symbol if self.color is Color.WHITE else self.kind.symbol.lower()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.color.name})"

    @abstractmethod
    def attacks(self, board: Board, square: Square) -> Sequence[Square]:
        """Casas atacadas a partir de `square`, inclusive as ocupadas por peças da mesma cor."""

    def pseudo_legal_moves(self, board: Board, square: Square) -> list[Move]:
        """Por padrão a peça vai para qualquer casa que ataca, salvo as ocupadas pela própria cor."""
        moves = []
        for target in self.attacks(board, square):
            occupant = board.grid[target[0]][target[1]]
            if occupant is None or occupant.color is not self.color:
                moves.append(Move(square, target))
        return moves


class SlidingPiece(Piece):
    """Base das peças que deslizam em linha reta: torre, bispo e dama."""

    directions: ClassVar[tuple[Offset, ...]]

    def attacks(self, board: Board, square: Square) -> list[Square]:
        """Percorre cada direção até a primeira peça: é aqui que acontece a colisão de caminho.

        A casa da peça encontrada entra na lista porque ela é atacada (captura ou defesa). As casas
        atrás dela não entram, e é isso que impede a peça de atravessar outra.
        """
        grid = board.grid
        rays = _RAYS[square]
        attacked = []
        for direction in self.directions:
            for target in rays[direction]:
                attacked.append(target)
                if grid[target[0]][target[1]] is not None:
                    break
        return attacked


class Rook(SlidingPiece):
    kind = PieceType.ROOK
    directions = ORTHOGONAL_DIRECTIONS


class Bishop(SlidingPiece):
    kind = PieceType.BISHOP
    directions = DIAGONAL_DIRECTIONS


class Queen(SlidingPiece):
    kind = PieceType.QUEEN
    directions = ORTHOGONAL_DIRECTIONS + DIAGONAL_DIRECTIONS


class Knight(Piece):
    """O cavalo não herda de `SlidingPiece`: ele salta, então nenhuma peça bloqueia o caminho."""

    kind = PieceType.KNIGHT

    def attacks(self, board: Board, square: Square) -> tuple[Square, ...]:
        return _KNIGHT_TARGETS[square]


class King(Piece):
    kind = PieceType.KING

    def attacks(self, board: Board, square: Square) -> tuple[Square, ...]:
        return _KING_TARGETS[square]

    def pseudo_legal_moves(self, board: Board, square: Square) -> list[Move]:
        return super().pseudo_legal_moves(board, square) + self._castling_moves(board, square)

    def _castling_moves(self, board: Board, square: Square) -> list[Move]:
        """Roques possíveis, sem olhar a casa de chegada do rei.

        Rei em xeque ou passando por casa atacada violam uma regra própria do roque, por isso são
        recusados aqui. A casa de chegada fica para o filtro geral de `rules.py`: chegar nela sob
        ataque é igual a qualquer outra jogada que deixa o rei em xeque.
        """
        rank = HOME_RANK[self.color]
        sides = [side for right, side in CASTLING_SIDES[self.color].items() if right in board.castling_rights]
        if not sides or square != SQUARE_GRID[KING_HOME_FILE][rank]:
            return []
        if board.is_attacked(square, self.color.opposite):
            return []
        return [
            Move(square, SQUARE_GRID[side.king_target_file][rank], is_castling=True)
            for side in sides
            if self._can_castle_on(board, side, rank)
        ]

    def _can_castle_on(self, board: Board, side: CastlingSide, rank: int) -> bool:
        """A torre precisa estar lá, o caminho livre e a casa que o rei atravessa não pode estar atacada.

        A casa que o rei atravessa é a mesma onde a torre termina. No roque grande, b1/b8 precisa
        estar vazia, mas pode estar atacada: o rei não passa por ela.
        """
        rook = board.grid[side.rook_file][rank]
        if rook is None or rook.kind is not PieceType.ROOK or rook.color is not self.color:
            return False
        if any(board.grid[file][rank] is not None for file in side.files_between):
            return False
        return not board.is_attacked(SQUARE_GRID[side.rook_target_file][rank], self.color.opposite)


class Pawn(Piece):
    kind = PieceType.PAWN

    def attacks(self, board: Board, square: Square) -> tuple[Square, ...]:
        """O peão ataca na diagonal mesmo com a casa vazia: é o que impede o rei de pisar nela."""
        return _PAWN_ATTACKS[self.color][square]

    def pseudo_legal_moves(self, board: Board, square: Square) -> list[Move]:
        return self._advances(board, square) + self._captures(board, square)

    def _advances(self, board: Board, square: Square) -> list[Move]:
        moves = []
        for steps_taken, target in enumerate(_PAWN_ADVANCES[self.color][square]):
            if board.grid[target[0]][target[1]] is not None:
                break
            moves.extend(self._moves_to(square, target, is_double_push=steps_taken == 1))
        return moves

    def _captures(self, board: Board, square: Square) -> list[Move]:
        moves = []
        for target in _PAWN_ATTACKS[self.color][square]:
            occupant = board.grid[target[0]][target[1]]
            if occupant is not None and occupant.color is not self.color:
                moves.extend(self._moves_to(square, target))
            elif self._can_capture_en_passant(board, target):
                moves.append(Move(square, target, is_en_passant=True))
        return moves

    def _can_capture_en_passant(self, board: Board, target: Square) -> bool:
        """Compara a vez porque o alvo vale só para o lado que joga agora.

        Sem isso, um peão preto na 7ª fileira "capturaria" o alvo deixado pelas próprias pretas
        quando alguém consulta as jogadas de quem não está na vez.
        """
        return target == board.en_passant_target and self.color is board.turn

    def _moves_to(self, origin: Square, target: Square, is_double_push: bool = False) -> list[Move]:
        """Chegar à última fileira gera uma jogada por peça de promoção; não existe peão que fique lá."""
        if target.rank == PAWN_PROMOTION_RANK[self.color]:
            return [Move(origin, target, promotion=kind) for kind in PROMOTION_KINDS]
        return [Move(origin, target, is_double_push=is_double_push)]


PIECE_CLASSES: dict[PieceType, type[Piece]] = {
    piece_class.kind: piece_class for piece_class in (Pawn, Knight, Bishop, Rook, Queen, King)
}
_KIND_BY_LETTER = {kind.symbol: kind for kind in PieceType}


def piece_from_symbol(symbol: str) -> Piece | None:
    """Cria a peça da letra FEN (`P` branca, `p` preta). Devolve None para letra desconhecida."""
    kind = _KIND_BY_LETTER.get(symbol.upper())
    if kind is None:
        return None
    return PIECE_CLASSES[kind](Color.WHITE if symbol.isupper() else Color.BLACK)
