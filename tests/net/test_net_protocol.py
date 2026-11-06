"""CT-88: o formato das mensagens. Tudo que vem da rede é conferido campo a campo antes de virar evento."""
import json
import math

import pytest

from xadrez.core import Color, EndReason, GameResult, PieceType, Square
from xadrez.net import parse_uci
from xadrez.net.protocol import (
    MAX_CLOCK_MS,
    MAX_LINE_BYTES,
    MAX_NAME_CHARS,
    LineSplitter,
    ProtocolError,
    clock_to_wire,
    decode_message,
    encode_message,
    is_valid_name,
    is_valid_uci,
    parse_result,
    result_fields,
    sanitize_name,
)

BIDI_OVERRIDE = chr(0x202E)
ZERO_WIDTH_SPACE = chr(0x200B)
START = {"white": "Brancas", "black": "Pretas", "your_color": "black", "minutes": 10, "increment": 0, "mode": "training"}

VALID_MESSAGES = [
    {"type": "hello", "version": 1, "name": "Pretas"},
    {"type": "start", **START},
    {"type": "start", **{**START, "minutes": 0.5, "increment": 2.5, "your_color": "white"}},
    {"type": "start", **{**START, "mode": "match"}},
    {"type": "refused", "code": "room_full"},
    {"type": "refused", "code": "version"},
    {"type": "move", "uci": "e2e4", "clock_ms": 0},
    {"type": "move", "uci": "a7a8q", "clock_ms": MAX_CLOCK_MS},
    {"type": "draw_answer", "accept": True},
    {"type": "draw_answer", "accept": False},
    {"type": "resign"},
    {"type": "draw_offer"},
    {"type": "rematch"},
    {"type": "bye"},
    {"type": "ping"},
    {"type": "result", "winner": "white", "reason": "checkmate", "plies": 3},
    {"type": "result", "winner": "black", "reason": "resignation", "plies": 0},
    {"type": "result", "winner": "white", "reason": "abandonment", "plies": 65535},
    {"type": "result", "winner": None, "reason": "stalemate", "plies": 9},
    {"type": "result", "winner": None, "reason": "agreement", "plies": 9},
    {"type": "result", "winner": None, "reason": "timeout", "plies": 9},
    {"type": "result", "winner": "black", "reason": "timeout", "plies": 9},
]

INVALID_MESSAGES = [
    "nulo-json",
    [],
    1,
    "move",
    {},
    {"type": None},
    {"type": 1},
    {"type": ["move"]},
    {"type": {"a": 1}},
    {"type": "desconhecido"},
    {"type": "ping", "extra": 1},
    {"type": "move", "uci": "e2e4"},
    {"type": "move", "clock_ms": 1},
    {"type": "move", "uci": "e2e4", "clock_ms": 1, "extra": 1},
    {"type": "move", "uci": 123, "clock_ms": 1},
    {"type": "move", "uci": None, "clock_ms": 1},
    {"type": "move", "uci": ["e2e4"], "clock_ms": 1},
    {"type": "move", "uci": "", "clock_ms": 1},
    {"type": "move", "uci": "e2", "clock_ms": 1},
    {"type": "move", "uci": "e2e9", "clock_ms": 1},
    {"type": "move", "uci": "i2e4", "clock_ms": 1},
    {"type": "move", "uci": "e2e4k", "clock_ms": 1},
    {"type": "move", "uci": "E2E4", "clock_ms": 1},
    {"type": "move", "uci": "e2e4\n", "clock_ms": 1},
    {"type": "move", "uci": "e2e4 ", "clock_ms": 1},
    {"type": "move", "uci": "e2e4q5", "clock_ms": 1},
    {"type": "move", "uci": "e2e4", "clock_ms": -1},
    {"type": "move", "uci": "e2e4", "clock_ms": MAX_CLOCK_MS + 1},
    {"type": "move", "uci": "e2e4", "clock_ms": 1.5},
    {"type": "move", "uci": "e2e4", "clock_ms": "1"},
    {"type": "move", "uci": "e2e4", "clock_ms": True},
    {"type": "move", "uci": "e2e4", "clock_ms": None},
    {"type": "draw_answer", "accept": "sim"},
    {"type": "draw_answer", "accept": 1},
    {"type": "draw_answer", "accept": None},
    {"type": "hello", "version": 1},
    {"type": "hello", "name": "x"},
    {"type": "hello", "version": "1", "name": "x"},
    {"type": "hello", "version": True, "name": "x"},
    {"type": "hello", "version": 1.0, "name": "x"},
    {"type": "hello", "version": -1, "name": "x"},
    {"type": "hello", "version": 70000, "name": "x"},
    {"type": "hello", "version": 1, "name": ""},
    {"type": "hello", "version": 1, "name": "   "},
    {"type": "hello", "version": 1, "name": None},
    {"type": "hello", "version": 1, "name": 7},
    {"type": "hello", "version": 1, "name": ["x"]},
    {"type": "hello", "version": 1, "name": "x" * (MAX_NAME_CHARS + 1)},
    {"type": "hello", "version": 1, "name": "com\ncontrole"},
    {"type": "hello", "version": 1, "name": "com\x00nulo"},
    {"type": "hello", "version": 1, "name": "com\x1bescape"},
    {"type": "hello", "version": 1, "name": f"a{BIDI_OVERRIDE}b"},
    {"type": "hello", "version": 1, "name": f"a{ZERO_WIDTH_SPACE}b"},
    {"type": "hello", "version": 1, "name": chr(0xD800)},
    {"type": "start", **{**START, "mode": "Partida"}},
    {"type": "start", **{**START, "mode": None}},
    {"type": "start", **{**START, "mode": ["match"]}},
    {"type": "start", **{**START, "mode": 1}},
    {"type": "start", **{key: value for key, value in START.items() if key != "mode"}},
    {"type": "start", **{**START, "your_color": "red"}},
    {"type": "start", **{**START, "your_color": ["white"]}},
    {"type": "start", **{**START, "your_color": None}},
    {"type": "start", **{**START, "minutes": -1}},
    {"type": "start", **{**START, "minutes": 100000}},
    {"type": "start", **{**START, "minutes": "10"}},
    {"type": "start", **{**START, "minutes": True}},
    {"type": "start", **{**START, "increment": -1}},
    {"type": "start", **{**START, "increment": 100000}},
    {"type": "start", **{**START, "white": ""}},
    {"type": "start", **{**START, "black": "x" * 100}},
    {"type": "refused", "code": "qualquer"},
    {"type": "refused", "code": ["room_full"]},
    {"type": "refused", "code": None},
]


def as_line(value):
    return json.dumps(value).encode()


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize("message", VALID_MESSAGES, ids=lambda message: message["type"])
def test_net_mensagem_valida_faz_ida_e_volta(message):
    line = encode_message(message)
    assert line.endswith(b"\n") and line.count(b"\n") == 1
    assert decode_message(line[:-1]) == message


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize("message", INVALID_MESSAGES, ids=range(len(INVALID_MESSAGES)))
def test_net_mensagem_invalida_e_recusada_nos_dois_sentidos(message):
    with pytest.raises(ProtocolError):
        decode_message(as_line(message))
    with pytest.raises(ProtocolError):
        encode_message(message)


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize(
    "line",
    [
        b"",
        b"   ",
        b"isto nao e json",
        b"{",
        b'{"type":"ping"',
        b"\xff\xfe\x00\x01",
        b'{"type":"ping"}\xff',
        b"[" * 4000,
        b'{"a":' * 800,
        b"NaN",
        b"Infinity",
        b'{"type":"move","uci":"e2e4","clock_ms":NaN}',
        b'{"type":"move","uci":"e2e4","clock_ms":Infinity}',
        b'{"type":"move","uci":"e2e4","clock_ms":-Infinity}',
        b'{"type":"move","uci":"e2e4","clock_ms":1e999}',
        b'{"type":"move","uci":"e2e4","clock_ms":' + b"9" * 4000 + b"}",
        b'{"type":"start","white":"a","black":"b","your_color":"white","minutes":1e999,"increment":0,"mode":"training"}',
        b'{"type":"hello","version":1,"name":"\\ud800"}',
    ],
    ids=range(18),
)
def test_net_linha_que_nem_e_mensagem_e_recusada_sem_derrubar(line):
    with pytest.raises(ProtocolError):
        decode_message(line)


@pytest.mark.ct("CT-88")
def test_net_chave_repetida_nao_escapa_da_conferencia():
    with pytest.raises(ProtocolError):
        decode_message(b'{"type":"move","uci":"e2e4","uci":"e2e9","clock_ms":1}')


@pytest.mark.ct("CT-88")
def test_net_mensagem_codificada_grande_demais_nao_sai(monkeypatch):
    monkeypatch.setattr("xadrez.net.protocol.MAX_LINE_BYTES", 10)
    with pytest.raises(ProtocolError, match="grande"):
        encode_message({"type": "hello", "version": 1, "name": "Pretas"})


@pytest.mark.ct("CT-88")
def test_net_infinito_nao_sai_pelo_codificador():
    with pytest.raises(ProtocolError):
        encode_message({"type": "move", "uci": "e2e4", "clock_ms": math.inf})
    with pytest.raises(ProtocolError):
        encode_message({"type": "start", **{**START, "minutes": math.nan}})


@pytest.mark.ct("CT-88")
def test_net_separa_linhas_vindas_em_pedacos():
    splitter = LineSplitter()
    assert splitter.feed(b'{"type"') == []
    assert splitter.feed(b':"ping"}\n{"type":"bye"}\n{"ty') == [b'{"type":"ping"}', b'{"type":"bye"}']
    assert splitter.feed(b'pe":"ping"}\n') == [b'{"type":"ping"}']
    assert splitter.feed(b"") == []


@pytest.mark.ct("CT-88")
def test_net_linha_no_limite_passa_e_um_byte_a_mais_nao():
    assert LineSplitter().feed(b"x" * MAX_LINE_BYTES + b"\n") == [b"x" * MAX_LINE_BYTES]
    with pytest.raises(ProtocolError):
        LineSplitter().feed(b"x" * (MAX_LINE_BYTES + 1) + b"\n")


@pytest.mark.ct("CT-88")
def test_net_linha_sem_fim_e_descartada_sem_acumular_memoria():
    splitter = LineSplitter()
    assert splitter.feed(b"x" * MAX_LINE_BYTES) == []
    with pytest.raises(ProtocolError):
        splitter.feed(b"x")
    assert len(splitter._partial) == 0


@pytest.mark.ct("CT-88")
def test_net_linha_gigante_no_meio_do_fluxo_e_recusada():
    splitter = LineSplitter()
    with pytest.raises(ProtocolError):
        splitter.feed(b'{"type":"ping"}\n' + b"x" * (MAX_LINE_BYTES + 1) + b"\n{}\n")
    assert len(splitter._partial) == 0


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Brancas", "Brancas"),
        ("  Brancas  ", "Brancas"),
        ("a\nb\x00c\x1bd", "abcd"),
        (f"a{BIDI_OVERRIDE}b{ZERO_WIDTH_SPACE}c", "abc"),
        ("x" * 100, "x" * MAX_NAME_CHARS),
        ("a" * (MAX_NAME_CHARS - 1) + " " + "b", "a" * (MAX_NAME_CHARS - 1)),
        ("", "Jogador"),
        ("   ", "Jogador"),
        ("\n\t\x00", "Jogador"),
        (None, "Jogador"),
        (123, "Jogador"),
        (chr(0xD800), "Jogador"),
    ],
    ids=range(12),
)
def test_net_nome_local_e_ajustado_e_sempre_passa_na_conferencia(raw, expected):
    assert sanitize_name(raw) == expected
    assert is_valid_name(sanitize_name(raw))


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize(
    "clock, expected",
    [
        (0, 0),
        (1500, 1500),
        (1500.7, 1500),
        (-5, 0),
        (math.inf, 0),
        (-math.inf, 0),
        (math.nan, 0),
        (None, 0),
        ("abc", 0),
        (10**15, MAX_CLOCK_MS),
    ],
    ids=range(10),
)
def test_net_relogio_sempre_sai_dentro_da_faixa(clock, expected):
    assert clock_to_wire(clock) == expected


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize(
    "uci, expected",
    [
        ("e2e4", (Square(4, 1), Square(4, 3), None)),
        ("a7a8q", (Square(0, 6), Square(0, 7), PieceType.QUEEN)),
        ("a7a8r", (Square(0, 6), Square(0, 7), PieceType.ROOK)),
        ("h2h1b", (Square(7, 1), Square(7, 0), PieceType.BISHOP)),
        ("h2h1n", (Square(7, 1), Square(7, 0), PieceType.KNIGHT)),
    ],
)
def test_net_jogada_vira_argumentos_do_motor(uci, expected):
    assert is_valid_uci(uci)
    assert parse_uci(uci) == expected


@pytest.mark.ct("CT-88")
@pytest.mark.parametrize("uci", ["", "e2", "e2e9", "e2e4x", None, 7, "e2e4\n"])
def test_net_jogada_mal_formada_nao_vira_casa(uci):
    assert not is_valid_uci(uci)
    with pytest.raises(ValueError):
        parse_uci(uci)


@pytest.mark.parametrize("message", [
    {"type": "result"},
    {"type": "result", "winner": "white", "reason": "checkmate"},
    {"type": "result", "reason": "checkmate", "plies": 1},
    {"type": "result", "winner": "white", "plies": 1},
    {"type": "result", "winner": "white", "reason": "checkmate", "plies": 1, "fen": "x"},
    {"type": "result", "winner": "red", "reason": "checkmate", "plies": 1},
    {"type": "result", "winner": 1, "reason": "checkmate", "plies": 1},
    {"type": "result", "winner": "white", "reason": "CHECKMATE", "plies": 1},
    {"type": "result", "winner": "white", "reason": "Xeque-mate", "plies": 1},
    {"type": "result", "winner": "white", "reason": ["checkmate"], "plies": 1},
    {"type": "result", "winner": "white", "reason": "checkmate", "plies": -1},
    {"type": "result", "winner": "white", "reason": "checkmate", "plies": 65536},
    {"type": "result", "winner": "white", "reason": "checkmate", "plies": 1.0},
    {"type": "result", "winner": "white", "reason": "checkmate", "plies": True},
    {"type": "result", "winner": None, "reason": "checkmate", "plies": 1},
    {"type": "result", "winner": None, "reason": "resignation", "plies": 1},
    {"type": "result", "winner": None, "reason": "abandonment", "plies": 1},
    {"type": "result", "winner": "white", "reason": "stalemate", "plies": 1},
    {"type": "result", "winner": "white", "reason": "insufficient_material", "plies": 1},
    {"type": "result", "winner": "white", "reason": "fifty_moves", "plies": 1},
    {"type": "result", "winner": "white", "reason": "threefold_repetition", "plies": 1},
    {"type": "result", "winner": "white", "reason": "agreement", "plies": 1},
])
def test_resultado_invalido_e_recusado_nos_dois_sentidos(message):
    with pytest.raises(ProtocolError):
        decode_message(json.dumps(message).encode())
    with pytest.raises(ProtocolError):
        encode_message(message)


@pytest.mark.parametrize("winner", [Color.WHITE, Color.BLACK, None])
def test_resultado_ida_e_volta_para_cada_motivo_possivel(winner):
    for reason in EndReason:
        fields = result_fields(GameResult(winner, reason), 7)
        message = {"type": "result", **fields}
        try:
            decoded = decode_message(encode_message(message).strip())
        except ProtocolError:
            continue
        assert parse_result(decoded) == GameResult(winner, reason)
        assert decoded["plies"] == 7


def test_todo_motivo_de_fim_tem_um_vencedor_valido_no_protocolo():
    for reason in EndReason:
        accepted = []
        for winner in (Color.WHITE, None):
            try:
                encode_message({"type": "result", **result_fields(GameResult(winner, reason), 0)})
            except ProtocolError:
                continue
            accepted.append(winner)
        assert accepted, reason
