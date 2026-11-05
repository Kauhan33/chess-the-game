"""Joga partidas de verdade entre os níveis da CPU e mostra se a força cresce com o nível (CT-74).

Para cada par de níveis, joga partidas com as cores alternadas e sementes fixas. No fim, imprime o
placar, o tempo médio e máximo por lance de cada nível e a profundidade alcançada no meio-jogo.

Uso: python tools/avaliar_cpu.py [--partidas 6] [--semente 1] [--max-segundos 0.5] [--pares easy-medium,hard-hardcore]
"""
from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xadrez.core import Color, Difficulty, GameEngine, GameResult, SearchReport, analyze

# Acima disso a partida é dada como empate. Os empates automáticos quase sempre chegam bem antes.
MAX_PLIES = 400
DEFAULT_PAIRS = "easy-medium,medium-hard,hard-hardcore"
MIDGAME_PLIES = range(16, 80)


@dataclass
class LevelStats:
    """Números acumulados de um nível em todas as partidas que jogou."""

    seconds: list[float] = field(default_factory=list)
    midgame_seconds: list[float] = field(default_factory=list)
    midgame_depths: list[int] = field(default_factory=list)
    nodes: int = 0

    def record(self, report: SearchReport, ply: int) -> None:
        self.seconds.append(report.seconds)
        self.nodes += report.nodes
        # Profundidade zero é lance único, respondido sem busca: não diz nada sobre o nível.
        if ply in MIDGAME_PLIES and report.depth:
            self.midgame_seconds.append(report.seconds)
            self.midgame_depths.append(report.depth)

    def summary(self) -> str:
        total = sum(self.seconds)
        moves = len(self.seconds)
        midgame = sum(self.midgame_seconds) / max(len(self.midgame_seconds), 1)
        depths = self.midgame_depths or [0]
        return (
            f"{moves:7} {total / moves:7.3f}s {max(self.seconds):7.3f}s {midgame:12.3f}s "
            f"{sum(depths) / len(depths):8.1f} {min(depths):3}-{max(depths):<3} {self.nodes / max(total, 1e-9):9.0f}"
        )


@dataclass
class PairScore:
    first: Difficulty
    second: Difficulty
    first_wins: int = 0
    second_wins: int = 0
    draws: int = 0
    plies: int = 0

    @property
    def games(self) -> int:
        return self.first_wins + self.second_wins + self.draws

    def record(self, result: GameResult | None, plies: int, first_is_white: bool) -> None:
        self.plies += plies
        winner = result.winner if result else None
        if winner is None:
            self.draws += 1
        elif (winner is Color.WHITE) == first_is_white:
            self.first_wins += 1
        else:
            self.second_wins += 1

    def summary(self) -> str:
        share = 100 * (self.first_wins + self.draws / 2) / self.games
        return (
            f"{self.first.label:9} x {self.second.label:9} {self.first_wins:3} - {self.draws:3} - {self.second_wins:3}"
            f"   ({share:5.1f}% para {self.first.label}, {self.plies / self.games:.0f} meios-lances em média)"
        )


def play_game(white: Difficulty, black: Difficulty, seed: int, max_seconds: float | None,
              stats: dict[Difficulty, LevelStats]) -> GameEngine:
    """Joga uma partida até o fim e devolve o motor, com o resultado e os lances."""
    engine = GameEngine(white.label, black.label)
    rng = random.Random(seed)
    while engine.result is None and len(engine.history) < MAX_PLIES:
        level = white if engine.turn is Color.WHITE else black
        report = analyze(engine.board, level, rng, max_seconds=max_seconds)
        stats[level].record(report, len(engine.history))
        outcome = engine.play(report.move.origin, report.move.target, report.move.promotion)
        if not outcome.ok:
            raise RuntimeError(f"CPU devolveu jogada ilegal: {report.move.uci} em {engine.final_fen}")
    return engine


def describe_result(engine: GameEngine) -> str:
    plies = len(engine.history)
    if engine.result is None:
        return f"1/2-1/2 em {plies} meios-lances, limite de lances"
    score = "1/2-1/2" if engine.result.winner is None else "1-0" if engine.result.winner is Color.WHITE else "0-1"
    return f"{score} em {plies} meios-lances, {engine.result.reason.label}"


def play_pair(score: PairScore, games: int, seed: int, max_seconds: float | None,
              stats: dict[Difficulty, LevelStats]) -> None:
    for game in range(games):
        first_is_white = game % 2 == 0
        white, black = (score.first, score.second) if first_is_white else (score.second, score.first)
        engine = play_game(white, black, seed + game, max_seconds, stats)
        score.record(engine.result, len(engine.history), first_is_white)
        print(f"  {white.label} (b) x {black.label} (p): {describe_result(engine)}", flush=True)


def parse_pairs(text: str) -> list[PairScore]:
    by_name = {level.label.lower(): level for level in Difficulty}
    pairs = []
    for item in text.split(","):
        first, second = item.strip().lower().split("-")
        pairs.append(PairScore(by_name[first], by_name[second]))
    return pairs


def print_report(scores: list[PairScore], stats: dict[Difficulty, LevelStats]) -> None:
    print("\nPlacar (vitórias do primeiro - empates - vitórias do segundo):")
    for score in scores:
        print(f"  {score.summary()}")
    print("\nTempo por lance e profundidade (meio-jogo: do 9º ao 40º lance):")
    headers = (f"{'lances':>7}", f"{'médio':>8}", f"{'máximo':>8}", f"{'meio-jogo':>13}", f"{'prof.':>8}", f"{'faixa':>7}", f"{'nós/s':>9}")
    print(f"  {'nível':9} {' '.join(headers)}")
    for level, level_stats in stats.items():
        if level_stats.seconds:
            print(f"  {level.label:9} {level_stats.summary()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--partidas", type=int, default=6, help="partidas por par de níveis")
    parser.add_argument("--semente", type=int, default=1)
    parser.add_argument("--max-segundos", type=float, default=None, help="teto por lance, para rodar mais rápido")
    parser.add_argument("--pares", default=DEFAULT_PAIRS, help="pares separados por vírgula, como easy-medium")
    options = parser.parse_args()

    stats = {level: LevelStats() for level in Difficulty}
    scores = parse_pairs(options.pares)
    for index, score in enumerate(scores):
        print(f"{score.first.label} x {score.second.label}", flush=True)
        play_pair(score, options.partidas, options.semente + 1000 * index, options.max_segundos, stats)
    print_report(scores, stats)


if __name__ == "__main__":
    main()
