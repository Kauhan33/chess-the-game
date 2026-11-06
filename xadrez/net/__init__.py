"""Sala em rede local por socket, em Python puro: sem pygame, numpy nem as outras camadas."""
from .events import (
    DrawAnswered,
    DrawOffered,
    GameDecided,
    GameStart,
    MoveReceived,
    NetEvent,
    NetworkError,
    PeerJoined,
    PeerLeft,
    PeerResigned,
    RematchRequested,
)
from .protocol import MAX_NAME_CHARS, PROTOCOL_VERSION, parse_uci
from .room_code import decode_room_code, encode_room_code, local_ipv4
from .session import DEFAULT_PORT, ClientSession, HostSession, NetTimings

__all__ = [
    "ClientSession",
    "DEFAULT_PORT",
    "DrawAnswered",
    "DrawOffered",
    "GameDecided",
    "GameStart",
    "HostSession",
    "MAX_NAME_CHARS",
    "MoveReceived",
    "NetEvent",
    "NetTimings",
    "NetworkError",
    "PROTOCOL_VERSION",
    "PeerJoined",
    "PeerLeft",
    "PeerResigned",
    "RematchRequested",
    "decode_room_code",
    "encode_room_code",
    "local_ipv4",
    "parse_uci",
]
