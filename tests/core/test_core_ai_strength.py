"""CT-74: partidas de verdade entre os níveis. Se um nível não ganhar do anterior, o erro é do nível."""
import random

import pytest

from xadrez.core import Color, Difficulty, GameEngine, choose_move

# Só o Hardcore tem limite aqui, para o teste não levar horas: com 4 s por lance ele fica ainda mais forte.
HARDCORE_SECONDS = 0.25
MAX_PLIES = 300
# Com poucas partidas, o acaso pesa. O Hardcore limitado fez 92,7% em 48 partidas e, mesmo assim, já fez 5,5 de 8.
GAMES_PER_PAIR = 12
# Vencer de forma clara: pelo menos 3 de cada 4 pontos em jogo, com empate valendo meio ponto.
CLEAR_SHARE = 0.75


def play_game(white, black, seed):
    engine = GameEngine(white.label, black.label)
    rng = random.Random(seed)
    while engine.result is None and len(engine.history) < MAX_PLIES:
        level = white if engine.turn is Color.WHITE else black
        limit = HARDCORE_SECONDS if level is Difficulty.HARDCORE else None
        move = choose_move(engine.board, level, rng, max_seconds=limit)
        outcome = engine.play(move.origin, move.target, move.promotion)
        assert outcome.ok, f"{level.label} jogou {move.uci} em {engine.final_fen}"
    return engine


def points_of_stronger(stronger, weaker, games, seed):
    points = 0.0
    for game in range(games):
        stronger_is_white = game % 2 == 0
        white, black = (stronger, weaker) if stronger_is_white else (weaker, stronger)
        result = play_game(white, black, seed + game).result
        if result is None or result.winner is None:
            points += 0.5
        elif (result.winner is Color.WHITE) == stronger_is_white:
            points += 1
    return points


@pytest.mark.ct("CT-74")
@pytest.mark.slow
@pytest.mark.parametrize(
    "stronger, weaker",
    [
        (Difficulty.MEDIUM, Difficulty.EASY),
        (Difficulty.HARD, Difficulty.MEDIUM),
        (Difficulty.HARDCORE, Difficulty.HARD),
    ],
    ids=lambda level: level.label,
)
def test_each_level_clearly_beats_the_previous_one(stronger, weaker):
    points = points_of_stronger(stronger, weaker, GAMES_PER_PAIR, seed=1000)
    assert points >= CLEAR_SHARE * GAMES_PER_PAIR, f"{stronger.label} fez {points} de {GAMES_PER_PAIR}"
