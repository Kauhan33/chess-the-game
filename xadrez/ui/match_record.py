"""Traduz uma partida encerrada no registro do histórico, do ponto de vista de quem está logado."""
from __future__ import annotations

from datetime import datetime

from xadrez.core import Color, EndReason, GameEngine, GameResult, Player, game_to_pgn
from xadrez.data import DataError, HistoryStore, MatchRecord
from xadrez.data.history import OUTCOME_DRAW, OUTCOME_LOSS, OUTCOME_WIN
from xadrez.ui.match import OPPONENT_CPU, MatchOptions, time_control_label

SAVE_FAILED_MESSAGE = "A partida não entrou no histórico: não foi possível gravar neste computador."
ABANDONED_REASON = "Abandonou a partida"


def _reason_for(result: GameResult, color: Color) -> str:
    """O texto do motor, "Adversário desconectou", é de quem ficou. Quem saiu lê o que ele mesmo fez."""
    if result.reason is EndReason.ABANDONMENT and result.winner is not color:
        return ABANDONED_REASON
    return result.reason.label


def build_record(engine: GameEngine, options: MatchOptions, local_player: Player) -> MatchRecord:
    color = local_player.color
    winner = engine.result.winner
    outcome = OUTCOME_DRAW if winner is None else OUTCOME_WIN if winner is color else OUTCOME_LOSS
    return MatchRecord(
        played_at=datetime.now().isoformat(timespec="seconds"),
        opponent=engine.players[color.opposite].name,
        opponent_kind=options.opponent_kind,
        difficulty=options.difficulty.label if options.opponent_kind == OPPONENT_CPU else None,
        color=color.label,
        outcome=outcome,
        reason=_reason_for(engine.result, color),
        moves=(len(engine.history) + 1) // 2,
        seconds=round(sum(engine.clock.elapsed(player.color) for player in engine.players.values()), 1),
        time_control=time_control_label(engine.time_control),
        mode=options.mode.label,
        pgn=game_to_pgn(engine),
        final_fen=engine.final_fen,
    )


def save_match(store: HistoryStore, engine: GameEngine, options: MatchOptions, local_player: Player) -> str | None:
    """Grava a partida. Devolve o aviso para a tela se não conseguir: o histórico nunca atrapalha o jogo."""
    try:
        store.add(build_record(engine, options, local_player))
    except DataError:
        return SAVE_FAILED_MESSAGE
    return None
