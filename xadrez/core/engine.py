"""Motor da partida: fachada que a interface usa para jogar, sem conhecer os detalhes das regras."""
from __future__ import annotations

from collections import Counter

from .board import STARTING_FEN, AppliedMove, Board
from .clock import ChessClock, TimeControl
from .move import Move, MoveOutcome
from .notation import move_to_san
from .player import Player
from .rules import (
    has_insufficient_material,
    has_legal_moves,
    is_in_check,
    leaves_king_in_check,
    legal_en_passant_moves,
    legal_moves_from,
    position_key,
)
from .types import Color, EndReason, GameResult, GameState, MoveError, PieceType, Square, coerce_square

_REPETITIONS_FOR_DRAW = 3
_FIFTY_MOVES_IN_HALFMOVES = 100
_WIN_POINTS = 1.0
_DRAW_POINTS = 0.5


class GameEngine:
    def __init__(
        self,
        white_name: str = "Jogador 1",
        black_name: str = "Jogador 2",
        time_control: TimeControl = TimeControl.UNLIMITED,
        fen: str | None = None,
    ) -> None:
        self.time_control = time_control
        self.players = {
            Color.WHITE: Player(white_name, Color.WHITE),
            Color.BLACK: Player(black_name, Color.BLACK),
        }
        self._start_fen = STARTING_FEN if fen is None else fen
        self._begin_game()

    def _begin_game(self) -> None:
        """Monta uma partida nova com os mesmos jogadores; só o placar da série sobrevive."""
        self.board = Board.from_fen(self._start_fen)
        self.first_turn = self.board.turn
        self.clock = ChessClock(self.time_control)
        self.state = GameState.IN_PROGRESS
        self.result: GameResult | None = None
        self.history: list[str] = []
        self._last_applied: AppliedMove | None = None
        self._position_counts: Counter[str] = Counter()
        for player in self.players.values():
            player.captured.clear()
        self._record_position()
        self.result = self._detect_board_result()
        if self.result is not None:
            # Posição montada que já nasce encerrada: ninguém jogou, então ninguém ganha ponto.
            self.state = GameState.FINISHED

    @property
    def turn(self) -> Color:
        return self.board.turn

    @property
    def current_player(self) -> Player:
        return self.players[self.turn]

    @property
    def in_check(self) -> bool:
        return is_in_check(self.board)

    @property
    def checked_king_square(self) -> Square | None:
        return self.board.king_square(self.turn) if self.in_check else None

    @property
    def checking_pieces(self) -> list[Square]:
        return self.board.attackers_of(self.board.king_square(self.turn), self.turn.opposite)

    def legal_moves_from(self, square: Square) -> list[Move]:
        """Jogadas legais da casa, só para a peça da vez e com a partida em andamento.

        Uma promoção aparece como quatro jogadas para a mesma casa, uma para cada peça possível.
        """
        origin = coerce_square(square)
        if self.state is not GameState.IN_PROGRESS or origin is None:
            return []
        piece = self.board.piece_at(origin)
        if piece is None or piece.color is not self.turn:
            return []
        return legal_moves_from(self.board, origin)

    def is_promotion_move(self, origin: Square, target: Square) -> bool:
        """Diz se a jogada é uma promoção legal, para a interface abrir o diálogo de escolha."""
        destination = coerce_square(target)
        return any(
            move.promotion is not None and move.target == destination for move in self.legal_moves_from(origin)
        )

    def play(self, origin: Square, target: Square, promotion: PieceType | None = None) -> MoveOutcome:
        """Tenta executar a jogada. Entrada inválida vira `MoveOutcome` de erro e não altera nada."""
        if self.state is not GameState.IN_PROGRESS:
            return MoveOutcome(ok=False, error=MoveError.GAME_NOT_ACTIVE)
        move_or_error = self._resolve_move(origin, target, promotion)
        if isinstance(move_or_error, MoveError):
            return MoveOutcome(ok=False, error=move_or_error)
        return self._execute(move_or_error)

    def _resolve_move(self, origin: object, target: object, promotion: object) -> Move | MoveError:
        origin_square = coerce_square(origin)
        piece = None if origin_square is None else self.board.piece_at(origin_square)
        if piece is None:
            return MoveError.NO_PIECE
        if piece.color is not self.turn:
            return MoveError.NOT_YOUR_TURN
        target_square = coerce_square(target)
        candidates = [
            move for move in piece.pseudo_legal_moves(self.board, origin_square) if move.target == target_square
        ]
        if not candidates:
            return MoveError.ILLEGAL_MOVE
        # A segurança do rei vem antes da escolha da promoção: não adianta a interface perguntar
        # qual peça o jogador quer se o peão está cravado e a jogada será recusada de qualquer jeito.
        if leaves_king_in_check(self.board, candidates[0]):
            return MoveError.LEAVES_KING_IN_CHECK
        return _pick_promotion(candidates, promotion)

    def _execute(self, move: Move) -> MoveOutcome:
        mover = self.current_player
        san = move_to_san(self.board, move)
        applied = self.board.apply(move)
        self._last_applied = applied
        if applied.captured is not None:
            mover.captured.append(applied.captured.kind)
        self.clock.add_increment(mover.color)
        self.history.append(san)
        self._record_position()
        return MoveOutcome(
            ok=True,
            move=move,
            piece=applied.piece,
            captured=applied.captured,
            captured_square=applied.captured_square,
            rook_path=applied.rook_path,
            promoted_to=move.promotion,
            gives_check=is_in_check(self.board),
            result=self._finish_if_over(),
            san=san,
        )

    def _record_position(self) -> None:
        key = position_key(self.board)
        self._position_counts[key] += 1
        self._repetitions = self._position_counts[key]

    def _finish_if_over(self) -> GameResult | None:
        result = self._detect_board_result()
        if result is not None:
            self._finish(result)
        return result

    def _detect_board_result(self) -> GameResult | None:
        """Verifica o fim de jogo pela posição, nesta ordem de precedência.

        O mate vem antes de tudo: quem dá mate no lance que completaria os 50 lances ou a tripla
        repetição vence a partida, porque o mate encerra o jogo na hora.
        """
        board = self.board
        if not has_legal_moves(board):
            if is_in_check(board):
                return GameResult(board.turn.opposite, EndReason.CHECKMATE)
            return GameResult(None, EndReason.STALEMATE)
        if has_insufficient_material(board):
            return GameResult(None, EndReason.INSUFFICIENT_MATERIAL)
        if self._repetitions >= _REPETITIONS_FOR_DRAW:
            return GameResult(None, EndReason.THREEFOLD_REPETITION)
        if board.halfmove_clock >= _FIFTY_MOVES_IN_HALFMOVES:
            return GameResult(None, EndReason.FIFTY_MOVES)
        return None

    def _finish(self, result: GameResult) -> GameResult:
        """Encerra a partida. É o único lugar que dá pontos na série, e só passa aqui uma vez por partida."""
        if self.state is GameState.FINISHED:
            return self.result
        self.state = GameState.FINISHED
        self.result = result
        self._award_points(result, 1)
        return result

    def _award_points(self, result: GameResult, factor: int) -> None:
        if result.winner is None:
            for player in self.players.values():
                player.match_points += _DRAW_POINTS * factor
        else:
            self.players[result.winner].match_points += _WIN_POINTS * factor

    def threatened_pieces(self, color: Color) -> list[Square]:
        """Peças da cor atacadas por ao menos uma inimiga, sem contar o rei (ele já tem o xeque).

        O en passant entra à parte: o peão que acabou de avançar duas casas pode ser capturado sem
        que nenhuma peça ataque a casa dele, pois o inimigo vai para a casa que ele pulou.
        """
        enemy = color.opposite
        threatened = [
            square
            for square, piece in self.board.pieces(color)
            if piece.kind is not PieceType.KING and self.board.is_attacked(square, enemy)
        ]
        if self.turn is enemy:
            victims = {move.captured_square for move in legal_en_passant_moves(self.board)}
            threatened.extend(victims.difference(threatened))
        return threatened

    def attackers_of(self, square: Square) -> list[Square]:
        """Peças que atacam a casa: as inimigas da peça que está nela, ou as do adversário da vez se vazia."""
        target = coerce_square(square)
        if target is None:
            return []
        occupant = self.board.piece_at(target)
        defender = occupant.color if occupant else self.turn
        return self.board.attackers_of(target, defender.opposite)

    def pause(self) -> None:
        if self.state is GameState.IN_PROGRESS:
            self.state = GameState.PAUSED

    def resume(self) -> None:
        if self.state is GameState.PAUSED:
            self.state = GameState.IN_PROGRESS

    def tick(self, dt: float) -> GameResult | None:
        """Avança o relógio de quem joga. Devolve o resultado só no tique em que o tempo acabou."""
        if self.state is not GameState.IN_PROGRESS:
            return None
        self.clock.tick(self.turn, dt)
        if not self.clock.is_flagged(self.turn):
            return None
        return self._finish(self._timeout_result(self.turn))

    def _timeout_result(self, flagged: Color) -> GameResult:
        """Quem fica sem tempo perde, salvo se o adversário só tem o rei: sem peças, ele não poderia vencer."""
        opponent = flagged.opposite
        opponent_has_only_king = all(piece.kind is PieceType.KING for _, piece in self.board.pieces(opponent))
        return GameResult(None if opponent_has_only_king else opponent, EndReason.TIMEOUT)

    def resign(self, color: Color | None = None) -> GameResult:
        """Desistência de `color`, ou de quem está na vez. Sem efeito se a partida já acabou."""
        loser = color or self.turn
        return self._finish(GameResult(loser.opposite, EndReason.RESIGNATION))

    def agree_draw(self) -> GameResult:
        return self._finish(GameResult(None, EndReason.AGREEMENT))

    def finish_with(self, result: GameResult) -> GameResult:
        """Encerra com um resultado decidido fora daqui, como pela sala em rede. Partida já encerrada não muda."""
        return self._finish(result)

    def take_back_last_move(self) -> None:
        """Desfaz o último lance e reabre a partida, se foi ele que a encerrou. Só desfaz um lance por vez.

        É para o lance que cruzou com o fim da partida na rede, que é decidido em seguida: por isso o relógio fica como está.
        """
        applied = self._last_applied
        if applied is None:
            raise IndexError("Não há lance para desfazer")
        if self.result is not None:
            self._award_points(self.result, -1)
        self._position_counts[position_key(self.board)] -= 1
        self.board.undo()
        self._repetitions = self._position_counts[position_key(self.board)]
        self.history.pop()
        if applied.captured is not None:
            self.players[applied.piece.color].captured.pop()
        self.state = GameState.IN_PROGRESS
        self.result = None
        self._last_applied = None

    def abandon(self, color: Color) -> GameResult:
        """Quem abandona a partida (queda de rede) perde. Partida já encerrada não muda de resultado."""
        return self._finish(GameResult(color.opposite, EndReason.ABANDONMENT))

    @property
    def start_fen(self) -> str:
        """FEN de onde a partida começou, a base para refazer os lances do PGN."""
        return self._start_fen

    @property
    def final_fen(self) -> str:
        """FEN da posição atual: ao fim da partida, é a posição final guardada no histórico."""
        return self.board.to_fen()

    def restart(self) -> None:
        """Volta à posição de partida com as mesmas cores. A partida abandonada não soma pontos."""
        self._begin_game()

    def rematch(self) -> None:
        """Nova partida com as cores invertidas, mantendo o placar da série."""
        white, black = self.players[Color.WHITE], self.players[Color.BLACK]
        white.color, black.color = Color.BLACK, Color.WHITE
        self.players = {Color.WHITE: black, Color.BLACK: white}
        self._begin_game()

    def material_balance(self) -> int:
        """Diferença de material capturado: positivo favorece as brancas, negativo as pretas."""
        return self.players[Color.WHITE].material_score - self.players[Color.BLACK].material_score


def _pick_promotion(candidates: list[Move], promotion: object) -> Move | MoveError:
    """Separa as jogadas de promoção das demais pela peça escolhida."""
    is_promotion = candidates[0].promotion is not None
    if not is_promotion:
        return MoveError.ILLEGAL_MOVE if promotion is not None else candidates[0]
    if promotion is None:
        return MoveError.PROMOTION_REQUIRED
    for move in candidates:
        if move.promotion is promotion:
            return move
    return MoveError.ILLEGAL_MOVE
