"""Leitura e escrita de JSON em disco, sem perder dados numa queda e sem derrubar o jogo com arquivo ruim."""
from __future__ import annotations

import json
import os
import secrets
import tempfile
import time
from datetime import datetime
from pathlib import Path

_QUARANTINE_MARK = "corrompido"
_REPLACE_ATTEMPTS = 5
_REPLACE_RETRY_SECONDS = 0.05
_PRIVATE_DIRECTORY_MODE = 0o700


class DataError(Exception):
    """Falha ao ler ou gravar os dados, com mensagem em pt-BR pronta para a tela."""


def read_json(path: Path) -> object | None:
    """Devolve o conteúdo do arquivo, ou None se ele não existe ou não era JSON (e foi posto de lado).

    Erro de leitura é diferente de arquivo ruim: levanta `DataError`, porque seguir com a lista vazia faria
    a próxima gravação apagar dados que ainda estão lá, só inacessíveis agora.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise DataError(f"Não foi possível ler {path.name}. Verifique a permissão da pasta de dados do jogo.") from error
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        payload = None
    if payload is None:
        quarantine(path)
    return payload


def quarantine(path: Path) -> None:
    """Guarda o arquivo ruim com outro nome, para a pessoa ainda poder recuperá-lo, e libera o nome original.

    Se nem renomear for possível, segue em frente: o jogo começa vazio de qualquer forma.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.{_QUARANTINE_MARK}-{stamp}-{secrets.token_hex(3)}")
    try:
        os.replace(path, target)
    except OSError:
        pass


def write_json_atomic(path: Path, payload: object) -> None:
    """Grava num temporário da mesma pasta e troca de uma vez: quem lê vê o arquivo antigo ou o novo, nunca metade.

    `mkstemp` cria o arquivo só com permissão para o dono, e a troca preserva isso nos sistemas com permissões.
    """
    text = json.dumps(payload, indent=2)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=_PRIVATE_DIRECTORY_MODE)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                file.write(text)
                file.flush()
                os.fsync(file.fileno())
            _replace_with_retry(temporary, path)
        except OSError:
            _remove_quietly(temporary)
            raise
    except OSError as error:
        raise DataError(
            "Não foi possível gravar na pasta de dados do jogo. Verifique o espaço livre e a permissão da pasta."
        ) from error


def _replace_with_retry(source: str, target: Path) -> None:
    """No Windows, outra cópia do jogo ou o antivírus lendo o arquivo bloqueiam a troca por um instante."""
    for _ in range(_REPLACE_ATTEMPTS - 1):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            time.sleep(_REPLACE_RETRY_SECONDS)
    os.replace(source, target)


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
