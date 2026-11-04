"""Fluxos de exceção: jogada fora do turno e jogada inválida precisam ficar visíveis (RF03, RF04)."""
import pytest
from ui_helpers import cell, click, start_game

from xadrez.core import Color, MoveError


def _assert_refused(scene, error, square, fen_before):
    assert scene.notices.text == error.message
    assert scene.notices.kind == "warning"
    assert scene.selection is None
    assert scene.view.shake_square == cell(square)
    assert scene.engine.board.to_fen() == fen_before


@pytest.mark.ct("CT-43")
def test_clique_na_peca_do_adversario_avisa_e_nao_altera_o_jogo(app):
    scene, player = start_game(app)
    fen = scene.engine.board.to_fen()
    click(player, "e7")
    _assert_refused(scene, MoveError.NOT_YOUR_TURN, "e7", fen)
    assert scene.engine.turn is Color.WHITE
    assert scene.engine.history == []


@pytest.mark.ct("CT-43")
def test_alvo_invalido_avisa_limpa_a_selecao_e_nao_altera_o_jogo(app):
    scene, player = start_game(app)
    fen = scene.engine.board.to_fen()
    click(player, "e2")
    click(player, "e5")
    _assert_refused(scene, MoveError.ILLEGAL_MOVE, "e5", fen)


@pytest.mark.ct("CT-43")
def test_peca_do_adversario_como_alvo_invalido_tambem_avisa(app):
    scene, player = start_game(app)
    fen = scene.engine.board.to_fen()
    click(player, "e2")
    click(player, "e7")
    _assert_refused(scene, MoveError.ILLEGAL_MOVE, "e7", fen)


@pytest.mark.ct("CT-43")
def test_casa_vazia_sem_selecao_avisa(app):
    scene, player = start_game(app)
    fen = scene.engine.board.to_fen()
    click(player, "d4")
    _assert_refused(scene, MoveError.NO_PIECE, "d4", fen)


@pytest.mark.ct("CT-43")
def test_jogada_que_expoe_o_rei_mostra_a_mensagem_do_motor(app):
    scene, player = start_game(app, "4k3/8/8/8/4r3/8/4N3/4K3 w - - 0 1", auto_rotate=False)
    fen = scene.engine.board.to_fen()
    click(player, "e2")
    assert scene.selection == cell("e2")
    assert scene.targets == {}
    click(player, "c3")
    _assert_refused(scene, MoveError.LEAVES_KING_IN_CHECK, "c3", fen)


def test_aviso_some_e_a_faixa_volta_a_mostrar_a_vez(app):
    scene, player = start_game(app)
    click(player, "e7")
    assert scene.notices.kind == "warning"
    player.seconds(3.5)
    assert scene.notices.kind == "turn"
    assert "Jogador 1" in scene.notices.text


def test_tremor_e_curto(app):
    scene, player = start_game(app)
    click(player, "e7")
    assert scene.view.shake_square == cell("e7")
    player.seconds(0.5)
    assert scene.view.shake_square is None


def test_tremor_em_casa_vazia_nao_derruba_o_desenho(app):
    scene, player = start_game(app)
    click(player, "d4")
    player.frames(5)
    assert scene.view.shake_square == cell("d4")
