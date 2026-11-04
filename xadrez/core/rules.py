"""Regras que dependem da posição inteira: legalidade, xeque, mate, afogamento e empates."""
from __future__ import annotations

from .board import Board
from .move import Move
from .pieces import Piece
from .types import Color, PieceType, Square

# Um único cavalo ou bispo, além dos reis, não consegue dar mate.
_LONE_MINOR_KINDS = (PieceType.BISHOP, PieceType.KNIGHT)


def is_in_check(board: Board, color: Color | None = None) -> bool:
    color = color or board.turn
    king = board.king_square(color)
    return king is not None and board.is_attacked(king, color.opposite)


def legal_moves(board: Board, color: Color | None = None) -> list[Move]:
    color = color or board.turn
    in_check = is_in_check(board, color)
    moves: list[Move] = []
    for square, piece in list(board.pieces(color)):
        moves.extend(_safe_moves_of(board, square, piece, in_check))
    return moves


def legal_moves_from(board: Board, square: Square) -> list[Move]:
    piece = board.piece_at(square)
    if piece is None:
        return []
    return _safe_moves_of(board, square, piece, is_in_check(board, piece.color))


def leaves_king_in_check(board: Board, move: Move) -> bool:
    """Testa a jogada de verdade: aplica, olha se o rei de quem jogou está atacado e desfaz."""
    color = board.piece_at(move.origin).color
    board.apply(move)
    exposed = is_in_check(board, color)
    board.undo()
    return exposed


def _safe_moves_of(board: Board, square: Square, piece: Piece, in_check: bool) -> list[Move]:
    """Remove das jogadas pseudolegais as que deixam o próprio rei em xeque.

    Testar toda jogada com `apply`/`undo` custaria caro, e a maioria não precisa disso. Com o rei fora
    de xeque, só pode expor o rei a jogada da peça alinhada com ele (na mesma coluna, fileira ou
    diagonal), pois é só nesse caso que ela pode estar cravada. Sobram para o teste completo o próprio
    rei e o en passant, que tira duas peças da mesma fileira de uma vez e por isso pode abrir uma
    linha mesmo com o peão que captura desalinhado.
    """
    moves = piece.pseudo_legal_moves(board, square)
    king = board.king_square(piece.color)
    if king is None:
        return moves
    can_expose_king = in_check or piece.kind is PieceType.KING or _is_aligned(square, king)
    return [
        move
        for move in moves
        if not (can_expose_king or move.is_en_passant) or not leaves_king_in_check(board, move)
    ]


def _is_aligned(square: Square, other: Square) -> bool:
    file_distance = abs(square[0] - other[0])
    rank_distance = abs(square[1] - other[1])
    return file_distance == 0 or rank_distance == 0 or file_distance == rank_distance


def has_legal_moves(board: Board) -> bool:
    """Para na primeira peça que tiver jogada, sem gerar as jogadas do lado inteiro."""
    in_check = is_in_check(board)
    return any(_safe_moves_of(board, square, piece, in_check) for square, piece in list(board.pieces(board.turn)))


def is_checkmate(board: Board) -> bool:
    return is_in_check(board) and not has_legal_moves(board)


def is_stalemate(board: Board) -> bool:
    return not is_in_check(board) and not has_legal_moves(board)


def has_insufficient_material(board: Board) -> bool:
    """Verdadeiro quando nenhuma sequência de jogadas pode terminar em mate.

    Cobre rei contra rei, rei e uma peça menor contra rei, e o caso geral em que só restam bispos
    em casas da mesma cor. Esse último inclui R+B x R+B e também dois bispos da mesma cor de casa:
    os bispos nunca atacam a outra cor, então o rei inimigo sempre tem fuga. Bispos em cores
    diferentes não entram, porque com ajuda do adversário eles conseguem dar mate.
    """
    others = [(square, piece) for square, piece in board.pieces() if piece.kind is not PieceType.KING]
    if not others:
        return True
    if len(others) == 1:
        return others[0][1].kind in _LONE_MINOR_KINDS
    only_bishops = all(piece.kind is PieceType.BISHOP for _, piece in others)
    return only_bishops and len({square.is_dark for square, _ in others}) == 1


def legal_en_passant_moves(board: Board) -> list[Move]:
    """Capturas en passant que o lado da vez pode fazer de fato agora."""
    if board.en_passant_target is None:
        return []
    return [move for move in legal_moves(board) if move.is_en_passant]


def position_key(board: Board) -> str:
    """Identifica a posição para a tripla repetição: peças, vez, direitos de roque e en passant.

    As regras tratam duas posições como iguais quando as jogadas possíveis são as mesmas. Depois de
    todo avanço duplo o FEN registra o alvo, mesmo sem peão capaz de capturar. Por isso o alvo só
    conta quando existe en passant legal: sem isso, a posição logo após o avanço nunca repetiria.
    """
    placement, turn, castling = board.to_fen().split(" ")[:3]
    en_passant = board.en_passant_target.name if legal_en_passant_moves(board) else "-"
    return f"{placement} {turn} {castling} {en_passant}"


def perft(board: Board, depth: int) -> int:
    """Conta as posições alcançáveis em `depth` meios-lances, a prova padrão de um gerador de jogadas.

    Os totais são conhecidos para posições de referência. Se o total confere, roque, en passant,
    promoção e cravadas estão certos, pois um único erro em qualquer um deles muda a contagem.
    """
    if depth <= 0:
        return 1
    moves = legal_moves(board)
    if depth == 1:
        return len(moves)
    total = 0
    for move in moves:
        board.apply(move)
        total += perft(board, depth - 1)
        board.undo()
    return total
