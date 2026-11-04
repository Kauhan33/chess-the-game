"""Atalhos compartilhados pelos testes do motor."""
from xadrez.core import Square


class IndexLikeInteger:
    """Imita um inteiro do numpy: não herda de int, mas converte com `__index__`."""

    def __init__(self, value):
        self.value = value

    def __index__(self):
        return self.value


def sq(name):
    return Square.from_name(name)


def play_all(engine, *uci_moves):
    """Joga a sequência em notação UCI, falhando o teste na primeira jogada recusada."""
    outcome = None
    for uci in uci_moves:
        outcome = engine.play(sq(uci[:2]), sq(uci[2:4]))
        assert outcome.ok, f"{uci} recusada: {outcome.error}"
    return outcome


def target_names(moves):
    return {move.target.name for move in moves}
