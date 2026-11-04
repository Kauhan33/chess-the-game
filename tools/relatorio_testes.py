"""Roda os testes e gera, a partir da execução real, o plano de testes e a matriz de rastreabilidade.

Uso: python tools/relatorio_testes.py [--rapido] [--reusar]
  --rapido  pula os testes marcados como `slow` (perft profundo).
  --reusar  não roda o pytest: usa a última execução guardada em build/.

Junta o resultado do pytest (`--ct-report`, JUnit e cobertura) com as especificações de
docs/testes/casos.json e escreve as seções geradas de docs/07-plano-de-testes.md e todo o
docs/08-matriz-rastreabilidade.md. Falha com mensagem clara se um RF ficar sem UC ou CT, se um CT
não existir na execução ou se faltar especificação. Teste que falhou aparece como falha no documento.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN_FILE = ROOT / "docs" / "plans" / "2026-11-03-xadrez-design.md"
CASES_FILE = ROOT / "docs" / "testes" / "casos.json"
MEASURES_FILE = ROOT / "docs" / "testes" / "medicoes.json"
RESULT_FILE = ROOT / "docs" / "testes" / "resultado.json"
TEST_PLAN_FILE = ROOT / "docs" / "07-plano-de-testes.md"
MATRIX_FILE = ROOT / "docs" / "08-matriz-rastreabilidade.md"
BUILD_DIR = ROOT / "build"
CT_REPORT_FILE = BUILD_DIR / "relatorio_ct.json"
JUNIT_FILE = BUILD_DIR / "relatorio_junit.xml"
COVERAGE_FILE = BUILD_DIR / "cobertura.json"
RUN_INFO_FILE = BUILD_DIR / "relatorio_execucao.json"

COVERAGE_GOAL = 90.0
LAYERS = ("core", "graphics", "ui")
CT_GROUPS = (
    ("Motor de regras", 1, 29),
    ("Computação gráfica", 30, 39),
    ("Interface", 40, 49),
    ("Ataques do QA", 50, 999),
)
_SPEC_FIELDS = ("titulo", "entrada", "procedimento", "esperado", "rf", "uc")


@dataclass
class Execution:
    """Tudo o que veio da execução real."""

    generated_at: str
    totals: dict
    cases: dict
    junit: dict[str, list[str]]
    coverage: dict
    info: dict


def _git(*arguments: str) -> str:
    completed = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True)
    return completed.stdout.strip()


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "desconhecida"


def run_tests(is_quick: bool) -> None:
    """Roda o pytest. Teste falhando não interrompe: a falha precisa aparecer no documento."""
    BUILD_DIR.mkdir(exist_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", f"--ct-report={CT_REPORT_FILE}", f"--junitxml={JUNIT_FILE}",
               "--cov=xadrez", "--cov-branch", "--cov-report=term", f"--cov-report=json:{COVERAGE_FILE}"]
    if is_quick:
        command += ["-m", "not slow"]
    print("Rodando:", " ".join(command[1:]))
    subprocess.run(command, cwd=ROOT, check=False)
    info = {
        "is_quick": is_quick,
        "python": platform.python_version(),
        "system": f"{platform.system()} {platform.release()}",
        "pytest": _package_version("pytest"),
        "pygame": _package_version("pygame"),
        "numpy": _package_version("numpy"),
        "commit": _git("rev-parse", "--short", "HEAD"),
        "has_local_changes": bool(_git("status", "--porcelain", "--", "xadrez", "tests")),
    }
    RUN_INFO_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_junit() -> dict[str, list[str]]:
    """Resultado de cada teste pelo nome, sem o parâmetro: teste parametrizado vira uma lista."""
    outcomes: dict[str, list[str]] = {}
    for case in ElementTree.parse(JUNIT_FILE).getroot().iter("testcase"):
        failed = case.find("failure") is not None or case.find("error") is not None
        skipped = case.find("skipped") is not None
        outcome = "failed" if failed else "skipped" if skipped else "passed"
        outcomes.setdefault(case.get("name").split("[")[0], []).append(outcome)
    return outcomes


def load_execution() -> Execution:
    required = (CT_REPORT_FILE, JUNIT_FILE, COVERAGE_FILE, RUN_INFO_FILE)
    missing = [path.name for path in required if not path.exists()]
    if missing:
        sys.exit(f"Não há execução guardada em build/ ({', '.join(missing)}). Rode sem --reusar.")
    report = json.loads(CT_REPORT_FILE.read_text(encoding="utf-8"))
    return Execution(
        generated_at=report["generated_at"],
        totals=report["totals"],
        cases=report["cases"],
        junit=_read_junit(),
        coverage=json.loads(COVERAGE_FILE.read_text(encoding="utf-8")),
        info=json.loads(RUN_INFO_FILE.read_text(encoding="utf-8")),
    )


def read_design_ids() -> dict:
    """IDs da seção 7 do design, a fonte única: RF e RNF com o texto, CT com o foco e os requisitos."""
    text = DESIGN_FILE.read_text(encoding="utf-8")
    requirements = re.findall(r"^\| (RF\d+) \| (.+?) \|$", text, re.MULTILINE)
    non_functional = re.findall(r"^\| (RNF\d+) \| (.+?) \|$", text, re.MULTILINE)
    cases = re.findall(r"^\| (CT-\d+) \| (.+?) \| (.+?) \|$", text, re.MULTILINE)
    return {
        "rf": dict(requirements),
        "rnf": dict(non_functional),
        "ct": {case_id: [item.strip() for item in linked.split(",")] for case_id, _, linked in cases},
    }


def _spec_skeleton(case_id: str, execution: Execution) -> str:
    """Modelo pronto para colar em casos.json, com os testes que precisam ser descritos."""
    tests = [test["test"] for test in execution.cases.get(case_id, {}).get("tests", [])]
    skeleton = {case_id: {"titulo": "", "rf": [], "uc": [], "entrada": "", "procedimento": "", "esperado": ""}}
    return json.dumps(skeleton, ensure_ascii=False) + f"  (testes: {', '.join(tests) or 'nenhum'})"


def _traceability_problems(spec: dict, design: dict) -> list[str]:
    problems = []
    cases, links = spec["casos"], spec["rf_para_uc"]
    covered_rfs = {rf for case in cases.values() for rf in case["rf"]}
    for rf in design["rf"]:
        if not links.get(rf):
            problems.append(f"{rf} está sem caso de uso em rf_para_uc.")
        if rf not in covered_rfs:
            problems.append(f"{rf} está sem caso de teste.")
    linked_ucs = {uc for ucs in links.values() for uc in ucs}
    problems += [f"{uc} não está ligado a nenhum RF." for uc in spec["ucs"] if uc not in linked_ucs]
    for case_id, linked in design["ct"].items():
        if case_id in cases and set(cases[case_id]["rf"]) != set(linked):
            problems.append(f"{case_id}: RF diferente do design ({cases[case_id]['rf']} em vez de {linked}).")
    return problems


def _spec_problems(spec: dict, design: dict, execution: Execution) -> list[str]:
    problems = []
    known = set(design["rf"]) | set(design["rnf"])
    executed_ids = set(execution.cases)
    for case_id in sorted((set(design["ct"]) | executed_ids) - set(spec["casos"])):
        problems.append(f"{case_id} está sem especificação em casos.json. Modelo: {_spec_skeleton(case_id, execution)}")
    for case_id, case in spec["casos"].items():
        if case_id not in executed_ids:
            problems.append(f"{case_id} está especificado, mas não existe na execução.")
        problems += [f"{case_id}: falta {field}." for field in _SPEC_FIELDS if not case.get(field)]
        problems += [f"{case_id}: requisito desconhecido {rf}." for rf in case.get("rf", []) if rf not in known]
        problems += [f"{case_id}: caso de uso desconhecido {uc}." for uc in case.get("uc", []) if uc not in spec["ucs"]]
    return problems


def _evidence_problems(spec: dict, design: dict, execution: Execution) -> list[str]:
    problems = [f"{rnf} está sem evidência em casos.json." for rnf in design["rnf"] if rnf not in spec["rnf"]]
    for rnf, entry in spec["rnf"].items():
        problems += [f"{rnf}: o teste {test} não existe na execução." for test in entry["testes"]
                     if test not in execution.junit]
    return problems


def validate(spec: dict, design: dict, execution: Execution) -> None:
    problems = _spec_problems(spec, design, execution)
    if not problems:
        problems = _traceability_problems(spec, design) + _evidence_problems(spec, design, execution)
    if problems:
        sys.exit("Rastreabilidade incompleta. Corrija docs/testes/casos.json:\n" + "\n".join(f"- {p}" for p in problems))


def _decimal(value: float, places: int = 2) -> str:
    return f"{value:.{places}f}".replace(".", ",")


def _count_label(count: int) -> str:
    return f"{count} teste" if count == 1 else f"{count} testes"


def obtained_result(case: dict) -> str:
    """O texto de "Resultado Obtido": sai só do que o pytest relatou."""
    tests = case["tests"]
    passed = sum(test["outcome"] == "passed" for test in tests)
    if passed == len(tests):
        return f"Conforme o esperado (PASSOU: {passed} de {_count_label(len(tests))})"
    failed = ", ".join(test["test"].split("::")[-1] for test in tests if test["outcome"] != "passed")
    return f"Diferente do esperado (FALHOU: {passed} de {_count_label(len(tests))} passaram; não passaram: {failed})"


def _case_number(case_id: str) -> int:
    return int(case_id.split("-")[1])


def markdown_table(header: tuple[str, ...], rows: list[tuple]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell).replace("|", "/") for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def render_run_summary(execution: Execution, measures: dict) -> str:
    info, totals = execution.info, execution.totals
    total = sum(totals.values())
    linked = sum(len(case["tests"]) for case in execution.cases.values())
    mode = "rápido, sem os testes marcados como `slow`" if info["is_quick"] else "completo, com os testes `slow`"
    changes = " (com alterações locais em `xadrez/` ou `tests/`)" if info["has_local_changes"] else ""
    fps_commit = measures["janela_real"]["commit"]
    return "\n".join((
        f"- **Data e hora da execução:** {execution.generated_at.replace('T', ' ')}",
        f"- **Commit testado:** `{info['commit']}`{changes}. As medições de FPS são do commit `{fps_commit}`.",
        f"- **Ambiente:** Python {info['python']}, {info['system']}, pytest {info['pytest']}, "
        f"pygame {info['pygame']}, numpy {info['numpy']}",
        f"- **Modo:** {mode}",
        f"- **Total:** {total} testes: {totals['passed']} passaram, {totals['failed']} falharam, "
        f"{totals['skipped']} foram pulados. Destes, {linked} estão vinculados a {len(execution.cases)} casos de teste.",
    ))


def render_focus_table(spec: dict, execution: Execution) -> str:
    rows = []
    for focus, case_ids in spec["focos_do_enunciado"].items():
        total = sum(len(execution.cases[case_id]["tests"]) for case_id in case_ids)
        passed = sum(test["outcome"] == "passed" for case_id in case_ids for test in execution.cases[case_id]["tests"])
        rows.append((focus, ", ".join(case_ids), f"{passed} de {_count_label(total)} passaram"))
    return markdown_table(("Foco exigido", "Casos", "Resultado real"), rows)


def render_cases(spec: dict, execution: Execution) -> str:
    sections = []
    for title, first, last in CT_GROUPS:
        ids = [case_id for case_id in sorted(spec["casos"], key=_case_number) if first <= _case_number(case_id) <= last]
        if not ids:
            continue
        rows = [_case_row(case_id, spec["casos"][case_id], execution) for case_id in ids]
        sections.append(f"### {title}\n\n" + markdown_table(
            ("Caso", "Entrada", "Procedimento", "Resultado Esperado", "Resultado Obtido"), rows))
    return "\n\n".join(sections)


def _case_row(case_id: str, case: dict, execution: Execution) -> tuple:
    links = ", ".join(case["rf"] + case["uc"])
    identity = f"**{case_id}** {case['titulo']} ({links})"
    return identity, case["entrada"], case["procedimento"], case["esperado"], obtained_result(execution.cases[case_id])


def coverage_by_layer(execution: Execution) -> dict[str, dict]:
    layers = {layer: dict(statements=0, covered=0, branches=0, covered_branches=0) for layer in LAYERS}
    for path, data in execution.coverage["files"].items():
        parts = Path(path).as_posix().split("/")
        if len(parts) < 3 or parts[1] not in layers:
            continue
        summary, layer = data["summary"], layers[parts[1]]
        layer["statements"] += summary["num_statements"]
        layer["covered"] += summary["covered_lines"]
        layer["branches"] += summary["num_branches"]
        layer["covered_branches"] += summary["covered_branches"]
    for layer in layers.values():
        layer["percent"] = 100.0 * (layer["covered"] + layer["covered_branches"]) / (layer["statements"] + layer["branches"])
    return layers


def render_coverage(execution: Execution) -> str:
    layers = coverage_by_layer(execution)
    rows = [(f"`xadrez/{name}`", f"{layer['covered']} de {layer['statements']}",
             f"{layer['covered_branches']} de {layer['branches']}", f"{_decimal(layer['percent'])}%")
            for name, layer in layers.items()]
    totals = execution.coverage["totals"]
    rows.append(("**Total**", f"{totals['covered_lines']} de {totals['num_statements']}",
                 f"{totals['covered_branches']} de {totals['num_branches']}", f"**{_decimal(totals['percent_covered'])}%**"))
    return markdown_table(("Camada", "Linhas cobertas", "Ramos cobertos", "Cobertura"), rows)


def _tests_evidence(tests: list[str], execution: Execution) -> tuple[str, bool]:
    if not tests:
        return "", True
    outcomes = [outcome for test in tests for outcome in execution.junit[test]]
    passed = outcomes.count("passed")
    names = ", ".join(f"`{test}`" for test in tests)
    return f"Testes {names}: {passed} de {len(outcomes)} passaram.", passed == len(outcomes)


def _fps_evidence(measures: dict) -> str:
    fps = measures["janela_real"]
    return (f"`{fps['ferramenta']}`, janela real em {fps['resolucao']}, com `display.flip`: "
            f"{_decimal(fps['fps_medio'], 1)} FPS médios em {fps['quadros']} quadros, intervalo médio de "
            f"{_decimal(fps['intervalo_medio_ms'])} ms, p95 de {_decimal(fps['intervalo_p95_ms'])} ms, "
            f"p99 de {_decimal(fps['intervalo_p99_ms'])} ms, máximo de {_decimal(fps['intervalo_max_ms'])} ms. "
            f"{fps['quadros_acima_de_25_ms']} quadros passaram de 25 ms ({_decimal(fps['percentual_acima_de_25_ms'])}%).")


def _rnf_row(rnf: str, description: str, entry: dict, execution: Execution, measures: dict) -> tuple:
    evidence, tests_passed = _tests_evidence(entry["testes"], execution)
    kind = entry.get("medicao")
    status = "Atendido" if tests_passed else "Não atendido: há teste falhando"
    if kind == "fps":
        evidence = f"{_fps_evidence(measures)} {evidence}"
        status = "Atendido nesta máquina" if tests_passed else status
    elif kind == "portabilidade":
        info = execution.info
        evidence = (f"Executado: Python {info['python']} em {info['system']}. "
                    f"{measures['pendencias_portabilidade']} {evidence}")
        status = "Atendido nos testes. Janela real só no Windows"
    elif kind == "cobertura_core":
        core = coverage_by_layer(execution)["core"]
        evidence = (f"Cobertura medida de {_decimal(core['percent'])}% em `xadrez/core` "
                    f"({core['statements']} linhas e {core['branches']} ramos).")
        status = "Atendido" if core["percent"] >= COVERAGE_GOAL else "Não atendido"
    return f"**{rnf}** {description}", entry["criterio"], evidence, status


def render_rnf(spec: dict, design: dict, execution: Execution, measures: dict) -> str:
    rows = [_rnf_row(rnf, design["rnf"][rnf], spec["rnf"][rnf], execution, measures) for rnf in design["rnf"]]
    return markdown_table(("Requisito", "Critério de aceite", "Evidência real", "Situação"), rows)


def render_machine(measures: dict) -> str:
    machine, fps = measures["maquina"], measures["janela_real"]
    return (f"O FPS em janela real depende da máquina. Máquina usada: {machine['cpu']}, {machine['gpu']}, "
            f"{machine['memoria_gb']} GB de memória, {machine['sistema']}. {machine['observacao']} "
            f"Na mesma medição, o trabalho médio por quadro foi de {_decimal(fps['trabalho_medio_ms'])} ms, "
            f"e a troca do menu para a partida levou {fps['troca_menu_partida_ms']} ms.")


def render_benchmark(measures: dict) -> str:
    bench = measures["sem_janela"]
    rows = [(item["nome"], item["quadros"], f"{_decimal(item['media_ms'])} ms", f"{_decimal(item['p95_ms'])} ms",
             f"{_decimal(item['p99_ms'])} ms", f"{_decimal(item['max_ms'])} ms", item["acima_de_16_67"])
            for item in bench["cenarios"]]
    table = markdown_table(("Cenário", "Quadros", "Média", "p95", "p99", "Máximo", "Acima de 16,67 ms"), rows)
    return f"`{bench['ferramenta']}`, commit `{bench['commit']}`, {bench['resolucao']}. {bench['observacao']}\n\n{table}"


def _case_status(case_ids: list[str], execution: Execution) -> str:
    failed = [case_id for case_id in case_ids if execution.cases[case_id]["status"] != "PASSOU"]
    return f"FALHOU: {', '.join(failed)}" if failed else "PASSOU"


def render_matrix(spec: dict, design: dict, execution: Execution) -> str:
    cases = sorted(spec["casos"], key=_case_number)
    by_rf = {rf: [case_id for case_id in cases if rf in spec["casos"][case_id]["rf"]] for rf in design["rf"]}
    rf_rows = [(f"**{rf}**", text, ", ".join(spec["rf_para_uc"][rf]), ", ".join(by_rf[rf]),
                _case_status(by_rf[rf], execution)) for rf, text in design["rf"].items()]
    uc_rows = []
    for uc, name in spec["ucs"].items():
        rfs = [rf for rf in design["rf"] if uc in spec["rf_para_uc"][rf]]
        linked = [case_id for case_id in cases if uc in spec["casos"][case_id]["uc"]]
        uc_rows.append((f"**{uc}** {name}", ", ".join(rfs), ", ".join(linked), _case_status(linked, execution)))
    ct_rows = [(f"**{case_id}** {spec['casos'][case_id]['titulo']}", ", ".join(spec["casos"][case_id]["rf"]),
                ", ".join(spec["casos"][case_id]["uc"]), execution.cases[case_id]["status"]) for case_id in cases]
    return "\n".join((
        "# 8. Matriz de rastreabilidade", "",
        "Arquivo gerado por `tools/relatorio_testes.py`. Não edite à mão: os vínculos ficam em "
        "`docs/testes/casos.json`, e a situação vem da execução real.", "",
        f"Execução de {execution.generated_at.replace('T', ' ')}, commit `{execution.info['commit']}`.", "",
        "## 8.1 Requisito, caso de uso e caso de teste", "",
        markdown_table(("RF", "Requisito", "Casos de uso", "Casos de teste", "Situação"), rf_rows), "",
        "## 8.2 Caso de uso, requisito e caso de teste", "",
        markdown_table(("Caso de uso", "Requisitos", "Casos de teste", "Situação"), uc_rows), "",
        "## 8.3 Caso de teste, requisito e caso de uso", "",
        markdown_table(("Caso de teste", "Requisitos", "Casos de uso", "Situação"), ct_rows), "",
    ))


def replace_section(text: str, name: str, content: str) -> str:
    """Troca o trecho entre os marcadores da seção. Marcador ausente é erro, para nada ficar para trás."""
    pattern = re.compile(rf"(<!-- GERADO:{name} -->\n).*?(<!-- FIM:{name} -->)", re.DOTALL)
    if not pattern.search(text):
        sys.exit(f"Marcadores da seção {name!r} não encontrados no documento.")
    return pattern.sub(lambda match: f"{match.group(1)}{content}\n{match.group(2)}", text)


def write_documents(spec: dict, design: dict, execution: Execution, measures: dict) -> None:
    sections = {
        "execucao": render_run_summary(execution, measures),
        "focos": render_focus_table(spec, execution),
        "casos": render_cases(spec, execution),
        "cobertura": render_coverage(execution),
        "rnf": render_rnf(spec, design, execution, measures),
        "maquina": render_machine(measures),
        "benchmark": render_benchmark(measures),
    }
    text = TEST_PLAN_FILE.read_text(encoding="utf-8")
    for name, content in sections.items():
        text = replace_section(text, name, content)
    TEST_PLAN_FILE.write_text(text, encoding="utf-8")
    MATRIX_FILE.write_text(render_matrix(spec, design, execution), encoding="utf-8")
    RESULT_FILE.write_text(json.dumps(_result_summary(execution), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _result_summary(execution: Execution) -> dict:
    """Registro da execução que fica junto dos documentos, para conferir de onde vieram os números."""
    layers = coverage_by_layer(execution)
    return {
        "generated_at": execution.generated_at,
        "info": execution.info,
        "totals": execution.totals,
        "coverage_percent": {name: round(layer["percent"], 2) for name, layer in layers.items()}
        | {"total": round(execution.coverage["totals"]["percent_covered"], 2)},
        "cases": {
            case_id: {"status": case["status"], "tests": len(case["tests"]),
                      "passed": sum(test["outcome"] == "passed" for test in case["tests"])}
            for case_id, case in sorted(execution.cases.items(), key=lambda item: _case_number(item[0]))
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rapido", action="store_true", help="Pula os testes marcados como slow.")
    parser.add_argument("--reusar", action="store_true", help="Usa a última execução guardada em build/.")
    args = parser.parse_args()
    if not args.reusar:
        run_tests(args.rapido)
    execution = load_execution()
    spec = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    design = read_design_ids()
    measures = json.loads(MEASURES_FILE.read_text(encoding="utf-8"))
    validate(spec, design, execution)
    write_documents(spec, design, execution, measures)
    print(f"Gerados: {TEST_PLAN_FILE.name}, {MATRIX_FILE.name} e {RESULT_FILE.name}")
    failed = execution.totals["failed"]
    if failed:
        print(f"ATENÇÃO: {failed} testes falharam. Os documentos registram a falha.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
