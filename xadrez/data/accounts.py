"""Contas com senha guardadas neste computador. A senha nunca vai para o disco, só o hash dela."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .paths import data_dir
from .storage import DataError, quarantine, read_json, write_json_atomic

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 16
MIN_PASSWORD_LENGTH = 8
# Mensagem única de propósito: dizer qual dos dois falhou ensinaria quais nomes de conta existem.
LOGIN_FAILED_MESSAGE = "Usuário ou senha incorretos."

_ACCOUNTS_FILE = "accounts.json"
_FORMAT_VERSION = 1
_HASH_NAME = "sha256"
_HASH_BYTES = 32
_SALT_BYTES = 16
# Mínimo recomendado pela OWASP para PBKDF2-HMAC-SHA256. Medido em 0,17 s por verificação: forte, sem travar a tela.
_PBKDF2_ITERATIONS = 600_000
# Um arquivo adulterado com número absurdo de iterações congelaria o login; acima disto ele é arquivo ruim.
_MAX_STORED_ITERATIONS = 10_000_000
_DECOY_SALT = bytes(_SALT_BYTES)


class AccountError(DataError):
    """Problema com a conta, com mensagem em pt-BR pronta para a tela."""


@dataclass(frozen=True)
class _Account:
    username: str
    salt: bytes
    iterations: int
    password_hash: bytes


def username_key(username: str) -> str:
    """Identidade da conta: "Ana", "ANA" e a mesma grafia em outra forma Unicode são a mesma pessoa."""
    return unicodedata.normalize("NFKC", username.strip()).casefold()


class AccountStore:
    """Sem cache em memória: duas cópias do jogo abertas no mesmo computador veem as contas uma da outra."""

    def __init__(self, directory: Path | None = None) -> None:
        self._path = (data_dir() if directory is None else Path(directory)) / _ACCOUNTS_FILE

    def create(self, username: str, password: str) -> None:
        """Cria a conta ou levanta `AccountError` com o motivo."""
        clean_name = _clean_username(username)
        _require_valid_password(password)
        key = username_key(clean_name)
        try:
            accounts = self._load()
            if key in accounts:
                raise AccountError("Já existe uma conta com esse nome.")
            accounts[key] = _new_account(clean_name, password)
            write_json_atomic(self._path, _serialize(accounts))
        except AccountError:
            raise
        except DataError as error:
            raise AccountError(str(error)) from error

    def authenticate(self, username: str, password: str) -> bool:
        """Sem exceção: em qualquer falha a resposta é não, e a tela mostra `LOGIN_FAILED_MESSAGE`."""
        if not isinstance(username, str) or not isinstance(password, str):
            return False
        account = self._find(username)
        if account is None:
            # Calcula mesmo sem conta: responder mais rápido revelaria que o nome não existe.
            _hash_password(password, _DECOY_SALT, _PBKDF2_ITERATIONS)
            return False
        computed = _hash_password(password, account.salt, account.iterations)
        return hmac.compare_digest(account.password_hash, computed)

    def usernames(self) -> list[str]:
        """Nomes na grafia original, em ordem alfabética sem diferenciar maiúsculas."""
        try:
            accounts = self._load()
        except DataError:
            return []
        return sorted((account.username for account in accounts.values()), key=str.casefold)

    def _find(self, username: str) -> _Account | None:
        try:
            return self._load().get(username_key(username))
        except DataError:
            return None

    def _load(self) -> dict[str, _Account]:
        payload = read_json(self._path)
        if payload is None:
            return {}
        try:
            return _parse_accounts(payload)
        except (AccountError, KeyError, TypeError, ValueError):
            quarantine(self._path)
            return {}


def _clean_username(username: object) -> str:
    if not isinstance(username, str):
        raise AccountError("Digite um nome de usuário.")
    clean_name = username.strip()
    if not MIN_USERNAME_LENGTH <= len(clean_name) <= MAX_USERNAME_LENGTH:
        raise AccountError(f"O nome precisa ter de {MIN_USERNAME_LENGTH} a {MAX_USERNAME_LENGTH} caracteres.")
    # `isprintable` recusa controle e também o que engana a leitura, como inversão de direção e largura zero.
    if not clean_name.isprintable():
        raise AccountError("O nome tem caracteres que não podem ser usados.")
    return clean_name


def _require_valid_password(password: object) -> None:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError(f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.")


def _hash_password(password: str, salt: bytes, iterations: int) -> bytes:
    # NFKC: o mesmo texto pode chegar em formas Unicode diferentes conforme o teclado e o sistema.
    normalized = unicodedata.normalize("NFKC", password).encode("utf-8", "surrogatepass")
    return hashlib.pbkdf2_hmac(_HASH_NAME, normalized, salt, iterations)


def _new_account(username: str, password: str) -> _Account:
    salt = secrets.token_bytes(_SALT_BYTES)
    return _Account(username, salt, _PBKDF2_ITERATIONS, _hash_password(password, salt, _PBKDF2_ITERATIONS))


def _serialize(accounts: dict[str, _Account]) -> dict[str, object]:
    return {
        "version": _FORMAT_VERSION,
        "accounts": [
            {
                "username": account.username,
                "salt": account.salt.hex(),
                "iterations": account.iterations,
                "hash": account.password_hash.hex(),
            }
            for account in accounts.values()
        ],
    }


def _parse_accounts(payload: object) -> dict[str, _Account]:
    """Levanta exceção em qualquer formato inesperado: quem chama põe o arquivo inteiro de lado."""
    if payload["version"] != _FORMAT_VERSION:
        raise ValueError("versão desconhecida")
    accounts: dict[str, _Account] = {}
    for entry in payload["accounts"]:
        account = _parse_account(entry)
        key = username_key(account.username)
        if key in accounts:
            raise ValueError("conta repetida")
        accounts[key] = account
    return accounts


def _parse_account(entry: dict[str, object]) -> _Account:
    salt = bytes.fromhex(entry["salt"])
    password_hash = bytes.fromhex(entry["hash"])
    iterations = entry["iterations"]
    if type(iterations) is not int or not 1 <= iterations <= _MAX_STORED_ITERATIONS:
        raise ValueError("iterações fora da faixa")
    if len(salt) < _SALT_BYTES or len(password_hash) != _HASH_BYTES:
        raise ValueError("sal ou hash de tamanho errado")
    return _Account(_clean_username(entry["username"]), salt, iterations, password_hash)
