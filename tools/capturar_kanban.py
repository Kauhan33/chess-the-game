"""Tira um print real do quadro Kanban público e salva com a data de hoje no nome.

Uso: python tools/capturar_kanban.py
Resultado: docs/img/kanban/AAAA-MM-DD.png. O enunciado pede a evolução das tarefas ao longo do tempo,
então rode em dias diferentes, depois de mover os cartões. A data do arquivo é sempre a do dia em
que o comando rodou: não há como escolher outra.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from gerar_pdf import find_browser

ROOT = Path(__file__).resolve().parent.parent
BOARD_URL = "https://github.com/users/Kauhan33/projects/1/views/1?layout=board"
OUTPUT_DIR = ROOT / "docs" / "img" / "kanban"
BROWSER_PROFILE = ROOT / "build" / "navegador_kanban"
WINDOW_SIZE = "1800,1100"
PAGE_WAIT_MS = 20000
TIMEOUT_SECONDS = 90


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"{date.today().isoformat()}.png"
    subprocess.run([
        find_browser(), "--headless=new", "--disable-gpu", "--no-first-run",
        f"--user-data-dir={BROWSER_PROFILE}", f"--window-size={WINDOW_SIZE}",
        f"--virtual-time-budget={PAGE_WAIT_MS}", f"--screenshot={output}", BOARD_URL,
    ], check=False, capture_output=True, timeout=TIMEOUT_SECONDS)
    if not output.exists():
        sys.exit("O navegador não gerou o print. Confira a internet e abra o quadro para ver se está público.")
    print(f"Print salvo em {output}. Abra a imagem para conferir antes de colocar no documento.")


if __name__ == "__main__":
    main()
