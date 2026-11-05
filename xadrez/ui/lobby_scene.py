"""Sala em rede: mostrar o código e esperar, ou digitar o código e entrar (RF19, UC11, UC12)."""
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pygame

from xadrez.core import Color, GameEngine, TimeControl
from xadrez.net import GameStart, NetworkError, PeerJoined, PeerLeft
from xadrez.net.room_code import ROOM_CODE_LENGTH
from xadrez.ui import clipboard, theme as tokens
from xadrez.ui.arena_scene import ArenaScene, draw_notes
from xadrez.ui.match import OPPONENT_NET, MatchOptions, time_control_label
from xadrez.ui.net_link import NetLink
from xadrez.ui.widgets import STYLE_PRIMARY, Button, FocusGroup, TextInput

if TYPE_CHECKING:
    from xadrez.ui.app import App

ROLE_HOST = "host"
ROLE_GUEST = "guest"
_DOT_SECONDS = 0.45
_FORM_TOP = 100
_CODE_PLATE_HEIGHT = 104
_STATUS_ROOM = 56


class LobbyScene(ArenaScene):
    def __init__(self, app: App, options: MatchOptions, role: str):
        super().__init__(app)
        self.options = replace(options, opponent_kind=OPPONENT_NET)
        self.role = role
        self.link: NetLink | None = None
        self.code = ""
        self.warning: str | None = None
        self.error = ""
        self.peer_name: str | None = None
        self.message = ""
        self._time = 0.0
        self._code_rect = pygame.Rect(0, 0, 1, 1)
        self._status_y = 0
        self.code_input = TextInput("Código da sala", f"{ROOM_CODE_LENGTH} letras e números", ROOM_CODE_LENGTH,
                                    on_submit=self.connect, transform=str.upper)
        self.code_input.set_character_filter(str.isalnum)
        self.connect_button = Button("Entrar na sala", self.connect, STYLE_PRIMARY, font_size=20)
        self.copy_button = Button("Copiar convite", self.copy_invite, STYLE_PRIMARY, font_size=18)
        self.retry_button = Button("Abrir a sala de novo", self.open_room)
        self.cancel_button = Button("Cancelar e voltar", self.cancel, hint="Esc")
        self.focus = FocusGroup([self.cancel_button])
        pygame.key.start_text_input()
        if role == ROLE_HOST:
            self.open_room()
        else:
            self._show_guest_form()
        self.resize(app.size)

    @property
    def is_host(self) -> bool:
        return self.role == ROLE_HOST

    @property
    def is_connecting(self) -> bool:
        return self.link is not None

    # Sala -----------------------------------------------------------------------------------------

    def open_room(self) -> None:
        self._close_session()
        self.error = ""
        session = self.app.network.host(self.options.white_name, self.options.time_control)
        session.start()
        self.link = NetLink(session)
        self.code = session.code
        self.warning = session.offline_warning
        self.focus.set_widgets([self.copy_button, self.cancel_button], self.copy_button)
        self._layout_form()

    def copy_invite(self) -> None:
        invite = f"Entre na minha sala de Chess - The Game. Código: {self.code}"
        self.message = "Convite copiado." if clipboard.copy_text(invite) else clipboard.COPY_FAILED_MESSAGE

    # Quem entra -----------------------------------------------------------------------------------

    def _show_guest_form(self) -> None:
        self.focus.set_widgets([self.code_input, self.connect_button, self.cancel_button], self.code_input)

    def connect(self) -> None:
        if self.is_connecting:
            return
        self.error = ""
        session = self.app.network.client(self.options.white_name, self.code_input.text)
        session.start()
        self.link = NetLink(session)

    # Eventos --------------------------------------------------------------------------------------

    def update(self, dt: float) -> None:
        super().update(dt)
        self._time += dt
        self.code_input.update(dt)
        if self.link is not None:
            self._receive_events()

    def _receive_events(self) -> None:
        self.link.pump()
        while self.link is not None and self.link.inbox and self.next_scene is None:
            self._handle(self.link.inbox.popleft())

    def _handle(self, event) -> None:
        if isinstance(event, PeerJoined):
            self.peer_name = event.name
        elif isinstance(event, GameStart):
            self._start_game(event)
        elif isinstance(event, (PeerLeft, NetworkError)):
            self._fail(event.reason if isinstance(event, PeerLeft) else event.message)

    def _fail(self, message: str) -> None:
        """A sessão já terminou. Quem criou pode abrir de novo; quem entrava corrige o código e tenta outra vez."""
        self._close_session()
        self.error = message
        self.peer_name = None
        if self.is_host:
            self.focus.set_widgets([self.retry_button, self.cancel_button], self.retry_button)
        self._layout_form()

    def _start_game(self, event: GameStart) -> None:
        link, self.link = self.link, None
        link.peer_name = event.black if event.your_color is Color.WHITE else event.white
        engine = GameEngine(event.white, event.black, TimeControl(event.minutes, event.increment))
        self.next_scene = self.app.game_scene(engine, self.options, local_player=engine.players[event.your_color], link=link)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.cancel()
            return
        self.focus.handle_event(event)

    def cancel(self) -> None:
        self._close_session()
        self.next_scene = self.app.menu_scene(self.options)

    def _close_session(self) -> None:
        link, self.link = self.link, None
        if link is not None:
            link.leave()

    def shutdown(self) -> None:
        self._close_session()

    # Desenho --------------------------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_arena(surface)
        title = "Criar sala em rede" if self.is_host else "Entrar em uma sala"
        self._draw_title(surface, title, 24, size=38)
        theme = self.app.theme
        if self.is_host and not self.error:
            self._draw_room_code(surface)
        self.focus.draw(surface, theme)
        draw_notes(surface, theme, self._notes)
        if self.error:
            self._draw_error(surface, self.error, self._status_y)
        else:
            self._draw_status(surface)

    def _draw_room_code(self, surface: pygame.Surface) -> None:
        """O código é o único elemento grande: é o que se dita para o outro jogador, de longe."""
        theme = self.app.theme
        rect = self._code_rect
        surface.blit(theme.plate(rect.size, tokens.PLATE_LIT), rect.topleft)
        digits = theme.text_fit(self.code, tokens.ROLE_NUMERIC, theme.px(66), tokens.INK, max(rect.width - theme.px(20), 1))
        surface.blit(digits, digits.get_rect(center=rect.center))

    def _status_text(self) -> str:
        if self.is_host:
            return f"{self.peer_name} entrou. Começando" if self.peer_name else "Aguardando adversário"
        return "Conectando" if self.is_connecting else ""

    def _draw_status(self, surface: pygame.Surface) -> None:
        theme = self.app.theme
        left, y = self._content_left(), self._status_y
        text = self._status_text()
        if text:
            dots = "." * (int(self._time / _DOT_SECONDS) % 3 + 1)
            surface.blit(theme.text(f"{text}{dots}", tokens.ROLE_DISPLAY, theme.px(22), tokens.IVORY), (left, y))
            y += theme.px(30)
        if self.message:
            message = theme.text_fit(self.message, tokens.ROLE_LABEL, theme.px(15), tokens.TEXT_MUTED, self._content_width())
            surface.blit(message, (left, y))

    # Layout ---------------------------------------------------------------------------------------

    def _layout_form(self) -> None:
        self._fit_spacing(self._layout_host if self.is_host else self._layout_guest)

    def _layout_host(self, spacing: float) -> int:
        theme = self.app.theme
        flow = self._flow(theme.px(_FORM_TOP), spacing)
        if not self.error:
            flow.note("Passe este código para quem vai jogar com você.", size=17)
            flow.gap(6)
            self._code_rect = pygame.Rect(flow.left, flow.y, flow.width, theme.px(_CODE_PLATE_HEIGHT))
            flow.y = self._code_rect.bottom
            flow.gap(14)
            flow.place(self.copy_button, 46)
            flow.gap(10)
        flow.note(f"Tempo: {time_control_label(self.options.time_control)}. Você joga de Brancas na primeira partida.")
        flow.note("O adversário precisa estar na mesma rede local que você.")
        flow.gap(14)
        self._status_y = flow.y
        flow.gap(max(_STATUS_ROOM, self._error_room(self.error)))
        self._layout_warning(flow)
        self._layout_bottom(flow)
        self._notes = flow.notes
        return flow.y

    def _layout_warning(self, flow) -> None:
        if self.warning and not self.error:
            flow.note(self.warning, tokens.ALERT_ON_DARK)
            flow.gap(10)

    def _layout_bottom(self, flow) -> None:
        if self.error and self.is_host:
            flow.place(self.retry_button, 44)
            flow.gap(10)
        flow.place(self.cancel_button, 42)

    def _layout_guest(self, spacing: float) -> int:
        theme = self.app.theme
        flow = self._flow(theme.px(_FORM_TOP), spacing)
        flow.note("Digite o código que o outro jogador passou. Quem criou a sala escolhe o tempo.", size=17)
        flow.field(self.code_input, 56)
        flow.gap(14)
        flow.place(self.connect_button, 50)
        flow.gap(16)
        self._status_y = flow.y
        flow.gap(max(_STATUS_ROOM, self._error_room(self.error)))
        flow.place(self.cancel_button, 42)
        self._notes = flow.notes
        return flow.y
