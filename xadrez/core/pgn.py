"""PGN: o formato de texto padrão para guardar uma partida, lido por qualquer programa de xadrez.

O arquivo tem cabeçalhos (`[White "Ana"]`) e depois os lances numerados em SAN. A SAN já vem pronta de
`GameEngine.history`. Aqui só entram a numeração, o resultado e os cabeçalhos.
"""
from __future__ import annotations

from datetime import date as calendar_date

from .board import STARTING_FEN, Board
from .clock import TimeControl
from .engine import GameEngine
from .types import Color, GameResult

_UNFINISHED = "*"
_DRAW = "1/2-1/2"
_WHITE_WINS = "1-0"
_BLACK_WINS = "0-1"
_NO_TIME_CONTROL = "-"
_UNKNOWN_TAG = "?"
_MAX_LINE_LENGTH = 80
_SECONDS_PER_MINUTE = 60
_BACKSLASH = "\\"


def game_to_pgn(engine: GameEngine, event: str = "Chess - The Game", date: str | None = None) -> str:
    """Escreve a partida em PGN. Em andamento, o resultado é `*`. Sem `date`, usa a data de hoje.

    O padrão pede a data como `AAAA.MM.DD`, então a forma ISO (`AAAA-MM-DD`) é convertida.
    """
    result = _result_text(engine.result)
    played_on = date if date is not None else calendar_date.today().isoformat()
    tags = [
        ("Event", event),
        ("Site", _UNKNOWN_TAG),
        ("Date", played_on.replace("-", ".")),
        ("Round", _UNKNOWN_TAG),
        ("White", engine.players[Color.WHITE].name),
        ("Black", engine.players[Color.BLACK].name),
        ("Result", result),
        ("TimeControl", _time_control_text(engine.time_control)),
    ]
    if engine.start_fen != STARTING_FEN:
        tags += [("SetUp", "1"), ("FEN", engine.start_fen)]
    header = "\n".join(f'[{name} "{_escaped(value)}"]' for name, value in tags)
    return f"{header}\n\n{_wrapped(_movetext(engine) + [result])}\n"


def _result_text(result: GameResult | None) -> str:
    if result is None:
        return _UNFINISHED
    if result.winner is None:
        return _DRAW
    return _WHITE_WINS if result.winner is Color.WHITE else _BLACK_WINS


def _time_control_text(time_control: TimeControl) -> str:
    """Forma do padrão PGN: segundos e, se houver, `+` incremento. Sem limite, um traço."""
    if time_control.is_unlimited:
        return _NO_TIME_CONTROL
    seconds = f"{time_control.minutes * _SECONDS_PER_MINUTE:g}"
    return f"{seconds}+{time_control.increment:g}" if time_control.increment else seconds


def _escaped(value: str) -> str:
    """Nome de jogador pode ter aspas ou barra, e quebra de linha desmontaria o cabeçalho."""
    single_line = " ".join(str(value).splitlines())
    return single_line.replace(_BACKSLASH, _BACKSLASH * 2).replace('"', _BACKSLASH + '"')


def _movetext(engine: GameEngine) -> list[str]:
    """Numera os lances. Se as pretas começam, o primeiro lance usa a forma `5...`, exigida pelo padrão."""
    start = Board.from_fen(engine.start_fen)
    number = start.fullmove_number
    tokens = []
    is_white_turn = start.turn is Color.WHITE
    for index, san in enumerate(engine.history):
        if is_white_turn:
            tokens.append(f"{number}. {san}")
        elif index == 0:
            tokens.append(f"{number}... {san}")
        else:
            tokens.append(san)
        if not is_white_turn:
            number += 1
        is_white_turn = not is_white_turn
    return tokens


def _wrapped(tokens: list[str]) -> str:
    lines = []
    current = ""
    for token in tokens:
        candidate = f"{current} {token}" if current else token
        if len(candidate) > _MAX_LINE_LENGTH:
            lines.append(current)
            candidate = token
        current = candidate
    lines.append(current)
    return "\n".join(lines)
