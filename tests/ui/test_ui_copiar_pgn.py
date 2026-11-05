"""Copiar o PGN: com área de transferência falsa, porque sem janela não há a de verdade (RF22, CT-98)."""
import sys

import pygame
import pytest
from ui_helpers import finish_with_mate, hud_button, start_game

from xadrez.ui import clipboard


class FakeScrap:
    """Imita `pygame.scrap`. Guarda o que chegou, para o teste conferir os bytes."""

    def __init__(self, is_ready=False, init_error=None, put_error=None):
        self.is_ready = is_ready
        self.init_error = init_error
        self.put_error = put_error
        self.stored = []

    def get_init(self):
        return self.is_ready

    def init(self):
        if self.init_error is not None:
            raise self.init_error
        self.is_ready = True

    def put(self, kind, data):
        if self.put_error is not None:
            raise self.put_error
        self.stored.append((kind, data))


@pytest.fixture
def copied(monkeypatch):
    texts = []
    monkeypatch.setattr(clipboard, "copy_text", lambda text: texts.append(text) or True)
    return texts


@pytest.mark.ct("CT-98")
def test_botao_copia_o_pgn_da_partida(app, copied):
    scene, player = start_game(app)
    player.play_all("e2e4 e7e5")
    player.click_widget(hud_button(scene, "Copiar PGN"))
    assert len(copied) == 1
    assert '[White "Jogador 1"]' in copied[0]
    assert "1. e4 e5" in copied[0]
    assert copied[0].rstrip().endswith("*"), "a partida ainda não acabou"
    assert "copiado" in scene.notices.text


@pytest.mark.ct("CT-98")
def test_tecla_c_copia(app, copied):
    scene, player = start_game(app)
    player.press(pygame.K_c)
    assert len(copied) == 1


@pytest.mark.ct("CT-98")
def test_tela_de_fim_copia_a_partida_com_resultado(app, copied):
    _, player = start_game(app)
    finish_with_mate(player)
    over = app.scene
    player.click_widget(over.copy_button)
    assert "Qxf7#" in copied[0]
    assert "1-0" in copied[0]
    assert "copiado" in over.notices.text
    player.press(pygame.K_c)
    assert len(copied) == 2
    player.seconds(3.0)
    assert over.notices.text == ""


@pytest.mark.ct("CT-98")
def test_copiar_que_falha_vira_aviso_nunca_excecao(app, monkeypatch):
    monkeypatch.setattr(clipboard, "copy_text", lambda text: False)
    scene, player = start_game(app)
    player.press(pygame.K_c)
    assert scene.notices.text == clipboard.COPY_FAILED_MESSAGE
    assert scene.notices.kind == "warning"


@pytest.mark.ct("CT-98")
def test_sem_janela_a_copia_de_verdade_devolve_nao(app):
    """O driver sem janela do SDL não tem área de transferência: é o pior caso real, e não pode levantar nada."""
    assert clipboard.copy_text("texto") is False


@pytest.mark.ct("CT-98")
def test_copia_inicia_a_area_de_transferencia_uma_vez(monkeypatch):
    fake = FakeScrap()
    monkeypatch.setattr(pygame, "scrap", fake)
    assert clipboard.copy_text("a") is True
    assert fake.is_ready
    assert clipboard.copy_text("b") is True
    assert [kind for kind, _ in fake.stored] == [pygame.SCRAP_TEXT] * 2


@pytest.mark.ct("CT-98")
@pytest.mark.parametrize("failure", [pygame.error("sem suporte"), NotImplementedError(), OSError("ocupada"), ValueError("texto")])
def test_qualquer_falha_ao_iniciar_ou_copiar_devolve_nao(monkeypatch, failure):
    monkeypatch.setattr(pygame, "scrap", FakeScrap(init_error=failure))
    assert clipboard.copy_text("a") is False
    monkeypatch.setattr(pygame, "scrap", FakeScrap(is_ready=True, put_error=failure))
    assert clipboard.copy_text("a") is False


@pytest.mark.ct("CT-98")
def test_fora_do_windows_o_texto_vai_em_utf8(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "linux")
    assert clipboard._encoded("João\n½") == "João\n½".encode("utf-8")


@pytest.mark.ct("CT-98")
@pytest.mark.skipif(sys.platform != "win32", reason="a codificação ANSI só existe no Windows")
def test_no_windows_o_texto_vai_na_codificacao_do_sistema_com_quebra_de_linha_do_sistema():
    assert clipboard._encoded("João\n½") == "João\r\n½".encode("mbcs")
