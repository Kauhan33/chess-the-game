"""Arrastar a peça para jogar: a mão faz o que o clique faz, e o clique continua igual (RF23, CT-96)."""
import numpy as np
import pygame
import pytest
from ui_helpers import cell, click, start_cpu_game, start_game

from xadrez.core import Color, Difficulty, GameState, MoveError, TimeControl
from xadrez.graphics import square_to_world
from xadrez.ui import GameMode
from xadrez.ui.autoplay import click_point, post_drag, post_mouse_down, post_mouse_move, post_mouse_up
from xadrez.ui.game_scene import CPU_TURN_NOTICE, GENERIC_REFUSAL
from xadrez.ui.overlays import PromotionDialog

PROMOTION_FEN = "4k3/1P6/8/8/8/8/8/4K3 w - - 0 1"
LIFT_HEIGHT = 0.2


def pixel(scene, name):
    return click_point(scene.view, cell(name))


def piece_position(scene, name):
    """Onde a peça está sendo desenhada neste quadro: a translação da matriz de modelo."""
    placed = next(piece for piece in scene.view._placed if piece.square == cell(name))
    return scene.view._adjusted_matrix(placed)[:3, 3]


@pytest.mark.ct("CT-96")
def test_arrastar_ate_o_destino_joga(app):
    scene, player = start_game(app, auto_rotate=False)
    player.drag_square(cell("e2"), cell("e4"))
    assert scene.engine.history == ["e4"]
    assert scene.selection is None
    assert scene.view.dragged_square is None
    assert scene.view.is_flying
    player.settle()
    assert scene.engine.turn is Color.BLACK


@pytest.mark.ct("CT-96")
def test_peca_acompanha_o_ponto_do_mouse_levantada(app):
    scene, player = start_game(app, auto_rotate=False)
    start, end = pixel(scene, "e2"), pixel(scene, "e4")
    post_drag(start, end, release=False)
    player.frames(1)
    assert scene.selection == cell("e2")
    assert scene.view.dragged_square == cell("e2")
    x, y, z = piece_position(scene, "e2")
    assert y > LIFT_HEIGHT, "a peça sobe"
    hit = scene.view.camera.pick_plane(*end, y)
    assert x == pytest.approx(hit[0], abs=1e-6)
    assert z == pytest.approx(hit[1], abs=1e-6)
    assert scene.engine.history == [], "só joga ao soltar"
    post_mouse_up(end)
    player.frames(1)
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-96")
def test_movimento_pequeno_nao_vira_arrasto(app):
    scene, player = start_game(app, auto_rotate=False)
    start = pixel(scene, "e2")
    post_drag(start, (start[0] + 3, start[1] + 2), release=False)
    player.frames(1)
    assert scene.view.dragged_square is None
    post_mouse_up(start)
    player.frames(1)
    assert scene.selection == cell("e2"), "foi um clique: a seleção fica"


@pytest.mark.ct("CT-96")
def test_soltar_na_propria_casa_devolve_e_mantem_a_selecao(app):
    scene, player = start_game(app, auto_rotate=False)
    start = pixel(scene, "e2")
    post_mouse_down(start)
    post_mouse_move(pixel(scene, "e4"), buttons=(1, 0, 0))
    post_mouse_move(start, buttons=(1, 0, 0))
    post_mouse_up(start)
    player.frames(1)
    assert scene.selection == cell("e2")
    assert scene.view.dragged_square is None
    assert scene.engine.history == []
    assert scene.targets, "os destinos continuam valendo"
    x, _, z = piece_position(scene, "e2")
    home_x, _, home_z = square_to_world(*cell("e2"))
    assert (x, z) == pytest.approx((home_x, home_z)), "a peça voltou para a casa"
    click(player, "e4")
    player.settle()
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-96")
def test_soltar_em_destino_ilegal_devolve_e_avisa(app):
    scene, player = start_game(app, auto_rotate=False)
    fen = scene.engine.board.to_fen()
    player.drag_square(cell("e2"), cell("e5"))
    assert scene.engine.board.to_fen() == fen
    assert scene.selection is None
    assert scene.notices.text == MoveError.ILLEGAL_MOVE.message
    assert scene.view.dragged_square is None


@pytest.mark.ct("CT-96")
def test_no_modo_partida_o_aviso_e_o_generico(app):
    scene, player = start_game(app, auto_rotate=False, mode=GameMode.MATCH)
    player.drag_square(cell("e2"), cell("e5"))
    assert scene.notices.text == GENERIC_REFUSAL
    assert scene.view.shake_square is None


@pytest.mark.ct("CT-96")
def test_soltar_fora_do_tabuleiro_devolve_sem_aviso(app):
    scene, player = start_game(app, auto_rotate=False)
    start = pixel(scene, "e2")
    post_drag(start, (3, 3))
    player.frames(1)
    assert scene.selection is None
    assert scene.notices.kind != "warning"
    assert scene.engine.history == []


@pytest.mark.ct("CT-96")
def test_soltar_no_painel_devolve_sem_acionar_botao(app):
    scene, player = start_game(app, auto_rotate=False)
    start = pixel(scene, "e2")
    target = scene.hud.buttons[0].rect.center
    post_drag(start, target)
    player.frames(1)
    assert scene.modals == [], "o botão não foi apertado: o clique começou no tabuleiro"
    assert scene.selection is None


@pytest.mark.ct("CT-96")
def test_arrastar_para_capturar_vale_a_peca_que_se_ve(app):
    scene, player = start_game(app, auto_rotate=False)
    player.play_all("e2e4 d7d5")
    player.drag_square(cell("e4"), cell("d5"))
    assert scene.engine.history[-1] == "exd5"
    assert scene.view._waiting_capture is not None


@pytest.mark.ct("CT-96")
def test_arrastar_a_promocao_abre_o_dialogo(app):
    scene, player = start_game(app, PROMOTION_FEN, auto_rotate=False)
    player.drag_square(cell("b7"), cell("b8"))
    assert isinstance(scene.modals[-1], PromotionDialog)
    assert scene.view.dragged_square is None
    player.choose_promotion("q")
    assert scene.engine.history[-1].startswith("b8=Q")


@pytest.mark.ct("CT-96")
def test_arrastar_outra_peca_troca_a_selecao(app):
    scene, player = start_game(app, auto_rotate=False)
    click(player, "g1")
    assert scene.selection == cell("g1")
    player.drag_square(cell("e2"), cell("e4"))
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-96")
def test_arrastar_a_peca_ja_selecionada(app):
    scene, player = start_game(app, auto_rotate=False)
    click(player, "e2")
    player.drag_square(cell("e2"), cell("e3"))
    assert scene.engine.history == ["e3"]


@pytest.mark.ct("CT-96")
def test_clique_clique_continua_funcionando(app):
    scene, player = start_game(app, auto_rotate=False)
    click(player, "e2")
    assert scene.selection == cell("e2")
    click(player, "e2")
    assert scene.selection is None, "clicar de novo desmarca"
    click(player, "e2")
    click(player, "e4")
    player.settle()
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-96")
def test_teclado_continua_funcionando(app):
    scene, player = start_game(app, auto_rotate=False)
    player.press(pygame.K_UP)
    player.press(pygame.K_RETURN)
    player.press(pygame.K_UP)
    player.press(pygame.K_UP)
    player.press(pygame.K_RETURN)
    player.settle()
    assert scene.engine.history == ["e4"]


@pytest.mark.ct("CT-96")
def test_botao_direito_continua_orbitando(app):
    scene, player = start_game(app, auto_rotate=False)
    yaw = scene.view.camera.yaw
    position = pixel(scene, "e2")
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=3))
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(position[0] + 30, position[1]), rel=(30, 0), buttons=(0, 0, 1)))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(position[0] + 30, position[1]), button=3))
    player.frames(1)
    assert scene.view.camera.yaw != pytest.approx(yaw)
    assert scene.selection is None
    assert scene.view.dragged_square is None


@pytest.mark.ct("CT-96")
def test_soltar_fora_da_janela_devolve_a_peca(app):
    scene, player = start_game(app, auto_rotate=False)
    start = pixel(scene, "e2")
    post_drag(start, pixel(scene, "e4"), release=False)
    player.frames(1)
    assert scene.view.dragged_square == cell("e2")
    post_mouse_move(start, buttons=(0, 0, 0))
    player.frames(1)
    assert scene.view.dragged_square is None
    assert scene.selection == cell("e2")
    assert scene.engine.history == []


@pytest.mark.ct("CT-96")
def test_pausa_no_meio_do_arrasto_devolve_a_peca(app):
    scene, player = start_game(app, auto_rotate=False)
    end = pixel(scene, "e4")
    post_drag(pixel(scene, "e2"), end, release=False)
    player.frames(1)
    player.press(pygame.K_p)
    assert scene.engine.state is GameState.PAUSED
    assert scene.view.dragged_square is None
    post_mouse_up(end)
    player.frames(1)
    assert scene.engine.history == [], "soltar com a pausa aberta não joga"
    player.press(pygame.K_p)
    assert scene.engine.history == []


@pytest.mark.ct("CT-96")
def test_esc_no_meio_do_arrasto_cancela(app):
    scene, player = start_game(app, auto_rotate=False)
    end = pixel(scene, "e4")
    post_drag(pixel(scene, "e2"), end, release=False)
    player.frames(1)
    player.press(pygame.K_ESCAPE)
    assert scene.selection is None
    assert scene.view.dragged_square is None
    post_mouse_up(end)
    player.frames(1)
    assert scene.engine.history == []


@pytest.mark.ct("CT-96")
def test_tempo_esgotado_no_meio_do_arrasto_devolve_a_peca(app):
    scene, player = start_game(app, auto_rotate=False, time_control=TimeControl(0.005))
    end = pixel(scene, "e4")
    post_drag(pixel(scene, "e2"), end, release=False)
    player.seconds(0.5)
    assert scene.engine.result is not None
    assert scene.view.dragged_square is None
    post_mouse_up(end)
    player.frames(1)
    assert scene.engine.history == []


@pytest.mark.ct("CT-96")
def test_peca_do_adversario_nao_e_arrastada(app):
    scene, player = start_game(app, auto_rotate=False)
    player.drag_square(cell("e7"), cell("e5"))
    assert scene.engine.history == []
    assert scene.view.dragged_square is None
    assert scene.notices.text == MoveError.NOT_YOUR_TURN.message


@pytest.mark.ct("CT-96")
def test_durante_o_voo_nao_ha_arrasto(app):
    scene, player = start_game(app, auto_rotate=False)
    player.drag_square(cell("e2"), cell("e4"))
    assert scene.view.is_flying
    player.drag_square(cell("e7"), cell("e5"))
    assert scene.engine.history == ["e4"]
    assert scene.view.dragged_square is None


@pytest.mark.ct("CT-96")
def test_na_vez_da_cpu_nao_ha_arrasto(app):
    scene, player = start_cpu_game(app, Difficulty.HARDCORE, human_color=Color.BLACK, time_control=TimeControl.UNLIMITED)
    player.drag_square(cell("e7"), cell("e5"))
    assert scene.view.dragged_square is None
    assert scene.notices.text == CPU_TURN_NOTICE


@pytest.mark.ct("CT-96")
def test_a_peca_arrastada_nao_atrapalha_o_clique_na_casa_atras_dela(app):
    scene, player = start_game(app, auto_rotate=False)
    post_drag(pixel(scene, "e2"), pixel(scene, "e3"), release=False)
    player.frames(1)
    assert scene.view.pick(pixel(scene, "e3")) == cell("e3")
    post_mouse_up(pixel(scene, "e3"))
    player.frames(1)
    assert scene.engine.history == ["e3"]


def test_peca_nao_sai_para_longe_do_tabuleiro(app):
    scene, player = start_game(app, auto_rotate=False)
    post_drag(pixel(scene, "e2"), (2, 2), release=False)
    player.frames(1)
    x, _, z = piece_position(scene, "e2")
    assert np.abs([x, z]).max() <= 5.0
    post_mouse_up((2, 2))
    player.frames(1)
