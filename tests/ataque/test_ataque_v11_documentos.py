"""O que a banca lê tem de falar da mesma versão que ela vê rodando.

CT-135: a matriz de rastreabilidade, os requisitos e o plano de testes cobrem RF17 a RF24, e cada RF existe mesmo no jogo.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from xadrez.core import Difficulty, TimeControl
from xadrez.data.history import MAX_RECORDS
from xadrez.ui import GameMode
from xadrez.ui.game_scene import GameScene
from xadrez.ui.lobby_scene import ROLE_GUEST, ROLE_HOST
from xadrez.ui.login_scene import LoginScene
from xadrez.ui.match import TIME_CONTROLS

ROOT = Path(__file__).resolve().parents[2]
NEW_REQUIREMENTS = [f"RF{number}" for number in range(17, 25)]


@pytest.mark.ct("CT-135")
def test_cada_requisito_novo_existe_no_jogo():
    assert {mode.label for mode in GameMode} == {"Treinamento", "Partida"}, "RF17"
    assert {level.label for level in Difficulty} == {"Easy", "Medium", "Hard", "Hardcore"}, "RF18"
    assert ROLE_HOST and ROLE_GUEST, "RF19"
    assert hasattr(LoginScene, "play_as_guest") and hasattr(LoginScene, "submit"), "RF20"
    assert MAX_RECORDS == 50, "RF21"
    assert hasattr(GameScene, "copy_pgn"), "RF22"
    assert hasattr(GameScene, "flip_board") and hasattr(GameScene, "_drop_piece"), "RF23"
    times = {control for _, control in TIME_CONTROLS}
    assert {TimeControl.BLITZ_3_2, TimeControl.RAPID_10, TimeControl.CLASSIC_15_10} <= times, "RF24"


@pytest.mark.ct("CT-135")
def test_contrato_da_versao_lista_os_requisitos_novos():
    text = (ROOT / "docs" / "plans" / "2026-11-03-xadrez-design.md").read_text(encoding="utf-8")
    assert all(requirement in text for requirement in NEW_REQUIREMENTS)


@pytest.mark.ct("CT-135")
@pytest.mark.parametrize("document", ["01-visao-e-requisitos.md", "07-plano-de-testes.md", "08-matriz-rastreabilidade.md"])
def test_documentos_da_entrega_cobrem_a_versao_1_1(document):
    text = (ROOT / "docs" / document).read_text(encoding="utf-8")
    assert all(requirement in text for requirement in NEW_REQUIREMENTS)


@pytest.mark.ct("CT-135")
def test_readme_cita_o_que_a_versao_1_1_trouxe():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert all(word in text for word in ("cpu", "rede", "conta", "histórico"))
