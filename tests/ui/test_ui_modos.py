"""Modos Treinamento e Partida: no modo Partida nada diz o que fazer, só o que aconteceu (RF17, CT-90)."""
import pygame
import pytest
from ui_helpers import SCHOLARS_MATE, cell, click, finish_with_mate, move_mouse_off_board, start_game, state_at

from xadrez.core import Color, MoveError, game_to_pgn
from xadrez.graphics import MARKER_CORNERS, CellState
from xadrez.ui import GameMode
from xadrez.ui import theme as tokens
from xadrez.ui.autoplay import click_point, post_mouse_move
from xadrez.ui.game_scene import GENERIC_REFUSAL
from xadrez.ui.hud import STATUS_CHECK, STATUS_TURN
from xadrez.ui.match import without_check_marks

HINT_STATES = {CellState.PATH, CellState.CAPTURE, CellState.THREAT, CellState.CHECK}
PATHS_LINE = "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6"
THREAT_LINE = "e2e4 e7e5 g1f3 b8c6 f1c4"
CHECK_LINE = "e2e4 d7d5 f1b5"
KING_PINNED = "4k3/8/8/8/4r3/8/4N3/4K3 w - - 0 1"


def start_match_mode(app, fen=None, **options):
    return start_game(app, fen, mode=GameMode.MATCH, **options)


def states(scene):
    return {CellState(int(value)) for value in scene.view.matrix.states.flat}


def assert_no_hints(scene):
    assert not states(scene) & HINT_STATES
    assert scene.view.tints == {}
    assert all(marker[2] == MARKER_CORNERS for marker in scene.view.markers), scene.view.markers
    neutral = {tokens.MARKER_SELECTED_COLOR, tokens.MARKER_CURSOR_COLOR}
    assert all(marker[3] in neutral for marker in scene.view.markers), scene.view.markers


@pytest.mark.ct("CT-90")
def test_partida_nao_mostra_caminhos_nem_capturas_da_peca_selecionada(app):
    scene, player = start_match_mode(app)
    player.play_all(PATHS_LINE)
    click(player, "b5")
    move_mouse_off_board(player)
    assert scene.selection == cell("b5")
    assert state_at(scene, "b5") == CellState.SELECTED
    assert state_at(scene, "c6") == CellState.NONE, "a captura do cavalo não pode aparecer"
    assert state_at(scene, "a6") == CellState.LAST_MOVE
    assert scene.view.markers == [(*cell("b5"), MARKER_CORNERS, tokens.MARKER_SELECTED_COLOR)]
    assert_no_hints(scene)


@pytest.mark.ct("CT-90")
def test_treinamento_mostra_tudo_na_mesma_posicao(app):
    scene, player = start_game(app)
    player.play_all(PATHS_LINE)
    click(player, "b5")
    assert state_at(scene, "c6") == CellState.CAPTURE
    assert state_at(scene, "c4") == CellState.PATH
    assert {CellState.PATH, CellState.CAPTURE} <= states(scene)


@pytest.mark.ct("CT-90")
def test_partida_nao_mostra_ameacas(app):
    scene, player = start_match_mode(app)
    player.play_all(THREAT_LINE)
    move_mouse_off_board(player)
    assert state_at(scene, "e5") == CellState.NONE
    assert state_at(scene, "f7") == CellState.NONE
    assert scene.view.markers == []
    assert_no_hints(scene)


@pytest.mark.ct("CT-90")
def test_partida_nao_mostra_xeque_em_lugar_nenhum(app):
    scene, player = start_match_mode(app)
    player.play_all(CHECK_LINE)
    move_mouse_off_board(player)
    assert scene.engine.in_check, "o rei está em xeque de verdade"
    assert scene.view.markers == [], "nem com o rei em xeque aparece marcador"
    assert_no_hints(scene)
    assert "Xeque" not in scene.notices.text
    assert scene.notices.kind == "turn"
    assert scene.hud.cards[Color.BLACK].info.status == STATUS_TURN
    assert scene.hud.checked_color is None


@pytest.mark.ct("CT-90")
def test_treinamento_mostra_o_xeque(app):
    scene, player = start_game(app)
    player.play_all(CHECK_LINE)
    assert state_at(scene, "e8") == CellState.CHECK
    assert scene.notices.text.startswith("Xeque!")
    assert scene.hud.cards[Color.BLACK].info.status == STATUS_CHECK


@pytest.mark.ct("CT-90")
def test_partida_nao_calcula_ameacas(app, monkeypatch):
    scene, player = start_match_mode(app)
    calls = []
    monkeypatch.setattr(scene.engine, "threatened_pieces", lambda color: calls.append(color) or [])
    player.play_all(THREAT_LINE)
    assert calls == []


@pytest.mark.ct("CT-90")
def test_planilha_omite_mais_e_cerquilha_enquanto_a_partida_corre(app, monkeypatch):
    scene, player = start_match_mode(app)
    composed = []
    original = scene.hud.sheet._compose
    monkeypatch.setattr(scene.hud.sheet, "_compose", lambda history, first: composed.append(list(history)) or original(history, first))
    player.play_all(CHECK_LINE)
    assert composed[-1] == ["e4", "d5", "Bb5"]
    assert scene.engine.history[-1] == "Bb5+", "o motor guarda a notação completa"
    assert "Bb5+" in game_to_pgn(scene.engine), "o PGN também"


@pytest.mark.ct("CT-90")
def test_planilha_mostra_a_notacao_completa_no_fim(app, monkeypatch):
    scene, player = start_match_mode(app)
    composed = []
    original = scene.hud.sheet._compose
    monkeypatch.setattr(scene.hud.sheet, "_compose", lambda history, first: composed.append(list(history)) or original(history, first))
    player.play_all(SCHOLARS_MATE)
    assert composed[-1][-1] == "Qxf7#"


@pytest.mark.ct("CT-90")
@pytest.mark.parametrize("origin, target", [("e2", "e5"), ("e2", "e7")])
def test_lance_ilegal_recebe_aviso_generico(app, origin, target):
    scene, player = start_match_mode(app)
    fen = scene.engine.board.to_fen()
    click(player, origin)
    click(player, target)
    assert scene.notices.text == GENERIC_REFUSAL
    assert scene.notices.kind == "warning"
    assert scene.selection is None
    assert scene.view.shake_square is None, "o anel de recusa seria mais um marcador"
    assert scene.engine.board.to_fen() == fen


@pytest.mark.ct("CT-90")
def test_lance_que_expoe_o_rei_nao_diz_o_motivo(app):
    scene, player = start_match_mode(app, KING_PINNED, auto_rotate=False)
    click(player, "e2")
    assert scene.selection == cell("e2")
    assert scene.notices.kind == "turn", "selecionar a peça cravada não pode avisar nada"
    click(player, "c3")
    assert scene.notices.text == GENERIC_REFUSAL
    assert scene.notices.text != MoveError.LEAVES_KING_IN_CHECK.message


@pytest.mark.ct("CT-90")
def test_peca_sem_jogada_e_selecionada_sem_aviso(app):
    scene, player = start_match_mode(app)
    click(player, "a1")
    assert scene.selection == cell("a1")
    assert scene.targets == {}
    assert scene.notices.kind == "turn"
    assert "não tem jogada" not in scene.notices.text
    assert_no_hints(scene)


@pytest.mark.ct("CT-90")
@pytest.mark.parametrize("square", ["e7", "d4"])
def test_clique_em_casa_vazia_ou_peca_do_outro_tem_o_mesmo_aviso(app, square):
    scene, player = start_match_mode(app)
    click(player, square)
    assert scene.notices.text == GENERIC_REFUSAL


@pytest.mark.ct("CT-90")
def test_regras_oficiais_nos_dois_modos(app):
    scene, player = start_match_mode(app)
    player.play("e2e4")
    assert scene.engine.history == ["e4"]
    click(player, "e4")
    click(player, "e5")
    assert scene.engine.history == ["e4"], "fora da vez: as Pretas é que jogam"


@pytest.mark.ct("CT-90")
def test_cursor_e_selecao_e_ultimo_lance_continuam_no_modo_partida(app):
    scene, player = start_match_mode(app)
    player.play("e2e4")
    post_mouse_move(click_point(scene.view, cell("d5")))
    player.frames(1)
    assert state_at(scene, "d5") == CellState.CURSOR
    assert state_at(scene, "e4") == CellState.LAST_MOVE
    click(player, "e7")
    assert state_at(scene, "e7") == CellState.SELECTED
    assert_no_hints(scene)


@pytest.mark.ct("CT-90")
def test_painel_f4_nao_revela_dica_no_modo_partida(app):
    scene, player = start_match_mode(app)
    player.press(pygame.K_F4)
    player.play_all(PATHS_LINE)
    click(player, "b5")
    player.frames(2)
    assert scene.didactic_panel.is_visible
    assert_no_hints(scene)


@pytest.mark.ct("CT-90")
def test_fim_da_partida_mostra_o_motivo_normalmente(app):
    scene, player = start_match_mode(app)
    player.play_all(SCHOLARS_MATE)
    assert scene.notices.text == "Xeque-mate! Jogador 1 venceu."
    player.seconds(3.0)
    assert app.scene._subline() == "Xeque-mate, jogando de Brancas"


@pytest.mark.ct("CT-90")
def test_modo_aparece_discreto_no_hud(app):
    scene, _ = start_match_mode(app)
    assert scene.hud.mode_label == "Partida"
    scene, _ = start_game(app)
    assert scene.hud.mode_label == "Treinamento"


@pytest.mark.parametrize("san, expected", [("Bb5+", "Bb5"), ("Qxf7#", "Qxf7"), ("e4", "e4"), ("O-O-O+", "O-O-O"), ("a8=Q#", "a8=Q")])
def test_lance_sem_marca_de_xeque(san, expected):
    assert without_check_marks(san) == expected


def test_revanche_continua_no_mesmo_modo(app):
    scene, player = start_match_mode(app)
    finish_with_mate(player)
    player.click_widget(app.scene.rematch_button)
    assert app.scene.hides_hints is True
