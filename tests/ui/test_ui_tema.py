"""Tema e aplicação: fontes com alternativa, cache de texto, contraste e laço do jogo."""
import runpy
import sys
from pathlib import Path

import pygame
import pytest
from ui_helpers import cell, start_game

from xadrez.ui import App, Button, GameScene, MenuScene, Selector, TextInput, drawing
from xadrez.ui import theme as tokens
from xadrez.ui.app import MAX_FRAME_SECONDS
from xadrez.ui.autoplay import _cell, click_point, post_click
from xadrez.ui.theme import Theme, window_scale


def _relative_luminance(color):
    def channel(value):
        scaled = value / 255.0
        return scaled / 12.92 if scaled <= 0.03928 else ((scaled + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in color[:3])
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first, second):
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("text, background", [
    (tokens.IVORY, tokens.WALNUT),
    (tokens.TEXT_MUTED, tokens.WALNUT),
    (tokens.TEXT_MUTED, tokens.WALNUT_RAISED),
    (tokens.BRASS_BRIGHT, tokens.WALNUT),
    (tokens.INK, tokens.PLATE_LIT.bottom),
    (tokens.INK_SOFT, tokens.PLATE_LIT.bottom),
    (tokens.INK, tokens.PAPER),
    (tokens.INK_SOFT, tokens.PAPER),
    (tokens.ALERT_ON_LIGHT, tokens.PLATE_LIT.bottom),
    (tokens.ALERT_ON_DARK, tokens.WALNUT),
    (tokens.IVORY, tokens.ALERT_PLATE),
    (tokens.INK, tokens.PLATE_PRIMARY.bottom),
    (tokens.INK, tokens.PLATE_KEYCAP.bottom),
    (tokens.IVORY, tokens.PLATE_DANGER.top),
])
def test_contraste_dos_textos_passa_de_4_5_para_1(text, background):
    assert _contrast(text, background) >= 4.5


def test_escala_da_janela_tem_limites():
    assert window_scale((1280, 720)) == 1.0
    assert window_scale((1920, 1080)) == 1.5
    assert window_scale((10, 10)) == tokens.MIN_SCALE
    assert window_scale((9000, 9000)) == tokens.MAX_SCALE


def test_fonte_cai_na_padrao_quando_nao_ha_nenhuma_do_sistema(app, monkeypatch):
    monkeypatch.setattr(pygame.font, "match_font", lambda *args, **kwargs: None)
    theme = Theme()
    for role in (tokens.ROLE_DISPLAY, tokens.ROLE_SERIF, tokens.ROLE_LABEL, tokens.ROLE_NUMERIC, tokens.ROLE_MONO):
        assert theme.text("Promoção à Dama, ½", role, 20, tokens.IVORY).get_width() > 0
    assert theme.tabular("09:57", tokens.ROLE_NUMERIC, 40, tokens.IVORY).get_width() > 0


def test_fonte_corrompida_tambem_cai_na_padrao(app, monkeypatch, tmp_path):
    broken = tmp_path / "quebrada.ttf"
    broken.write_bytes(b"isto nao e uma fonte")
    monkeypatch.setattr(pygame.font, "match_font", lambda *args, **kwargs: str(broken))
    theme = Theme()
    assert theme.text("Xeque", tokens.ROLE_DISPLAY, 20, tokens.IVORY).get_width() > 0


def test_jogo_inteiro_abre_sem_nenhuma_fonte_do_sistema(monkeypatch):
    monkeypatch.setattr(pygame.font, "match_font", lambda *args, **kwargs: None)
    application = App(seed=1)
    pygame.event.clear()
    application.step(1 / 60)
    application.scene.start_match()
    application.step(1 / 60)
    assert isinstance(application.scene, GameScene)
    application.step(1 / 60)


def test_texto_renderizado_fica_em_cache(app):
    first = app.theme.text("Vez das Brancas", tokens.ROLE_LABEL, 18, tokens.IVORY)
    second = app.theme.text("Vez das Brancas", tokens.ROLE_LABEL, 18, tokens.IVORY)
    assert first is second
    assert app.theme.text("Vez das Brancas", tokens.ROLE_LABEL, 18, tokens.BRASS) is not first


def test_cache_de_texto_tem_limite(app):
    theme = Theme()
    for number in range(tokens._TEXT_CACHE_LIMIT + 50):
        theme.text(str(number), tokens.ROLE_LABEL, 12, tokens.IVORY)
    assert len(theme._texts) == tokens._TEXT_CACHE_LIMIT


def test_cache_de_placas_tem_limite(app):
    theme = Theme()
    for width in range(1, tokens._PLATE_CACHE_LIMIT + 30):
        theme.plate((width, 4), tokens.PLATE_DEBUG)
    assert len(theme._plates) <= tokens._PLATE_CACHE_LIMIT


def test_relogio_nao_treme_quando_o_digito_muda(app):
    widths = {app.theme.tabular(f"0{d}:1{d}", tokens.ROLE_NUMERIC, 60, tokens.INK).get_width() for d in "0123456789"}
    assert len(widths) == 1


def test_texto_ajustado_nao_passa_da_largura(app):
    for width in (300, 120, 60, 20):
        fitted = app.theme.text_fit("Jogador com nome bem longo", tokens.ROLE_DISPLAY, 24, tokens.INK, width)
        assert fitted.get_width() <= max(width, 40)


def test_texto_vazio_nao_quebra(app):
    assert app.theme.text("", tokens.ROLE_LABEL, 14, tokens.IVORY).get_height() > 0


@pytest.mark.parametrize("size", [(1, 1), (3, 200), (200, 3), (0, 0)])
def test_formas_aguentam_tamanhos_minimos(app, size):
    assert drawing.render_plate(size, tokens.IVORY, tokens.PAPER, tokens.BRASS, 8).get_width() >= 1
    assert drawing.render_glow(size, tokens.LAMP_GLOW, 80).get_width() >= 1
    assert drawing.render_panel_ground(size).get_width() >= 1


def test_chao_do_painel_fica_em_cache_ate_a_janela_mudar(app):
    ground = app.theme.panel_ground((300, 400))
    assert app.theme.panel_ground((300, 400)) is ground
    app.theme.set_window_size((1000, 600))
    assert app.theme.panel_ground((300, 400)) is not ground


def test_quadro_longo_nao_vira_salto_de_relogio(app):
    scene, _ = start_game(app)
    remaining = scene.engine.clock.remaining(scene.engine.turn)
    app.step(30.0)
    assert remaining - scene.engine.clock.remaining(scene.engine.turn) == pytest.approx(MAX_FRAME_SECONDS)


def test_dt_negativo_e_ignorado(app):
    scene, _ = start_game(app)
    remaining = scene.engine.clock.remaining(scene.engine.turn)
    app.step(-5.0)
    assert scene.engine.clock.remaining(scene.engine.turn) == remaining


def test_janela_comeca_em_1280_por_720_e_no_menu(app):
    assert app.size == (1280, 720)
    assert isinstance(app.scene, MenuScene)
    assert pygame.display.get_caption()[0] == "Chess - The Game"


def test_fechar_a_janela_encerra_o_laco(app):
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    app.run()
    assert app.running is False
    App(seed=1)
    pygame.event.clear()


def test_run_frame_mede_o_tempo_do_quadro(app):
    app.run_frame()
    app.run_frame()
    assert app.frame_ms > 0.0


def test_pacote_exporta_os_nomes_do_contrato():
    assert all(isinstance(item, type) for item in (App, Button, Selector, TextInput))


def test_entrada_main_abre_e_fecha(monkeypatch):
    calls = []
    monkeypatch.setattr(App, "run", lambda self: calls.append(self))
    root = Path(__file__).resolve().parents[2]
    runpy.run_path(str(root / "main.py"), run_name="__main__")
    monkeypatch.delitem(sys.modules, "xadrez.__main__", raising=False)
    runpy.run_module("xadrez", run_name="__main__")
    assert len(calls) == 2
    pygame.event.clear()


def test_ajuda_do_autoplay_converte_nome_de_casa():
    assert _cell("a1") == (0, 0)
    assert _cell("h8") == (7, 7)


def test_ponto_de_clique_cai_na_peca_mesmo_com_camera_de_lado(app):
    scene, player = start_game(app)
    scene.view.camera.orbit_by(0.7, -0.2)
    for name in ("a2", "e2", "h1", "d8", "g7", "d4", "e5", "b6"):
        assert scene.view.pick(click_point(scene.view, cell(name))) == cell(name)


def test_clique_real_cai_na_casa_com_camera_de_lado(app):
    scene, player = start_game(app)
    scene.view.camera.orbit_by(0.7, -0.2)
    post_click(click_point(scene.view, cell("e2")))
    player.frames(1)
    assert scene.selection == cell("e2")
