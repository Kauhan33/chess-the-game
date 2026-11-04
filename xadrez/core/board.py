"""Tabuleiro 8x8: guarda a posição, aplica e desfaz jogadas e lê e escreve FEN.

O tabuleiro não decide se uma jogada é legal: `apply` executa o que recebe. Quem filtra é
`rules.py`, usando `apply` e `undo` para testar a jogada sem copiar o tabuleiro inteiro.
"""
from __future__ import annotations

from typing import Iterator, NamedTuple

from .move import Move
from .pieces import (
    CASTLING_SIDES,
    HOME_RANK,
    KING_HOME_FILE,
    PAWN_FORWARD,
    PIECE_CLASSES,
    Piece,
    castling_rook_path,
    piece_from_symbol,
)
from .types import BOARD_SIZE, SQUARE_GRID, Color, PieceType, Square

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_NO_RIGHTS: frozenset[str] = frozenset()
_CASTLING_LETTERS = "KQkq"
_FEN_FIELD_COUNT = 6

# Toda jogada que sai de uma dessas casas ou chega nelas encerra os direitos listados: ou o rei ou a
# torre se moveu, ou a torre foi capturada na casa original. Um único mapa cobre os três casos.
_RIGHTS_LOST_AT = {
    Square(4, 0): frozenset("KQ"),
    Square(7, 0): frozenset("K"),
    Square(0, 0): frozenset("Q"),
    Square(4, 7): frozenset("kq"),
    Square(7, 7): frozenset("k"),
    Square(0, 7): frozenset("q"),
}

# Fileira do alvo de en passant deixado pelo avanço duplo de cada cor.
_EN_PASSANT_TARGET_RANK = {Color.WHITE: 2, Color.BLACK: 5}


class AppliedMove(NamedTuple):
    """Tudo o que `undo` precisa para voltar atrás e `GameEngine` precisa para relatar a jogada."""

    move: Move
    piece: Piece
    captured: Piece | None
    captured_square: Square | None
    rook_path: tuple[Square, Square] | None
    castling_rights: frozenset[str]
    en_passant_target: Square | None
    halfmove_clock: int
    fullmove_number: int


class Board:
    def __init__(self) -> None:
        self.grid: list[list[Piece | None]] = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.turn = Color.WHITE
        self.castling_rights = _NO_RIGHTS
        self.en_passant_target: Square | None = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        # O filtro de legalidade pergunta pelo rei a cada jogada testada; manter a casa dele
        # evita varrer o tabuleiro inteiro toda vez.
        self._king_squares: dict[Color, Square | None] = {Color.WHITE: None, Color.BLACK: None}
        self._applied: list[AppliedMove] = []

    @classmethod
    def initial(cls) -> Board:
        return cls.from_fen(STARTING_FEN)

    @classmethod
    def from_fen(cls, fen: str) -> Board:
        """Monta o tabuleiro a partir de um FEN. FEN malformado ou impossível levanta ValueError."""
        fields = str(fen).split()
        if len(fields) != _FEN_FIELD_COUNT:
            raise ValueError(f"FEN deve ter {_FEN_FIELD_COUNT} campos: {fen!r}")
        placement, turn, castling, en_passant, halfmove, fullmove = fields
        board = cls()
        _read_placement(board, placement)
        board.turn = _parse_turn(turn)
        board.castling_rights = _parse_castling(castling)
        board.en_passant_target = _parse_en_passant(en_passant)
        board.halfmove_clock = _parse_counter(halfmove, minimum=0, field="relógio de meio-lance")
        board.fullmove_number = _parse_counter(fullmove, minimum=1, field="número do lance")
        _validate_position(board)
        return board

    def to_fen(self) -> str:
        castling = "".join(letter for letter in _CASTLING_LETTERS if letter in self.castling_rights)
        en_passant = self.en_passant_target.name if self.en_passant_target else "-"
        turn = "w" if self.turn is Color.WHITE else "b"
        fields = (self._placement_fen(), turn, castling or "-", en_passant, self.halfmove_clock, self.fullmove_number)
        return " ".join(str(field) for field in fields)

    def _placement_fen(self) -> str:
        return "/".join(self._rank_fen(rank) for rank in reversed(range(BOARD_SIZE)))

    def _rank_fen(self, rank: int) -> str:
        text = ""
        empty_run = 0
        for column in self.grid:
            piece = column[rank]
            if piece is None:
                empty_run += 1
                continue
            text += f"{empty_run or ''}{piece.symbol}"
            empty_run = 0
        return text + str(empty_run or "")

    def piece_at(self, square: Square) -> Piece | None:
        """Devolve a peça da casa, ou None se a casa estiver vazia ou fora do tabuleiro."""
        file, rank = square
        if 0 <= file < BOARD_SIZE and 0 <= rank < BOARD_SIZE:
            return self.grid[file][rank]
        return None

    def place(self, square: Square, piece: Piece) -> None:
        self.remove(square)
        self.grid[square[0]][square[1]] = piece
        if piece.kind is PieceType.KING:
            self._king_squares[piece.color] = square

    def remove(self, square: Square) -> Piece | None:
        file, rank = square
        piece = self.grid[file][rank]
        if piece is None:
            return None
        self.grid[file][rank] = None
        if piece.kind is PieceType.KING:
            self._king_squares[piece.color] = None
        return piece

    def pieces(self, color: Color | None = None) -> Iterator[tuple[Square, Piece]]:
        """Percorre as peças de uma cor, ou todas se `color` for None."""
        for squares, column in zip(SQUARE_GRID, self.grid):
            for square, piece in zip(squares, column):
                if piece is not None and (color is None or piece.color is color):
                    yield square, piece

    def king_square(self, color: Color) -> Square | None:
        return self._king_squares[color]

    def is_attacked(self, square: Square, by_color: Color) -> bool:
        """Pergunta a cada peça se ela ataca a casa, e para na primeira que disser sim."""
        return any(square in piece.attacks(self, origin) for origin, piece in self.pieces(by_color))

    def attackers_of(self, square: Square, by_color: Color) -> list[Square]:
        return [origin for origin, piece in self.pieces(by_color) if square in piece.attacks(self, origin)]

    def apply(self, move: Move) -> AppliedMove:
        """Executa a jogada e empilha o necessário para desfazê-la. Não verifica legalidade."""
        piece = self.piece_at(move.origin)
        if piece is None:
            raise ValueError(f"Não há peça em {move.origin.name} para aplicar {move.uci}")
        captured_square = move.captured_square
        captured = self.remove(captured_square)
        rook_path = castling_rook_path(move) if move.is_castling else None
        applied = AppliedMove(
            move, piece, captured, captured_square if captured else None, rook_path,
            self.castling_rights, self.en_passant_target, self.halfmove_clock, self.fullmove_number,
        )
        self._move_pieces(move, piece, rook_path)
        self._update_state(move, piece, captured)
        self._applied.append(applied)
        return applied

    def _move_pieces(self, move: Move, piece: Piece, rook_path: tuple[Square, Square] | None) -> None:
        self.remove(move.origin)
        self.place(move.target, PIECE_CLASSES[move.promotion](piece.color) if move.promotion else piece)
        if rook_path is not None:
            self.place(rook_path[1], self.remove(rook_path[0]))

    def _update_state(self, move: Move, piece: Piece, captured: Piece | None) -> None:
        self.castling_rights = self._rights_after(move)
        # O alvo fica na casa que o peão pulou e vale só para o lance imediato do adversário: toda
        # jogada sobrescreve o valor anterior, e é isso que fecha a janela do en passant.
        self.en_passant_target = (
            Square(move.origin.file, (move.origin.rank + move.target.rank) // 2) if move.is_double_push else None
        )
        # Regra dos 50 lances: só peão movido ou captura zera o relógio, pois são irreversíveis.
        is_irreversible = piece.kind is PieceType.PAWN or captured is not None
        self.halfmove_clock = 0 if is_irreversible else self.halfmove_clock + 1
        if self.turn is Color.BLACK:
            self.fullmove_number += 1
        self.turn = self.turn.opposite

    def _rights_after(self, move: Move) -> frozenset[str]:
        if not self.castling_rights:
            return self.castling_rights
        lost_at_origin = _RIGHTS_LOST_AT.get(move.origin, _NO_RIGHTS)
        lost_at_target = _RIGHTS_LOST_AT.get(move.target, _NO_RIGHTS)
        return self.castling_rights - lost_at_origin - lost_at_target

    def undo(self) -> None:
        """Desfaz a última jogada, restaurando exatamente o estado anterior."""
        if not self._applied:
            raise IndexError("Não há jogada para desfazer")
        applied = self._applied.pop()
        move = applied.move
        self.remove(move.target)
        self.place(move.origin, applied.piece)
        if applied.captured is not None:
            self.place(applied.captured_square, applied.captured)
        if applied.rook_path is not None:
            self.place(applied.rook_path[0], self.remove(applied.rook_path[1]))
        self.castling_rights = applied.castling_rights
        self.en_passant_target = applied.en_passant_target
        self.halfmove_clock = applied.halfmove_clock
        self.fullmove_number = applied.fullmove_number
        self.turn = self.turn.opposite


def _read_placement(board: Board, placement: str) -> None:
    rows = placement.split("/")
    if len(rows) != BOARD_SIZE:
        raise ValueError(f"FEN deve descrever {BOARD_SIZE} fileiras: {placement!r}")
    for rank, row in zip(reversed(range(BOARD_SIZE)), rows):
        _read_rank(board, rank, row)


def _read_rank(board: Board, rank: int, row: str) -> None:
    file = 0
    for char in row:
        if char in "12345678":
            file += int(char)
            continue
        piece = piece_from_symbol(char)
        if piece is None:
            raise ValueError(f"Peça desconhecida no FEN: {char!r}")
        if file >= BOARD_SIZE:
            raise ValueError(f"Fileira do FEN com mais de {BOARD_SIZE} casas: {row!r}")
        board.place(Square(file, rank), piece)
        file += 1
    if file != BOARD_SIZE:
        raise ValueError(f"Fileira do FEN deve somar {BOARD_SIZE} casas: {row!r}")


def _parse_turn(turn: str) -> Color:
    if turn not in ("w", "b"):
        raise ValueError(f"Vez inválida no FEN: {turn!r}")
    return Color.WHITE if turn == "w" else Color.BLACK


def _parse_castling(castling: str) -> frozenset[str]:
    if castling == "-":
        return _NO_RIGHTS
    is_valid = all(letter in _CASTLING_LETTERS for letter in castling) and len(set(castling)) == len(castling)
    if not is_valid:
        raise ValueError(f"Direitos de roque inválidos no FEN: {castling!r}")
    return frozenset(castling)


def _parse_en_passant(en_passant: str) -> Square | None:
    return None if en_passant == "-" else Square.from_name(en_passant)


def _parse_counter(text: str, minimum: int, field: str) -> int:
    if not text.isascii() or not text.isdigit() or int(text) < minimum:
        raise ValueError(f"Valor inválido para {field} no FEN: {text!r}")
    return int(text)


def _validate_position(board: Board) -> None:
    """Recusa posições que quebrariam o motor depois, com erro claro já na leitura."""
    _validate_kings(board)
    _validate_pawn_ranks(board)
    _validate_castling_rights(board)
    _validate_en_passant(board)
    idle_king = board.king_square(board.turn.opposite)
    if board.is_attacked(idle_king, board.turn):
        raise ValueError("Posição impossível no FEN: o lado que não joga está em xeque")


def _validate_kings(board: Board) -> None:
    for color in Color:
        king_count = sum(piece.kind is PieceType.KING for _, piece in board.pieces(color))
        if king_count != 1:
            raise ValueError(f"FEN deve ter exatamente um rei de cada cor: {color.label} tem {king_count}")


def _validate_pawn_ranks(board: Board) -> None:
    for square, piece in board.pieces():
        is_last_or_first_rank = square.rank in (0, BOARD_SIZE - 1)
        if piece.kind is PieceType.PAWN and is_last_or_first_rank:
            raise ValueError(f"FEN com peão em {square.name}: peão não fica na primeira nem na última fileira")


def _validate_castling_rights(board: Board) -> None:
    for color, sides in CASTLING_SIDES.items():
        rank = HOME_RANK[color]
        for right, side in sides.items():
            has_pieces = _holds(board, KING_HOME_FILE, rank, PieceType.KING, color) and _holds(
                board, side.rook_file, rank, PieceType.ROOK, color
            )
            if right in board.castling_rights and not has_pieces:
                raise ValueError(f"Direito de roque {right!r} sem rei e torre nas casas originais")


def _validate_en_passant(board: Board) -> None:
    target = board.en_passant_target
    if target is None:
        return
    pushed_color = board.turn.opposite
    is_coherent = (
        target.rank == _EN_PASSANT_TARGET_RANK[pushed_color]
        and board.grid[target.file][target.rank] is None
        and _holds(board, target.file, target.rank + PAWN_FORWARD[pushed_color], PieceType.PAWN, pushed_color)
    )
    if not is_coherent:
        raise ValueError(f"Alvo de en passant incoerente no FEN: {target.name}")


def _holds(board: Board, file: int, rank: int, kind: PieceType, color: Color) -> bool:
    piece = board.grid[file][rank]
    return piece is not None and piece.kind is kind and piece.color is color
