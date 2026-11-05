"""CT-85: código de sala em ida e volta, recusa de código inválido e descoberta do IP local."""
import ipaddress
import random

import pytest

from xadrez.core import TimeControl
from xadrez.net import HostSession, decode_room_code, encode_room_code, local_ipv4
from xadrez.net import room_code, session
from xadrez.net.room_code import _ALPHABET, is_lan_address

AMBIGUOUS = set("0O1IL")
EXAMPLES = [
    "0.0.0.0",
    "255.255.255.255",
    "127.0.0.1",
    "10.0.0.1",
    "10.255.255.254",
    "172.16.0.1",
    "172.31.255.254",
    "192.168.0.1",
    "192.168.255.254",
    "169.254.10.20",
    "192.0.2.1",
    "198.51.100.200",
    "203.0.113.77",
]


def random_ipv4s(count, seed=2026):
    rng = random.Random(seed)
    return [str(ipaddress.IPv4Address(rng.getrandbits(32))) for _ in range(count)]


def substitutions(code):
    """Todos os códigos a um dígito trocado de distância."""
    for position, original in enumerate(code):
        for char in _ALPHABET:
            if char != original:
                yield code[:position] + char + code[position + 1 :]


def transpositions(code):
    """Todos os códigos com dois dígitos vizinhos trocados de lugar."""
    for position in range(len(code) - 1):
        if code[position] != code[position + 1]:
            yield code[:position] + code[position + 1] + code[position] + code[position + 2 :]


def is_accepted(code):
    try:
        decode_room_code(code)
    except ValueError:
        return False
    return True


def detection_rate(variations):
    results = [not is_accepted(code) for ip in random_ipv4s(300) for code in variations(encode_room_code(ip))]
    return sum(results) / len(results)


@pytest.mark.ct("CT-85")
@pytest.mark.parametrize("ipv4", EXAMPLES)
def test_net_codigo_ida_e_volta(ipv4):
    code = encode_room_code(ipv4)
    assert len(code) == 7
    assert decode_room_code(code) == ipv4


@pytest.mark.ct("CT-85")
def test_net_codigo_ida_e_volta_com_ips_variados():
    for ipv4 in random_ipv4s(5000):
        code = encode_room_code(ipv4)
        assert len(code) == 7
        assert not set(code) & AMBIGUOUS
        assert decode_room_code(code) == ipv4


@pytest.mark.ct("CT-85")
def test_net_alfabeto_nao_tem_caractere_ambiguo_nem_repetido():
    assert len(set(_ALPHABET)) == len(_ALPHABET) == 31
    assert not set(_ALPHABET) & AMBIGUOUS
    assert _ALPHABET.isalnum() and _ALPHABET.isascii() and _ALPHABET.upper() == _ALPHABET


@pytest.mark.ct("CT-85")
def test_net_todos_os_ipv4_cabem_em_7_caracteres():
    largest = encode_room_code("255.255.255.255")
    assert len(largest) == 7
    assert decode_room_code(largest) == "255.255.255.255"


@pytest.mark.ct("CT-85")
def test_net_codigo_aceita_minusculas_e_espacos():
    code = encode_room_code("192.168.0.10")
    expected = "192.168.0.10"
    assert decode_room_code(code.lower()) == expected
    assert decode_room_code(f"  {code[:3]} {code[3:]}  ") == expected
    assert decode_room_code(" ".join(code.lower())) == expected
    assert decode_room_code(f"{code[:3]}\t{code[3:]}\n") == expected


@pytest.mark.ct("CT-85")
def test_net_digito_trocado_e_detectado_na_maioria_dos_casos():
    assert detection_rate(substitutions) >= 0.80


@pytest.mark.ct("CT-85")
def test_net_vizinhos_trocados_sao_detectados_na_maioria_dos_casos():
    assert detection_rate(transpositions) >= 0.80


@pytest.mark.ct("CT-85")
@pytest.mark.parametrize(
    "code, message",
    [
        ("", "7 caracteres"),
        ("ABC", "7 caracteres"),
        ("ABCDEFGH", "7 caracteres"),
        ("       ", "7 caracteres"),
        ("ABCDEF0", "sem 0, O, 1, I e L"),
        ("ABCDEFO", "sem 0, O, 1, I e L"),
        ("ABCDEF1", "sem 0, O, 1, I e L"),
        ("ABCDEFI", "sem 0, O, 1, I e L"),
        ("ABCDEFL", "sem 0, O, 1, I e L"),
        ("ABCDEF-", "sem 0, O, 1, I e L"),
        ("ABCDEFé", "sem 0, O, 1, I e L"),
        ("ABCDEF٣", "sem 0, O, 1, I e L"),
        ("ZZZZZZZ", "inválido"),
    ],
)
def test_net_codigo_invalido_explica_em_portugues(code, message):
    with pytest.raises(ValueError, match=message):
        decode_room_code(code)


@pytest.mark.ct("CT-85")
@pytest.mark.parametrize("code", [None, 1234567, b"ABCDEFG", ["A"] * 7])
def test_net_codigo_de_tipo_errado_vira_erro_de_valor(code):
    with pytest.raises(ValueError):
        decode_room_code(code)


@pytest.mark.ct("CT-85")
@pytest.mark.parametrize("ipv4", ["", "abc", "256.0.0.1", "1.2.3", "::1", "1.2.3.4.5", None])
def test_net_ip_invalido_nao_vira_codigo(ipv4):
    with pytest.raises(ValueError):
        encode_room_code(ipv4)


@pytest.mark.ct("CT-85")
def test_net_ip_local_e_um_ipv4_valido():
    assert ipaddress.IPv4Address(local_ipv4())


class FakeUdpSocket:
    """Registra o que foi pedido à rede, para provar que nenhum pacote foi enviado."""

    used = []

    def __init__(self, address="192.168.0.10", error=None):
        self.address = address
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def connect(self, destination):
        FakeUdpSocket.used.append(destination)
        if self.error is not None:
            raise self.error

    def getsockname(self):
        return (self.address, 40000)


@pytest.mark.ct("CT-85")
def test_net_ip_local_nao_envia_pacote(monkeypatch):
    FakeUdpSocket.used = []
    monkeypatch.setattr(room_code.socket, "socket", lambda *args: FakeUdpSocket())
    assert local_ipv4() == "192.168.0.10"
    assert len(FakeUdpSocket.used) == 1
    assert not hasattr(FakeUdpSocket, "send") and not hasattr(FakeUdpSocket, "sendto")


@pytest.mark.ct("CT-85")
def test_net_sem_rota_padrao_procura_a_rede_local(monkeypatch):
    attempts = iter([FakeUdpSocket(error=OSError("sem rota")), FakeUdpSocket(error=OSError("sem rota")), FakeUdpSocket("10.0.0.5")])
    monkeypatch.setattr(room_code.socket, "socket", lambda *args: next(attempts))
    assert local_ipv4() == "10.0.0.5"


@pytest.mark.ct("CT-85")
@pytest.mark.parametrize("answer", [OSError("rede inacessível"), "127.0.0.1", "0.0.0.0"], ids=["erro", "loopback", "sem-endereco"])
def test_net_sem_rede_devolve_loopback(monkeypatch, answer):
    fake = FakeUdpSocket(error=answer) if isinstance(answer, OSError) else FakeUdpSocket(address=answer)
    monkeypatch.setattr(room_code.socket, "socket", lambda *args: fake)
    assert local_ipv4() == "127.0.0.1"


@pytest.mark.ct("CT-85")
def test_net_sala_sem_rede_avisa_a_tela(monkeypatch):
    monkeypatch.setattr(session, "local_ipv4", lambda: "127.0.0.1")
    host = HostSession("Brancas", TimeControl.UNLIMITED)
    assert decode_room_code(host.code) == "127.0.0.1"
    assert "Sem rede local" in host.offline_warning


@pytest.mark.ct("CT-85")
def test_net_sala_com_rede_usa_o_ip_local_e_nao_avisa(monkeypatch):
    monkeypatch.setattr(session, "local_ipv4", lambda: "192.168.0.10")
    host = HostSession("Brancas", TimeControl.UNLIMITED)
    assert decode_room_code(host.code) == "192.168.0.10"
    assert host.offline_warning is None


@pytest.mark.ct("CT-85")
def test_net_sala_presa_a_uma_interface_usa_o_ip_dela():
    host = HostSession("Brancas", TimeControl.UNLIMITED, bind="127.0.0.1")
    assert decode_room_code(host.code) == "127.0.0.1"
    assert host.offline_warning is None


@pytest.mark.ct("CT-85")
@pytest.mark.parametrize("ipv4", ["127.0.0.1", "10.1.2.3", "172.16.0.1", "192.168.1.1", "169.254.1.1", "100.64.0.1"])
def test_net_enderecos_da_rede_local(ipv4):
    assert is_lan_address(ipv4)


@pytest.mark.ct("CT-85")
@pytest.mark.parametrize("ipv4", ["1.2.3.4", "172.32.0.1", "11.0.0.1"])
def test_net_enderecos_fora_da_rede_local(ipv4):
    assert not is_lan_address(ipv4)
