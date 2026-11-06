"""Menu: quem entrou, as abas Jogar e Meu histórico e o formulário que muda com o adversário."""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pygame

from xadrez.core import Color, Difficulty
from xadrez.data.accounts import username_key
from xadrez.ui import theme as tokens
from xadrez.ui.arena_scene import ArenaScene, draw_notes
from xadrez.ui.history_panel import HistoryPanel
from xadrez.ui.lobby_scene import ROLE_GUEST, ROLE_HOST
from xadrez.ui.match import (
    DEFAULT_BLACK_NAME,
    DEFAULT_WHITE_NAME,
    OPPONENT_CPU,
    OPPONENT_LOCAL,
    OPPONENT_NET,
    TIME_CONTROLS,
    GameMode,
    MatchOptions,
)
from xadrez.ui.overlays import HelpOverlay, Overlay
from xadrez.ui.widgets import STYLE_PRIMARY, Button, FocusGroup, SegmentedControl, Selector, TabBar, TextInput

if TYPE_CHECKING:
    from xadrez.ui.app import App

TAB_PLAY = "jogar"
TAB_HISTORY = "historico"
TIME_OPTIONS = TIME_CONTROLS
CAMERA_OPTIONS = (
    ("Gira a cada turno", True),
    ("Fixa no lado das Brancas", False),
)
OPPONENT_OPTIONS = (("2 jogadores", OPPONENT_LOCAL), ("Contra a CPU", OPPONENT_CPU), ("Rede local", OPPONENT_NET))
MODE_OPTIONS = tuple((mode.label, mode) for mode in GameMode)
DIFFICULTY_OPTIONS = tuple((level.label, level) for level in Difficulty)
COLOR_OPTIONS = (("Brancas", Color.WHITE), ("Pretas", Color.BLACK), ("Sorteio", None))
NETWORK_NOTE = "Quem cria a sala escolhe o modo e o tempo dos dois, e joga de Brancas na primeira partida."
NETWORK_OFF_MESSAGE = "A rede fica desligada neste modo de teste. Abra o jogo pelo main.py."
_TAB_OPTIONS = (("Jogar", TAB_PLAY), ("Meu histórico", TAB_HISTORY))
_TITLE_TOP = 12
_ACCOUNT_TOP = 62
_ACCOUNT_BUTTON_WIDTH = 118
_ACCOUNT_BUTTON_HEIGHT = 26
_TABS_TOP = 92
_TABS_HEIGHT = 36
_FIELD_HEIGHT = 40
_BOTTOM_MARGIN = 14
_QUIT_BUTTON_WIDTH = 92
_ROW_HEIGHT = 34


class MenuScene(ArenaScene):
    def __init__(self, app: App, defaults: MatchOptions | None = None):
        super().__init__(app)
        options = defaults if defaults is not None else MatchOptions()
        self.white_input = self._name_input("Brancas", DEFAULT_WHITE_NAME, self._first_name(options))
        self.black_input = self._name_input("Pretas", DEFAULT_BLACK_NAME, options.black_name)
        self.opponent_selector = SegmentedControl("Adversário", OPPONENT_OPTIONS, _index_of(OPPONENT_OPTIONS, options.opponent_kind),
                                                  on_change=self._rebuild_form)
        self.mode_selector = SegmentedControl("Modo", MODE_OPTIONS, _index_of(MODE_OPTIONS, options.mode), on_change=self._layout_form)
        self.difficulty_selector = SegmentedControl("Nível", DIFFICULTY_OPTIONS, _index_of(DIFFICULTY_OPTIONS, options.difficulty),
                                                    on_change=self._layout_form)
        self.color_selector = SegmentedControl("Sua cor", COLOR_OPTIONS, _index_of(COLOR_OPTIONS, options.human_color))
        self.time_selector = Selector("Tempo por jogador", TIME_OPTIONS, _index_of(TIME_OPTIONS, options.time_control))
        self.camera_selector = Selector("Câmera", CAMERA_OPTIONS, _index_of(CAMERA_OPTIONS, options.auto_rotate))
        self.start_button = Button("Iniciar partida", self.start_match, STYLE_PRIMARY, font_size=22)
        self.create_room_button = Button("Criar sala", self.create_room, STYLE_PRIMARY, font_size=20)
        self.join_room_button = Button("Entrar com código", self.join_room, font_size=18)
        self.help_button = Button("Ver todos os controles", self.open_help, hint="F1")
        self.quit_button = Button("Sair", self.quit_game)
        self.account_button = self._create_account_button()
        self.tab_bar = TabBar(_TAB_OPTIONS, on_change=self._apply_tab)
        self.history = HistoryPanel(app.theme, app.history_store(), self._invite_callback())
        self.focus = FocusGroup([self.white_input])
        self.modal: Overlay | None = None
        self.notice = ""
        self._notes: list = []
        self._mouse_pos: tuple[int, int] | None = None
        self._help_just_closed = False
        self._rng = random.Random(app.seed)
        pygame.key.start_text_input()
        self._rebuild_form()
        self.resize(app.size)

    def _first_name(self, options: MatchOptions) -> str:
        """Em 2 jogadores, quem está logado já vem no primeiro campo."""
        is_default = options.white_name == DEFAULT_WHITE_NAME
        return self.app.account if self.app.account and is_default else options.white_name

    def _name_input(self, label: str, placeholder: str, name: str) -> TextInput:
        field = TextInput(label, placeholder, value="" if name == placeholder else name)
        theme = self.app.theme
        field.set_character_filter(lambda char: theme.has_glyph(char, tokens.ROLE_DISPLAY, theme.px(19)))
        return field

    def _create_account_button(self) -> Button | None:
        if self.app.account is not None:
            return Button("Sair da conta", self.sign_out, font_size=14)
        return Button("Entrar", self.sign_in, font_size=14) if self.app.require_login else None

    def _invite_callback(self):
        return self.create_account if self.app.require_login else None

    # O que o menu decide --------------------------------------------------------------------------

    @property
    def opponent_kind(self) -> str:
        return self.opponent_selector.value

    def options(self) -> MatchOptions:
        # Contra a CPU e em rede não há campo de nome para quem está logado: quem joga é a conta.
        first_name = self.white_input.value if self.opponent_kind == OPPONENT_LOCAL else self.app.account or self.white_input.value
        return MatchOptions(first_name, self.black_input.value,
                            self.time_selector.value, self.camera_selector.value,
                            self.mode_selector.value, self.opponent_kind,
                            self.difficulty_selector.value, self.color_selector.value)

    def start_match(self) -> None:
        if self.next_scene is not None:
            return
        options = self.options()
        if options.opponent_kind == OPPONENT_NET:
            self.create_room()
            return
        color = options.human_color or self._rng.choice((Color.WHITE, Color.BLACK))
        engine = options.create_engine(human_color=color)
        self.next_scene = self.app.game_scene(engine, options, local_player=self._local_player(engine, options, color))

    def _local_player(self, engine, options: MatchOptions, color: Color):
        """Contra a CPU, a cor escolhida. Em 2 jogadores, a do campo com o nome da conta; sem conta, a primeira."""
        if options.opponent_kind == OPPONENT_CPU:
            return engine.players[color]
        account = self.app.account
        is_on_black_side = (
            account is not None
            and username_key(options.black_name) == username_key(account)
            and username_key(options.white_name) != username_key(account)
        )
        return engine.players[Color.BLACK if is_on_black_side else Color.WHITE]

    def create_room(self) -> None:
        self._open_lobby(ROLE_HOST)

    def join_room(self) -> None:
        self._open_lobby(ROLE_GUEST)

    def _open_lobby(self, role: str) -> None:
        if self.next_scene is not None:
            return
        if self.app.network is None:
            self.notice = NETWORK_OFF_MESSAGE
            return
        self.next_scene = self.app.lobby_scene(self.options(), role)

    def sign_out(self) -> None:
        self.app.account = None
        self.next_scene = self.app.login_scene()

    def sign_in(self) -> None:
        self.next_scene = self.app.login_scene()

    def create_account(self) -> None:
        self.next_scene = self.app.login_scene(start_creating=True)

    def open_help(self) -> None:
        self.modal = HelpOverlay(self.app.theme, self._close_help)
        self.modal.layout(self.app.size)

    def _close_help(self) -> None:
        self.modal = None
        self._help_just_closed = True

    def quit_game(self) -> None:
        self.app.running = False

    # Formulário -----------------------------------------------------------------------------------

    def _rebuild_form(self) -> None:
        """Mostra só o que importa para este adversário. O foco fica onde estava, se o controle continua na tela."""
        self.notice = ""
        previous = self.focus.focused
        widgets = self._visible_widgets()
        focused = previous if previous in widgets else self._first_typing_widget(widgets)
        self.focus.set_widgets(widgets, focused)
        self._layout_form()

    def _first_typing_widget(self, widgets: list):
        """Onde o teclado começa: o nome, se o formulário pede um; senão, o botão de iniciar."""
        return next((widget for widget in (self.white_input, self.start_button) if widget in widgets), widgets[0])

    def _visible_widgets(self) -> list:
        account = [self.account_button] if self.account_button is not None else []
        common_end = [self.help_button, self.quit_button]
        if self.tab_bar.value == TAB_HISTORY:
            return [*account, self.tab_bar, *self.history.widgets(), *common_end]
        return [*account, self.tab_bar, self.opponent_selector, self.mode_selector, *self._play_fields(), *common_end]

    def _play_fields(self) -> list:
        kind = self.opponent_kind
        if kind == OPPONENT_LOCAL:
            return [self.white_input, self.black_input, self.time_selector, self.camera_selector, self.start_button]
        if kind == OPPONENT_CPU:
            return [self.difficulty_selector, self.color_selector, self.time_selector, self.start_button]
        name = [] if self.app.account else [self.white_input]
        return [*name, self.time_selector, self.create_room_button, self.join_room_button]

    def _apply_tab(self) -> None:
        if self.tab_bar.value == TAB_HISTORY:
            self.history.reload()
        self._refresh_widgets_keeping_focus()
        self._layout_form()

    def _refresh_widgets_keeping_focus(self) -> None:
        """Se o controle focado saiu da tela, o foco fica nas abas: cair no primeiro seria cair em 'Sair da conta'."""
        widgets = self._visible_widgets()
        focused = self.focus.focused
        self.focus.set_widgets(widgets, focused if focused in widgets else self.tab_bar)

    # Eventos e quadro -----------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
        if self.modal is not None:
            self.modal.handle_event(event)
            return
        # H fecha a ajuda, e o SDL entrega a mesma tecla como texto logo em seguida: não é digitação.
        if event.type == pygame.TEXTINPUT and self._help_just_closed:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.open_help()
            return
        if self.tab_bar.value == TAB_HISTORY and self._handle_history_event(event):
            return
        was_open = self.history.opened
        self.focus.handle_event(event)
        if self.history.opened is not was_open:
            self._refresh_history_focus()

    def _handle_history_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEWHEEL:
            self.history.handle_wheel(event.y, self._mouse_pos)
            return True
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_ESCAPE:
            self._step_back_in_history()
            return True
        if event.key == pygame.K_c and self.history.opened is not None:
            self.history.copy_pgn()
            return True
        return False

    def _step_back_in_history(self) -> None:
        """Esc fecha a folha aberta; sem folha aberta, volta para a aba Jogar."""
        if self.history.opened is not None:
            self.history.close_record()
            self._refresh_history_focus()
        else:
            self.tab_bar.select(0)

    def _refresh_history_focus(self) -> None:
        focused = self.history.copy_button if self.history.opened is not None else self.history.list
        self.focus.set_widgets(self._visible_widgets(), focused)

    def update(self, dt: float) -> None:
        super().update(dt)
        self._help_just_closed = False
        for widget in (self.white_input, self.black_input):
            widget.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_arena(surface)
        self._draw_header(surface)
        theme = self.app.theme
        if self.tab_bar.value == TAB_HISTORY:
            self.history.draw_column(surface)
            self._draw_history_widgets(surface)
        else:
            self.focus.draw(surface, theme)
            draw_notes(surface, theme, self._notes)
            self._draw_notice(surface)
        if self.modal is not None:
            self.modal.draw(surface)

    def _draw_history_widgets(self, surface: pygame.Surface) -> None:
        """A folha aberta fica por cima de tudo: os botões dela são desenhados junto com ela, não na lista do foco."""
        sheet_buttons = (self.history.copy_button, self.history.close_button)
        for widget in self.focus.widgets:
            if widget not in sheet_buttons:
                widget.draw(surface, self.app.theme)
        self.history.draw_sheet(surface)

    def _draw_header(self, surface: pygame.Surface) -> None:
        self._draw_title(surface, "Chess - The Game", _TITLE_TOP)
        theme = self.app.theme
        account = self.app.account
        text = f"Jogando como {account}" if account else "Jogando como convidado, sem histórico"
        reserved = theme.px(_ACCOUNT_BUTTON_WIDTH + 8) if self.account_button is not None else 0
        line = theme.text_fit(text, tokens.ROLE_LABEL, theme.px(16), tokens.TEXT_MUTED, max(self._content_width() - reserved, 1))
        surface.blit(line, line.get_rect(midleft=(self._content_left(), theme.px(_ACCOUNT_TOP + _ACCOUNT_BUTTON_HEIGHT // 2))))

    def _draw_notice(self, surface: pygame.Surface) -> None:
        if not self.notice:
            return
        theme = self.app.theme
        text = theme.text_fit(self.notice, tokens.ROLE_LABEL, theme.px(15), tokens.ALERT_ON_DARK, self._content_width())
        surface.blit(text, (self._content_left(), self.help_button.rect.y - text.get_height() - theme.px(4)))

    # Layout ---------------------------------------------------------------------------------------

    def _layout_form(self) -> None:
        self._layout_header()
        if self.tab_bar.value == TAB_HISTORY:
            self._layout_history()
        else:
            self._fit_spacing(self._layout_play)
        self._layout_bottom_row()

    def _layout_header(self) -> None:
        theme = self.app.theme
        left, width = self._content_left(), self._content_width()
        self.tab_bar.rect = pygame.Rect(left, theme.px(_TABS_TOP), width, theme.px(_TABS_HEIGHT))
        if self.account_button is not None:
            button_width = min(theme.px(_ACCOUNT_BUTTON_WIDTH), width)
            self.account_button.rect = pygame.Rect(left + width - button_width, theme.px(_ACCOUNT_TOP), button_width,
                                                   theme.px(_ACCOUNT_BUTTON_HEIGHT))

    def _layout_play(self, spacing: float) -> int:
        theme = self.app.theme
        flow = self._flow(self.tab_bar.rect.bottom, spacing)
        flow.gap(6)
        flow.field(self.opponent_selector, _FIELD_HEIGHT)
        flow.field(self.mode_selector, _FIELD_HEIGHT)
        flow.note(self.mode_selector.value.description, reserve_lines=2)
        kind = self.opponent_kind
        if kind == OPPONENT_LOCAL:
            self._flow_local(flow)
        elif kind == OPPONENT_CPU:
            self._flow_cpu(flow)
        else:
            self._flow_network(flow)
        self._notes = flow.notes
        return flow.y + theme.px(_ROW_HEIGHT + _BOTTOM_MARGIN + 8)

    def _flow_local(self, flow) -> None:
        self.white_input.label = "Brancas"
        flow.pair(self.white_input, self.black_input, _FIELD_HEIGHT)
        flow.field(self.time_selector, _FIELD_HEIGHT)
        flow.field(self.camera_selector, _FIELD_HEIGHT)
        flow.gap(14)
        flow.place(self.start_button, 50)

    def _flow_cpu(self, flow) -> None:
        flow.field(self.difficulty_selector, _FIELD_HEIGHT)
        flow.note(self.difficulty_selector.value.description, reserve_lines=2)
        flow.field(self.color_selector, _FIELD_HEIGHT)
        flow.field(self.time_selector, _FIELD_HEIGHT)
        flow.gap(14)
        flow.place(self.start_button, 50)

    def _flow_network(self, flow) -> None:
        if not self.app.account:
            self.white_input.label = "Seu nome"
            flow.field(self.white_input, _FIELD_HEIGHT)
        flow.field(self.time_selector, _FIELD_HEIGHT)
        flow.note(NETWORK_NOTE, reserve_lines=2)
        flow.gap(6)
        flow.place(self.create_room_button, 48)
        flow.gap(8)
        flow.place(self.join_room_button, 42)

    def _layout_history(self) -> None:
        theme = self.app.theme
        top = self.tab_bar.rect.bottom + theme.px(14)
        bottom = self._form.height - theme.px(_ROW_HEIGHT + _BOTTOM_MARGIN + 10)
        column = pygame.Rect(self._content_left(), top, self._content_width(), max(bottom - top, 1))
        self.history.layout(column, pygame.Rect(0, 0, max(self._form.x, 1), self._form.height))

    def _layout_bottom_row(self) -> None:
        theme = self.app.theme
        left, width = self._content_left(), self._content_width()
        height = theme.px(_ROW_HEIGHT)
        y = self._form.height - theme.px(_BOTTOM_MARGIN) - height
        quit_width = min(theme.px(_QUIT_BUTTON_WIDTH), width // 3)
        gap = theme.px(8)
        self.help_button.rect = pygame.Rect(left, y, max(width - quit_width - gap, 1), height)
        self.quit_button.rect = pygame.Rect(left + width - quit_width, y, max(quit_width, 1), height)

    def resize(self, size: tuple[int, int]) -> None:
        super().resize(size)
        if self.modal is not None:
            self.modal.layout(size)


def _index_of(options, value) -> int:
    return next((index for index, (_, option) in enumerate(options) if option == value), 0)
