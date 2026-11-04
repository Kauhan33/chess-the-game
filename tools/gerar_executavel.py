"""Gera o executável do jogo com PyInstaller: arquivo único, sem console e sem precisar de Python.

Uso: python tools/gerar_executavel.py
Resultado: dist/XadrezTheGame.exe (ou XadrezTheGame, fora do Windows).
Requer: pip install pyinstaller pillow
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import PyInstaller.__main__
import pygame
from PIL import Image

from xadrez.graphics import IVORY, Camera, Renderer3D, build_piece_meshes

APP_NAME = "XadrezTheGame"
ICON_PIXELS = 256
ICON_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def build_icon() -> Path:
    """Renderiza o cavalo de marfim com o próprio pipeline do jogo e salva como .ico."""
    pygame.init()
    pygame.display.set_mode((1, 1))
    icon = Renderer3D(Camera()).render_icon(build_piece_meshes()["knight"], IVORY, ICON_PIXELS)
    png_path = ROOT / "build" / "icone.png"
    ico_path = ROOT / "build" / "icone.ico"
    png_path.parent.mkdir(exist_ok=True)
    pygame.image.save(icon, str(png_path))
    Image.open(png_path).save(ico_path, sizes=ICON_SIZES)
    pygame.quit()
    return ico_path


def main() -> None:
    icon = build_icon()
    PyInstaller.__main__.run([
        str(ROOT / "main.py"),
        "--name", APP_NAME,
        "--onefile",
        "--windowed",
        "--icon", str(icon),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build" / "pyinstaller"),
        "--noconfirm",
        "--clean",
    ])
    print(f"\nExecutável: {ROOT / 'dist' / APP_NAME}")


if __name__ == "__main__":
    main()
