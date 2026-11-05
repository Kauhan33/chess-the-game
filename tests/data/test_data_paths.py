"""CT-83: o local dos dados em cada sistema, e a variável de ambiente que os testes usam."""
import os
from pathlib import Path

import pytest

from xadrez.data import AccountStore, data_dir
from xadrez.data.paths import _platform_dir


@pytest.mark.ct("CT-83")
def test_data_variavel_de_ambiente_substitui_o_local(tmp_path, monkeypatch):
    monkeypatch.setenv("CHESS_THE_GAME_DATA", str(tmp_path / "x"))
    assert data_dir() == tmp_path / "x"


@pytest.mark.ct("CT-83")
def test_data_pasta_do_sistema_quando_nao_ha_variavel(monkeypatch):
    monkeypatch.delenv("CHESS_THE_GAME_DATA")
    assert data_dir().name in ("ChessTheGame", "chess-the-game")


@pytest.mark.ct("CT-83")
def test_data_pasta_no_windows_usa_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert _platform_dir("win32") == tmp_path / "ChessTheGame"


@pytest.mark.ct("CT-83")
def test_data_pasta_no_windows_sem_appdata_usa_a_pasta_do_usuario(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    assert _platform_dir("win32") == Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "ChessTheGame"


@pytest.mark.ct("CT-83")
def test_data_pasta_no_macos():
    assert _platform_dir("darwin") == Path(os.path.expanduser("~")) / "Library" / "Application Support" / "ChessTheGame"


@pytest.mark.ct("CT-83")
def test_data_pasta_no_linux():
    assert _platform_dir("linux") == Path(os.path.expanduser("~")) / ".local" / "share" / "chess-the-game"


@pytest.mark.ct("CT-83")
def test_data_nada_e_gravado_ao_abrir_so_ao_criar(isolated_data_dir):
    store = AccountStore()
    assert store.usernames() == []
    assert not isolated_data_dir.exists()
    store.create("Conta", "senha-de-teste-1")
    assert isolated_data_dir.is_dir()


@pytest.mark.ct("CT-83")
def test_data_diretorio_aceita_texto_alem_de_path(tmp_path):
    store = AccountStore(str(tmp_path))
    store.create("Conta", "senha-de-teste-1")
    assert (tmp_path / "accounts.json").is_file()
