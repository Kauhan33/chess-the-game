"""Prepara o GitHub a partir de docs/kanban/tarefas.json: etiquetas, marcos, issues e o quadro.

Uso: python tools/preparar_github.py [--executar]
Sem a flag, só imprime o que faria e não chama o GitHub. Com `--executar`, usa o `gh` de verdade.
Precisa do repositório já publicado e do escopo `project` no token: gh auth refresh -s project

A issue de uma tarefa já concluída é criada e fechada na hora, e o texto dela diz isso. A data da
issue é a data real da criação: este script não tenta reconstruir o histórico do quadro.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_FILE = ROOT / "docs" / "kanban" / "tarefas.json"
PROJECT_TITLE = "Chess - The Game"
DONE_COLUMN = "Concluído"
MILESTONE_ENDPOINT = "repos/{owner}/{repo}/milestones"
MAX_LISTED_ISSUES = "500"
REQUIRED_SCOPE = "project"
_COLUMN_COLORS = ("GRAY", "YELLOW", "ORANGE", "GREEN")
_UPDATE_STATUS_FIELD = """
mutation($field: ID!) {
  updateProjectV2Field(input: {fieldId: $field, singleSelectOptions: [%s]}) {
    projectV2Field { ... on ProjectV2SingleSelectField { id options { id name } } }
  }
}"""


def milestone_title(code: str, description: str) -> str:
    return f"{code} {description}"


def issue_title(task: dict) -> str:
    return f"{task['id']} {task['titulo']}"


def issue_body(task: dict) -> str:
    lines = [f"Tarefa de `docs/kanban/tarefas.json`. Coluna: {task['coluna']}."]
    if task.get("evidencia"):
        lines.append(f"Evidência: {task['evidencia']}.")
    if task["coluna"] == DONE_COLUMN:
        lines.append("Tarefa já concluída quando esta issue foi criada: a data da issue não é a data do trabalho.")
    return "\n\n".join(lines)


def label_commands(tasks: dict) -> list[list[str]]:
    return [["gh", "label", "create", name, "--color", color, "--force"] for name, color in tasks["etiquetas"].items()]


def milestone_command(code: str, description: str) -> list[str]:
    return ["gh", "api", MILESTONE_ENDPOINT, "-f", f"title={milestone_title(code, description)}"]


def issue_command(task: dict, tasks: dict) -> list[str]:
    command = ["gh", "issue", "create", "--title", issue_title(task), "--body", issue_body(task),
               "--milestone", milestone_title(task["marco"], tasks["marcos"][task["marco"]])]
    for label in task["etiquetas"]:
        command += ["--label", label]
    return command


def status_options_query(columns: list[str]) -> str:
    options = ", ".join(f'{{name: "{column}", color: {color}, description: ""}}'
                        for column, color in zip(columns, _COLUMN_COLORS))
    return _UPDATE_STATUS_FIELD % options


def print_plan(tasks: dict) -> None:
    print("Simulação: nada foi enviado ao GitHub. Use --executar para aplicar.\n")
    print(f"Etiquetas ({len(tasks['etiquetas'])}):")
    for command in label_commands(tasks):
        print(" ", " ".join(command))
    print(f"\nMarcos ({len(tasks['marcos'])}):")
    for code, description in tasks["marcos"].items():
        print(" ", " ".join(milestone_command(code, description)))
    print(f"\nIssues ({len(tasks['tarefas'])}):")
    for task in tasks["tarefas"]:
        print(f"  [{task['coluna']}] {issue_title(task)} ({task['marco']}; {', '.join(task['etiquetas'])})")
    print(f"\nQuadro: gh project create --owner @me --title \"{PROJECT_TITLE}\"")
    print(f"Colunas do campo Status: {', '.join(tasks['colunas'])}")
    print("Cada issue entra no quadro com gh project item-add e gh project item-edit, na coluna da tarefa.")
    print("Depois, é preciso trocar a visualização para Board à mão: o gh não faz isso.")


def _gh(command: list[str]) -> str:
    """Roda o gh e devolve a saída. Erro encerra na hora, com a mensagem dele."""
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        sys.exit(f"Falhou: {' '.join(command)}\n{completed.stderr}")
    return completed.stdout.strip()


def check_prerequisites() -> str:
    """Confere gh, repositório e escopo do token. Devolve o nome do repositório."""
    if shutil.which("gh") is None:
        sys.exit("O GitHub CLI (gh) não está instalado.")
    repository = _gh(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    status = subprocess.run(["gh", "auth", "status"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if f"'{REQUIRED_SCOPE}'" not in status.stdout + status.stderr:
        sys.exit(f"O token não tem o escopo '{REQUIRED_SCOPE}'. Rode: gh auth refresh -s {REQUIRED_SCOPE}")
    return repository


def create_milestones(tasks: dict) -> None:
    existing = set(_gh(["gh", "api", MILESTONE_ENDPOINT, "--paginate", "--jq", ".[].title"]).splitlines())
    for code, description in tasks["marcos"].items():
        if milestone_title(code, description) not in existing:
            _gh(milestone_command(code, description))


def create_issues(tasks: dict) -> dict[str, str]:
    """Cria o que falta e devolve o endereço da issue de cada tarefa. Pode rodar de novo sem duplicar."""
    listed = json.loads(_gh(["gh", "issue", "list", "--state", "all", "--limit", MAX_LISTED_ISSUES, "--json", "title,url"]))
    urls = {issue["title"]: issue["url"] for issue in listed}
    result = {}
    for task in tasks["tarefas"]:
        title = issue_title(task)
        url = urls.get(title) or _create_issue(task, tasks)
        result[task["id"]] = url
    return result


def _create_issue(task: dict, tasks: dict) -> str:
    url = _gh(issue_command(task, tasks))
    if task["coluna"] == DONE_COLUMN:
        _gh(["gh", "issue", "close", url])
    return url


def _find_or_create_project() -> dict:
    """Rodar de novo depois de uma falha reaproveita o quadro em vez de criar outro."""
    listed = json.loads(_gh(["gh", "project", "list", "--owner", "@me", "--format", "json"]))["projects"]
    existing = next((project for project in listed if project["title"] == PROJECT_TITLE), None)
    if existing is not None:
        return existing
    return json.loads(_gh(["gh", "project", "create", "--owner", "@me", "--title", PROJECT_TITLE, "--format", "json"]))


def create_board(tasks: dict, repository: str, issue_urls: dict[str, str]) -> str:
    project = _find_or_create_project()
    number, project_id = str(project["number"]), project["id"]
    # Aqui o dono precisa ser o nome de verdade: o gh monta "dono/repo" e não resolve "@me" nesse caso.
    owner, repository_name = repository.split("/")
    _gh(["gh", "project", "link", number, "--owner", owner, "--repo", repository_name])
    options, field_id = _configure_status_field(number, tasks["colunas"])
    for task in tasks["tarefas"]:
        added = json.loads(_gh(["gh", "project", "item-add", number, "--owner", "@me",
                                "--url", issue_urls[task["id"]], "--format", "json"]))
        _gh(["gh", "project", "item-edit", "--id", added["id"], "--project-id", project_id, "--field-id", field_id,
             "--single-select-option-id", options[task["coluna"]]])
    return project["url"]


def _configure_status_field(number: str, columns: list[str]) -> tuple[dict[str, str], str]:
    fields = json.loads(_gh(["gh", "project", "field-list", number, "--owner", "@me", "--format", "json"]))["fields"]
    field = next(field for field in fields if field["name"] == "Status")
    field_id = field["id"]
    existing = {option["name"]: option["id"] for option in field.get("options", [])}
    if list(existing) == columns:
        # Recriar as opções soltaria as tarefas da coluna, e algumas ficariam em "No Status" na página do quadro.
        return existing, field_id
    answer = _gh(["gh", "api", "graphql", "-f", f"query={status_options_query(columns)}", "-f", f"field={field_id}"])
    options = json.loads(answer)["data"]["updateProjectV2Field"]["projectV2Field"]["options"]
    return {option["name"]: option["id"] for option in options}, field_id


def execute(tasks: dict) -> None:
    repository = check_prerequisites()
    print(f"Repositório: {repository}")
    for command in label_commands(tasks):
        _gh(command)
    create_milestones(tasks)
    issue_urls = create_issues(tasks)
    board_url = create_board(tasks, repository, issue_urls)
    print(f"Quadro criado: {board_url}")
    print("Falta trocar a visualização para Board à mão e começar a capturar os prints.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--executar", action="store_true", help="Aplica no GitHub. Sem isso, só simula.")
    args = parser.parse_args()
    tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    if args.executar:
        execute(tasks)
    else:
        print_plan(tasks)


if __name__ == "__main__":
    main()
