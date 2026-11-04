"""Peças sob ameaça, rei em xeque e o cuidado de só recalcular quando o estado muda (RF10)."""
import pytest
from ui_helpers import cell, start_game, state_at

from xadrez.core import Color
from xadrez.graphics import MARKER_CORNERS, MARKER_TRIANGLE, CellState
from xadrez.ui import theme as tokens

THREAT_LINE = "e2e4 e7e5 g1f3 b8c6 f1c4"
CHECK_LINE = "e2e4 d7d5 f1b5"


@pytest.mark.ct("CT-44")
def test_pecas_ameacadas_aparecem_na_matriz_com_forma_e_tint(app):
    scene, player = start_game(app)
    player.play_all(THREAT_LINE)
    for name in ("e5", "f7"):
        assert state_at(scene, name) == CellState.THREAT
        assert scene.view.tints[cell(name)] == tokens.THREAT_TINT
        assert (*cell(name), MARKER_TRIANGLE, tokens.MARKER_THREAT_COLOR) in scene.view.markers
    assert state_at(scene, "c6") == CellState.NONE


@pytest.mark.ct("CT-44")
def test_xeque_marca_o_rei_e_os_atacantes_e_avisa_na_faixa(app):
    scene, player = start_game(app)
    player.play_all(CHECK_LINE)
    assert state_at(scene, "e8") == CellState.CHECK
    assert state_at(scene, "b5") == CellState.CHECK
    assert scene.view.tints[cell("e8")] == tokens.CHECK_TINT
    assert (*cell("b5"), MARKER_CORNERS, tokens.MARKER_CHECK_COLOR) in scene.view.markers
    assert scene.notices.text.startswith("Xeque!")
    assert scene.notices.kind == "danger"


@pytest.mark.ct("CT-44")
def test_alertas_somem_quando_a_jogada_resolve_o_xeque(app):
    scene, player = start_game(app)
    player.play_all(CHECK_LINE)
    player.play("c7c6")
    assert state_at(scene, "e8") == CellState.NONE
    assert scene.notices.kind == "turn"
    assert cell("e8") not in scene.view.tints


def test_alertas_so_sao_recalculados_quando_o_estado_muda(app, monkeypatch):
    scene, player = start_game(app)
    player.play_all(THREAT_LINE)
    calls = []
    original = scene.engine.threatened_pieces
    monkeypatch.setattr(scene.engine, "threatened_pieces", lambda color: calls.append(color) or original(color))
    player.frames(60)
    assert calls == []
    player.play("g8f6")
    assert len(calls) == 1


def test_casa_ameacada_pisca_mas_a_cor_e_funcao_do_tempo(app):
    scene, player = start_game(app)
    player.play_all(THREAT_LINE)
    e5 = cell("e5")
    colors = set()
    for _ in range(40):
        player.frames(1)
        colors.add(tuple(scene.view.matrix.rgb(scene.view.time)[e5]))
    assert len(colors) > 1


def test_ultimo_lance_continua_marcado_junto_com_a_ameaca(app):
    scene, player = start_game(app)
    player.play_all(THREAT_LINE)
    assert state_at(scene, "f1") == CellState.LAST_MOVE
    assert state_at(scene, "c4") == CellState.LAST_MOVE


def test_placa_de_quem_esta_em_xeque_mostra_o_estado(app):
    scene, player = start_game(app)
    player.play_all(CHECK_LINE)
    assert scene.hud.cards[Color.BLACK].info.status == "check"
    assert scene.hud.cards[Color.WHITE].info.status is None
