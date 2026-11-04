"""Diálogo de promoção: abre antes de jogar, e a peça escolhida é a que entra no tabuleiro (RF05)."""
import pygame
import pytest
from ui_helpers import cell, click, start_game

from xadrez.core import Color, EndReason, PieceType, TimeControl
from xadrez.ui.overlays import PromotionDialog

WHITE_PROMOTES = "4k3/1P6/8/8/8/8/8/4K3 w - - 0 1"
BLACK_PROMOTES = "4k3/8/8/8/8/8/1p6/4K3 b - - 0 1"


def _open_dialog(app, fen=WHITE_PROMOTES, origin="b7", target="b8"):
    scene, player = start_game(app, fen, auto_rotate=False)
    click(player, origin)
    click(player, target)
    assert isinstance(scene.modals[-1], PromotionDialog)
    return scene, player


@pytest.mark.ct("CT-48")
def test_dialogo_abre_antes_de_jogar_e_a_peca_escolhida_entra(app):
    scene, player = _open_dialog(app)
    assert scene.engine.history == []
    assert scene.engine.board.piece_at(cell("b7")).kind is PieceType.PAWN
    dialog = scene.modals[-1]
    player.click_widget(dialog.buttons[dialog.kinds.index(PieceType.ROOK)])
    assert scene.modals == []
    player.settle()
    assert scene.engine.board.piece_at(cell("b8")).kind is PieceType.ROOK
    assert scene.engine.history[-1].startswith("b8=R")


@pytest.mark.ct("CT-48")
@pytest.mark.parametrize("kind", [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT])
def test_as_quatro_pecas_estao_no_dialogo(app, kind):
    scene, player = _open_dialog(app)
    dialog = scene.modals[-1]
    player.click_widget(dialog.buttons[dialog.kinds.index(kind)])
    player.settle()
    assert scene.engine.board.piece_at(cell("b8")).kind is kind


@pytest.mark.ct("CT-48")
def test_promocao_pelo_teclado(app):
    scene, player = _open_dialog(app)
    player.press(pygame.K_RIGHT)
    player.press(pygame.K_RIGHT)
    player.press(pygame.K_LEFT)
    player.press(pygame.K_RETURN)
    player.settle()
    assert scene.engine.board.piece_at(cell("b8")).kind is PieceType.ROOK


@pytest.mark.ct("CT-48")
def test_numeros_escolhem_direto(app):
    scene, player = _open_dialog(app)
    player.press(pygame.K_4)
    player.settle()
    assert scene.engine.board.piece_at(cell("b8")).kind is PieceType.KNIGHT


@pytest.mark.ct("CT-48")
def test_esc_cancela_sem_jogar(app):
    scene, player = _open_dialog(app)
    player.press(pygame.K_ESCAPE)
    assert scene.modals == []
    assert scene.selection is None
    assert scene.engine.history == []
    assert scene.engine.board.piece_at(cell("b7")).kind is PieceType.PAWN


@pytest.mark.ct("CT-48")
def test_pretas_tambem_promovem(app):
    scene, player = _open_dialog(app, BLACK_PROMOTES, "b2", "b1")
    assert scene.modals[-1].color is Color.BLACK
    player.press(pygame.K_1)
    player.settle()
    assert scene.engine.board.piece_at(cell("b1")).kind is PieceType.QUEEN


def test_peca_promovida_nasce_com_animacao_e_depois_fica_parada(app):
    scene, player = _open_dialog(app)
    player.press(pygame.K_1)
    player.settle()
    assert cell("b8") in scene.view._hidden_squares()
    player.seconds(0.6)
    assert cell("b8") not in scene.view._hidden_squares()


def test_relogio_continua_correndo_durante_a_escolha(app):
    scene, player = _open_dialog(app)
    remaining = scene.engine.clock.remaining(Color.WHITE)
    player.frames(30)
    assert scene.engine.clock.remaining(Color.WHITE) < remaining
    assert scene.is_frozen is False


def test_tabuleiro_nao_recebe_clique_durante_a_escolha(app):
    scene, player = _open_dialog(app)
    selection = scene.selection
    click(player, "e1")
    assert scene.selection == selection
    assert isinstance(scene.modals[-1], PromotionDialog)


def test_tempo_esgotado_durante_a_escolha_fecha_o_dialogo(app):
    scene, player = start_game(app, WHITE_PROMOTES, TimeControl(0.01), auto_rotate=False)
    click(player, "b7")
    click(player, "b8")
    assert isinstance(scene.modals[-1], PromotionDialog)
    player.seconds(1.0)
    assert scene.modals == []
    assert scene.engine.result.reason is EndReason.TIMEOUT
