"""Garante a regra de dependência entre as camadas (RNF05)."""
import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent / "xadrez"

FORBIDDEN_IMPORTS = {
    "core": {"pygame", "numpy", "xadrez.graphics", "xadrez.ui"},
    "graphics": {"xadrez.core", "xadrez.ui"},
}


def imported_modules(source_file):
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def is_forbidden(module, forbidden):
    return any(module == name or module.startswith(f"{name}.") for name in forbidden)


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_camada_nao_importa_o_que_nao_deve(layer):
    violations = [
        f"{source_file.name} importa {module}"
        for source_file in (PACKAGE / layer).rglob("*.py")
        for module in imported_modules(source_file)
        if is_forbidden(module, FORBIDDEN_IMPORTS[layer])
    ]
    assert not violations, violations
