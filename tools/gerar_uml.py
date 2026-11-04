"""Gera as imagens UML de docs/uml/img/ e confere os diagramas de classes contra o código real.

Uso: python tools/gerar_uml.py [--so-conferir]
Requer Java e o PlantUML em tools/.cache/plantuml.jar. Sem Graphviz: os diagramas usam smetana.

A conferência lê o código com `ast`. Toda classe, atributo e método citado em um diagrama de classes, e toda
chamada citada em um diagrama de sequência, precisa existir em xadrez/. Assim, um diagrama desatualizado
derruba a geração em vez de ir para a entrega.
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UML_DIR = ROOT / "docs" / "uml"
OUTPUT_DIR_NAME = "img"
PLANTUML_JAR = ROOT / "tools" / ".cache" / "plantuml.jar"
PLANTUML_RELEASES = "https://github.com/plantuml/plantuml/releases"
SOURCE_DIR = ROOT / "xadrez"
CLASS_DIAGRAM_PREFIX = "classes_"
SEQUENCE_DIAGRAM_PREFIX = "seq_"
RENDER_TIMEOUT_SECONDS = 300
_INSTANCE_VARIABLES = {"self", "member"}

_CLASS_OPENING = re.compile(r"^(?:abstract\s+class|class|enum)\s+(\w+)(\s+<<module>>)?[^{]*\{\s*$")
_MEMBER_NAME = re.compile(r"^(?:\{(?:static|abstract)\}\s*)?[+\-#~]?\s*(?:\{(?:static|abstract)\}\s*)?(\w+)")
_SEPARATOR = re.compile(r"^(--|\.\.|==|__)")
_MESSAGE_LINE = re.compile(r"^\s*\w+\s*-+>+\s*\w+\s*:\s*(.+)$")
_CALLED_NAME = re.compile(r"\b(_?[A-Za-z]\w*)\(")


def _names_assigned_in_method(method: ast.AST) -> set[str]:
    """Atributos de instância: `self.nome = ...`, ou `member.nome = ...` no `__new__` de um enum."""
    names = set()
    for node in ast.walk(method):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            if isinstance(node.value, ast.Name) and node.value.id in _INSTANCE_VARIABLES:
                names.add(node.attr)
    return names


def _class_members(class_node: ast.ClassDef) -> set[str]:
    members = set()
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            members.add(node.name)
            members |= _names_assigned_in_method(node)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            members.add(node.target.id)
        elif isinstance(node, ast.Assign):
            members |= {target.id for target in node.targets if isinstance(target, ast.Name)}
    return members


def _read_source_model() -> tuple[dict[str, set[str]], dict[str, list[str]], dict[str, set[str]]]:
    """Lê classes, bases e funções de módulo de todo o pacote xadrez."""
    members: dict[str, set[str]] = defaultdict(set)
    bases: dict[str, list[str]] = defaultdict(list)
    modules: dict[str, set[str]] = {}
    for source_file in SOURCE_DIR.rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        modules[source_file.stem] = {
            node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                members[node.name] |= _class_members(node)
                bases[node.name] += [base.id for base in node.bases if isinstance(base, ast.Name)]
    return members, bases, modules


def _all_members_of(class_name: str, members: dict[str, set[str]], bases: dict[str, list[str]]) -> set[str]:
    """Membros da classe, somados aos herdados das classes do projeto."""
    collected = set(members.get(class_name, set()))
    for base in bases.get(class_name, []):
        collected |= _all_members_of(base, members, bases)
    return collected


def _diagram_blocks(path: Path) -> list[tuple[str, bool, list[str]]]:
    """Devolve (nome da classe, se é módulo, nomes dos membros) de cada bloco `class X { ... }`."""
    blocks = []
    current: tuple[str, bool, list[str]] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if current is None:
            opening = _CLASS_OPENING.match(line)
            if opening:
                current = (opening.group(1), bool(opening.group(2)), [])
            continue
        if line == "}":
            blocks.append(current)
            current = None
            continue
        member = _MEMBER_NAME.match(line)
        if member and not _SEPARATOR.match(line):
            current[2].append(member.group(1))
    return blocks


def _declarations(path: Path) -> list[tuple[str, bool]]:
    """Devolve (nome, se é módulo) de toda classe declarada, com ou sem bloco de membros."""
    declaration = re.compile(r"^\s*(?:abstract\s+class|class|enum)\s+(\w+)([^\n{]*<<module>>)?", re.MULTILINE)
    return [(match.group(1), bool(match.group(2))) for match in declaration.finditer(path.read_text(encoding="utf-8"))]


def find_divergences() -> list[str]:
    """Compara cada diagrama de classes com o código. Lista vazia significa que tudo confere."""
    members, bases, modules = _read_source_model()
    problems = []
    for path in sorted(UML_DIR.glob(f"{CLASS_DIAGRAM_PREFIX}*.puml")):
        for name, is_module in _declarations(path):
            if name not in (modules if is_module else members):
                problems.append(f"{path.name}: {name} não existe em xadrez/")
        for name, is_module, member_names in _diagram_blocks(path):
            known = modules.get(name, set()) if is_module else _all_members_of(name, members, bases)
            for member in member_names:
                if member not in known:
                    problems.append(f"{path.name}: {name}.{member} não existe em xadrez/")
    return problems


def _callable_names() -> set[str]:
    """Toda função, método e classe do pacote: o que uma mensagem de sequência pode citar."""
    names: set[str] = set()
    for source_file in SOURCE_DIR.rglob("*.py"):
        for node in ast.walk(ast.parse(source_file.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
    return names


def find_sequence_divergences() -> list[str]:
    """Toda chamada citada em uma mensagem de um diagrama de sequência precisa existir no código."""
    known = _callable_names()
    problems = []
    for path in sorted(UML_DIR.glob(f"{SEQUENCE_DIAGRAM_PREFIX}*.puml")):
        for line in path.read_text(encoding="utf-8").splitlines():
            message = _MESSAGE_LINE.match(line)
            if message:
                problems += [f"{path.name}: {name}() não existe em xadrez/"
                             for name in _CALLED_NAME.findall(message.group(1)) if name not in known]
    return problems


def render_diagrams() -> None:
    """Chama o PlantUML para todos os .puml. Erro de sintaxe encerra com a mensagem dele."""
    java = shutil.which("java")
    if java is None:
        sys.exit("Java não encontrado. Instale um JRE 8 ou mais novo para gerar os diagramas.")
    if not PLANTUML_JAR.exists():
        sys.exit(f"PlantUML não encontrado em {PLANTUML_JAR}. Baixe o plantuml.jar de {PLANTUML_RELEASES}.")
    sources = sorted(path.name for path in UML_DIR.glob("*.puml"))
    command = [java, "-Djava.awt.headless=true", "-jar", str(PLANTUML_JAR), "-charset", "UTF-8", "-tpng", "-nometadata",
               "-o", OUTPUT_DIR_NAME, *sources]
    completed = subprocess.run(command, cwd=UML_DIR, capture_output=True, text=True, timeout=RENDER_TIMEOUT_SECONDS)
    if completed.returncode != 0:
        sys.exit(f"O PlantUML recusou um diagrama:\n{completed.stdout}\n{completed.stderr}")
    print(f"{len(sources)} diagramas gerados em {UML_DIR / OUTPUT_DIR_NAME}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--so-conferir", action="store_true", help="Só compara os diagramas com o código.")
    args = parser.parse_args()
    problems = find_divergences() + find_sequence_divergences()
    if problems:
        sys.exit("Diagramas diferentes do código:\n" + "\n".join(f"- {problem}" for problem in problems))
    print("Diagramas de classes e de sequência conferem com o código.")
    if not args.so_conferir:
        render_diagrams()


if __name__ == "__main__":
    main()
