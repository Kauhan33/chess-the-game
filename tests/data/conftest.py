"""Nenhum teste de dados pode tocar na pasta real do jogador."""
import pytest

from xadrez.data import accounts

PRODUCTION_ITERATIONS = accounts._PBKDF2_ITERATIONS
_TEST_ITERATIONS = 1000


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    directory = tmp_path / "dados"
    monkeypatch.setenv("CHESS_THE_GAME_DATA", str(directory))
    return directory


@pytest.fixture(autouse=True)
def cheap_password_hash(monkeypatch):
    """O custo real é alto de propósito. Em centenas de contas de teste, ele só deixaria a suíte lenta."""
    monkeypatch.setattr(accounts, "_PBKDF2_ITERATIONS", _TEST_ITERATIONS)


@pytest.fixture
def production_iterations(monkeypatch):
    monkeypatch.setattr(accounts, "_PBKDF2_ITERATIONS", PRODUCTION_ITERATIONS)
    return PRODUCTION_ITERATIONS
