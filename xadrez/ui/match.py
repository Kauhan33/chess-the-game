"""Opções de uma partida e formatação dos números que o jogador lê na tela."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from xadrez.core import Color, Difficulty, GameEngine, TimeControl

DEFAULT_WHITE_NAME = "Jogador 1"
DEFAULT_BLACK_NAME = "Jogador 2"
# Os mesmos valores que `xadrez.data.history` aceita em `opponent_kind`.
OPPONENT_LOCAL = "local"
OPPONENT_CPU = "cpu"
OPPONENT_NET = "rede"
# Clássica 30 vem antes de 15+10 porque esta é a ordem que o seletor percorre desde a versão 1.0.
TIME_CONTROLS = (
    ("Sem limite", TimeControl.UNLIMITED),
    ("Blitz 3+2", TimeControl.BLITZ_3_2),
    ("Blitz 5", TimeControl.BLITZ_5),
    ("Rápida 10+0", TimeControl.RAPID_10),
    ("Clássica 30", TimeControl.CLASSIC_30),
    ("Clássica 15+10", TimeControl.CLASSIC_15_10),
)
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_MINUTE = 60


class GameMode(Enum):
    """Treinamento mostra tudo; Partida só mostra o que aconteceu, nunca o que fazer."""

    TRAINING = ("Treinamento", "Mostra caminhos, capturas, ameaças e xeque enquanto você joga.")
    MATCH = ("Partida", "Sem dicas nem avisos de xeque, como em um torneio. Lance ilegal é recusado sem explicação.")

    def __new__(cls, label: str, description: str) -> GameMode:
        member = object.__new__(cls)
        member._value_ = label
        member.label = label
        member.description = description
        return member


@dataclass(frozen=True)
class MatchOptions:
    """O que o menu decide. Sobrevive à revanche e volta ao menu para não redigitar os nomes.

    `human_color` é a escolha do menu: `None` significa sorteio, que só é resolvido ao iniciar. Contra a
    CPU e em rede, `white_name` guarda o nome de quem joga neste computador, seja qual for a cor dele.
    """

    white_name: str = DEFAULT_WHITE_NAME
    black_name: str = DEFAULT_BLACK_NAME
    time_control: TimeControl = TimeControl.RAPID_10
    auto_rotate: bool = True
    mode: GameMode = GameMode.TRAINING
    opponent_kind: str = OPPONENT_LOCAL
    difficulty: Difficulty = Difficulty.EASY
    human_color: Color | None = Color.WHITE

    @property
    def is_local(self) -> bool:
        return self.opponent_kind == OPPONENT_LOCAL

    @property
    def cpu_name(self) -> str:
        return f"CPU ({self.difficulty.label})"

    def create_engine(self, fen: str | None = None, human_color: Color | None = None) -> GameEngine:
        """Contra a CPU, `human_color` é a cor já sorteada. Sem ela, vale a escolha do menu, e o padrão são as Brancas."""
        if self.opponent_kind != OPPONENT_CPU:
            return GameEngine(self.white_name, self.black_name, self.time_control, fen)
        color = human_color or self.human_color or Color.WHITE
        names = (self.white_name, self.cpu_name) if color is Color.WHITE else (self.cpu_name, self.white_name)
        return GameEngine(*names, self.time_control, fen)


def time_control_label(time_control: TimeControl) -> str:
    """Nome do tempo, como no menu. Um tempo fora da lista aparece como minutos e incremento."""
    for label, known in TIME_CONTROLS:
        if known == time_control:
            return label
    return f"{time_control.minutes:g}+{time_control.increment:g}".replace(".", ",")


def format_clock(seconds: float) -> str:
    """Relógio de jogo: 09:57, ou 1:02:33 acima de uma hora. Fração arredonda para cima, como em um relógio de torneio."""
    total = max(0, math.ceil(seconds - 1e-9))
    hours, remainder = divmod(total, _SECONDS_PER_HOUR)
    minutes, secs = divmod(remainder, _SECONDS_PER_MINUTE)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_points(points: float) -> str:
    """Placar da série em português: 1, 0,5 e 1,5."""
    return f"{points:g}".replace(".", ",")


def without_check_marks(san: str) -> str:
    """Lance sem `+` nem `#`, para a planilha não virar aviso de xeque no modo Partida."""
    return san.rstrip("+#")
