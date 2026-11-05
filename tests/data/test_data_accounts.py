"""CT-80: criar conta, entrar, recusar senha errada e nome repetido. CT-81: a senha nunca vai para o disco."""
import base64
import hashlib
import json
import os
import stat
import sys
import unicodedata

import pytest

from xadrez.data import LOGIN_FAILED_MESSAGE, AccountError, AccountStore
from xadrez.data import accounts as accounts_module

PASSWORD = "cavalo-em-f3-2026"
# Por `chr`, e não literais: caractere invisível no código-fonte é exatamente o que este projeto recusa nos nomes.
BIDI_OVERRIDE = chr(0x202E)
ZERO_WIDTH_SPACE = chr(0x200B)


@pytest.fixture
def store(isolated_data_dir):
    return AccountStore()


@pytest.mark.ct("CT-80")
def test_data_cria_e_entra_com_a_senha_certa(store):
    store.create("Conta Um", PASSWORD)
    assert store.authenticate("Conta Um", PASSWORD) is True


@pytest.mark.ct("CT-80")
def test_data_recusa_senha_errada_e_usuario_inexistente(store):
    store.create("Conta Um", PASSWORD)
    assert store.authenticate("Conta Um", PASSWORD + "x") is False
    assert store.authenticate("Conta Dois", PASSWORD) is False


@pytest.mark.ct("CT-80")
def test_data_mensagem_de_login_nao_diz_o_que_falhou():
    assert LOGIN_FAILED_MESSAGE == "Usuário ou senha incorretos."


@pytest.mark.ct("CT-80")
def test_data_usuario_inexistente_custa_o_mesmo_hash(store, monkeypatch):
    """Responder sem calcular revelaria, pelo tempo, quais nomes de conta existem."""
    calls = []
    real_hash = accounts_module._hash_password
    monkeypatch.setattr(accounts_module, "_hash_password", lambda *args: calls.append(args[2]) or real_hash(*args))
    assert store.authenticate("Ninguem", PASSWORD) is False
    assert calls == [accounts_module._PBKDF2_ITERATIONS]


@pytest.mark.ct("CT-80")
@pytest.mark.parametrize("repeated", ["Conta Um", "conta um", "CONTA UM", "  Conta Um  "])
def test_data_recusa_nome_repetido_sem_diferenciar_maiusculas(store, repeated):
    store.create("Conta Um", PASSWORD)
    with pytest.raises(AccountError, match="Já existe"):
        store.create(repeated, "outra-senha-qualquer")
    assert store.authenticate("Conta Um", PASSWORD) is True
    assert store.authenticate("Conta Um", "outra-senha-qualquer") is False


@pytest.mark.ct("CT-80")
def test_data_nome_nao_diferencia_maiusculas_e_preserva_a_grafia(store):
    store.create("CoNtA", PASSWORD)
    assert store.authenticate("conta", PASSWORD) is True
    assert store.authenticate("CONTA", PASSWORD) is True
    assert store.usernames() == ["CoNtA"]


@pytest.mark.ct("CT-80")
def test_data_grafias_unicode_equivalentes_sao_a_mesma_conta(store):
    composed, decomposed = (unicodedata.normalize(form, "Peão") for form in ("NFC", "NFD"))
    assert composed != decomposed
    store.create(composed, PASSWORD)
    with pytest.raises(AccountError):
        store.create(decomposed, PASSWORD)
    assert store.authenticate(decomposed.upper(), PASSWORD) is True


@pytest.mark.ct("CT-80")
def test_data_senha_tem_mesma_identidade_em_formas_unicode_diferentes(store):
    composed, decomposed = (unicodedata.normalize(form, "café-com-leite") for form in ("NFC", "NFD"))
    assert composed != decomposed
    store.create("Conta", composed)
    assert store.authenticate("Conta", decomposed) is True


@pytest.mark.ct("CT-80")
def test_data_lista_nomes_em_ordem_alfabetica(store):
    for name in ("zeta", "Alfa", "beta"):
        store.create(name, PASSWORD)
    assert store.usernames() == ["Alfa", "beta", "zeta"]


@pytest.mark.ct("CT-80")
def test_data_outra_copia_do_jogo_ve_a_conta_criada(isolated_data_dir):
    first, second = AccountStore(), AccountStore()
    first.create("Conta Um", PASSWORD)
    second.create("Conta Dois", PASSWORD)
    assert first.usernames() == ["Conta Dois", "Conta Um"]
    assert second.authenticate("Conta Um", PASSWORD) is True


@pytest.mark.ct("CT-80")
def test_data_aceita_os_limites_de_tamanho(store):
    store.create("abc", "12345678")
    store.create("a" * 16, "x" * 500)
    assert store.authenticate("abc", "12345678")
    assert store.authenticate("a" * 16, "x" * 500)


@pytest.mark.ct("CT-80")
@pytest.mark.parametrize(
    "name",
    ["", "ab", "   ", "  ab  ", "a" * 17, "com\ncontrole", "abc\x00def", "abc\x1bdef", f"abc{BIDI_OVERRIDE}def", f"abc{ZERO_WIDTH_SPACE}def", None, 123],
    ids=["vazio", "curto", "espacos", "curto-com-espacos", "longo", "nova-linha", "nulo", "escape", "bidi", "largura-zero", "None", "numero"],
)
def test_data_recusa_nome_invalido(store, name):
    with pytest.raises(AccountError):
        store.create(name, PASSWORD)
    assert store.usernames() == []


@pytest.mark.ct("CT-80")
@pytest.mark.parametrize("password", ["", "1234567", None, 12345678], ids=["vazia", "curta", "None", "numero"])
def test_data_recusa_senha_fraca_ou_invalida(store, password):
    with pytest.raises(AccountError, match="senha"):
        store.create("Conta", password)
    assert store.usernames() == []


@pytest.mark.ct("CT-80")
@pytest.mark.parametrize("username, password", [(None, PASSWORD), ("Conta", None), (123, 456), (b"Conta", PASSWORD)])
def test_data_login_com_tipos_errados_so_responde_nao(store, username, password):
    store.create("Conta", PASSWORD)
    assert store.authenticate(username, password) is False


@pytest.mark.ct("CT-80")
def test_data_senha_com_surrogate_solto_nao_derruba(store):
    store.create("Conta", "\ud800-senha-estranha")
    assert store.authenticate("Conta", "\ud800-senha-estranha") is True
    assert store.authenticate("Conta", "\udfff-senha-estranha") is False


@pytest.mark.ct("CT-80")
def test_data_registra_as_iteracoes_reais_por_conta(store, isolated_data_dir, production_iterations):
    store.create("Conta", PASSWORD)
    assert store.authenticate("Conta", PASSWORD) is True
    entry = json.loads((isolated_data_dir / "accounts.json").read_text(encoding="utf-8"))["accounts"][0]
    assert entry["iterations"] == production_iterations >= 600_000


@pytest.mark.ct("CT-80")
def test_data_conta_antiga_com_menos_iteracoes_continua_entrando(store, isolated_data_dir):
    """As iterações ficam gravadas por conta justamente para poder subir o padrão sem invalidar quem já existe."""
    salt = bytes(range(16))
    old_hash = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode("utf-8"), salt, 1000)
    entry = {"username": "Antiga", "salt": salt.hex(), "iterations": 1000, "hash": old_hash.hex()}
    isolated_data_dir.mkdir(parents=True)
    (isolated_data_dir / "accounts.json").write_text(json.dumps({"version": 1, "accounts": [entry]}), encoding="utf-8")
    assert store.authenticate("Antiga", PASSWORD) is True
    assert store.authenticate("Antiga", "senha-errada-aqui") is False


@pytest.mark.ct("CT-81")
@pytest.mark.parametrize("password", [PASSWORD, "sênhä-com-acênto"], ids=["ascii", "acentos"])
def test_data_senha_nao_aparece_em_nenhum_byte(store, isolated_data_dir, password):
    store.create("Conta", password)
    assert store.authenticate("Conta", password)
    encoded = password.encode("utf-8")
    forms = [
        encoded,
        encoded.hex().encode(),
        password.encode("utf-16-le"),
        password.encode("utf-16-be"),
        base64.b64encode(encoded),
        json.dumps(password).encode(),
    ]
    files = [path for path in isolated_data_dir.rglob("*") if path.is_file()]
    assert files
    for path in files:
        raw = path.read_bytes()
        assert not any(form in raw for form in forms), path.name
        assert not any(form.lower() in raw.lower() for form in forms), path.name


@pytest.mark.ct("CT-81")
def test_data_arquivo_guarda_so_nome_sal_iteracoes_e_hash(store, isolated_data_dir):
    store.create("Conta", PASSWORD)
    entry = json.loads((isolated_data_dir / "accounts.json").read_text(encoding="utf-8"))["accounts"][0]
    assert set(entry) == {"username", "salt", "iterations", "hash"}
    assert len(bytes.fromhex(entry["salt"])) == 16
    assert len(bytes.fromhex(entry["hash"])) == 32


@pytest.mark.ct("CT-81")
def test_data_sal_diferente_para_a_mesma_senha(store, isolated_data_dir):
    store.create("Conta Um", PASSWORD)
    store.create("Conta Dois", PASSWORD)
    first, second = json.loads((isolated_data_dir / "accounts.json").read_text(encoding="utf-8"))["accounts"]
    assert first["salt"] != second["salt"]
    assert first["hash"] != second["hash"]


@pytest.mark.ct("CT-81")
def test_data_erro_nao_repete_a_senha(store):
    store.create("Conta", PASSWORD)
    with pytest.raises(AccountError) as caught:
        store.create("Conta", PASSWORD)
    assert PASSWORD not in str(caught.value)
    with pytest.raises(AccountError) as caught:
        store.create("x", PASSWORD)
    assert PASSWORD not in str(caught.value)


# Sem marca de CT de propósito: o relatório conta teste pulado como falha do caso, e no Windows este é pulado.
@pytest.mark.skipif(sys.platform == "win32", reason="permissões de dono são um conceito POSIX")
def test_data_arquivo_de_contas_so_o_dono_le(store, isolated_data_dir):
    store.create("Conta", PASSWORD)
    mode = stat.S_IMODE(os.stat(isolated_data_dir / "accounts.json").st_mode)
    assert mode == 0o600
