"""Código de sala: o IPv4 de quem criou a sala escrito em 7 caracteres fáceis de ditar, com conferência.

Sem 0, O, 1, I e L sobram 31 símbolos, não 32. Por isso o código é um número em base 31, e não 35 bits em
base 32. Como 31^7 cabe 6,4 vezes em 2^32, o número guarda `ip * 6 + conferência`. Isso dá 6 valores de
conferência, que pegam cerca de 5 em cada 6 dígitos trocados. Pegar todos exigiria 31 valores, e não há espaço.
"""
from __future__ import annotations

import hashlib
import ipaddress
import socket

ROOM_CODE_LENGTH = 7
LOOPBACK_IPV4 = "127.0.0.1"

_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_BASE = len(_ALPHABET)
_CHECK_VALUES = 6
_IPV4_VALUES = 2**32
_BAD_CODE = "Código de sala inválido. Confira se foi digitado certo."
# O primeiro destino segue a rota padrão. Os outros acham a placa quando a rede local não tem roteador.
_ROUTE_PROBES = ("192.0.2.1", "10.255.255.254", "172.31.255.254", "192.168.255.254", "169.254.255.254")
_PROBE_PORT = 9


def encode_room_code(ipv4: str) -> str:
    """Levanta `ValueError` se o texto não for um IPv4."""
    try:
        ip_value = int(ipaddress.IPv4Address(ipv4))
    except ValueError as error:
        raise ValueError(f"Endereço IPv4 inválido: {ipv4!r}") from error
    value = ip_value * _CHECK_VALUES + _check_value(ip_value)
    digits = []
    for _ in range(ROOM_CODE_LENGTH):
        value, digit = divmod(value, _BASE)
        digits.append(_ALPHABET[digit])
    return "".join(reversed(digits))


def decode_room_code(code: str) -> str:
    """Aceita minúsculas e espaços, porque a pessoa digita o que ouviu. Levanta `ValueError` em pt-BR."""
    if not isinstance(code, str):
        raise ValueError(_BAD_CODE)
    cleaned = "".join(code.split()).upper()
    if len(cleaned) != ROOM_CODE_LENGTH:
        raise ValueError(f"O código da sala tem {ROOM_CODE_LENGTH} caracteres.")
    if not set(cleaned) <= set(_ALPHABET):
        raise ValueError("Código de sala inválido: ele só usa letras e números, sem 0, O, 1, I e L.")
    value = 0
    for char in cleaned:
        value = value * _BASE + _ALPHABET.index(char)
    ip_value, check = divmod(value, _CHECK_VALUES)
    if ip_value >= _IPV4_VALUES or check != _check_value(ip_value):
        raise ValueError(_BAD_CODE)
    return str(ipaddress.IPv4Address(ip_value))


def local_ipv4() -> str:
    """IP desta máquina na rede local, ou `127.0.0.1` sem rede.

    Em UDP, `connect` só escolhe a rota e não envia nenhum pacote, então isto não depende de internet.
    """
    for probe in _ROUTE_PROBES:
        address = _interface_towards(probe)
        if address is not None:
            return address
    return LOOPBACK_IPV4


def is_lan_address(ipv4: str) -> bool:
    """Diz se o endereço é da rede local. O jogo não conversa com a internet, nem por um código digitado errado."""
    return not ipaddress.IPv4Address(ipv4).is_global


def _check_value(ip_value: int) -> int:
    # Um hash não deixa padrão: nenhum tipo de erro de digitação escapa sempre, e cada um tem a mesma chance de ser pego.
    return hashlib.sha256(ip_value.to_bytes(4, "big")).digest()[0] % _CHECK_VALUES


def _interface_towards(probe: str) -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe_socket:
            probe_socket.connect((probe, _PROBE_PORT))
            address = probe_socket.getsockname()[0]
    except OSError:
        return None
    is_usable = not (ipaddress.IPv4Address(address).is_loopback or ipaddress.IPv4Address(address).is_unspecified)
    return address if is_usable else None
