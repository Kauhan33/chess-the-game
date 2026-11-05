"""PGN: confere o texto gerado com um leitor simples, que refaz os lances em um motor novo."""
import re
from datetime import date

import pytest
from core_helpers import play_all, sq

from xadrez.core import Color, EndReason, GameEngine, PieceType, TimeControl, game_to_pgn, move_to_san

SCHOLARS_MATE = ("e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "g8f6", "h5f7")
TAG = re.compile(r'^\[(\w+) "(.*)"\]$')
MOVE_NUMBER = re.compile(r"^\d+\.(\.\.)?$")


def read_pgn(text):
    """Separa cabeçalhos e lances, recusando o que um leitor de PGN recusaria."""
    header, separator, movetext = text.partition("\n\n")
    assert separator, "PGN sem a linha em branco entre cabeçalhos e lances"
    tags = {}
    for line in header.splitlines():
        match = TAG.match(line)
        assert match, f"cabeçalho inválido: {line!r}"
        tags[match.group(1)] = match.group(2)
    tokens = movetext.split()
    return tags, [token for token in tokens[:-1] if not MOVE_NUMBER.match(token)], tokens[-1]


def replay(tags, sans):
    """Refaz os lances pelo texto. Um único SAN sem jogada legal correspondente derruba o teste."""
    engine = GameEngine(fen=tags.get("FEN"))
    for san in sans:
        move = next(
            (
                candidate
                for square, _ in list(engine.board.pieces(engine.turn))
                for candidate in engine.legal_moves_from(square)
                if move_to_san(engine.board, candidate) == san
            ),
            None,
        )
        assert move is not None, f"SAN sem jogada legal: {san}"
        assert engine.play(move.origin, move.target, move.promotion).ok
    return engine


def round_trip(engine):
    tags, sans, result = read_pgn(game_to_pgn(engine, date="2026.11.04"))
    assert tags["Result"] == result
    replayed = replay(tags, sans)
    assert replayed.final_fen == engine.final_fen
    return tags, sans, result


@pytest.mark.ct("CT-76")
def test_mate_game_is_valid_with_winner_and_required_tags():
    engine = GameEngine("Ana", "Bia")
    play_all(engine, *SCHOLARS_MATE)
    text = game_to_pgn(engine, event="Final", date="2026.11.04")
    tags, sans, result = read_pgn(text)
    assert tags == {
        "Event": "Final", "Site": "?", "Date": "2026.11.04", "Round": "?",
        "White": "Ana", "Black": "Bia", "Result": "1-0", "TimeControl": "-",
    }
    assert result == "1-0"
    assert sans == engine.history
    assert "1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# 1-0" in text
    assert text.endswith("\n")
    assert replay(tags, sans).result.reason is EndReason.CHECKMATE


@pytest.mark.ct("CT-76")
def test_black_win_draw_and_unfinished_results():
    black_wins = GameEngine()
    black_wins.resign(Color.WHITE)
    assert read_pgn(game_to_pgn(black_wins))[2] == "0-1"

    drawn = GameEngine()
    drawn.agree_draw()
    assert read_pgn(game_to_pgn(drawn))[2] == "1/2-1/2"

    unfinished = GameEngine()
    play_all(unfinished, "e2e4")
    assert read_pgn(game_to_pgn(unfinished))[2] == "*"

    abandoned = GameEngine()
    abandoned.abandon(Color.BLACK)
    assert read_pgn(game_to_pgn(abandoned))[2] == "1-0"


@pytest.mark.ct("CT-76")
def test_game_without_moves_still_has_the_result():
    engine = GameEngine()
    text = game_to_pgn(engine, date="2026.11.04")
    assert text.endswith("\n\n*\n")


@pytest.mark.ct("CT-76")
def test_custom_position_writes_setup_and_fen():
    fen = "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"
    engine = GameEngine(fen=fen)
    play_all(engine, "e2e4")
    tags, _, _ = round_trip(engine)
    assert tags["SetUp"] == "1"
    assert tags["FEN"] == fen


@pytest.mark.ct("CT-76")
def test_official_start_has_no_setup_tags():
    tags, _, _ = read_pgn(game_to_pgn(GameEngine()))
    assert "SetUp" not in tags
    assert "FEN" not in tags


@pytest.mark.ct("CT-76")
def test_black_to_move_first_uses_three_dots_and_correct_numbers():
    engine = GameEngine(fen="4k3/4p3/8/8/8/8/4P3/4K3 b - - 3 12")
    play_all(engine, "e7e5", "e2e4", "e8e7", "e1e2")
    text = game_to_pgn(engine, date="2026.11.04")
    assert "12... e5 13. e4 Ke7 14. Ke2 *" in text
    round_trip(engine)


@pytest.mark.ct("CT-76")
def test_white_to_move_keeps_the_number_of_the_fen():
    engine = GameEngine(fen="4k3/4p3/8/8/8/8/4P3/4K3 w - - 0 7")
    play_all(engine, "e2e4", "e7e5", "e1e2")
    assert "7. e4 e5 8. Ke2 *" in game_to_pgn(engine, date="2026.11.04")


@pytest.mark.ct("CT-76")
def test_special_moves_round_trip():
    engine = GameEngine(fen="r3k2r/P6p/8/8/4Pp2/8/7P/R3K2R b KQkq e3 0 1")
    play_all(engine, "f4e3", "e1g1", "e8c8")
    assert engine.play(sq("a7"), sq("a8"), PieceType.KNIGHT).ok
    _, sans, _ = round_trip(engine)
    assert sans == ["fxe3", "O-O", "O-O-O", "a8=N"]


@pytest.mark.ct("CT-76")
@pytest.mark.parametrize(
    "time_control, text",
    [
        (TimeControl.UNLIMITED, "-"),
        (TimeControl.BLITZ_5, "300"),
        (TimeControl.RAPID_10, "600"),
        (TimeControl.BLITZ_3_2, "180+2"),
        (TimeControl.CLASSIC_15_10, "900+10"),
        (TimeControl(1.5, 0.5), "90+0.5"),
    ],
)
def test_time_control_tag(time_control, text):
    engine = GameEngine(time_control=time_control)
    assert read_pgn(game_to_pgn(engine))[0]["TimeControl"] == text


@pytest.mark.ct("CT-76")
def test_names_with_quotes_backslash_and_line_breaks_do_not_break_the_header():
    engine = GameEngine('Ana "Rainha"', "Bia\\Dois\nLinhas")
    text = game_to_pgn(engine, event='Copa "A"', date="2026.11.04")
    tags, _, _ = read_pgn(text)
    assert tags["White"] == 'Ana \\"Rainha\\"'
    assert tags["Black"] == "Bia\\\\Dois Linhas"
    assert tags["Event"] == 'Copa \\"A\\"'


@pytest.mark.ct("CT-76")
def test_default_date_is_today_in_pgn_format():
    tags, _, _ = read_pgn(game_to_pgn(GameEngine()))
    assert tags["Date"] == date.today().strftime("%Y.%m.%d")


@pytest.mark.ct("CT-76")
def test_iso_date_is_converted_to_the_pgn_format():
    tags, _, _ = read_pgn(game_to_pgn(GameEngine(), date="2026-11-04"))
    assert tags["Date"] == "2026.11.04"


@pytest.mark.ct("CT-76")
def test_long_games_wrap_lines_at_eighty_columns():
    engine = GameEngine()
    shuffle = ("g1f3", "g8f6", "f3g1", "f6g8")
    # Os peões avançam entre uma volta e outra para a posição não se repetir e encerrar a partida.
    pawn_pushes = ("a2a3", "a7a6", "b2b3", "b7b6", "c2c3", "c7c6", "d2d3", "d7d6", "e2e3", "e7e6", "f2f3", "f7f6")
    for white_push, black_push in zip(pawn_pushes[::2], pawn_pushes[1::2]):
        play_all(engine, *shuffle, white_push, black_push)
    text = game_to_pgn(engine, date="2026.11.04")
    assert all(len(line) <= 80 for line in text.splitlines())
    assert len(text.split("\n\n")[1].splitlines()) > 1
    round_trip(engine)


@pytest.mark.ct("CT-76")
def test_black_tag_after_rematch_follows_the_colors():
    engine = GameEngine("Ana", "Bia")
    engine.rematch()
    tags, _, _ = read_pgn(game_to_pgn(engine))
    assert tags["White"] == "Bia"
    assert tags["Black"] == "Ana"
