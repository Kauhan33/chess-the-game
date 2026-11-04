"""Notação algébrica padrão (SAN), a forma usual de escrever lances: Nf3, exd5, O-O, e8=Q+."""
from __future__ import annotations

from .board import Board
from .move import Move
from .rules import has_legal_moves, is_in_check, legal_moves
from .types import PieceType


def move_to_san(board: Board, move: Move) -> str:
    """Escreve a jogada em SAN. Deve ser chamada antes de a jogada ser aplicada no tabuleiro."""
    return _describe_move(board, move) + _check_suffix(board, move)


def _describe_move(board: Board, move: Move) -> str:
    if move.is_castling:
        return "O-O" if move.target.file > move.origin.file else "O-O-O"
    kind = board.piece_at(move.origin).kind
    capture = "x" if move.is_en_passant or board.piece_at(move.target) is not None else ""
    if kind is PieceType.PAWN:
        # Peão não tem letra; na captura, entra a coluna de origem.
        origin_file = move.origin.name[0] if capture else ""
        promotion = f"={move.promotion.symbol}" if move.promotion else ""
        return f"{origin_file}{capture}{move.target.name}{promotion}"
    return f"{kind.symbol}{_disambiguation(board, move, kind)}{capture}{move.target.name}"


def _disambiguation(board: Board, move: Move, kind: PieceType) -> str:
    """Indica a origem só quando outra peça igual também pode ir à mesma casa.

    A coluna tem preferência, depois a fileira, e por último a casa inteira. Só jogadas legais contam:
    uma peça cravada não pode ir até lá, então ela não cria ambiguidade.
    """
    rivals = [
        other.origin
        for other in legal_moves(board)
        if other.target == move.target and other.origin != move.origin and board.piece_at(other.origin).kind is kind
    ]
    if not rivals:
        return ""
    if all(origin.file != move.origin.file for origin in rivals):
        return move.origin.name[0]
    if all(origin.rank != move.origin.rank for origin in rivals):
        return move.origin.name[1]
    return move.origin.name


def _check_suffix(board: Board, move: Move) -> str:
    board.apply(move)
    suffix = ""
    if is_in_check(board):
        suffix = "+" if has_legal_moves(board) else "#"
    board.undo()
    return suffix
