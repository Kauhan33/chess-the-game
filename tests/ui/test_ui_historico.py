"""Histórico da conta: partida encerrada entra, do ponto de vista de quem está logado, e a aba mostra (RF21, CT-94)."""
from dataclasses import replace

import pygame
import pytest
from ui_helpers import SCHOLARS_MATE, finish_with_mate, resign_by_buttons, start_cpu_game, start_game

from xadrez.core import Color, Difficulty, GameEngine, TimeControl
from xadrez.data import DataError, HistoryStore, MatchRecord
from xadrez.ui import App, GameMode, GameOverScene, MatchOptions, MenuScene
from xadrez.ui import clipboard
from xadrez.ui.autoplay import Autoplayer, post_click, post_mouse_move
from xadrez.ui.history_panel import EMPTY_LINES, NO_ACCOUNT_LINES, _movetext, format_played_at, outcome_word
from xadrez.ui.match_record import SAVE_FAILED_MESSAGE, build_record

ACCOUNT = "Jogador 1"
WHEEL_DOWN = -1


def record(opponent="Jogador 2", outcome="vitoria", moves=4, played_at="2026-11-05T19:42:00", pgn=None, seconds=214.0):
    return MatchRecord(
        played_at=played_at, opponent=opponent, opponent_kind="local", difficulty=None, color="Brancas", outcome=outcome,
        reason="Xeque-mate", moves=moves, seconds=seconds, time_control="Blitz 3+2", mode="Partida",
        pgn=pgn or '[White "A"]\n[Black "B"]\n\n1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# 1-0\n',
        final_fen="r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4",
    )


@pytest.fixture
def logged_app(app):
    app.account = ACCOUNT
    return app


def store():
    return HistoryStore(ACCOUNT)


def open_tab(app):
    """Abre o menu de quem entrou, já na aba do histórico, com as partidas que estão no disco agora."""
    app.scene.next_scene = app.menu_scene()
    player = Autoplayer(app)
    player.frames(1)
    menu = app.scene
    player.click_segment(menu.tab_bar, 1)
    return menu, player


# Gravar -------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-94")
def test_partida_encerrada_entra_no_historico_da_conta(logged_app):
    _, player = start_game(logged_app, time_control=TimeControl.BLITZ_3_2)
    finish_with_mate(player)
    records = store().records()
    assert len(records) == 1
    saved = records[0]
    assert saved.opponent == "Jogador 2"
    assert saved.opponent_kind == "local"
    assert saved.difficulty is None
    assert saved.color == "Brancas"
    assert saved.outcome == "vitoria"
    assert saved.reason == "Xeque-mate"
    assert saved.moves == 4
    assert saved.time_control == "Blitz 3+2"
    assert saved.mode == "Treinamento"
    assert "Qxf7#" in saved.pgn
    assert '[White "Jogador 1"]' in saved.pgn
    assert saved.final_fen == logged_app.scene.engine.final_fen
    assert saved.seconds > 0.0


@pytest.mark.ct("CT-94")
def test_revanche_troca_a_cor_de_quem_esta_logado(logged_app):
    _, player = start_game(logged_app)
    finish_with_mate(player)
    player.click_widget(logged_app.scene.rematch_button)
    player.settle()
    finish_with_mate(player)
    newest, oldest = store().records()
    assert oldest.color == "Brancas" and oldest.outcome == "vitoria"
    assert newest.color == "Pretas" and newest.outcome == "derrota", "Jogador 2 deu mate de Brancas"
    assert newest.opponent == "Jogador 2"


@pytest.mark.ct("CT-94")
def test_quem_esta_logado_pode_ser_o_das_pretas(app):
    app.account = "Titular"
    menu_player = Autoplayer(app)
    app.scene.next_scene = app.menu_scene()
    menu_player.frames(1)
    menu = app.scene
    assert menu.white_input.text == "Titular", "o nome de quem entrou já vem no primeiro campo"
    menu.white_input.text = "Outra Pessoa"
    menu.black_input.text = "titular"
    menu_player.click_widget(menu.start_button)
    scene = app.scene
    assert scene.local_color is Color.BLACK, "o nome da conta não diferencia maiúsculas"
    menu_player.settle()
    finish_with_mate(menu_player)
    saved = HistoryStore("Titular").records()[0]
    assert saved.color == "Pretas" and saved.outcome == "derrota"


@pytest.mark.ct("CT-94")
def test_falha_ao_gravar_tambem_aparece_na_tela_de_fim(logged_app, monkeypatch):
    def refuse(self, entry):
        raise DataError("disco cheio")

    monkeypatch.setattr(HistoryStore, "add", refuse)
    scene, player = start_game(logged_app)
    resign_by_buttons(player, scene)
    assert scene.notices.text == SAVE_FAILED_MESSAGE
    player.seconds(1.2)
    assert logged_app.scene.notices.text == SAVE_FAILED_MESSAGE


@pytest.mark.ct("CT-94")
def test_partida_contra_a_cpu_guarda_o_nivel(logged_app):
    scene, player = start_cpu_game(logged_app, Difficulty.HARD, time_control=TimeControl.UNLIMITED, mode=GameMode.MATCH,
                                   names=(ACCOUNT, "Jogador 2"))
    resign_by_buttons(player, scene)
    saved = store().records()[0]
    assert saved.opponent == "CPU (Hard)"
    assert saved.opponent_kind == "cpu"
    assert saved.difficulty == "Hard"
    assert saved.outcome == "derrota"
    assert saved.reason == "Desistência"
    assert saved.mode == "Partida"


@pytest.mark.ct("CT-94")
def test_empate_e_gravado_como_empate(logged_app):
    scene, player = start_game(logged_app)
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[2])
    player.click_widget(scene.modals[-1].buttons[0])
    saved = store().records()[0]
    assert saved.outcome == "empate"
    assert saved.reason == "Empate por acordo"


@pytest.mark.ct("CT-94")
def test_mate_entra_uma_vez_so(logged_app):
    _, player = start_game(logged_app)
    finish_with_mate(player)
    player.seconds(1.0)
    assert len(store().records()) == 1


@pytest.mark.ct("CT-94")
def test_mate_ja_fica_gravado_com_a_peca_no_ar(logged_app):
    scene, player = start_game(logged_app)
    for uci in SCHOLARS_MATE.split()[:-1]:
        player.play(uci)
    player.click_square((7, 4))
    player.click_square((5, 6))
    assert scene.view.is_flying
    assert len(store().records()) == 1, "fechar o jogo agora não perde a partida"


@pytest.mark.ct("CT-94")
def test_partida_abandonada_sem_resultado_nao_entra(logged_app):
    scene, player = start_game(logged_app)
    player.play("e2e4")
    player.press(pygame.K_p)
    player.click_widget(scene.modals[-1].buttons[-1])
    player.click_widget(scene.modals[-1].buttons[0])
    assert isinstance(logged_app.scene, MenuScene)
    assert store().records() == []


@pytest.mark.ct("CT-94")
def test_reiniciar_nao_entra_no_historico(logged_app):
    scene, player = start_game(logged_app)
    player.play("e2e4")
    player.press(pygame.K_r)
    player.click_widget(scene.modals[-1].buttons[0])
    assert store().records() == []


@pytest.mark.ct("CT-94")
def test_convidado_nao_grava_nada(app, tmp_path):
    _, player = start_game(app)
    finish_with_mate(player)
    assert isinstance(app.scene, GameOverScene)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.ct("CT-94")
def test_falha_ao_gravar_vira_aviso_e_nao_derruba(logged_app, monkeypatch):
    def refuse(self, entry):
        raise DataError("disco cheio")

    monkeypatch.setattr(HistoryStore, "add", refuse)
    scene, player = start_game(logged_app)
    player.play_all(SCHOLARS_MATE)
    assert scene.notices.text == SAVE_FAILED_MESSAGE
    player.seconds(3.0)
    assert isinstance(logged_app.scene, GameOverScene)


def test_registro_do_ponto_de_vista_de_cada_cor():
    engine = GameEngine("A", "B", TimeControl.BLITZ_5)
    engine.resign(Color.WHITE)
    options = MatchOptions("A", "B", TimeControl.BLITZ_5)
    assert build_record(engine, options, engine.players[Color.WHITE]).outcome == "derrota"
    assert build_record(engine, options, engine.players[Color.BLACK]).outcome == "vitoria"


# Mostrar ------------------------------------------------------------------------------------------


@pytest.mark.ct("CT-94")
def test_aba_mostra_estatisticas_e_lista(logged_app):
    for outcome in ("vitoria", "vitoria", "derrota", "empate"):
        store().add(record(outcome=outcome))
    menu, player = open_tab(logged_app)
    history = menu.history
    assert (history.stats.played, history.stats.wins, history.stats.losses, history.stats.draws) == (4, 2, 1, 1)
    assert len(history.list.records) == 4
    assert history.list in menu.focus.widgets
    player.frames(2)


@pytest.mark.ct("CT-94")
def test_partida_do_jogo_aparece_na_aba(logged_app):
    _, player = start_game(logged_app)
    finish_with_mate(player)
    player.click_widget(logged_app.scene.menu_button)
    menu = logged_app.scene
    player.seconds(0.3)
    player.click_segment(menu.tab_bar, 1)
    assert menu.history.list.records[0].opponent == "Jogador 2"


@pytest.mark.ct("CT-94")
def test_clique_abre_a_partida_e_copiar_pgn_funciona(logged_app, monkeypatch):
    copied = []
    monkeypatch.setattr(clipboard, "copy_text", lambda text: copied.append(text) or True)
    store().add(record(opponent="Primeira"))
    store().add(record(opponent="Segunda"))
    menu, player = open_tab(logged_app)
    history = menu.history
    post_click(history.list.row_rect(1).center)
    player.frames(2)
    assert history.opened.opponent == "Primeira"
    assert menu.focus.focused is history.copy_button
    player.click_widget(history.copy_button)
    assert copied == [history.opened.pgn]
    assert history.message == "PGN copiado."
    player.click_widget(history.close_button)
    assert history.opened is None
    assert history.copy_button not in menu.focus.widgets


@pytest.mark.ct("CT-94")
def test_copiar_que_falha_avisa_na_folha(logged_app, monkeypatch):
    monkeypatch.setattr(clipboard, "copy_text", lambda text: False)
    store().add(record())
    menu, player = open_tab(logged_app)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(1)
    player.press(pygame.K_c)
    assert menu.history.message == clipboard.COPY_FAILED_MESSAGE
    player.frames(2)


@pytest.mark.ct("CT-94")
def test_teclado_navega_abre_e_fecha(logged_app):
    for index in range(12):
        store().add(record(opponent=f"Rival {index}"))
    menu, player = open_tab(logged_app)
    history = menu.history
    menu.focus.focus(history.list)
    for _ in range(11):
        player.press(pygame.K_DOWN)
    assert history.list.index == 11
    assert history.list.scroll > 0, "a lista rola para mostrar a seleção"
    assert history.list.row_rect(11).bottom <= history.list.rect.bottom
    assert menu.focus.focused is history.list, "as setas ficam na lista"
    player.press(pygame.K_PAGEUP)
    assert history.list.index == 7
    player.press(pygame.K_RETURN)
    assert history.opened.opponent == history.list.records[7].opponent
    player.press(pygame.K_ESCAPE)
    assert history.opened is None
    assert menu.focus.focused is history.list


@pytest.mark.ct("CT-94")
def test_esc_sem_folha_aberta_volta_para_a_aba_jogar(logged_app):
    store().add(record())
    menu, player = open_tab(logged_app)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(1)
    player.press(pygame.K_ESCAPE)
    assert menu.history.opened is None
    assert menu.tab_bar.value == "historico", "o primeiro Esc só fecha a folha"
    player.press(pygame.K_ESCAPE)
    assert menu.tab_bar.value == "jogar"
    assert menu.start_button in menu.focus.widgets


@pytest.mark.ct("CT-94")
def test_roda_do_mouse_rola_a_lista_e_para_nas_pontas(logged_app):
    for index in range(20):
        store().add(record(opponent=f"Rival {index}"))
    menu, player = open_tab(logged_app)
    listing = menu.history.list
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=WHEEL_DOWN, flipped=False))
    player.frames(1)
    assert listing.scroll > 0
    for _ in range(40):
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=WHEEL_DOWN, flipped=False))
    player.frames(1)
    assert listing.row_rect(19).bottom == listing.rect.bottom
    for _ in range(40):
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1, flipped=False))
    player.frames(1)
    assert listing.scroll == 0


@pytest.mark.ct("CT-94")
def test_roda_sobre_a_folha_rola_os_lances(logged_app):
    moves = " ".join(f"{number}. e4 e5" for number in range(1, 200))
    store().add(record(pgn=f'[White "A"]\n\n{moves}\n'))
    menu, player = open_tab(logged_app)
    history = menu.history
    post_click(history.list.row_rect(0).center)
    player.frames(2)
    post_mouse_move(history._sheet.center)
    player.frames(1)
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=WHEEL_DOWN, flipped=False))
    player.frames(2)
    assert history._moves_scroll == 1
    assert history.list.scroll == 0, "a lista não rola junto"
    for _ in range(500):
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=WHEEL_DOWN, flipped=False))
    player.frames(2)
    scrolled = history._moves_scroll
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1, flipped=False))
    player.frames(2)
    assert history._moves_scroll == scrolled - 1, "o limite é o fim do texto"


@pytest.mark.ct("CT-94")
def test_lista_vazia_explica_o_que_fazer(logged_app):
    menu, player = open_tab(logged_app)
    assert menu.history.list.records == []
    assert menu.history.stats.played == 0
    assert EMPTY_LINES[0]
    menu.focus.focus(menu.history.list)
    player.press(pygame.K_DOWN)
    player.press(pygame.K_RETURN)
    assert menu.history.opened is None


@pytest.mark.ct("CT-94")
def test_arquivo_corrompido_nao_derruba_a_aba(logged_app):
    store().add(record())
    store()._path.write_text("isto não é json", encoding="utf-8")
    menu, player = open_tab(logged_app)
    assert menu.history.list.records == []
    player.frames(2)


@pytest.mark.ct("CT-94")
def test_convidado_ve_o_convite_na_aba(app, player):
    menu = app.scene
    player.click_segment(menu.tab_bar, 1)
    assert not menu.history.has_account
    assert NO_ACCOUNT_LINES[0]
    assert menu.history.invite_button is None, "sem login no jogo, não há para onde convidar"
    player.frames(2)


@pytest.mark.ct("CT-94")
def test_convidado_do_jogo_de_verdade_tem_botao_de_criar_conta():
    application = App(seed=11, require_login=True)
    pygame.event.clear()
    player = Autoplayer(application)
    player.click_widget(application.scene.guest_button)
    menu = application.scene
    player.click_segment(menu.tab_bar, 1)
    assert menu.history.invite_button in menu.focus.widgets
    player.seconds(0.3)
    player.click_widget(menu.history.invite_button)
    assert application.scene.is_creating
    application.scene.shutdown()


@pytest.mark.ct("CT-94")
def test_voltar_para_a_aba_jogar_mostra_o_formulario(logged_app):
    menu, player = open_tab(logged_app)
    assert menu.start_button not in menu.focus.widgets
    player.click_segment(menu.tab_bar, 0)
    assert menu.start_button in menu.focus.widgets


@pytest.mark.parametrize("size", [(1, 1), (200, 200), (640, 360), (800, 600), (1024, 640), (1920, 1080)])
def test_aba_e_folha_nao_quebram_em_janela_pequena(logged_app, size):
    for index in range(8):
        store().add(record(opponent="W" * 16, outcome=("vitoria", "derrota", "empate")[index % 3]))
    menu, player = open_tab(logged_app)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(1)
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1]))
    player.frames(2)
    assert menu.history.opened is not None


@pytest.mark.parametrize("text, expected", [
    ("2026-11-05T19:42:00", "05/11/2026 19:42"),
    ("isto não é data de jeito nenhum", "isto não é data "),
])
def test_data_do_arquivo_nunca_derruba(text, expected):
    assert format_played_at(text) == expected


@pytest.mark.ct("CT-94")
def test_arquivo_editado_a_mao_com_caractere_de_controle_nao_derruba(logged_app):
    tampered = "Nul\x00l \ud83d\x07fim"
    store().add(replace(record(opponent="Normal"), opponent=tampered, reason=tampered, final_fen=tampered, played_at=tampered))
    menu, player = open_tab(logged_app)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(2)
    assert menu.history.opened.opponent == "Null fim"


@pytest.mark.ct("CT-94")
def test_numeros_absurdos_no_arquivo_nao_derrubam(logged_app):
    store().add(replace(record(), moves=10**30, seconds=1e300))
    menu, player = open_tab(logged_app)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(2)
    assert menu.history.opened is not None


def test_palavra_do_resultado():
    assert [outcome_word(word) for word in ("vitoria", "derrota", "empate")] == ["Vitória", "Derrota", "Empate"]


def test_lances_do_pgn_sem_os_cabecalhos():
    assert _movetext('[White "A"]\n[Black "B"]\n\n1. e4 e5\n2. Nf3 1-0\n') == "1. e4 e5 2. Nf3 1-0"


def test_registro_com_um_lance_e_nome_comprido_desenha(logged_app):
    store().add(replace(record(opponent="W" * 16), moves=1))
    menu, player = open_tab(logged_app)
    post_click(menu.history.list.row_rect(0).center)
    player.frames(2)
    assert menu.history.opened.moves == 1
