"""CT-83: arquivo corrompido, pasta sem permissão e falha no meio da gravação não derrubam o jogo."""
import json
import os
import tempfile

import pytest

from xadrez.data import AccountError, AccountStore, DataError, HistoryStore, MatchRecord
from xadrez.data import storage

PASSWORD = "cavalo-em-f3-2026"
VALID_ACCOUNT = {"username": "Conta", "salt": "00" * 16, "iterations": 1000, "hash": "00" * 32}


def record():
    return MatchRecord(
        played_at="2026-11-04T10:00:00",
        opponent="CPU",
        opponent_kind="cpu",
        difficulty="Easy",
        color="white",
        outcome="vitoria",
        reason="Xeque-mate",
        moves=10,
        seconds=60.0,
        time_control="10+0",
        mode="Treinamento",
        pgn="1. e4 *",
        final_fen="8/8/8/8/8/8/8/8 w - - 0 1",
    )


def accounts_with(**changes):
    return json.dumps({"version": 1, "accounts": [{**VALID_ACCOUNT, **changes}]}).encode()


BAD_ACCOUNT_FILES = {
    "binario": b"\xff\xfe\x00\x80lixo",
    "texto": b"isto nao e json",
    "vazio": b"",
    "truncado": b'{"version": 1, "accounts": [{"username": "Co',
    "lista": b"[]",
    "numero": b"123",
    "nulo": b"null",
    "sem-versao": b'{"accounts": []}',
    "versao-futura": b'{"version": 99, "accounts": []}',
    "contas-nao-lista": b'{"version": 1, "accounts": 7}',
    "entrada-nao-objeto": b'{"version": 1, "accounts": ["Conta"]}',
    "sem-sal": b'{"version": 1, "accounts": [{"username": "Conta"}]}',
    "sal-invalido": accounts_with(salt="nao-e-hexa"),
    "sal-curto": accounts_with(salt="00"),
    "sal-numero": accounts_with(salt=7),
    "hash-curto": accounts_with(hash="00"),
    "iteracoes-texto": accounts_with(iterations="1000"),
    "iteracoes-booleano": accounts_with(iterations=True),
    "iteracoes-zero": accounts_with(iterations=0),
    "iteracoes-absurdas": accounts_with(iterations=10**12),
    "nome-invalido": accounts_with(username="a"),
    "nome-numero": accounts_with(username=7),
    "repetida": json.dumps({"version": 1, "accounts": [VALID_ACCOUNT, {**VALID_ACCOUNT, "username": "CONTA"}]}).encode(),
    "aninhamento-profundo": b"[" * 200_000,
    "numero-gigante": b"9" * 10_000,
}


def corrupted_copies(directory, name):
    return sorted(directory.glob(f"{name}.corrompido-*"))


@pytest.mark.ct("CT-83")
@pytest.mark.parametrize("content", BAD_ACCOUNT_FILES.values(), ids=BAD_ACCOUNT_FILES.keys())
def test_data_arquivo_de_contas_ruim_vira_lista_vazia_e_copia_guardada(isolated_data_dir, content):
    isolated_data_dir.mkdir(parents=True)
    path = isolated_data_dir / "accounts.json"
    path.write_bytes(content)
    store = AccountStore()
    assert store.usernames() == []
    assert not path.exists()
    copies = corrupted_copies(isolated_data_dir, "accounts.json")
    assert [copy.read_bytes() for copy in copies] == [content]
    store.create("Conta", PASSWORD)
    assert store.authenticate("Conta", PASSWORD) is True


@pytest.mark.ct("CT-83")
def test_data_arquivo_de_contas_real_truncado_nao_derruba(isolated_data_dir):
    store = AccountStore()
    store.create("Conta Um", PASSWORD)
    path = isolated_data_dir / "accounts.json"
    path.write_bytes(path.read_bytes()[: path.stat().st_size // 2])
    assert store.authenticate("Conta Um", PASSWORD) is False
    assert store.usernames() == []
    assert len(corrupted_copies(isolated_data_dir, "accounts.json")) == 1


@pytest.mark.ct("CT-83")
def test_data_duas_corrupcoes_seguidas_guardam_duas_copias(isolated_data_dir):
    isolated_data_dir.mkdir(parents=True)
    path = isolated_data_dir / "accounts.json"
    store = AccountStore()
    for content in (b"lixo 1", b"lixo 2"):
        path.write_bytes(content)
        assert store.usernames() == []
    assert len(corrupted_copies(isolated_data_dir, "accounts.json")) == 2


@pytest.mark.ct("CT-83")
@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xfe\x00",
        b"[]",
        b'{"version": 2, "records": []}',
        b'{"version": 1, "records": 3}',
        b'{"version": 1, "records": [1]}',
        b'{"version": 1, "records": [{"opponent": "CPU"}]}',
        b'{"version": 1, "records": [' + b"[" * 200_000,
    ],
    ids=["binario", "lista", "versao", "records-numero", "entrada-numero", "campos-faltando", "profundo"],
)
def test_data_historico_ruim_vira_lista_vazia_e_copia_guardada(isolated_data_dir, content):
    store = HistoryStore("Conta")
    store.add(record())
    path = next(isolated_data_dir.glob("history-*.json"))
    path.write_bytes(content)
    assert store.records() == []
    assert store.stats().played == 0
    assert [copy.read_bytes() for copy in corrupted_copies(isolated_data_dir, path.name)] == [content]
    store.add(record())
    assert store.records() == [record()]


@pytest.mark.ct("CT-83")
def test_data_historico_com_valor_invalido_em_um_campo_e_posto_de_lado(isolated_data_dir):
    store = HistoryStore("Conta")
    store.add(record())
    path = next(isolated_data_dir.glob("history-*.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0]["seconds"] = float("inf")
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert store.records() == []
    assert len(corrupted_copies(isolated_data_dir, path.name)) == 1


@pytest.mark.ct("CT-83")
def test_data_corrompido_que_nao_pode_ser_renomeado_ainda_vira_lista_vazia(isolated_data_dir, monkeypatch):
    isolated_data_dir.mkdir(parents=True)
    (isolated_data_dir / "accounts.json").write_bytes(b"lixo")

    def refuse(*args):
        raise PermissionError("recusado")

    monkeypatch.setattr(storage.os, "replace", refuse)
    assert AccountStore().usernames() == []


@pytest.fixture
def blocked_directory(tmp_path):
    """Um arquivo no lugar da pasta: falha de verdade em qualquer sistema, mesmo rodando como administrador."""
    path = tmp_path / "bloqueado"
    path.write_bytes(b"sou um arquivo")
    return path


@pytest.mark.ct("CT-83")
def test_data_pasta_impossivel_vira_erro_claro_nas_contas(blocked_directory):
    store = AccountStore(blocked_directory)
    with pytest.raises(AccountError, match="Não foi possível"):
        store.create("Conta", PASSWORD)
    assert store.usernames() == []
    assert store.authenticate("Conta", PASSWORD) is False


@pytest.mark.ct("CT-83")
def test_data_pasta_impossivel_vira_erro_claro_no_historico(blocked_directory):
    store = HistoryStore("Conta", blocked_directory)
    with pytest.raises(DataError, match="Não foi possível"):
        store.add(record())
    assert store.records() == []
    assert store.stats().played == 0


@pytest.mark.ct("CT-83")
def test_data_sem_permissao_de_escrita_vira_erro_claro(isolated_data_dir, monkeypatch):
    """Por mock porque `chmod` não restringe pasta no Windows, e o administrador do CI ignora permissões."""

    def refuse(*args, **kwargs):
        raise PermissionError("recusado")

    monkeypatch.setattr(tempfile, "mkstemp", refuse)
    with pytest.raises(AccountError, match="permissão") as caught:
        AccountStore().create("Conta", PASSWORD)
    assert PASSWORD not in str(caught.value)
    with pytest.raises(DataError, match="permissão"):
        HistoryStore("Conta").add(record())


@pytest.mark.ct("CT-83")
def test_data_erro_de_leitura_nao_apaga_o_que_ja_existe(isolated_data_dir, monkeypatch):
    """Sem isto, um erro passageiro faria a gravação seguinte substituir as contas por uma lista vazia."""
    store = AccountStore()
    store.create("Conta Um", PASSWORD)
    original = (isolated_data_dir / "accounts.json").read_bytes()

    def refuse(self):
        raise PermissionError("recusado")

    with monkeypatch.context() as patch:
        patch.setattr(storage.Path, "read_bytes", refuse)
        with pytest.raises(AccountError, match="ler"):
            store.create("Conta Dois", PASSWORD)
        assert store.usernames() == []
        assert store.authenticate("Conta Um", PASSWORD) is False
        assert HistoryStore("Conta Um").records() == []
    assert (isolated_data_dir / "accounts.json").read_bytes() == original
    assert store.authenticate("Conta Um", PASSWORD) is True


@pytest.mark.ct("CT-83")
def test_data_falha_na_troca_mantem_o_arquivo_antigo_e_nao_deixa_temporario(isolated_data_dir, monkeypatch):
    store = AccountStore()
    store.create("Conta Um", PASSWORD)
    original = (isolated_data_dir / "accounts.json").read_bytes()

    def refuse(*args):
        raise OSError("disco cheio")

    with monkeypatch.context() as patch:
        patch.setattr(storage.os, "replace", refuse)
        with pytest.raises(AccountError):
            store.create("Conta Dois", PASSWORD)
    assert (isolated_data_dir / "accounts.json").read_bytes() == original
    assert [path.name for path in isolated_data_dir.iterdir()] == ["accounts.json"]


@pytest.mark.ct("CT-83")
def test_data_troca_bloqueada_por_um_instante_tenta_de_novo(isolated_data_dir, monkeypatch):
    real_replace = os.replace
    attempts = []

    def blocked_twice(source, target):
        attempts.append(target)
        if len(attempts) <= 2:
            raise PermissionError("outra cópia do jogo lendo")
        real_replace(source, target)

    monkeypatch.setattr(storage.os, "replace", blocked_twice)
    monkeypatch.setattr(storage, "_REPLACE_RETRY_SECONDS", 0)
    store = AccountStore()
    store.create("Conta", PASSWORD)
    assert len(attempts) == 3
    assert store.authenticate("Conta", PASSWORD) is True


@pytest.mark.ct("CT-83")
def test_data_troca_sempre_bloqueada_desiste_e_nao_deixa_temporario(isolated_data_dir, monkeypatch):
    isolated_data_dir.mkdir(parents=True)

    def always_blocked(*args):
        raise PermissionError("bloqueado")

    monkeypatch.setattr(storage.os, "replace", always_blocked)
    monkeypatch.setattr(storage, "_REPLACE_RETRY_SECONDS", 0)
    with pytest.raises(AccountError):
        AccountStore().create("Conta", PASSWORD)
    assert list(isolated_data_dir.iterdir()) == []


@pytest.mark.ct("CT-83")
def test_data_remocao_do_temporario_que_falha_nao_troca_o_erro(isolated_data_dir, monkeypatch):
    def refuse(*args):
        raise OSError("sem acesso")

    with monkeypatch.context() as patch:
        patch.setattr(storage.os, "replace", refuse)
        patch.setattr(storage.os, "remove", refuse)
        with pytest.raises(DataError, match="Não foi possível gravar"):
            storage.write_json_atomic(isolated_data_dir / "a.json", {})
