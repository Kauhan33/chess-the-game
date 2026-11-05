"""CPU adversária: negamax com poda alfa-beta, quiescence e aprofundamento iterativo.

A mesma busca serve aos quatro níveis, e o que muda entre eles é só a tabela `_LEVELS`: profundidade,
ruído na nota dos lances, tempo e as técnicas seletivas que só o Hardcore usa.

Ideias principais, na ordem em que aparecem na busca:

- Negamax: a nota de um lance para mim é o negativo da nota para o adversário, então um único código
  serve aos dois lados.
- Poda alfa-beta: `alpha` é o que já tenho garantido e `beta` é o que o adversário permite. Passou de
  `beta`, o adversário nunca deixaria chegar aqui, e o resto dos lances pode ser ignorado.
- Ordenação: a poda só corta muito se os melhores lances vierem primeiro. Por isso vêm antes o lance
  da tabela de transposição, as capturas (MVV-LVA: maior vítima com o menor atacante), as promoções,
  e depois os lances que já causaram corte em posições parecidas.
- Quiescence: ao chegar na profundidade limite, continua só pelas capturas. Sem isso, a busca pararia
  no meio de uma troca e acharia que ganhou uma peça que será recapturada no lance seguinte.
- Aprofundamento iterativo: busca 1, 2, 3... lances. O resultado de cada volta ordena a seguinte, e
  sempre há uma resposta pronta quando o tempo acaba ou a busca é cancelada.
- Tabela de transposição: a mesma posição aparece por caminhos diferentes, e a nota dela só é
  calculada uma vez. Vive só durante a chamada, o que mantém `choose_move` sem estado.

Só o Hardcore é seletivo: estende a busca em xeque, reduz lances tardios e corta pela avaliação estática.
Cada técnica foi medida em partidas entre a versão com e a versão sem ela, a 0,15 s por lance:

- Ficaram: tabela de transposição (60,9% dos pontos em 64 partidas), corte estático (56,6% em 144) e
  redução de lances tardios (53,9% em 64).
- Saíram por não mostrar ganho: "null move" (47,4% em 232, parte a 0,3 s, e a mesma profundidade em 4 s)
  e poda de futilidade (49,3% em 144). Menos código para defender e sem risco de errar em zugzwang.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .board import Board
from .evaluation import QUEEN, evaluate
from .move import Move
from .rules import legal_moves
from .search_board import (
    FLAG_DOUBLE_PUSH,
    FLAG_EN_PASSANT,
    FLAG_PROMOTE_QUEEN,
    FLAG_SHIFT,
    FROM_TO_MASK,
    MOVE_MASK,
    SQUARE_MASK,
    TARGET_SHIFT,
    SearchBoard,
    encode_move,
)

_INFINITY = 1_000_000
_MATE = 100_000
# Daqui para cima, em valor absoluto, a nota é de mate: `_MATE - n`, com n meios-lances até ele.
_MATE_THRESHOLD = _MATE - 1_000
_DRAW = 0

# Limite de segurança da recursão: uma sequência de xeques estendidos não pode crescer sem fim.
_MAX_PLY = 96
_UNLIMITED_DEPTH = 64

# Consultar o relógio e o cancelamento a cada 64 nós mantém o custo desprezível e a resposta em milissegundos.
_POLL_MASK = 63

_EXACT, _LOWER_BOUND, _UPPER_BOUND = 0, 1, 2

# Faixas da ordenação. A nota de cada lance é combinada com ele num único inteiro, para ordenar sem criar tuplas.
_MOVE_BITS = 15
_HISTORY_LIMIT = (1 << 20) - 1
_SECOND_KILLER_SCORE = 1 << 20
_FIRST_KILLER_SCORE = _SECOND_KILLER_SCORE + 1
_CAPTURE_SCORE = 1 << 21
_HASH_MOVE_SCORE = 1 << 24

# Valor das peças para a ordenação e a quiescence, indexado pelo código da peça (negativo nas pretas).
_PAWN_VALUE = 100
_PIECE_VALUE = [0, _PAWN_VALUE, 320, 330, 500, 900, 20_000, 20_000, 900, 500, 330, 320, _PAWN_VALUE]
_VICTIM_WEIGHT = 16
# Ganho que a marca da jogada acrescenta: en passant tira um peão, e a promoção a dama troca peão por dama.
_FLAG_GAIN = [0] * (FLAG_PROMOTE_QUEEN + 1)
_FLAG_GAIN[FLAG_EN_PASSANT] = _PAWN_VALUE
_FLAG_GAIN[FLAG_PROMOTE_QUEEN] = _PIECE_VALUE[QUEEN] - _PAWN_VALUE

# Poda delta: nem ganhar esta peça, com esta folga, alcançaria alpha.
_DELTA_MARGIN = 200

# Técnicas seletivas do Hardcore: cortam ramos que quase nunca importam para ir mais fundo no resto.
_REDUCTION_MIN_DEPTH = 3
_REDUCTION_MIN_MOVE_NUMBER = 4
_DEEP_REDUCTION_MOVE_NUMBER = 12
_STATIC_CUTOFF_MARGIN_PER_DEPTH = 100
_STATIC_CUTOFF_MAX_DEPTH = 3
# As técnicas seletivas podem esconder um mate curto por umas voltas. Com esta folga, ele aparece antes de parar.
_SELECTIVE_MATE_SLACK = 2

# Por quantos lances da partida o Hardcore ainda sorteia entre lances quase iguais.
_OPENING_FULL_MOVES = 8


class Difficulty(Enum):
    EASY = ("Easy", "Enxerga só um lance e erra com frequência. Bom para quem está começando.")
    MEDIUM = ("Medium", "Calcula dois lances e não entrega peça à toa, mas erra na posição.")
    HARD = ("Hard", "Calcula três lances e não erra de propósito. Exige atenção a cada jogada.")
    HARDCORE = ("Hardcore", "Pensa cerca de 4 segundos por lance, o máximo que a CPU consegue.")

    def __new__(cls, label: str, description: str) -> Difficulty:
        member = object.__new__(cls)
        member._value_ = label
        member.label = label
        member.description = description
        return member


@dataclass(frozen=True)
class _Level:
    """O que distingue um nível do outro. Margens e ruído em centésimos de peão."""

    max_depth: int
    noise: int = 0
    tie_margin: int = 0
    opening_margin: int = 0
    seconds: float | None = None
    # Limitar por nós, e não por tempo, mantém o nível determinístico com semente em qualquer máquina.
    node_limit: int | None = None
    uses_quiescence: bool = True
    is_selective: bool = False


_LEVELS = {
    Difficulty.EASY: _Level(max_depth=1, noise=300, uses_quiescence=False),
    Difficulty.MEDIUM: _Level(max_depth=2, noise=40, node_limit=30_000),
    Difficulty.HARD: _Level(max_depth=3, tie_margin=10, node_limit=90_000),
    Difficulty.HARDCORE: _Level(max_depth=_UNLIMITED_DEPTH, opening_margin=20, seconds=4.0, is_selective=True),
}


@dataclass(frozen=True)
class SearchReport:
    """Resultado da busca, com os números que as ferramentas de avaliação usam."""

    move: Move
    score: int
    depth: int
    nodes: int
    seconds: float


class _SearchStopped(Exception):
    """Sai da recursão de uma vez. O `SearchBoard` fica no meio da busca, mas ele é descartado."""


class _Search:
    def __init__(self, board: SearchBoard, level: _Level, margin: int,
                 should_stop: Callable[[], bool] | None, deadline: float) -> None:
        self.board = board
        self.level = level
        self.is_selective = level.is_selective
        self.uses_quiescence = level.uses_quiescence
        self.spread = _root_spread(level.noise, margin)
        self.should_stop = should_stop
        self.deadline = deadline
        self.node_limit = level.node_limit if level.node_limit is not None else float("inf")
        self.nodes = 0
        self.completed_depth = 0
        self.candidates: list[tuple[int, int]] = []
        self.table: dict[int, tuple[int, int, int, int]] = {}
        self.killers = [[0, 0] for _ in range(_MAX_PLY + 2)]
        self.history = [0] * (FROM_TO_MASK + 1)

    def run(self, root_moves: list[int]) -> None:
        """Aprofundamento iterativo. Se for interrompido, fica com a última resposta que confia."""
        moves = self._ordered(root_moves, 0, 0)
        partial: list[tuple[int, int]] = []
        try:
            self._raise_if_stopped()
            for depth in range(1, self.level.max_depth + 1):
                partial = []
                moves = self._search_root(moves, depth, partial)
                self.candidates = partial
                self.completed_depth = depth
                slack = _SELECTIVE_MATE_SLACK if self.is_selective else 0
                if _is_settled_mate(partial, depth - slack):
                    break
        except _SearchStopped:
            self._adopt_partial_iteration(partial)
        if not self.candidates:
            self.candidates = [(0, moves[0])]

    def _adopt_partial_iteration(self, partial: list[tuple[int, int]]) -> None:
        """Volta incompleta só vale se um lance superou o primeiro, que era o melhor da volta anterior.

        Como aquele lance foi pesquisado primeiro, quem passou dele é melhor com certeza. Sem nenhuma
        volta completa, qualquer nota serve, pois é melhor que a ordem inicial sem nota nenhuma.
        """
        if not partial:
            return
        best_move = max(partial, key=lambda scored: scored[0])[1]
        if not self.candidates or best_move != partial[0][1]:
            self.candidates = partial

    def _search_root(self, moves: list[int], depth: int, scored: list[tuple[int, int]]) -> list[int]:
        board = self.board
        best = -_INFINITY
        for move in moves:
            board.make(move)
            score = self._score_root_move(depth, best, not scored)
            board.unmake()
            scored.append((score, move))
            if score > best:
                best = score
        # `sorted` é estável: os lances que empatam mantêm a ordem da volta anterior.
        return [move for _, move in sorted(scored, key=lambda item: item[0], reverse=True)]

    def _score_root_move(self, depth: int, best: int, is_first: bool) -> int:
        if self.spread or is_first:
            floor = max(best - self.spread, -_INFINITY)
            return -self._negamax(depth - 1, -_INFINITY, -floor, 1)
        # Só o lance candidato a melhor precisa de nota exata. Os outros basta provar que são piores.
        score = -self._negamax(depth - 1, -best - 1, -best, 1)
        if score > best:
            score = -self._negamax(depth - 1, -_INFINITY, -best, 1)
        return score

    def _raise_if_stopped(self) -> None:
        if self.should_stop is not None and self.should_stop():
            raise _SearchStopped
        if self.nodes >= self.node_limit or time.perf_counter() >= self.deadline:
            raise _SearchStopped

    def _negamax(self, depth: int, alpha: int, beta: int, ply: int) -> int:
        """Devolve a nota da posição para quem joga. Fora da janela, a nota é só um limite."""
        self.nodes += 1
        if not self.nodes & _POLL_MASK:
            self._raise_if_stopped()
        board = self.board
        if board.is_rule_draw():
            # O mate vale mais que o empate: quem dá mate no 50º lance vence a partida.
            return -_MATE + ply if board.in_check() and not board.has_legal_move() else _DRAW
        in_check = board.in_check()
        if in_check and self.is_selective:
            depth += 1
        if depth <= 0 or ply >= _MAX_PLY:
            return self._leaf(alpha, beta, ply, in_check)
        entry = self.table.get(board.key)
        if entry is not None and entry[0] >= depth:
            score = _conclusive_table_score(entry, alpha, beta, ply)
            if score is not None:
                return score
        if self.is_selective and depth <= _STATIC_CUTOFF_MAX_DEPTH and beta - alpha == 1 and not in_check:
            # Tão acima de beta, a tão poucos lances do fim, que o adversário não teria como reagir.
            static_score = evaluate(board)
            if static_score - _STATIC_CUTOFF_MARGIN_PER_DEPTH * depth >= beta:
                return static_score
        hash_move = entry[3] if entry is not None else 0
        moves = self._ordered(board.generate_moves(), hash_move, ply)
        return self._search_moves(moves, depth, alpha, beta, ply, in_check)

    def _search_moves(self, moves: list[int], depth: int, alpha: int, beta: int, ply: int, in_check: bool) -> int:
        """Percorre os lances em ordem, parando no corte beta, e guarda o resultado na tabela."""
        board = self.board
        squares = board.squares
        key = board.key
        original_alpha = alpha
        best = -_INFINITY
        best_move = 0
        searched = 0
        for move in moves:
            is_quiet = not squares[move >> TARGET_SHIFT & SQUARE_MASK] and move >> FLAG_SHIFT <= FLAG_DOUBLE_PUSH
            if not board.try_make(move, in_check):
                continue
            searched += 1
            score = self._score_child(depth, alpha, beta, ply, searched, is_quiet and not in_check)
            board.unmake()
            if score > best:
                best = score
                best_move = move
                if score > alpha:
                    alpha = score
                    if score >= beta:
                        if is_quiet:
                            self._remember_cutoff(move, depth, ply)
                        break
        if not searched:
            return -_MATE + ply if in_check else _DRAW
        bound = _UPPER_BOUND if best <= original_alpha else _LOWER_BOUND if best >= beta else _EXACT
        self.table[key] = (depth, _score_to_table(best, ply), bound, best_move)
        return best

    def _score_child(self, depth: int, alpha: int, beta: int, ply: int, move_number: int, can_reduce: bool) -> int:
        """Só o primeiro lance recebe a janela inteira: é o favorito, pois a ordenação o pôs ali.

        Os demais recebem uma janela mínima, só para provar que não superam alpha, o que é bem mais
        barato. Lance tardio e quieto ainda vai com menos profundidade ("late move reduction"). Se
        algum surpreender, é buscado de novo por inteiro, e por isso a nota final continua confiável.
        """
        if move_number == 1:
            return -self._negamax(depth - 1, -beta, -alpha, ply + 1)
        reduction = self._late_move_reduction(depth, move_number) if can_reduce else 0
        score = -self._negamax(depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
        if score > alpha and (reduction or score < beta):
            score = -self._negamax(depth - 1, -beta, -alpha, ply + 1)
        return score

    def _late_move_reduction(self, depth: int, move_number: int) -> int:
        if not self.is_selective or depth < _REDUCTION_MIN_DEPTH or move_number <= _REDUCTION_MIN_MOVE_NUMBER:
            return 0
        return 2 if move_number > _DEEP_REDUCTION_MOVE_NUMBER and depth > _REDUCTION_MIN_DEPTH else 1

    def _remember_cutoff(self, move: int, depth: int, ply: int) -> None:
        """Um lance que cortou aqui deve ser bom também nas posições vizinhas: são os "killers" e a história."""
        killers = self.killers[ply]
        if killers[0] != move:
            killers[1] = killers[0]
            killers[0] = move
        index = move & FROM_TO_MASK
        self.history[index] = min(self.history[index] + depth * depth, _HISTORY_LIMIT)

    def _leaf(self, alpha: int, beta: int, ply: int, in_check: bool) -> int:
        if self.uses_quiescence:
            return self._quiesce(alpha, beta, ply, in_check)
        if in_check and not self.board.has_legal_move():
            return -_MATE + ply
        return evaluate(self.board)

    def _quiesce(self, alpha: int, beta: int, ply: int, in_check: bool) -> int:
        """Continua só pelas capturas até a posição acalmar. Em xeque, examina todas as saídas."""
        self.nodes += 1
        if not self.nodes & _POLL_MASK:
            self._raise_if_stopped()
        board = self.board
        if in_check:
            # Sem saída legal, o laço não roda e fica esta nota: é mate. As capturas se esgotam, então
            # esta recursão sempre termina. Os "killers" da raiz bastam aqui, onde a ordem pouco importa.
            best = -_MATE + ply
            moves = self._ordered(board.generate_moves(), 0, 0)
        else:
            # "Stand pat": ninguém é obrigado a capturar, então a nota atual já é um piso.
            stand_pat = best = evaluate(board)
            if best >= beta:
                return best
            if best > alpha:
                alpha = best
            moves = self._ordered_tactics()
        for move in moves:
            if not in_check and self._capture_is_hopeless(move, stand_pat, alpha):
                continue
            if not board.try_make(move, in_check):
                continue
            score = -self._quiesce(-beta, -alpha, ply + 1, board.in_check())
            board.unmake()
            if score > best:
                best = score
                if score > alpha:
                    alpha = score
                    if score >= beta:
                        break
        return best

    def _capture_is_hopeless(self, move: int, stand_pat: int, alpha: int) -> bool:
        """Corta o que não pode dar certo, porque a explosão de capturas é o maior custo da quiescence.

        Poda delta: nem ganhando a peça a nota alcança alpha. O outro caso é a peça cara capturar algo
        barato numa casa protegida por peão: perde material na recaptura.
        """
        board = self.board
        squares = board.squares
        target = move >> TARGET_SHIFT & SQUARE_MASK
        gain = _PIECE_VALUE[squares[target]] + _FLAG_GAIN[move >> FLAG_SHIFT]
        if stand_pat + gain + _DELTA_MARGIN <= alpha:
            return True
        return _PIECE_VALUE[squares[move & SQUARE_MASK]] > gain + _PAWN_VALUE and board.defended_by_pawn(target)

    def _ordered_tactics(self) -> list[int]:
        squares = self.board.squares
        scored = []
        for move in self.board.generate_tactical_moves():
            gain = _PIECE_VALUE[squares[move >> TARGET_SHIFT & SQUARE_MASK]] + _FLAG_GAIN[move >> FLAG_SHIFT]
            scored.append(_capture_priority(gain, squares[move & SQUARE_MASK]) << _MOVE_BITS | move)
        scored.sort(reverse=True)
        return [item & MOVE_MASK for item in scored]

    def _ordered(self, moves: list[int], hash_move: int, ply: int) -> list[int]:
        squares = self.board.squares
        first_killer, second_killer = self.killers[ply]
        history = self.history
        scored = []
        for move in moves:
            victim = squares[move >> TARGET_SHIFT & SQUARE_MASK]
            flag = move >> FLAG_SHIFT
            if move == hash_move:
                score = _HASH_MOVE_SCORE
            elif victim or flag == FLAG_EN_PASSANT or flag == FLAG_PROMOTE_QUEEN:
                gain = _PIECE_VALUE[victim] + _FLAG_GAIN[flag]
                score = _CAPTURE_SCORE + _capture_priority(gain, squares[move & SQUARE_MASK])
            elif move == first_killer:
                score = _FIRST_KILLER_SCORE
            elif move == second_killer:
                score = _SECOND_KILLER_SCORE
            else:
                score = history[move & FROM_TO_MASK]
            scored.append(score << _MOVE_BITS | move)
        scored.sort(reverse=True)
        return [item & MOVE_MASK for item in scored]


def _capture_priority(gain: int, attacker: int) -> int:
    """MVV-LVA: primeiro a vítima mais valiosa e, entre vítimas iguais, o atacante mais barato."""
    return _VICTIM_WEIGHT * gain - _PIECE_VALUE[attacker] // _PAWN_VALUE


def _root_spread(noise: int, margin: int) -> int:
    """Até onde a nota de um lance na raiz precisa ser exata.

    Um lance só pode ser sorteado se a nota dele for exata. Por isso, a janela da raiz inclui tudo o que
    o ruído (para mais ou para menos) ou a margem ainda poderiam colocar no topo.
    """
    return margin + 2 * noise


def _is_mate_score(score: int) -> bool:
    return abs(score) >= _MATE_THRESHOLD


def _conclusive_table_score(entry: tuple[int, int, int, int], alpha: int, beta: int, ply: int) -> int | None:
    """Devolve a nota guardada se ela já decide este nó, ou None se o nó ainda precisa ser buscado."""
    _, stored, bound, _ = entry
    score = _score_from_table(stored, ply)
    if bound == _EXACT or (bound == _LOWER_BOUND and score >= beta) or (bound == _UPPER_BOUND and score <= alpha):
        return score
    return None


def _score_to_table(score: int, ply: int) -> int:
    """A tabela guarda a distância do mate a partir do nó, pois a mesma posição surge em alturas diferentes."""
    if score >= _MATE_THRESHOLD:
        return score + ply
    if score <= -_MATE_THRESHOLD:
        return score - ply
    return score


def _score_from_table(score: int, ply: int) -> int:
    if score >= _MATE_THRESHOLD:
        return score - ply
    if score <= -_MATE_THRESHOLD:
        return score + ply
    return score


def _is_settled_mate(scored: list[tuple[int, int]], depth: int) -> bool:
    """Se o mate já cabe na profundidade atual, buscar mais fundo não acha nada mais rápido."""
    best = max(score for score, _ in scored)
    return _is_mate_score(best) and _MATE - abs(best) <= depth


def _pick_root_move(candidates: list[tuple[int, int]], noise: int, margin: int, rng: random.Random) -> tuple[int, int]:
    """Escolhe entre os lances com nota exata, aplicando o ruído e a margem do nível.

    Nota de mate nunca recebe ruído nem margem: mate em 1 e mate em 2 diferem por poucos pontos, e a
    CPU não pode sortear entre eles.
    """
    spread = _root_spread(noise, margin)
    if not spread:
        # Sem sorteio, a raiz só provou que os outros lances não superam o melhor: nota igual é só um limite.
        return max(candidates, key=lambda scored: scored[0])
    best_exact = max(score for score, _ in candidates)
    noisy = [
        (score if _is_mate_score(score) else score + rng.uniform(-noise, noise), score, move)
        for score, move in candidates
        if score > best_exact - spread
    ]
    top = max(item[0] for item in noisy)
    tolerance = 0 if _is_mate_score(best_exact) else margin
    finalists = [(score, move) for value, score, move in noisy if value >= top - tolerance]
    # Adiar a promoção rende quase a mesma nota, porque a dama nasce dali a dois lances dentro da busca.
    # Sorteado, isso faria a CPU passear com o rei ao lado de um peão pronto para virar dama.
    promotions = [finalist for finalist in finalists if finalist[1] >> FLAG_SHIFT == FLAG_PROMOTE_QUEEN]
    return rng.choice(promotions or finalists)


def _load_game_history(board: Board, search_board: SearchBoard) -> None:
    """Passa à busca as posições da partida desde o último lance irreversível, para reconhecer repetição.

    Sem isso, a CPU em vantagem poderia repetir lances até empatar sem perceber. `board` é a cópia de
    trabalho: voltar os lances nela não mexe no tabuleiro da partida.
    """
    keys = []
    for _ in range(min(board.halfmove_clock, board.undoable_moves)):
        board.undo()
        keys.append(SearchBoard.from_board(board).key)
    keys.reverse()
    search_board.seed_history(keys)


def _is_regular_position(board: Board) -> bool:
    """Diz se a posição obedece às regras do FEN, as mesmas que a busca presume (um rei de cada cor, etc.)."""
    try:
        Board.from_fen(board.to_fen())
    except ValueError:
        return False
    return True


def _time_budget(level: _Level, max_seconds: float | None) -> float:
    budgets = [limit for limit in (level.seconds, max_seconds) if limit is not None]
    return min(budgets) if budgets else float("inf")


def analyze(
    board: Board,
    difficulty: Difficulty,
    rng: random.Random | None = None,
    should_stop: Callable[[], bool] | None = None,
    max_seconds: float | None = None,
) -> SearchReport:
    """Faz a busca e devolve a jogada com os números dela. `choose_move` é o que a interface usa."""
    started = time.perf_counter()
    rng = rng if rng is not None else random.Random()
    working = board.copy()
    legal = legal_moves(working)
    if not legal:
        raise ValueError("Não há jogada legal nesta posição: a partida já terminou")
    if len(legal) == 1 or not _is_regular_position(working):
        return SearchReport(rng.choice(legal), 0, 0, 0, time.perf_counter() - started)

    level = _LEVELS[difficulty]
    search_board = SearchBoard.from_board(working)
    fullmove_number = working.fullmove_number
    _load_game_history(working, search_board)
    margin = max(level.tie_margin, level.opening_margin if fullmove_number <= _OPENING_FULL_MOVES else 0)
    deadline = started + _time_budget(level, max_seconds)
    search = _Search(search_board, level, margin, should_stop, deadline)
    by_code = {encode_move(move): move for move in legal}
    search.run(list(by_code))
    score, code = _pick_root_move(search.candidates, level.noise, margin, rng)
    return SearchReport(by_code[code], score, search.completed_depth, search.nodes, time.perf_counter() - started)


def choose_move(
    board: Board,
    difficulty: Difficulty,
    rng: random.Random | None = None,
    should_stop: Callable[[], bool] | None = None,
    max_seconds: float | None = None,
) -> Move:
    """Escolhe a jogada da CPU. Devolve sempre uma jogada legal, com a promoção já definida.

    Não altera `board`, então pode rodar em outra thread. `should_stop` cancela a busca e `max_seconds`
    limita o tempo: nos dois casos, a resposta é a melhor jogada achada até ali. Com `rng` de semente, o
    resultado se repete, exceto quando o tempo real interrompe a busca, o que sempre pode acontecer no
    Hardcore. Levanta ValueError se não houver jogada legal.
    """
    return analyze(board, difficulty, rng, should_stop, max_seconds).move
