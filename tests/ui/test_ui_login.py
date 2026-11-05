"""Entrar, criar conta e jogar como convidado (RF20, CT-93)."""
import runpy
from pathlib import Path

import pygame
import pytest

from xadrez.data import LOGIN_FAILED_MESSAGE, AccountError, AccountStore
from xadrez.ui import App, LoginScene, MenuScene
from xadrez.ui.autoplay import Autoplayer
from xadrez.ui.login_scene import PASSWORD_MISMATCH_MESSAGE

PASSWORD = "cavalo-branco-7"
NAME = "Jogador Um"


@pytest.fixture
def login_app():
    application = App(seed=11, require_login=True)
    pygame.event.clear()
    yield application
    application.scene.shutdown()
    pygame.event.clear()


@pytest.fixture
def login(login_app):
    return Autoplayer(login_app)


def fill_sign_in(player, name=NAME, password=PASSWORD):
    player.type_text(name)
    player.press(pygame.K_TAB)
    player.type_text(password)


@pytest.mark.ct("CT-93")
def test_main_abre_no_login_e_app_comum_abre_no_menu(login_app, app):
    assert isinstance(login_app.scene, LoginScene)
    assert isinstance(app.scene, MenuScene)
    assert app.account is None


@pytest.mark.ct("CT-93")
def test_main_py_usa_o_login(monkeypatch):
    created = []
    monkeypatch.setattr(App, "run", lambda self: created.append(self))
    root = Path(__file__).resolve().parents[2]
    runpy.run_path(str(root / "main.py"), run_name="__main__")
    assert isinstance(created[0].scene, LoginScene)
    assert created[0].network is not None, "o jogo do jogador tem rede"
    pygame.event.clear()


def test_app_comum_nao_tem_rede_nem_contas(app):
    assert app.network is None
    assert app.history_store() is None


@pytest.mark.ct("CT-93")
def test_conta_nova_entra_e_fica_gravada(login_app, login):
    scene = login_app.scene
    login.click_segment(scene.mode_selector, 1)
    assert scene.submit_button.label == "Criar conta"
    login.click_widget(scene.username_input)
    fill_sign_in(login)
    login.press(pygame.K_TAB)
    login.type_text(PASSWORD)
    login.press(pygame.K_RETURN)
    assert login_app.account == NAME
    assert isinstance(login_app.scene, MenuScene)
    assert AccountStore().authenticate(NAME, PASSWORD)


@pytest.mark.ct("CT-93")
def test_entrar_com_senha_certa_pelo_teclado(login_app, login):
    AccountStore().create(NAME, PASSWORD)
    fill_sign_in(login)
    login.press(pygame.K_RETURN)
    assert isinstance(login_app.scene, MenuScene)
    assert login_app.account == NAME


@pytest.mark.ct("CT-93")
def test_entrar_pelo_botao_com_outra_grafia_mostra_o_nome_original(login_app, login):
    AccountStore().create(NAME, PASSWORD)
    fill_sign_in(login, name="JOGADOR UM")
    login.click_widget(login_app.scene.submit_button)
    assert login_app.account == NAME, "o nome aparece como foi criado"


@pytest.mark.ct("CT-93")
def test_senha_errada_mostra_o_erro_e_nao_entra(login_app, login):
    AccountStore().create(NAME, PASSWORD)
    scene = login_app.scene
    fill_sign_in(login, password="senha-errada")
    login.press(pygame.K_RETURN)
    assert login_app.scene is scene
    assert scene.error == LOGIN_FAILED_MESSAGE
    assert login_app.account is None
    assert scene.password_input.text == "", "a senha não fica guardada depois de usada"
    assert scene.focus.focused is scene.password_input
    login.frames(2)


@pytest.mark.ct("CT-93")
def test_usuario_que_nao_existe_tem_a_mesma_mensagem(login_app, login):
    scene = login_app.scene
    fill_sign_in(login, name="Ninguem")
    login.press(pygame.K_RETURN)
    assert scene.error == LOGIN_FAILED_MESSAGE


@pytest.mark.ct("CT-93")
@pytest.mark.parametrize("name, password, fragment", [
    ("ab", PASSWORD, "3 a 16"),
    (NAME, "curta", "pelo menos 8"),
])
def test_conta_invalida_mostra_a_mensagem_de_account_error(login_app, login, name, password, fragment):
    scene = login_app.scene
    login.click_segment(scene.mode_selector, 1)
    login.click_widget(scene.username_input)
    fill_sign_in(login, name, password)
    login.press(pygame.K_TAB)
    login.type_text(password)
    login.press(pygame.K_RETURN)
    assert login_app.scene is scene
    assert fragment in scene.error
    assert login_app.account is None


@pytest.mark.ct("CT-93")
def test_nome_repetido_e_recusado(login_app, login):
    AccountStore().create(NAME, PASSWORD)
    scene = login_app.scene
    login.click_segment(scene.mode_selector, 1)
    login.click_widget(scene.username_input)
    fill_sign_in(login)
    login.press(pygame.K_TAB)
    login.type_text(PASSWORD)
    login.press(pygame.K_RETURN)
    assert "Já existe" in scene.error


@pytest.mark.ct("CT-93")
def test_senhas_diferentes_nao_criam_conta(login_app, login):
    scene = login_app.scene
    login.click_segment(scene.mode_selector, 1)
    login.click_widget(scene.username_input)
    fill_sign_in(login)
    login.press(pygame.K_TAB)
    login.type_text("outra-senha-9")
    login.press(pygame.K_RETURN)
    assert scene.error == PASSWORD_MISMATCH_MESSAGE
    assert AccountStore().usernames() == []
    assert scene.repeat_input.text == ""


@pytest.mark.ct("CT-93")
def test_convidado_entra_sem_conta_e_avisa_que_nao_grava(login_app, login):
    scene = login_app.scene
    login.type_text(NAME)
    login.click_widget(scene.guest_button)
    assert isinstance(login_app.scene, MenuScene)
    assert login_app.account is None
    assert login_app.history_store() is None
    assert any("não ficam guardadas" in line for lines, *_ in scene._notes for line in lines)


@pytest.mark.ct("CT-93")
def test_campo_de_senha_e_mascarado_e_nao_passa_pelo_cache_de_texto(login_app, login):
    scene = login_app.scene
    login.click_widget(scene.password_input)
    login.type_text(PASSWORD)
    login.frames(3)
    assert scene.password_input.is_secret
    assert scene.password_input.text == PASSWORD
    cached = [str(key[0]) for key in login_app.theme._texts]
    assert not any(PASSWORD in text for text in cached), "o texto da senha não pode ser desenhado"


@pytest.mark.ct("CT-93")
def test_senha_com_mais_pontos_que_o_campo_nao_vaza(login_app, login):
    scene = login_app.scene
    login.click_widget(scene.password_input)
    login.type_text("x" * 120)
    login.frames(2)
    assert len(scene.password_input.text) == 120


@pytest.mark.ct("CT-93")
def test_tab_percorre_os_campos_em_ordem(login_app, login):
    scene = login_app.scene
    assert scene.focus.focused is scene.username_input
    login.press(pygame.K_TAB)
    assert scene.focus.focused is scene.password_input
    login.press(pygame.K_TAB)
    assert scene.focus.focused is scene.submit_button
    login.press(pygame.K_TAB)
    assert scene.focus.focused is scene.guest_button


@pytest.mark.ct("CT-93")
def test_enter_no_usuario_vai_para_a_senha(login_app, login):
    scene = login_app.scene
    login.type_text(NAME)
    login.press(pygame.K_RETURN)
    assert scene.focus.focused is scene.password_input


@pytest.mark.ct("CT-93")
def test_trocar_o_modo_limpa_o_erro_e_a_repeticao(login_app, login):
    scene = login_app.scene
    fill_sign_in(login, name="Ninguem")
    login.press(pygame.K_RETURN)
    assert scene.error
    login.click_segment(scene.mode_selector, 1)
    assert scene.error == ""
    assert scene.repeat_input in scene.focus.widgets
    login.click_segment(scene.mode_selector, 0)
    assert scene.repeat_input not in scene.focus.widgets


@pytest.mark.ct("CT-93")
def test_sair_da_conta_volta_ao_login(login_app, login):
    AccountStore().create(NAME, PASSWORD)
    fill_sign_in(login)
    login.press(pygame.K_RETURN)
    menu = login_app.scene
    assert menu.account_button.label == "Sair da conta"
    login.click_widget(menu.account_button)
    assert isinstance(login_app.scene, LoginScene)
    assert login_app.account is None


@pytest.mark.ct("CT-93")
def test_convidado_pode_entrar_na_conta_pelo_menu(login_app, login):
    login.click_widget(login_app.scene.guest_button)
    menu = login_app.scene
    assert menu.account_button.label == "Entrar"
    login.seconds(0.3)
    login.click_widget(menu.account_button)
    assert isinstance(login_app.scene, LoginScene)


def test_botao_sair_do_login_encerra_o_jogo(login_app, login):
    login.click_widget(login_app.scene.quit_button)
    assert login_app.running is False


def test_nome_do_usuario_recusa_o_que_a_fonte_nao_desenha(login_app, login):
    scene = login_app.scene
    login.type_text("\U0001F600")
    assert scene.username_input.text == ""


def test_fechar_o_jogo_no_login_limpa_a_senha(login_app, login):
    scene = login_app.scene
    login.click_widget(scene.password_input)
    login.type_text(PASSWORD)
    scene.shutdown()
    assert scene.password_input.text == ""


def test_convidado_limpa_a_senha_digitada(login_app, login):
    scene = login_app.scene
    login.click_widget(scene.password_input)
    login.type_text(PASSWORD)
    login.click_widget(scene.guest_button)
    assert scene.password_input.text == ""


@pytest.mark.parametrize("size", [(1, 1), (320, 200), (800, 600), (1024, 640), (1920, 1080)])
def test_login_nao_quebra_em_janela_pequena(login_app, login, size):
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
    login.frames(2)
    scene = login_app.scene
    scene.error = "Mensagem de erro bem comprida para conferir a quebra de linha na tela."
    login.click_segment(scene.mode_selector, 1)
    scene.error = "Mensagem de erro bem comprida para conferir a quebra de linha na tela."
    login.frames(2)


def test_falha_ao_gravar_a_conta_vira_mensagem(login_app, login, monkeypatch):
    def refuse(self, username, password):
        raise AccountError("Não foi possível gravar.")

    monkeypatch.setattr(AccountStore, "create", refuse)
    scene = login_app.scene
    login.click_segment(scene.mode_selector, 1)
    login.click_widget(scene.username_input)
    fill_sign_in(login)
    login.press(pygame.K_TAB)
    login.type_text(PASSWORD)
    login.press(pygame.K_RETURN)
    assert scene.error == "Não foi possível gravar."
