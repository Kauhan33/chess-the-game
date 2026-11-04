"""Gera toda a documentação, em ordem, uma vez só. É o comando a rodar depois de qualquer mudança no jogo.

Uso: python tools/gerar_documentacao.py [--rapido] [--reusar-testes] [--sem-prints]
  --rapido         pula os testes marcados como `slow`.
  --reusar-testes  não roda o pytest: usa a última execução guardada em build/.
  --sem-prints     não refaz os prints de docs/img/.

Ordem: prints, wireframes, UML, seções geradas, testes e matriz, conferência das referências e PDFs.
Teste falhando não interrompe, porque a falha precisa aparecer nos documentos, mas o código de saída vira 1.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
DOCS_DIR = ROOT / "docs"
KANBAN_DOC = DOCS_DIR / "09-kanban.md"
GRAPHICS_DOC = DOCS_DIR / "06-computacao-grafica.md"
TASKS_FILE = DOCS_DIR / "kanban" / "tarefas.json"
README_FILE = ROOT / "README.md"
BOARD_SQUARES = 64
PIECE_LABELS = {"pawn": "Peão", "knight": "Cavalo", "bishop": "Bispo", "rook": "Torre", "queen": "Dama", "king": "Rei"}

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TOOLS_DIR))

from relatorio_testes import markdown_table, replace_section  # noqa: E402

_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_PROJECT_PATH = re.compile(r"^(?:xadrez|tools|tests|docs|\.github)/[\w./-]+$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_COMMIT_HASH = re.compile(r"^[0-9a-f]{7,40}$")
_LINK_TARGET = re.compile(r"\]\(([^)#\s]+)\)")


def _run_tool(script: str, *arguments: str) -> int:
    """Roda uma ferramenta com o mesmo Python, mostrando a saída dela."""
    print(f"\n=== {script} {' '.join(arguments)}".rstrip(), flush=True)
    return subprocess.run([sys.executable, str(TOOLS_DIR / script), *arguments], cwd=ROOT, check=False).returncode


def _require(script: str, *arguments: str) -> None:
    if _run_tool(script, *arguments) != 0:
        sys.exit(f"{script} falhou: a geração parou aqui.")


def render_meshes() -> str:
    """Conta as faces das malhas reais, para o texto não ficar para trás se um modelo mudar."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from xadrez.core import Board
    from xadrez.graphics import build_piece_meshes

    meshes = build_piece_meshes()
    rows = [(PIECE_LABELS[kind], len(mesh.vertices), len(mesh.faces)) for kind, mesh in meshes.items()]
    table = markdown_table(("Peça", "Vértices", "Faces"), rows)
    piece_faces = sum(len(meshes[piece.kind.value].faces) for _, piece in Board.initial().pieces())
    return (f"{table}\n\nNa posição inicial, as 32 peças somam {piece_faces} faces. Com as {BOARD_SQUARES} casas, "
            f"são {piece_faces + BOARD_SQUARES} polígonos, o valor que a tecla F3 mostra no começo da partida.")


def render_tasks(tasks: dict) -> str:
    order = {column: index for index, column in enumerate(tasks["colunas"])}
    rows = [(task["coluna"], task["id"], task["titulo"], task["marco"], task.get("evidencia", "ainda não feita"))
            for task in sorted(tasks["tarefas"], key=lambda task: order[task["coluna"]])]
    return markdown_table(("Coluna", "ID", "Tarefa", "Marco", "Evidência"), rows)


def render_git_history() -> str:
    log = subprocess.run(["git", "log", "--reverse", "--date=format:%Y-%m-%d %H:%M", "--pretty=%ad|%h|%s"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    rows = [tuple(line.split("|", 2)) for line in log.splitlines()]
    rows = [(date, f"`{commit}`", subject) for date, commit, subject in rows]
    return markdown_table(("Data e hora", "Commit", "Mensagem"), rows)


def update_generated_sections() -> None:
    tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    _replace_sections(KANBAN_DOC, {"kanban": render_tasks(tasks), "evolucao": render_git_history()})
    _replace_sections(GRAPHICS_DOC, {"malhas": render_meshes()})
    print("Seções geradas atualizadas: malhas, Kanban e evolução pelo git.")


def _replace_sections(path: Path, sections: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for name, content in sections.items():
        text = replace_section(text, name, content)
    path.write_text(text, encoding="utf-8")


def _source_text() -> str:
    """Todo o código do projeto, para conferir se os nomes citados nos documentos ainda existem."""
    files = [path for folder in ("xadrez", "tools", "tests") for path in (ROOT / folder).rglob("*.py")]
    return "\n".join(path.read_text(encoding="utf-8") for path in files) + (ROOT / "main.py").read_text(encoding="utf-8")


def find_stale_references() -> list[str]:
    """Caminho ou identificador citado em crase que não existe mais é documento desatualizado."""
    source = _source_text()
    problems = []
    for document in [*sorted(DOCS_DIR.glob("0*.md")), README_FILE]:
        text = document.read_text(encoding="utf-8")
        problems += _broken_links(document, text)
        for span in _CODE_SPAN.findall(text):
            if _PROJECT_PATH.match(span):
                if not (ROOT / span).exists():
                    problems.append(f"{document.name}: o caminho {span} não existe")
            elif _IDENTIFIER.match(span) and not _COMMIT_HASH.match(span) and span.rsplit(".", 1)[-1] not in source:
                problems.append(f"{document.name}: {span} não aparece no código")
    return sorted(set(problems))


def _broken_links(document: Path, text: str) -> list[str]:
    """Imagens e links relativos precisam existir, para o documento abrir certo também no GitHub."""
    targets = [target for target in _LINK_TARGET.findall(text) if not target.startswith("http")]
    return [f"{document.name}: o link {target} não existe" for target in targets if not (document.parent / target).exists()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rapido", action="store_true", help="Pula os testes marcados como slow.")
    parser.add_argument("--reusar-testes", action="store_true", help="Usa a última execução guardada em build/.")
    parser.add_argument("--sem-prints", action="store_true", help="Não refaz os prints de docs/img/.")
    args = parser.parse_args()
    if not args.sem_prints:
        _require("capturar_telas.py")
    _require("gerar_wireframes.py")
    _require("gerar_uml.py")
    update_generated_sections()
    report_arguments = ["--rapido"] if args.rapido else []
    report_arguments += ["--reusar"] if args.reusar_testes else []
    tests_passed = _run_tool("relatorio_testes.py", *report_arguments) == 0
    problems = find_stale_references()
    if problems:
        sys.exit("Referências desatualizadas nos documentos:\n" + "\n".join(f"- {problem}" for problem in problems))
    print("\nReferências dos documentos conferem com o código.")
    _require("gerar_pdf.py")
    print("\nDocumentação gerada." if tests_passed else "\nDocumentação gerada, mas há teste falhando ou rastreabilidade a revisar.")
    return 0 if tests_passed else 1


if __name__ == "__main__":
    sys.exit(main())
