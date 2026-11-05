"""Onde os dados do jogo ficam em cada sistema operacional."""
from __future__ import annotations

import os
import sys
from pathlib import Path

DATA_DIR_ENV = "CHESS_THE_GAME_DATA"


def data_dir() -> Path:
    """Pasta dos dados deste computador. A variável de ambiente existe para os testes não tocarem na pasta real."""
    override = os.environ.get(DATA_DIR_ENV)
    return Path(override) if override else _platform_dir(sys.platform)


def _platform_dir(platform: str) -> Path:
    # `expanduser` em vez de `Path.home()`: este levanta exceção quando o sistema não informa a pasta do
    # usuário, e o jogo precisa continuar abrindo mesmo assim.
    home = Path(os.path.expanduser("~"))
    if platform == "win32":
        appdata = os.environ.get("APPDATA")
        return (Path(appdata) if appdata else home / "AppData" / "Roaming") / "ChessTheGame"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "ChessTheGame"
    return home / ".local" / "share" / "chess-the-game"
