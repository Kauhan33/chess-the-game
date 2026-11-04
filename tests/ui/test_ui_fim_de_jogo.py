"""Todos os fins de partida e o que a tela final mostra para cada um (RF07, RF14)."""
import pygame
import pytest
from ui_helpers import ENDING_SECONDS, finish_with_mate, start_game

from xadrez.core import Color, EndReason, GameResult, TimeControl
from xadrez.ui import GameOverScene, drawing
from xadrez.ui.game_over_scene import _moves_text, result_score

STALEMATE_IN_ONE = "7k/5K2/8/6Q1/8/8/8/8 w - - 0 1"
ALREADY_MATED = "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1"
INSUFFICIENT_AFTER_CAPTURE = "7k/8/8/8/8/8/6p1/6K1 w - - 0 1"


def test_tempo_esgotado_encerra_sem_tombar_o_rei(app):
    scene, player = start_game(app, time_control=TimeControl(0.01))
    player.seconds(0.65)
    assert scene.engine.result is not None
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.engine.result.winner is Color.BLACK
    assert scene.view._fallen_king is None
    player.seconds(1.2)
    assert isinstance(app.scene, GameOverScene)


def test_tempo_esgotado_com_a_peca_no_ar_nao_recomeca_o_fim(app):
    scene, player = start_game(app, time_control=TimeControl(0.005))
    player.click_square((4, 1))
    player.click_square((4, 3))
    player.seconds(0.32)
    assert scene.engine.result.reason is EndReason.TIMEOUT
    assert scene.view.is_flying
    player.seconds(0.9)
    assert isinstance(app.scene, GameOverScene)


def test_afogamento_e_empate_sem_rei_caido(app):
    scene, player = start_game(app, STALEMATE_IN_ONE, auto_rotate=False)
    player.play("g5g6")
    assert scene.engine.result.reason is EndReason.STALEMATE
    assert scene.engine.result.is_draw
    assert scene.view._fallen_king is None
    player.seconds(1.2)
    end = app.scene
    assert isinstance(end, GameOverScene)
    assert end._headline() == "Partida empatada"
    assert end._subline() == EndReason.STALEMATE.label


def test_material_insuficiente_encerra_pelo_lance(app):
    scene, player = start_game(app, INSUFFICIENT_AFTER_CAPTURE, auto_rotate=False)
    player.play("g1g2")
    assert scene.engine.result.reason is EndReason.INSUFFICIENT_MATERIAL
    player.seconds(1.2)
    assert isinstance(app.scene, GameOverScene)


def test_posicao_ja_terminada_vai_direto_para_o_fim(app):
    _, player = start_game(app, ALREADY_MATED)
    player.seconds(ENDING_SECONDS)
    assert isinstance(app.scene, GameOverScene)
    assert app.scene.result.winner is Color.WHITE


def test_tela_de_vitoria_mostra_vencedor_motivo_placar_e_lances(app):
    _, player = start_game(app)
    finish_with_mate(player)
    end = app.scene
    assert end._headline() == "Jogador 1 venceu"
    assert end._subline() == "Xeque-mate, jogando de Brancas"
    assert result_score(end.result) == "1 - 0"
    assert _moves_text(len(end.engine.history)) == "Partida de 4 lances"


def test_troca_para_a_tela_final_nao_mexe_no_tabuleiro_nem_refaz_o_fundo(app, monkeypatch):
    scene, player = start_game(app)
    player.play_all("e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7")
    viewport = scene.view.camera.viewport
    ground_renders = []
    monkeypatch.setattr(drawing, "render_panel_ground", lambda size: ground_renders.append(size) or pygame.Surface(size))
    player.seconds(ENDING_SECONDS)
    assert isinstance(app.scene, GameOverScene)
    assert scene.view.camera.viewport == viewport
    assert ground_renders == []


def test_camera_se_afasta_aos_poucos_na_tela_final(app):
    _, player = start_game(app)
    finish_with_mate(player)
    camera = app.scene.view.camera
    distance = camera.distance
    player.frames(5)
    assert distance < camera.distance < distance * 1.14


def test_fogos_continuam_na_tela_final(app):
    _, player = start_game(app)
    finish_with_mate(player)
    player.seconds(1.0)
    assert app.scene.view.particles.alive_count > 0


def test_camera_gira_devagar_na_tela_final(app):
    _, player = start_game(app)
    finish_with_mate(player)
    yaw = app.scene.view.camera.yaw
    player.seconds(0.5)
    assert app.scene.view.camera.yaw != yaw


@pytest.mark.parametrize("winner, expected", [(Color.WHITE, "1 - 0"), (Color.BLACK, "0 - 1"), (None, "½ - ½")])
def test_resultado_escrito_como_na_planilha(winner, expected):
    assert result_score(GameResult(winner, EndReason.RESIGNATION)) == expected


def test_lances_no_singular_e_no_plural():
    assert _moves_text(1) == "Partida de 1 lance"
    assert _moves_text(2) == "Partida de 1 lance"
    assert _moves_text(3) == "Partida de 2 lances"
