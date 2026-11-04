"""Motor de regras do xadrez em Python puro: não depende de pygame, numpy nem das outras camadas."""
from .board import STARTING_FEN, AppliedMove, Board
from .clock import ChessClock, TimeControl
from .engine import GameEngine
from .move import Move, MoveOutcome
from .notation import move_to_san
from .pieces import Bishop, King, Knight, Pawn, Piece, Queen, Rook, SlidingPiece
from .player import Player
from .rules import (
    has_insufficient_material,
    has_legal_moves,
    is_checkmate,
    is_in_check,
    is_stalemate,
    leaves_king_in_check,
    legal_en_passant_moves,
    legal_moves,
    legal_moves_from,
    perft,
    position_key,
)
from .types import Color, EndReason, GameResult, GameState, MoveError, PieceType, Square

__all__ = [
    "AppliedMove",
    "Bishop",
    "Board",
    "ChessClock",
    "Color",
    "EndReason",
    "GameEngine",
    "GameResult",
    "GameState",
    "King",
    "Knight",
    "Move",
    "MoveError",
    "MoveOutcome",
    "Pawn",
    "Piece",
    "PieceType",
    "Player",
    "Queen",
    "Rook",
    "STARTING_FEN",
    "SlidingPiece",
    "Square",
    "TimeControl",
    "has_insufficient_material",
    "has_legal_moves",
    "is_checkmate",
    "is_in_check",
    "is_stalemate",
    "leaves_king_in_check",
    "legal_en_passant_moves",
    "legal_moves",
    "legal_moves_from",
    "move_to_san",
    "perft",
    "position_key",
]
