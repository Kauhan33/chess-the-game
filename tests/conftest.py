"""Configuração comum: SDL sem janela e relatório real dos casos de teste (CT)."""
import json
import os
from datetime import datetime
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def pytest_addoption(parser):
    parser.addoption(
        "--ct-report",
        default=None,
        help="Grava em JSON o resultado de cada caso de teste marcado com @pytest.mark.ct.",
    )


def pytest_configure(config):
    config._ct_results = {}
    config._ct_totals = {"passed": 0, "failed": 0, "skipped": 0}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    is_final_phase = report.when == "call" or (report.when == "setup" and report.outcome != "passed")
    if not is_final_phase:
        return
    item.config._ct_totals[report.outcome] += 1
    for marker in item.iter_markers("ct"):
        tests = item.config._ct_results.setdefault(marker.args[0], [])
        tests.append({"test": report.nodeid, "outcome": report.outcome, "seconds": round(report.duration, 4)})


def _case_status(tests):
    """Teste pulado não é falha (por exemplo, o que só vale em POSIX), mas um caso todo pulado não passou."""
    outcomes = {test["outcome"] for test in tests}
    if "failed" in outcomes:
        return "FALHOU"
    return "PASSOU" if "passed" in outcomes else "PULADO"


def pytest_sessionfinish(session):
    destination = session.config.getoption("--ct-report")
    if not destination:
        return
    cases = {
        case_id: {
            "status": _case_status(tests),
            "tests": tests,
        }
        for case_id, tests in sorted(session.config._ct_results.items())
    }
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "totals": session.config._ct_totals,
        "cases": cases,
    }
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
