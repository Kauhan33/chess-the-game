"""HUD: placas, relógio, capturas, planilha, faixa de avisos e painéis de bancada (RF11)."""
import math

import pygame
import pytest
from ui_helpers import click, finish_with_mate, start_game

from xadrez.core import Color, PieceType, TimeControl
from xadrez.ui.autoplay import post_click, post_mouse_move
from xadrez.ui.hud import STATUS_CHECK, STATUS_TURN, ScoreSheet
from xadrez.ui.match import MatchOptions, format_clock, format_points


@pytest.mark.parametrize("seconds, expected", [
    (600, "10:00"), (599.2, "10:00"), (59.01, "01:00"), (9, "00:09"), (0, "00:00"), (0.2, "00:01"),
    (3723, "1:02:03"), (-3, "00:00"),
])
def test_formato_do_relogio(seconds, expected):
    assert format_clock(seconds) == expected


@pytest.mark.parametrize("points, expected", [(0.0, "0"), (1.0, "1"), (0.5, "0,5"), (2.5, "2,5")])
def test_formato_do_placar_em_portugues(points, expected):
    assert format_points(points) == expected


def test_opcoes_criam_o_motor_com_o_que_foi_escolhido():
    engine = MatchOptions("Alfa", "Bravo", TimeControl.BLITZ_5).create_engine()
    assert engine.players[Color.BLACK].name == "Bravo"
    assert engine.time_control == TimeControl.BLITZ_5


def test_placa_da_vez_e_de_quem_joga_e_troca_com_o_lance(app):
    scene, player = start_game(app)
    hud = scene.hud
    assert hud.cards[Color.WHITE].info.status == STATUS_TURN
    assert hud.cards[Color.BLACK].info.status is None
    assert hud._lamp[Color.WHITE] == 1.0
    click(player, "e2")
    click(player, "e4")
    assert hud.active_color is Color.BLACK
    player.seconds(0.5)
    assert hud._lamp[Color.BLACK] == 1.0
    assert hud._lamp[Color.WHITE] == 0.0


def test_relogio_corre_para_quem_joga(app):
    scene, player = start_game(app)
    player.seconds(2.0)
    assert scene.engine.clock.remaining(Color.WHITE) < 599.0
    assert scene.hud.cards[Color.WHITE].info.clock == format_clock(scene.engine.clock.remaining(Color.WHITE))
    assert scene.hud.cards[Color.BLACK].info.clock == "10:00"


def test_relogio_sem_limite_mostra_o_tempo_decorrido(app):
    scene, player = start_game(app, time_control=TimeControl.UNLIMITED)
    assert scene.hud.cards[Color.WHITE].info.is_elapsed
    player.seconds(1.2)
    elapsed = scene.engine.clock.elapsed(Color.WHITE)
    assert scene.hud.cards[Color.WHITE].info.clock == format_clock(math.floor(elapsed))
    assert scene.hud.cards[Color.WHITE].info.clock != "00:00"
    assert scene.hud.cards[Color.BLACK].info.clock == "00:00"


def test_tempo_baixo_muda_a_placa(app):
    scene, player = start_game(app, time_control=TimeControl(0.6))
    assert not scene.hud.cards[Color.WHITE].info.is_low_time
    player.seconds(7.0)
    assert scene.hud.cards[Color.WHITE].info.is_low_time
    assert not scene.hud.cards[Color.BLACK].info.is_low_time


def test_capturas_material_e_pontos_aparecem_na_placa(app):
    scene, player = start_game(app)
    player.play_all("e2e4 d7d5 e4d5")
    white, black = scene.hud.cards[Color.WHITE].info, scene.hud.cards[Color.BLACK].info
    assert white.captured == (PieceType.PAWN,)
    assert white.points == 1
    assert white.lead == 1
    assert black.captured == ()
    assert black.lead == -1
    player.play("d8d5")
    white, black = scene.hud.cards[Color.WHITE].info, scene.hud.cards[Color.BLACK].info
    assert black.captured == (PieceType.PAWN,)
    assert white.lead == 0


def test_placar_da_serie_aparece_na_placa(app):
    _, player = start_game(app)
    finish_with_mate(player)
    player.click_widget(app.scene.rematch_button)
    scene = app.scene
    assert scene.hud.cards[Color.BLACK].info.series == "1"
    assert scene.hud.cards[Color.WHITE].info.series == "0"


def test_placa_pronta_nao_e_refeita_se_nada_mudou(app, monkeypatch):
    scene, player = start_game(app, time_control=TimeControl.UNLIMITED)
    card = scene.hud.cards[Color.BLACK]
    composed = []
    original = card._compose
    monkeypatch.setattr(card, "_compose", lambda *args: composed.append(args) or original(*args))
    player.frames(30)
    assert composed == []


def test_placa_de_tempo_so_e_refeita_quando_o_segundo_vira(app, monkeypatch):
    scene, player = start_game(app)
    card = scene.hud.cards[Color.WHITE]
    composed = []
    original = card._compose
    monkeypatch.setattr(card, "_compose", lambda *args: composed.append(args) or original(*args))
    shown = [card.info.clock]
    for _ in range(150):
        player.frames(1)
        if card.info.clock != shown[-1]:
            shown.append(card.info.clock)
    assert len(shown) >= 3
    # Duas versões por virada de segundo: na sombra e sob a luz.
    assert len(composed) == 2 * (len(shown) - 1)


def test_status_de_xeque_na_placa(app):
    scene, player = start_game(app)
    player.play_all("e2e4 d7d5 f1b5")
    assert scene.hud.cards[Color.BLACK].info.status == STATUS_CHECK


def test_nome_comprido_nao_vaza_da_placa(app):
    scene, player = start_game(app, names=("WWWWWWWWWWWWWWWW", "MMMMMMMMMMMMMMMM"))
    player.frames(2)
    assert app.theme.text_fit("W" * 16, "display", 24, (0, 0, 0), 120).get_width() <= 120


def test_planilha_mostra_so_as_ultimas_linhas(app):
    scene, _ = start_game(app)
    sheet = ScoreSheet(app.theme)
    sheet.layout(pygame.Rect(0, 0, 280, 120))
    sheet.refresh(["e4"] * 80, Color.WHITE)
    surface = pygame.Surface((400, 200))
    sheet.draw(surface)
    assert sheet._rendered_count == 80


def test_planilha_vazia_nao_quebra_quando_nao_cabe(app):
    sheet = ScoreSheet(app.theme)
    sheet.layout(pygame.Rect(0, 0, 280, 0))
    sheet.refresh([], Color.WHITE)
    sheet.draw(pygame.Surface((10, 10)))


def test_planilha_so_e_refeita_quando_ha_lance_novo(app, monkeypatch):
    scene, player = start_game(app)
    composed = []
    original = scene.hud.sheet._compose
    monkeypatch.setattr(scene.hud.sheet, "_compose", lambda *args: composed.append(args) or original(*args))
    player.frames(30)
    assert composed == []
    player.play("e2e4")
    assert len(composed) == 1


def test_faixa_mostra_a_vez_com_nome_e_cor(app):
    scene, player = start_game(app, names=("Alfa", "Bravo"))
    assert scene.notices.text == "Vez de Alfa, Brancas"
    player.play("e2e4")
    assert scene.notices.text == "Vez de Bravo, Pretas"


def test_cliques_no_painel_nao_chegam_ao_tabuleiro(app):
    scene, player = start_game(app)
    post_click((app.size[0] - 30, 300))
    player.frames(1)
    assert scene.notices.kind == "turn"
    assert scene.selection is None


def test_paineis_de_bancada_desenham_com_mouse_e_sem_mouse(app):
    scene, player = start_game(app)
    player.press(pygame.K_F4)
    player.press(pygame.K_F3)
    player.frames(2)
    post_mouse_move((5, 5))
    player.frames(2)
    post_mouse_move((scene.view.camera.viewport[0] + 300, 300))
    player.frames(2)
    assert scene.view.scene_polygons > 64


def test_poligonos_em_cena_acompanham_as_pecas(app):
    scene, player = start_game(app)
    before = scene.view.scene_polygons
    player.play_all("e2e4 d7d5 e4d5")
    assert scene.view.scene_polygons < before
