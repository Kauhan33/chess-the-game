"""Contas e histórico guardados neste computador, em Python puro: sem pygame, numpy nem as outras camadas."""
from .accounts import LOGIN_FAILED_MESSAGE, AccountError, AccountStore
from .history import HistoryStats, HistoryStore, MatchRecord
from .paths import data_dir
from .storage import DataError

__all__ = [
    "AccountError",
    "AccountStore",
    "DataError",
    "HistoryStats",
    "HistoryStore",
    "LOGIN_FAILED_MESSAGE",
    "MatchRecord",
    "data_dir",
]
