"""Contas e histórico sob ataque: login por eventos, arquivos adulterados e registro certo em cada fim de partida.

CT-118: login e criação de conta por teclado e mouse: nome com maiúsculas, acento, espaços e emoji; senha vazia, longa, com espaços e acento.
CT-119: a senha não fica no widget nem em nenhum cache de texto depois de usada.
CT-120: arquivo de contas corrompido, com tipos errados, gigante, ou pasta sem acesso: a tela mostra aviso, nunca cai.
CT-121: histórico editado à mão, com tipos errados, controle, PGN gigante e números absurdos: a aba abre e desenha.
CT-122: registro correto em cada fim: vitória, derrota, empate, adversário, cor depois da revanche, duração, modo.
CT-123: duas contas separadas, convidado sem gravar, "Sair da conta", 51ª partida e lista rolando com 50 itens.
"""
from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path

import pygame
import pytest
from test_ataque_v11_apoio import *  # noqa: F403

from xadrez.core import Color, Difficulty, EndReason, TimeControl
from xadrez.data import LOGIN_FAILED_MESSAGE, AccountStore, HistoryStore, MatchRecord
from xadrez.ui import LoginScene, MenuScene
from xadrez.ui.login_scene import PASSWORD_MISMATCH_MESSAGE
from xadrez.ui.match_record import ABANDONED_REASON

PASSWORD = "Abacaxi!123"
SECRET_MARK = "ZZSENHASECRETAZZ"
SCHOLARS_MATE = "e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7"
FOOLS_MATE = "f2f3 e7e5 g2g4 d8h4"


def valid_entry(**changes):
    entry = {
        "played_at": "2026-11-05T10:00:00", "opponent": "Bia", "opponent_kind": "local", "difficulty": None,
        "color": "Brancas", "outcome": "vitoria", "reason": "Xeque-mate", "moves": 10, "seconds": 90.5,
        "time_control": "Blitz 5", "mode": "Treinamento", "pgn": "[White \"a\"]\n\n1. e4 e5 *\n", "final_fen": "8/8/8/8/8/8/8/8 w - - 0 1",
    }
    entry.update(changes)
    return entry


def history_path(username):
    from xadrez.data.history import _history_file_name
    from xadrez.data.paths import data_dir
    return data_dir() / _history_file_name(username)


def write_history(username, entries):
    path = history_path(username)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "records": entries}), encoding="utf-8")


def login_app():
    application = make_app(require_login=True, network=None)
    return application, Autoplayer(application)


def create_by_mouse(player, username, password, repeated=None):
    scene = player.app.scene
    player.click_segment(scene.mode_selector, 1)
    player.click_widget(scene.username_input)
    for _ in range(40):
        post_key(pygame.K_BACKSPACE)
    player.frames(1)
    player.type_text(username)
    player.click_widget(scene.password_input)
    player.type_text(password)
    player.click_widget(scene.repeat_input)
    player.type_text(password if repeated is None else repeated)
    player.click_widget(scene.submit_button)


def sign_in_by_mouse(player, username, password):
    scene = player.app.scene
    player.click_widget(scene.username_input)
    for _ in range(40):
        post_key(pygame.K_BACKSPACE)
    player.frames(1)
    player.type_text(username)
    player.click_widget(scene.password_input)
    player.type_text(password)
    player.click_widget(scene.submit_button)


def open_history_tab(player):
    menu = player.app.scene
    player.click_segment(menu.tab_bar, 1)
    player.frames(1)
    return menu


# Login ---------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-118")
def test_conta_com_acento_e_maiusculas_entra_por_qualquer_grafia():
    application, player = login_app()
    create_by_mouse(player, "João", PASSWORD)
    assert isinstance(application.scene, MenuScene)
    assert application.account == "João"
    player.click_widget(application.scene.account_button)
    assert isinstance(application.scene, LoginScene)
    for typed in ("JOÃO", "joão", "João", "  João  "):
        sign_in_by_mouse(player, typed, PASSWORD)
        assert isinstance(application.scene, MenuScene), typed
        assert application.account == "João"
        player.click_widget(application.scene.account_button)


@pytest.mark.ct("CT-118")
@pytest.mark.parametrize("name, expected_error", [
    ("", True), ("   ", True), ("ab", True), ("  a  ", True),
])
def test_nome_curto_ou_so_de_espacos_vira_aviso(name, expected_error):
    application, player = login_app()
    create_by_mouse(player, name, PASSWORD)
    assert isinstance(application.scene, LoginScene)
    assert application.scene.error
    assert AccountStore().usernames() == []


@pytest.mark.ct("CT-118")
def test_emoji_no_nome_nao_entra_pelo_campo():
    application, player = login_app()
    scene = application.scene
    player.click_widget(scene.username_input)
    player.type_text("A\U0001f600B")
    assert "\U0001f600" not in scene.username_input.text


@pytest.mark.ct("CT-118")
@pytest.mark.parametrize("password, is_ok", [
    ("", False), ("1234567", False), ("        ", True), ("senha com espaço", True), ("ação çãõ é", True),
    ("x" * 128, True), ("\U0001f600" * 8, True),
])
def test_cada_tipo_de_senha_criada_e_depois_conferida(password, is_ok):
    application, player = login_app()
    create_by_mouse(player, "Ana", password)
    if not is_ok:
        assert isinstance(application.scene, LoginScene) and application.scene.error
        return
    assert isinstance(application.scene, MenuScene), application.scene.error if hasattr(application.scene, "error") else ""
    player.click_widget(application.scene.account_button)
    sign_in_by_mouse(player, "ana", password)
    assert isinstance(application.scene, MenuScene)


@pytest.mark.ct("CT-118")
def test_senha_maior_que_o_limite_e_cortada_igual_nas_duas_vezes():
    application, player = login_app()
    long_password = "y" * 500
    create_by_mouse(player, "Ana", long_password)
    assert isinstance(application.scene, MenuScene)
    player.click_widget(application.scene.account_button)
    sign_in_by_mouse(player, "Ana", long_password)
    assert isinstance(application.scene, MenuScene)


@pytest.mark.ct("CT-118")
def test_nome_repetido_e_senhas_diferentes_viram_aviso_e_limpam_as_senhas():
    application, player = login_app()
    create_by_mouse(player, "Ana", PASSWORD)
    player.click_widget(application.scene.account_button)
    scene = application.scene
    create_by_mouse(player, "ANA", PASSWORD)
    assert scene.error == "Já existe uma conta com esse nome."
    assert scene.password_input.text == "" and scene.repeat_input.text == ""
    player.click_widget(scene.username_input)
    for _ in range(4):
        post_key(pygame.K_BACKSPACE)
    player.frames(1)
    player.type_text("Bia")
    player.click_widget(scene.password_input)
    player.type_text(PASSWORD)
    player.click_widget(scene.repeat_input)
    player.type_text(PASSWORD + "x")
    player.click_widget(scene.submit_button)
    assert scene.error == PASSWORD_MISMATCH_MESSAGE
    assert AccountStore().usernames() == ["Ana"]


@pytest.mark.ct("CT-118")
def test_senha_errada_e_conta_inexistente_recebem_a_mesma_mensagem():
    application, player = login_app()
    create_by_mouse(player, "Ana", PASSWORD)
    player.click_widget(application.scene.account_button)
    scene = application.scene
    sign_in_by_mouse(player, "Ana", "senhaerrada")
    first = scene.error
    sign_in_by_mouse(player, "Ninguem", "senhaerrada")
    assert first == scene.error == LOGIN_FAILED_MESSAGE


@pytest.mark.ct("CT-118")
def test_criar_conta_so_pelo_teclado_com_enter_entre_os_campos():
    """Usuário, Enter, senha, Enter, repetir, Enter: é o caminho de quem preenche um formulário sem o mouse."""
    application, player = login_app()
    scene = application.scene
    player.click_segment(scene.mode_selector, 1)
    player.click_widget(scene.username_input)
    player.type_text("Ana")
    player.press(pygame.K_RETURN)
    assert scene.focus.focused is scene.password_input
    player.type_text(PASSWORD)
    player.press(pygame.K_RETURN)
    assert scene.error == "", f"recusou antes de deixar repetir a senha: {scene.error}"
    assert scene.focus.focused is scene.repeat_input
    player.type_text(PASSWORD)
    player.press(pygame.K_RETURN)
    assert isinstance(application.scene, MenuScene)


# Senha na memória ----------------------------------------------------------------------------------


def _cached_strings(theme):
    for mapping in (theme._texts, theme._wrapped, theme._glyphs):
        for entry in mapping:
            for part in entry:
                if isinstance(part, str):
                    yield part


@pytest.mark.ct("CT-119")
@pytest.mark.parametrize("path", ["entrou", "errou", "criou", "convidado", "trocou_de_aba", "reabriu_login"])
def test_senha_nao_fica_em_widget_nem_em_cache(path):
    application, player = login_app()
    scene = application.scene
    if path == "entrou":
        AccountStore().create("Ana", SECRET_MARK)
        sign_in_by_mouse(player, "Ana", SECRET_MARK)
        assert isinstance(application.scene, MenuScene)
    elif path == "errou":
        sign_in_by_mouse(player, "Ana", SECRET_MARK)
    elif path == "criou":
        create_by_mouse(player, "Ana", SECRET_MARK)
    elif path == "convidado":
        player.click_widget(scene.password_input)
        player.type_text(SECRET_MARK)
        player.click_widget(scene.guest_button)
    elif path == "trocou_de_aba":
        player.click_widget(scene.password_input)
        player.type_text(SECRET_MARK)
        player.frames(3)
        player.click_segment(scene.mode_selector, 1)
        player.frames(3)
        player.click_segment(scene.mode_selector, 0)
    else:
        create_by_mouse(player, "Ana", SECRET_MARK)
        player.click_widget(application.scene.account_button)
        player.frames(3)
    player.frames(3)
    strings = list(_cached_strings(application.theme))
    assert not any(SECRET_MARK in text for text in strings), "a senha entrou em um cache de texto"
    assert not any(char in text for char in "Z" for text in strings if text == "Z"), "letra da senha desenhada sozinha"
    if path != "trocou_de_aba":
        for widget in (scene.password_input, scene.repeat_input):
            assert widget.text == ""
    assert SECRET_MARK not in repr(vars(application.scene).get("error", ""))


@pytest.mark.ct("CT-119")
def test_senha_mascarada_desenha_so_pontos_iguais_para_senhas_diferentes():
    application, player = login_app()
    scene = application.scene
    player.click_widget(scene.password_input)
    player.type_text("abcdefgh")
    application.step(0.0)
    first = surface_array(application.screen, scene.password_input.rect)
    for _ in range(8):
        post_key(pygame.K_BACKSPACE)
    player.frames(1)
    player.type_text("WWWWWWWW")
    application.step(0.0)
    second = surface_array(application.screen, scene.password_input.rect)
    assert (first == second).all(), "o desenho muda conforme as letras: a máscara vaza"


@pytest.mark.ct("CT-119")
def test_arquivo_de_contas_nao_tem_a_senha_em_nenhum_formato():
    AccountStore().create("Ana", SECRET_MARK)
    from xadrez.data.paths import data_dir
    raw = (data_dir() / "accounts.json").read_bytes()
    assert SECRET_MARK.encode() not in raw
    assert SECRET_MARK.encode("utf-16-le") not in raw
    assert SECRET_MARK.encode().hex().encode() not in raw


# Arquivo de contas ---------------------------------------------------------------------------------


def accounts_path():
    from xadrez.data.paths import data_dir
    return data_dir() / "accounts.json"


@pytest.mark.ct("CT-120")
@pytest.mark.parametrize("content", [
    b"", b"null", b"[]", b"42", b'"texto"', b"{", b"\xff\xfe\x00", b"[" * 200000,
    b'{"version":2,"accounts":[]}', b'{"version":1,"accounts":5}', b'{"version":1,"accounts":[1]}',
    b'{"version":1,"accounts":[{"username":5,"salt":"00","iterations":1,"hash":"00"}]}',
    b'{"version":1,"accounts":[{"username":"Ana","salt":"zz","iterations":1,"hash":"00"}]}',
    b'{"version":1,"accounts":[{"username":"Ana","salt":"00000000000000000000000000000000","iterations":1e9,"hash":"00"}]}',
    b'{"version":1,"accounts":[{"username":"A\\u0000na","salt":"00000000000000000000000000000000","iterations":1,"hash":"' + b"00" * 32 + b'"}]}',
    b'{"version":1,"accounts":[{"username":"Ana\\ud83d","salt":"00000000000000000000000000000000","iterations":1,"hash":"' + b"00" * 32 + b'"}]}',
])
def test_contas_corrompidas_nao_derrubam_e_a_conta_nova_funciona(content):
    path = accounts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    application, player = login_app()
    scene = application.scene
    sign_in_by_mouse(player, "Ana", PASSWORD)
    assert scene.error == LOGIN_FAILED_MESSAGE
    create_by_mouse(player, "Ana", PASSWORD)
    assert isinstance(application.scene, MenuScene)
    assert AccountStore().authenticate("Ana", PASSWORD)


@pytest.mark.ct("CT-120")
def test_uma_conta_ruim_nao_perde_o_arquivo_sem_copia(tmp_path):
    AccountStore().create("Ana", PASSWORD)
    path = accounts_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["accounts"].append({"username": 5})
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert AccountStore().authenticate("Ana", PASSWORD) is False
    copies = [item for item in path.parent.iterdir() if "corrompido" in item.name]
    assert copies, "o arquivo ruim tem de ficar guardado, com a conta boa dentro"
    assert b"Ana" in copies[0].read_bytes()


@pytest.mark.ct("CT-120")
def test_pasta_de_dados_invalida_vira_aviso_no_login_e_na_criacao(monkeypatch, tmp_path):
    blocker = tmp_path / "um_arquivo"
    blocker.write_text("não é pasta", encoding="utf-8")
    monkeypatch.setenv("CHESS_THE_GAME_DATA", str(blocker / "dados"))
    application, player = login_app()
    scene = application.scene
    sign_in_by_mouse(player, "Ana", PASSWORD)
    assert scene.error == LOGIN_FAILED_MESSAGE
    create_by_mouse(player, "Ana", PASSWORD)
    assert isinstance(application.scene, LoginScene)
    assert "gravar" in scene.error or "ler" in scene.error
    # E dá para jogar mesmo assim, como convidado.
    player.click_widget(scene.guest_button)
    assert isinstance(application.scene, MenuScene)


@pytest.mark.ct("CT-120")
def test_arquivo_de_contas_que_e_uma_pasta(monkeypatch):
    path = accounts_path()
    path.mkdir(parents=True, exist_ok=True)
    application, player = login_app()
    scene = application.scene
    sign_in_by_mouse(player, "Ana", PASSWORD)
    assert scene.error == LOGIN_FAILED_MESSAGE
    create_by_mouse(player, "Ana", PASSWORD)
    assert isinstance(application.scene, LoginScene) and scene.error


# Histórico adulterado ------------------------------------------------------------------------------


def open_tampered_history(entries):
    write_history("Ana", entries)
    application = make_app()
    application.account = "Ana"
    application.scene.next_scene = application.menu_scene()
    player = Autoplayer(application)
    player.frames(1)
    open_history_tab(player)
    return application, player, application.scene


@pytest.mark.ct("CT-121")
@pytest.mark.parametrize("field, value", [
    ("opponent", ""), ("opponent", "\x00\x07\x1b[31m"), ("opponent", "W" * 300), ("opponent", "\U0001f600" * 40),
    ("opponent", chr(0x202e) + "invertido"), ("opponent", chr(0x301) * 20),
    ("played_at", ""), ("played_at", "ontem à noite"), ("played_at", "0001-01-01"), ("played_at", "9999-12-31T23:59:59"),
    ("played_at", "2026-13-45"), ("played_at", "x" * 5000),
    ("reason", ""), ("reason", "\n\n\n"), ("color", "Roxas" * 100), ("mode", "\t"), ("time_control", "\x7f"),
    ("moves", 0), ("moves", 10**30), ("seconds", 0), ("seconds", 1e308), ("seconds", 10**30),
    ("pgn", ""), ("pgn", "[só cabeçalho"), ("pgn", "\n" * 500), ("pgn", "x" * 3000), ("pgn", "1. e4 " * 2000),
    ("final_fen", ""), ("final_fen", "y" * 3000), ("final_fen", "\x00"),
    ("difficulty", "Impossível"),
])
def test_historico_editado_abre_lista_e_folha(field, value):
    application, player, menu = open_tampered_history([valid_entry(**{field: value})])
    history = menu.history
    assert len(history.list.records) == 1, "um registro válido não pode sumir"
    post_click(history.list.row_rect(0).center)
    player.frames(2)
    assert history.opened is not None
    player.press(pygame.K_c)
    player.press(pygame.K_ESCAPE)
    player.frames(1)
    application.scene.shutdown()


@pytest.mark.ct("CT-121")
def test_duracao_com_inteiro_gigante_nao_derruba_a_aba():
    application, player, menu = open_tampered_history([valid_entry(seconds=10**400)])
    application.step(0.0)
    assert len(menu.history.list.records) in (0, 1)


@pytest.mark.ct("CT-121")
@pytest.mark.parametrize("record", [
    "texto", 5, None, [], {}, valid_entry(moves=-1), valid_entry(moves=1.5), valid_entry(moves=True), valid_entry(seconds=-1),
    valid_entry(seconds="1"), valid_entry(outcome="ganhou"), valid_entry(opponent_kind="alien"), valid_entry(pgn=5),
    valid_entry(difficulty=5),
])
def test_registro_com_tipo_errado_poe_o_arquivo_de_lado_e_a_aba_abre_vazia(record):
    application, player, menu = open_tampered_history([record])
    assert menu.history.list.records == []
    application.step(0.0)
    copies = [item for item in history_path("Ana").parent.iterdir() if "corrompido" in item.name]
    assert copies


@pytest.mark.ct("CT-121")
@pytest.mark.parametrize("content", [b"", b"null", b"{", b"[1]", b"\xff", b'{"version":9,"records":[]}', b'{"version":1,"records":3}', b"[" * 200000])
def test_historico_corrompido_na_gravacao_nao_perde_a_partida_nova(content):
    path = history_path("Ana")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    application = make_app()
    application.account = "Ana"
    scene, player = open_game(application, mode=GameMode.TRAINING)
    player.play_all(FOOLS_MATE)
    assert len(HistoryStore("Ana").records()) == 1


@pytest.mark.ct("CT-121")
def test_historico_que_nao_se_consegue_gravar_vira_aviso_e_a_partida_termina(monkeypatch, tmp_path):
    blocker = tmp_path / "um_arquivo"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("CHESS_THE_GAME_DATA", str(blocker / "dados"))
    application = make_app()
    application.account = "Ana"
    scene, player = open_game(application, mode=GameMode.TRAINING)
    player.play_all(FOOLS_MATE)
    player.seconds(3.0)
    assert isinstance(application.scene, GameOverScene)
    assert "histórico" in application.scene.notices.text


@pytest.mark.ct("CT-121")
def test_nome_gigante_no_historico_nao_trava_a_lista():
    application, player, menu = open_tampered_history([valid_entry(opponent="W" * 20000)])
    started = time.perf_counter()
    application.step(0.0)
    elapsed = time.perf_counter() - started
    assert elapsed < 0.25, f"quadro de {elapsed:.2f} s"


@pytest.mark.ct("CT-121")
def test_pgn_de_cem_mil_lances_nao_trava_a_folha_para_sempre():
    application, player, menu = open_tampered_history([valid_entry(pgn="1. e4 e5 " * 100000)])
    post_click(menu.history.list.row_rect(0).center)
    player.frames(1)
    assert menu.history.opened is not None
    started = time.perf_counter()
    application.step(0.0)
    elapsed = time.perf_counter() - started
    assert elapsed < 1.0, f"quadro depois de aberta a folha: {elapsed:.2f} s"


# Registro de cada fim ------------------------------------------------------------------------------


def account_app(name="Ana"):
    application = make_app()
    application.account = name
    return application


def latest(name="Ana"):
    return HistoryStore(name).records()[0]


@pytest.mark.ct("CT-122")
def test_vitoria_por_mate_em_dois_jogadores():
    application = account_app()
    scene, player = open_game(application, mode=GameMode.MATCH, names=("Ana", "Bia"), time_control=TimeControl.BLITZ_5)
    player.seconds(2.0)
    player.play_all(SCHOLARS_MATE)
    record = latest()
    assert (record.outcome, record.opponent, record.color) == ("vitoria", "Bia", "Brancas")
    assert (record.moves, record.mode, record.opponent_kind, record.difficulty) == (4, "Partida", "local", None)
    assert record.reason == EndReason.CHECKMATE.label
    assert record.time_control == "Blitz 5"
    assert record.seconds == pytest.approx(2.0, abs=1.2)
    assert record.pgn.startswith('[Event "Chess - The Game"]')
    assert "Qxf7#" in record.pgn and "1-0" in record.pgn
    assert record.final_fen == scene.engine.final_fen


@pytest.mark.ct("CT-122")
def test_partida_e_gravada_uma_vez_so_apesar_do_voo_e_da_tela_de_fim():
    application = account_app()
    scene, player = open_game(application, mode=GameMode.TRAINING, names=("Ana", "Bia"))
    player.play_all(SCHOLARS_MATE)
    player.seconds(3.2)
    assert isinstance(application.scene, GameOverScene)
    assert len(HistoryStore("Ana").records()) == 1


@pytest.mark.ct("CT-122")
def test_cor_e_resultado_depois_da_revanche():
    application = account_app()
    scene, player = open_game(application, mode=GameMode.TRAINING, names=("Ana", "Bia"))
    player.play_all(SCHOLARS_MATE)
    player.seconds(3.2)
    application.scene.rematch()
    player.frames(1)
    second = application.scene
    player.settle()
    # Ana agora é preta, e quem joga de brancas leva o mate do louco.
    player.play_all("f2f3 e7e5 g2g4 d8h4")
    record = latest()
    assert record.color == "Pretas"
    assert record.outcome == "vitoria"
    assert record.opponent == "Bia"
    assert record.moves == 2
    player.seconds(3.2)
    application.scene.rematch()
    player.frames(1)
    player.settle()
    player.play_all(SCHOLARS_MATE)
    assert latest().color == "Brancas" and latest().outcome == "vitoria"
    assert len(HistoryStore("Ana").records()) == 3
    assert second is not application.scene


@pytest.mark.ct("CT-122")
@pytest.mark.parametrize("ending, reason, outcome", [
    ("tempo", EndReason.TIMEOUT, "derrota"),
    ("desistir", EndReason.RESIGNATION, "derrota"),
    ("empate", EndReason.AGREEMENT, "empate"),
])
def test_cada_fim_em_dois_jogadores_grava_o_motivo_certo(ending, reason, outcome):
    application = account_app()
    scene, player = open_game(application, mode=GameMode.MATCH, names=("Ana", "Bia"), time_control=TimeControl.BLITZ_5)
    if ending == "tempo":
        fast_forward_clock(scene, Color.WHITE, 0.01)
        player.frames(2)
    elif ending == "desistir":
        scene._confirm_resign()
        player.frames(1)
        player.click_widget(scene.modals[-1].buttons[0])
    else:
        scene.open_pause()
        player.frames(1)
        draw = next(button for button in scene.modals[-1].buttons if button.label == "Propor empate")
        player.click_widget(draw)
        player.seconds(0.3)
        player.click_widget(scene.modals[-1].buttons[0])
    record = latest()
    assert record.reason == reason.label
    assert record.outcome == outcome


@pytest.mark.ct("CT-122")
def test_contra_a_cpu_grava_nivel_e_cor_depois_de_desistir(monkeypatch):
    application = account_app()
    scene, player = open_game(application, mode=GameMode.TRAINING, opponent_kind="cpu", difficulty=Difficulty.HARD,
                              human_color=Color.BLACK, names=("Ana", "Bia"))
    scene._stop_cpu()
    scene._confirm_resign()
    player.frames(1)
    player.click_widget(scene.modals[-1].buttons[0])
    record = latest()
    assert (record.outcome, record.color, record.opponent, record.difficulty) == ("derrota", "Pretas", "CPU (Hard)", "Hard")
    assert record.opponent_kind == "cpu"


@pytest.mark.ct("CT-122")
def test_em_rede_os_dois_gravam_visoes_opostas_mesmo_depois_da_revanche(host_app, guest_app):
    host_app.account = "Ana"
    guest_app.account = "Bia"
    from xadrez.ui.match import MatchOptions as _  # noqa: F401
    host_app.scene.next_scene = host_app.menu_scene()
    guest_app.scene.next_scene = guest_app.menu_scene()
    host_app.step(0.0)
    guest_app.step(0.0)
    table = connected_table(host_app, guest_app)
    table.play_all(SCHOLARS_MATE)
    table.run_until_both_over()
    first_host, first_guest = latest("Ana"), latest("Bia")
    assert (first_host.outcome, first_host.color, first_host.opponent) == ("vitoria", "Brancas", "Bia")
    assert (first_guest.outcome, first_guest.color, first_guest.opponent) == ("derrota", "Pretas", "Ana")
    assert first_host.pgn.split("\n\n")[1] == first_guest.pgn.split("\n\n")[1]
    assert first_host.final_fen == first_guest.final_fen
    table.host.rematch()
    drive(table.apps, lambda: table.guest.link.peer_wants_rematch)
    table.guest.rematch()
    drive(table.apps, lambda: isinstance(table.host, GameScene) and isinstance(table.guest, GameScene))
    table.settle()
    guest = table.guest
    guest._resign()
    drive(table.apps, lambda: table.host.engine.result is not None and guest.engine.result is not None)
    second_host, second_guest = latest("Ana"), latest("Bia")
    assert (second_host.outcome, second_host.color) == ("vitoria", "Pretas")
    assert (second_guest.outcome, second_guest.color) == ("derrota", "Brancas")


@pytest.mark.ct("CT-122")
def test_abandono_em_rede_grava_para_os_dois(host_app, guest_app):
    host_app.account = "Ana"
    guest_app.account = "Bia"
    host_app.scene.next_scene = host_app.menu_scene()
    guest_app.scene.next_scene = guest_app.menu_scene()
    host_app.step(0.0)
    guest_app.step(0.0)
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    guest = table.guest
    table.host._leave_room()
    drive([guest_app], lambda: guest.engine.result is not None)
    assert latest("Ana").outcome == "derrota" and latest("Bia").outcome == "vitoria"
    assert latest("Ana").reason == ABANDONED_REASON, "quem saiu não lê que o adversário desconectou"
    assert latest("Bia").reason == EndReason.ABANDONMENT.label


@pytest.mark.ct("CT-122")
def test_fechar_a_janela_em_rede_grava_a_derrota_de_quem_saiu(host_app, guest_app):
    host_app.account = "Ana"
    guest_app.account = "Bia"
    host_app.scene.next_scene = host_app.menu_scene()
    guest_app.scene.next_scene = guest_app.menu_scene()
    host_app.step(0.0)
    guest_app.step(0.0)
    table = connected_table(host_app, guest_app)
    table.play("e2e4")
    guest = table.guest
    # Mesmo caminho de `App.run`: QUIT e `scene.shutdown()`.
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    host_app.step(FRAME)
    host_app.scene.shutdown()
    drive([guest_app], lambda: guest.engine.result is not None)
    assert latest("Bia").outcome == "vitoria"
    assert HistoryStore("Ana").records(), "quem abandona pela janela não fica sem derrota"


# Contas separadas, convidado, 51ª partida e lista ----------------------------------------------------


@pytest.mark.ct("CT-123")
def test_contas_tem_historicos_separados_mesmo_com_nomes_parecidos():
    for name in ("Ana", "Ana2", "Bia"):
        application = account_app(name)
        open_game(application, mode=GameMode.TRAINING, names=(name, "X"))[1].play_all(FOOLS_MATE)
    assert len(HistoryStore("Ana").records()) == 1
    assert len(HistoryStore("ANA").records()) == 1, "mesma conta, outra grafia"
    assert len(HistoryStore("Ana2").records()) == 1
    assert len(HistoryStore("Bia").records()) == 1
    assert HistoryStore("Ana").records()[0].opponent == "X"


@pytest.mark.ct("CT-123")
def test_convidado_nao_toca_a_pasta_de_dados(isolated_data_dir):
    application = make_app()
    scene, player = open_game(application, mode=GameMode.TRAINING)
    player.play_all(FOOLS_MATE)
    player.seconds(3.2)
    assert isinstance(application.scene, GameOverScene)
    assert list(isolated_data_dir.iterdir()) == []


@pytest.mark.ct("CT-123")
def test_sair_da_conta_para_de_gravar_e_nao_mostra_o_historico_de_quem_saiu():
    application, player = login_app()
    create_by_mouse(player, "Ana", PASSWORD)
    write_history("Ana", [valid_entry()])
    menu = application.scene
    player.click_widget(menu.account_button)
    assert application.account is None
    player.click_widget(application.scene.guest_button)
    guest_menu = application.scene
    open_history_tab(player)
    assert guest_menu.history.list.records == []
    assert guest_menu.history.has_account is False
    guest_menu.history.reload()
    player.frames(1)
    guest_game, game_player = open_game(application, mode=GameMode.TRAINING)
    game_player.play_all(FOOLS_MATE)
    assert len(HistoryStore("Ana").records()) == 1, "partida de convidado não entra na conta de quem saiu"


@pytest.mark.ct("CT-123")
def test_partida_51_empurra_a_mais_antiga_e_a_lista_rola_ate_o_fim():
    entries = [valid_entry(opponent=f"Rival {index:02d}", played_at=f"2026-01-{(index % 28) + 1:02d}T10:00:00") for index in range(50)]
    write_history("Ana", entries)
    application = account_app()
    scene, player = open_game(application, mode=GameMode.TRAINING, names=("Ana", "Nova"))
    player.play_all(FOOLS_MATE)
    records = HistoryStore("Ana").records()
    assert len(records) == 50
    assert records[0].opponent == "Nova"
    assert records[-1].opponent == "Rival 48", "a mais antiga saiu"
    application.scene.next_scene = application.menu_scene()
    player.frames(1)
    menu = open_history_tab(player)
    box = menu.history.list
    assert len(box.records) == 50
    assert menu.history.stats.played == 50
    # Rola pela roda até passar do fim.
    post_mouse_move(box.rect.center)
    for _ in range(200):
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False))
    player.frames(1)
    last_row = box.row_rect(49)
    assert last_row.bottom <= box.rect.bottom + 1, "a última partida precisa aparecer"
    post_click((last_row.centerx, last_row.centery))
    player.frames(1)
    assert menu.history.opened is box.records[49]
    player.press(pygame.K_ESCAPE)
    # Pelo teclado, do fim ao começo, com Page Up.
    for _ in range(20):
        post_key(pygame.K_PAGEUP)
    player.frames(1)
    assert box.index == 0 and box.scroll == 0


@pytest.mark.ct("CT-123")
def test_clique_fora_das_linhas_e_lista_vazia_nao_abrem_nada():
    application = account_app()
    application.scene.next_scene = application.menu_scene()
    player = Autoplayer(application)
    player.frames(1)
    menu = open_history_tab(player)
    post_click(menu.history.list.rect.center)
    player.press(pygame.K_RETURN)
    player.press(pygame.K_DOWN)
    player.press(pygame.K_PAGEDOWN)
    player.press(pygame.K_c)
    assert menu.history.opened is None


@pytest.mark.ct("CT-123")
def test_esc_esc_enter_no_historico_nao_sai_da_conta():
    application = make_app(require_login=True)
    application.account = "Ana"
    write_history("Ana", [valid_entry()])
    application.scene.next_scene = application.menu_scene()
    player = Autoplayer(application)
    player.frames(1)
    menu = open_history_tab(player)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(1)
    assert menu.history.opened is not None
    player.press(pygame.K_ESCAPE)
    assert menu.history.opened is None
    player.press(pygame.K_ESCAPE)
    assert menu.tab_bar.value == "jogar"
    assert menu.focus.focused is not menu.account_button, "o foco caiu em 'Sair da conta'"
    player.press(pygame.K_RETURN)
    assert application.account == "Ana"
    assert isinstance(application.scene, (MenuScene, GameScene))


@pytest.mark.ct("CT-120")
def test_arquivo_somente_leitura_vira_aviso_e_nao_deixa_temporario():
    AccountStore().create("Ana", PASSWORD)
    path = accounts_path()
    os.chmod(path, stat.S_IREAD)
    try:
        application, player = login_app()
        create_by_mouse(player, "Bia", PASSWORD)
        assert isinstance(application.scene, LoginScene)
        assert application.scene.error
        assert AccountStore().authenticate("Ana", PASSWORD), "a conta que já existia continua valendo"
        leftovers = [item.name for item in path.parent.iterdir() if item.name.endswith(".tmp")]
        assert leftovers == []
    finally:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)


@pytest.mark.ct("CT-121")
def test_historico_somente_leitura_vira_aviso_na_tela_de_fim():
    write_history("Ana", [valid_entry()])
    path = history_path("Ana")
    os.chmod(path, stat.S_IREAD)
    try:
        application = account_app()
        scene, player = open_game(application, mode=GameMode.TRAINING, names=("Ana", "Bia"))
        player.play_all(FOOLS_MATE)
        player.seconds(3.2)
        assert isinstance(application.scene, GameOverScene)
        assert "histórico" in application.scene.notices.text
        assert len(HistoryStore("Ana").records()) == 1, "a partida antiga continua lá"
    finally:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)


# Histórico lido do disco é entrada não confiável ------------------------------------------------------------


@pytest.mark.ct("CT-121")
@pytest.mark.parametrize("field, value, limit", [
    ("opponent", "W" * 20000, 64),
    ("played_at", "x" * 20000, 40),
    ("reason", "y" * 20000, 64),
    ("final_fen", "z" * 20000, 128),
    ("pgn", "1. e4 " * 50000, 100_000),
])
def test_texto_gigante_e_cortado_ao_carregar(field, value, limit):
    write_history("Ana", [valid_entry(**{field: value})])
    record = HistoryStore("Ana").records()[0]
    assert len(getattr(record, field)) == limit


@pytest.mark.ct("CT-121")
@pytest.mark.parametrize("seconds", [10**400, 10**30, 1e308])
def test_duracao_gigante_fica_no_limite_ao_carregar(seconds):
    write_history("Ana", [valid_entry(seconds=seconds)])
    assert HistoryStore("Ana").records()[0].seconds == 1_000_000_000


@pytest.mark.ct("CT-121")
def test_lances_gigantes_ficam_no_limite_ao_carregar():
    write_history("Ana", [valid_entry(moves=10**400)])
    assert HistoryStore("Ana").records()[0].moves == 1_000_000


@pytest.mark.ct("CT-121")
@pytest.mark.parametrize("seconds", ["Infinity", "-Infinity", "NaN", "-1"])
def test_limite_nao_faz_aceitar_numero_invalido(seconds):
    path = history_path("Ana")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"version": 1, "records": [valid_entry(seconds=123456)]})
    path.write_text(text.replace("123456", seconds), encoding="utf-8")
    assert HistoryStore("Ana").records() == []


@pytest.mark.ct("CT-121")
def test_partida_nova_continua_entrando_com_registro_gigante_no_arquivo():
    write_history("Ana", [valid_entry(opponent="W" * 20000, seconds=10**400)])
    application = make_app()
    application.account = "Ana"
    scene, player = open_game(application, mode=GameMode.TRAINING)
    player.play_all(FOOLS_MATE)
    records = HistoryStore("Ana").records()
    assert len(records) == 2
    assert len(records[1].opponent) == 64


@pytest.mark.ct("CT-118")
def test_voltar_de_criar_conta_devolve_o_enter_que_envia_na_senha():
    AccountStore().create("Ana", PASSWORD)
    application, player = login_app()
    scene = application.scene
    player.click_segment(scene.mode_selector, 1)
    player.click_segment(scene.mode_selector, 0)
    player.click_widget(scene.username_input)
    player.type_text("Ana")
    player.press(pygame.K_RETURN)
    player.type_text(PASSWORD)
    player.press(pygame.K_RETURN)
    assert isinstance(application.scene, MenuScene)


@pytest.mark.ct("CT-118")
def test_senhas_diferentes_avisam_antes_de_pedir_de_novo():
    application, player = login_app()
    scene = application.scene
    player.click_segment(scene.mode_selector, 1)
    player.click_widget(scene.username_input)
    player.type_text("Ana")
    player.press(pygame.K_RETURN)
    player.type_text(PASSWORD)
    player.press(pygame.K_RETURN)
    player.type_text("outra-senha")
    player.press(pygame.K_RETURN)
    assert scene.error == PASSWORD_MISMATCH_MESSAGE, "nunca apaga a senha em silêncio"
    assert scene.password_input.text == "" and scene.focus.focused is scene.password_input
