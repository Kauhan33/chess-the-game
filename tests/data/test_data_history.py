"""CT-82: o histórico guarda as 50 mais recentes, em ordem, com estatísticas e sem sair da pasta de dados."""
import json
import math
from dataclasses import asdict, replace

import pytest

from xadrez.data import HistoryStats, HistoryStore, MatchRecord


def record(number=0, **changes):
    fields = {
        "played_at": f"2026-11-04T10:{number:02d}:00",
        "opponent": "CPU",
        "opponent_kind": "cpu",
        "difficulty": "Hard",
        "color": "white",
        "outcome": "vitoria",
        "reason": "Xeque-mate",
        "moves": 20 + number,
        "seconds": 90.5,
        "time_control": "10+0",
        "mode": "Partida",
        "pgn": '[White "Conta"]\n\n1. e4 e5 *',
        "final_fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    }
    return MatchRecord(**{**fields, **changes})


@pytest.mark.ct("CT-82")
def test_data_historico_comeca_vazio():
    store = HistoryStore("Conta")
    assert store.records() == []
    assert store.stats() == HistoryStats(played=0, wins=0, losses=0, draws=0)


@pytest.mark.ct("CT-82")
def test_data_historico_devolve_o_mais_recente_primeiro():
    store = HistoryStore("Conta")
    for number in range(3):
        store.add(record(number))
    assert [item.moves for item in store.records()] == [22, 21, 20]


@pytest.mark.ct("CT-82")
def test_data_historico_guarda_todos_os_campos_em_json():
    store = HistoryStore("Conta")
    original = record(difficulty=None, opponent_kind="rede", opponent="Pretas ♞", seconds=0)
    store.add(original)
    assert store.records() == [original]
    assert asdict(store.records()[0]) == asdict(original)


@pytest.mark.ct("CT-82")
def test_data_51a_partida_empurra_a_mais_antiga(isolated_data_dir):
    store = HistoryStore("Conta")
    for number in range(51):
        store.add(record(number))
    records = store.records()
    assert len(records) == 50
    assert records[0].moves == 20 + 50
    assert records[-1].moves == 20 + 1
    assert all(item.moves != 20 for item in records)
    # O limite vale para o disco também: só cortar na leitura deixaria o arquivo crescer para sempre.
    stored = json.loads(next(isolated_data_dir.glob("history-*.json")).read_text(encoding="utf-8"))
    assert len(stored["records"]) == 50


@pytest.mark.ct("CT-82")
def test_data_arquivo_com_mais_de_50_partidas_e_limitado_na_leitura(isolated_data_dir):
    store = HistoryStore("Conta")
    store.add(record())
    path = next(isolated_data_dir.glob("history-*.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"] = payload["records"] * 60
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert len(store.records()) == 50


@pytest.mark.ct("CT-82")
def test_data_estatisticas_contam_cada_resultado():
    store = HistoryStore("Conta")
    for outcome in ("vitoria", "vitoria", "vitoria", "derrota", "derrota", "empate"):
        store.add(record(outcome=outcome))
    assert store.stats() == HistoryStats(played=6, wins=3, losses=2, draws=1)


@pytest.mark.ct("CT-82")
def test_data_estatisticas_valem_para_as_partidas_guardadas():
    store = HistoryStore("Conta")
    store.add(record(outcome="derrota"))
    for _ in range(50):
        store.add(record(outcome="vitoria"))
    assert store.stats() == HistoryStats(played=50, wins=50, losses=0, draws=0)


@pytest.mark.ct("CT-82")
def test_data_cada_conta_tem_seu_historico_sem_diferenciar_maiusculas():
    HistoryStore("Conta Um").add(record(1))
    HistoryStore("Conta Dois").add(record(2))
    assert [item.moves for item in HistoryStore("CONTA UM").records()] == [21]
    assert [item.moves for item in HistoryStore("conta dois").records()] == [22]


@pytest.mark.ct("CT-82")
def test_data_outra_copia_do_jogo_ve_a_partida_gravada():
    first, second = HistoryStore("Conta"), HistoryStore("Conta")
    first.add(record(1))
    second.add(record(2))
    assert [item.moves for item in first.records()] == [22, 21]


MALICIOUS_NAMES = [
    "../../x",
    "..",
    "../..",
    "..\\..\\x",
    "/raiz/absoluta",
    "\\\\servidor\\pasta",
    "a/b/c",
    "CON",
    "NUL",
    "LPT1",
    "nome.json",
    "a\x00b",
    "a\nb",
    "\ud800",
    "",
    "." * 300,
    "x" * 5000,
]


@pytest.mark.ct("CT-82")
@pytest.mark.parametrize("name", MALICIOUS_NAMES, ids=range(len(MALICIOUS_NAMES)))
def test_data_nome_malicioso_nao_sai_da_pasta_de_dados(tmp_path, name):
    outer = tmp_path / "fora"
    directory = outer / "dentro" / "dados"
    directory.mkdir(parents=True)
    store = HistoryStore(name, directory)
    store.add(record())
    assert store.records() == [record()]
    written = [path for path in outer.rglob("*") if path.is_file()]
    assert len(written) == 1
    assert written[0].parent == directory
    assert written[0].name.startswith("history-") and written[0].name.endswith(".json")
    assert written[0].name.replace("history-", "").replace(".json", "").isalnum()


@pytest.mark.ct("CT-82")
def test_data_nomes_diferentes_nao_dividem_o_arquivo(tmp_path):
    HistoryStore("../../x", tmp_path).add(record(1))
    HistoryStore("x", tmp_path).add(record(2))
    assert [item.moves for item in HistoryStore("../../x", tmp_path).records()] == [21]
    assert [item.moves for item in HistoryStore("x", tmp_path).records()] == [22]


@pytest.mark.ct("CT-82")
@pytest.mark.parametrize(
    "changes",
    [
        {"outcome": "ganhou"},
        {"outcome": None},
        {"opponent_kind": "internet"},
        {"opponent": None},
        {"pgn": 1},
        {"difficulty": 3},
        {"moves": -1},
        {"moves": 1.5},
        {"moves": True},
        {"seconds": -1},
        {"seconds": math.inf},
        {"seconds": math.nan},
        {"seconds": "10"},
        {"seconds": True},
    ],
    ids=lambda changes: "-".join(f"{key}-{value}" for key, value in changes.items()),
)
def test_data_registro_invalido_nem_chega_a_existir(changes):
    with pytest.raises(ValueError):
        record(**changes)


@pytest.mark.ct("CT-82")
def test_data_registro_e_imutavel_e_aceita_campos_validos():
    item = record()
    with pytest.raises(AttributeError):
        item.moves = 1
    assert replace(item, difficulty=None, seconds=12).seconds == 12


@pytest.mark.ct("CT-82")
def test_data_arquivo_de_historico_ignora_campo_extra_de_versao_futura(isolated_data_dir):
    store = HistoryStore("Conta")
    store.add(record())
    path = next(isolated_data_dir.glob("history-*.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0]["novo_campo"] = "qualquer"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert store.records() == [record()]
