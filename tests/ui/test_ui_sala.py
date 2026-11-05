"""Sala em rede: mostrar o código, digitar o código, e cada erro com mensagem clara (RF19, UC11, UC12)."""
import pygame
import pytest
from ui_helpers import LoopbackNetwork, drive

from xadrez.core import Color, TimeControl
from xadrez.net import GameStart, MoveReceived, NetworkError, PeerJoined, PeerLeft
from xadrez.net.session import OFFLINE_WARNING
from xadrez.ui import App, GameScene, LobbyScene, MatchOptions, MenuScene
from xadrez.ui import clipboard
from xadrez.ui.autoplay import Autoplayer
from xadrez.ui.lobby_scene import ROLE_GUEST, ROLE_HOST
from xadrez.ui.match import OPPONENT_NET
from xadrez.ui.menu_scene import NETWORK_OFF_MESSAGE

OPTIONS = MatchOptions("Jogador 1", "Jogador 2", TimeControl.BLITZ_3_2, opponent_kind=OPPONENT_NET)


class FakeSession:
    """Sessão de mentira: o teste escolhe o que `poll` entrega, sem depender de tempo de rede."""

    def __init__(self, code="GEJXWVH", warning=None):
        self.code = code
        self.offline_warning = warning
        self.events = []
        self.closed = False
        self.said_bye = False

    def start(self):
        pass

    def poll(self):
        events, self.events = self.events, []
        return events

    def send_bye(self):
        self.said_bye = True

    def close(self):
        self.closed = True


class FakeNetwork:
    def __init__(self):
        self.sessions = []
        self.warning = None

    def host(self, name, time_control):
        self.sessions.append(FakeSession(warning=self.warning))
        return self.sessions[-1]

    def client(self, name, code):
        self.sessions.append(FakeSession(code=code))
        return self.sessions[-1]


@pytest.fixture
def network():
    return FakeNetwork()


@pytest.fixture
def lobby_app(network):
    application = App(seed=4, network=network)
    pygame.event.clear()
    yield application
    application.scene.shutdown()


def open_lobby(app, role=ROLE_HOST):
    app.scene.next_scene = app.lobby_scene(OPTIONS, role)
    player = Autoplayer(app)
    player.frames(1)
    return app.scene, player


def start_event(your_color=Color.WHITE):
    return GameStart("Jogador 1", "Jogador 2", your_color, 3, 2)


def test_menu_sem_rede_avisa_e_nao_abre_porta(app, player):
    menu = app.scene
    player.click_segment(menu.opponent_selector, 2)
    player.click_widget(menu.create_room_button)
    assert isinstance(app.scene, MenuScene)
    assert menu.notice == NETWORK_OFF_MESSAGE
    player.click_widget(menu.join_room_button)
    assert isinstance(app.scene, MenuScene)
    player.frames(1)


def test_sala_mostra_o_codigo_e_espera(lobby_app, network):
    lobby, player = open_lobby(lobby_app)
    assert lobby.code == "GEJXWVH"
    assert lobby._status_text() == "Aguardando adversário"
    assert lobby.focus.focused is lobby.copy_button
    player.seconds(1.0)
    assert lobby_app.scene is lobby


def test_copiar_convite_tem_o_codigo(lobby_app, monkeypatch):
    copied = []
    monkeypatch.setattr(clipboard, "copy_text", lambda text: copied.append(text) or True)
    lobby, player = open_lobby(lobby_app)
    player.click_widget(lobby.copy_button)
    assert "GEJXWVH" in copied[0]
    assert lobby.message == "Convite copiado."


def test_copiar_convite_que_falha_avisa(lobby_app, monkeypatch):
    monkeypatch.setattr(clipboard, "copy_text", lambda text: False)
    lobby, player = open_lobby(lobby_app)
    player.click_widget(lobby.copy_button)
    assert lobby.message == clipboard.COPY_FAILED_MESSAGE


def test_aviso_de_sala_sem_rede_aparece(lobby_app, network):
    network.warning = OFFLINE_WARNING
    lobby, player = open_lobby(lobby_app)
    assert lobby.warning == OFFLINE_WARNING
    assert any(OFFLINE_WARNING.startswith(lines[0]) for lines, *_ in lobby._notes)
    player.frames(2)


def test_quem_entra_aparece_antes_de_comecar(lobby_app, network):
    lobby, player = open_lobby(lobby_app)
    network.sessions[0].events.append(PeerJoined("Jogador 2"))
    player.frames(1)
    assert lobby.peer_name == "Jogador 2"
    assert "entrou" in lobby._status_text()
    assert lobby_app.scene is lobby


def test_inicio_da_partida_abre_o_tabuleiro_e_nada_se_perde(lobby_app, network):
    lobby, player = open_lobby(lobby_app, ROLE_GUEST)
    player.type_text("gejxwvh")
    player.press(pygame.K_RETURN)
    session = network.sessions[0]
    session.events += [PeerJoined("Jogador 1"), start_event(Color.BLACK), MoveReceived("e2e4", 0)]
    player.frames(1)
    game = lobby_app.scene
    assert isinstance(game, GameScene)
    assert game.local_color is Color.BLACK
    assert game.engine.time_control == TimeControl.BLITZ_3_2
    assert game.net.link.peer_name == "Jogador 1"
    player.frames(2)
    assert game.engine.history == ["e4"], "a jogada que veio junto com o início não pode se perder"
    assert session.closed is False


def test_campo_do_codigo_aceita_minuscula_e_corta_em_7(lobby_app):
    lobby, player = open_lobby(lobby_app, ROLE_GUEST)
    player.type_text("abc-de fghijk")
    assert lobby.code_input.text == "ABCDEFG"


def test_entrar_nao_abre_duas_conexoes(lobby_app, network):
    lobby, player = open_lobby(lobby_app, ROLE_GUEST)
    player.type_text("ABCDEFG")
    player.click_widget(lobby.connect_button)
    assert lobby.is_connecting
    assert lobby._status_text() == "Conectando"
    player.click_widget(lobby.connect_button)
    assert len(network.sessions) == 1
    player.frames(2)


def test_erro_ao_entrar_mostra_a_mensagem_e_deixa_tentar_de_novo(lobby_app, network):
    lobby, player = open_lobby(lobby_app, ROLE_GUEST)
    player.type_text("ABCDEFG")
    player.press(pygame.K_RETURN)
    network.sessions[0].events.append(NetworkError("Código de sala inválido."))
    player.frames(2)
    assert lobby.error == "Código de sala inválido."
    assert not lobby.is_connecting
    assert network.sessions[0].closed
    assert lobby_app.scene is lobby
    player.press(pygame.K_RETURN)
    assert len(network.sessions) == 2
    assert lobby.error == ""


def test_erro_na_sala_mostra_a_mensagem_e_permite_abrir_de_novo(lobby_app, network):
    lobby, player = open_lobby(lobby_app)
    network.sessions[0].events.append(NetworkError("A porta está ocupada."))
    player.frames(2)
    assert lobby.error == "A porta está ocupada."
    assert lobby.retry_button in lobby.focus.widgets
    assert lobby.copy_button not in lobby.focus.widgets
    player.click_widget(lobby.retry_button)
    assert len(network.sessions) == 2
    assert lobby.error == ""
    assert lobby.copy_button in lobby.focus.widgets


def test_adversario_que_desiste_de_entrar_volta_a_mostrar_o_erro(lobby_app, network):
    lobby, player = open_lobby(lobby_app)
    network.sessions[0].events += [PeerJoined("Jogador 2"), PeerLeft("O adversário saiu.")]
    player.frames(2)
    assert lobby.error == "O adversário saiu."
    assert lobby.peer_name is None


@pytest.mark.parametrize("role", [ROLE_HOST, ROLE_GUEST])
def test_cancelar_fecha_a_sessao_e_volta_ao_menu_com_as_opcoes(lobby_app, network, role):
    lobby, player = open_lobby(lobby_app, role)
    if role == ROLE_GUEST:
        player.type_text("ABCDEFG")
        player.click_widget(lobby.connect_button)
    player.click_widget(lobby.cancel_button)
    menu = lobby_app.scene
    assert isinstance(menu, MenuScene)
    assert network.sessions[0].closed and network.sessions[0].said_bye
    assert menu.opponent_kind == OPPONENT_NET
    assert menu.time_selector.value == TimeControl.BLITZ_3_2


def test_esc_tambem_cancela(lobby_app, network):
    lobby, player = open_lobby(lobby_app)
    player.press(pygame.K_ESCAPE)
    assert isinstance(lobby_app.scene, MenuScene)
    assert network.sessions[0].closed


def test_fechar_o_jogo_na_sala_fecha_a_sessao(lobby_app, network):
    lobby, player = open_lobby(lobby_app)
    lobby_app.scene.shutdown()
    assert network.sessions[0].closed
    lobby_app.scene.shutdown()


@pytest.mark.parametrize("role", [ROLE_HOST, ROLE_GUEST])
@pytest.mark.parametrize("size", [(1, 1), (320, 200), (800, 600), (1024, 640), (1920, 1080)])
def test_sala_nao_quebra_em_janela_pequena(lobby_app, network, role, size):
    network.warning = OFFLINE_WARNING
    lobby, player = open_lobby(lobby_app, role)
    lobby.error = "Mensagem de erro bem comprida para conferir a quebra de linha na tela."
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
    player.frames(2)
    assert lobby_app.scene is lobby


# Sessões de verdade, em 127.0.0.1 -----------------------------------------------------------------


@pytest.fixture
def real_network():
    loopback = LoopbackNetwork()
    yield loopback
    loopback.close_all()


@pytest.fixture
def real_app(real_network):
    application = App(seed=4, network=real_network)
    pygame.event.clear()
    yield application
    application.scene.shutdown()


@pytest.mark.ct("CT-95")
def test_codigo_invalido_mostra_erro_claro(real_app):
    lobby, player = open_lobby(real_app, ROLE_GUEST)
    player.type_text("ABC")
    player.press(pygame.K_RETURN)
    drive([real_app], lambda: bool(lobby.error))
    assert "7 caracteres" in lobby.error


@pytest.mark.ct("CT-95")
def test_conexao_recusada_mostra_erro_claro(real_app, real_network):
    host = real_network.host("Fechada", TimeControl.UNLIMITED)
    host.start()
    code = host.code
    host.close()
    lobby, player = open_lobby(real_app, ROLE_GUEST)
    player.type_text(code)
    player.press(pygame.K_RETURN)
    drive([real_app], lambda: bool(lobby.error), limit=30.0)
    assert "Confira o código" in lobby.error


@pytest.mark.ct("CT-95")
def test_codigo_de_verdade_tem_7_caracteres_e_a_sala_fica_escutando(real_app):
    lobby, player = open_lobby(real_app)
    assert len(lobby.code) == 7
    assert lobby.warning is None
    assert isinstance(lobby, LobbyScene)
