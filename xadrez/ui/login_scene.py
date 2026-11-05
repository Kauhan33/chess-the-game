"""Tela de entrada: entrar, criar conta ou jogar como convidado (RF20).

A senha só existe no campo de texto, desenhada como pontos, até ser usada. Depois disso o campo é limpo.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from xadrez.data import LOGIN_FAILED_MESSAGE, AccountError, AccountStore
from xadrez.data.accounts import MAX_USERNAME_LENGTH, username_key
from xadrez.ui import theme as tokens
from xadrez.ui.arena_scene import ArenaScene, draw_notes
from xadrez.ui.widgets import STYLE_PRIMARY, Button, FocusGroup, SegmentedControl, TextInput

if TYPE_CHECKING:
    from xadrez.ui.app import App

MODE_SIGN_IN = "entrar"
MODE_CREATE = "criar"
PASSWORD_MISMATCH_MESSAGE = "As duas senhas não são iguais. Digite de novo."
_MODE_OPTIONS = (("Entrar", MODE_SIGN_IN), ("Criar conta", MODE_CREATE))
_MAX_PASSWORD_LENGTH = 128
_FORM_TOP = 142


class LoginScene(ArenaScene):
    def __init__(self, app: App, start_creating: bool = False):
        super().__init__(app)
        self.username_input = TextInput("Usuário", "De 3 a 16 caracteres", MAX_USERNAME_LENGTH)
        theme = app.theme
        self.username_input.set_character_filter(lambda char: theme.has_glyph(char, tokens.ROLE_DISPLAY, theme.px(19)))
        self.password_input = TextInput("Senha", "Pelo menos 8 caracteres", _MAX_PASSWORD_LENGTH, is_secret=True, on_submit=self.submit)
        self.repeat_input = TextInput("Repita a senha", "A mesma senha", _MAX_PASSWORD_LENGTH, is_secret=True, on_submit=self.submit)
        self.mode_selector = SegmentedControl("", _MODE_OPTIONS, 1 if start_creating else 0, on_change=self._apply_mode)
        self.submit_button = Button("Entrar", self.submit, STYLE_PRIMARY, font_size=22)
        self.guest_button = Button("Jogar como convidado", self.play_as_guest)
        self.quit_button = Button("Sair do jogo", self.quit_game)
        self.focus = FocusGroup([self.username_input])
        self.error = ""
        self._error_top = 0
        pygame.key.start_text_input()
        self._apply_mode()
        self.resize(app.size)

    @property
    def is_creating(self) -> bool:
        return self.mode_selector.value == MODE_CREATE

    def _apply_mode(self) -> None:
        self.error = ""
        self.repeat_input.clear()
        self.submit_button.label = "Criar conta" if self.is_creating else "Entrar"
        repeat = [self.repeat_input] if self.is_creating else []
        widgets = [self.mode_selector, self.username_input, self.password_input, *repeat,
                   self.submit_button, self.guest_button, self.quit_button]
        focused = self.focus.focused if self.focus.focused in widgets else self.username_input
        self.focus.set_widgets(widgets, focused)
        self._layout_form()

    def submit(self) -> None:
        username, password = self.username_input.text, self.password_input.text
        repeated = self.repeat_input.text
        self.password_input.clear()
        self.repeat_input.clear()
        if self.is_creating:
            self._create_account(username, password, repeated)
        else:
            self._sign_in(username, password)

    def _sign_in(self, username: str, password: str) -> None:
        store = AccountStore()
        if store.authenticate(username, password):
            self._enter(store, username)
        else:
            self._show_error(LOGIN_FAILED_MESSAGE)

    def _create_account(self, username: str, password: str, repeated: str) -> None:
        if password != repeated:
            self._show_error(PASSWORD_MISMATCH_MESSAGE)
            return
        store = AccountStore()
        try:
            store.create(username, password)
        except AccountError as error:
            self._show_error(str(error))
            return
        self._enter(store, username)

    def _show_error(self, message: str) -> None:
        self.error = message
        self.focus.focus(self.password_input)
        self._layout_form()

    def _enter(self, store: AccountStore, username: str) -> None:
        """A conta aparece na grafia em que foi criada, mesmo se a pessoa digitou diferente ao entrar."""
        key = username_key(username)
        self.app.account = next((name for name in store.usernames() if username_key(name) == key), username.strip())
        self.next_scene = self.app.menu_scene()

    def play_as_guest(self) -> None:
        self.password_input.clear()
        self.repeat_input.clear()
        self.app.account = None
        self.next_scene = self.app.menu_scene()

    def quit_game(self) -> None:
        self.app.running = False

    def handle_event(self, event: pygame.event.Event) -> None:
        self.focus.handle_event(event)

    def update(self, dt: float) -> None:
        super().update(dt)
        for widget in (self.username_input, self.password_input, self.repeat_input):
            widget.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_arena(surface)
        self._draw_title(surface, "Chess - The Game", 24, size=48)
        theme = self.app.theme
        tagline = theme.text_fit("Entre para guardar suas partidas e estatísticas.", tokens.ROLE_LABEL, theme.px(18),
                                 tokens.TEXT_MUTED, self._content_width())
        surface.blit(tagline, (self._content_left(), self._form.y + theme.px(84)))
        self.focus.draw(surface, theme)
        draw_notes(surface, theme, self._notes)
        if self.error:
            self._draw_error(surface, self.error, self._error_top)

    def _layout_form(self) -> None:
        self._fit_spacing(self._layout_at)

    def _layout_at(self, spacing: float) -> int:
        theme = self.app.theme
        flow = self._flow(theme.px(_FORM_TOP), spacing)
        flow.place(self.mode_selector, 40)
        flow.field(self.username_input, 44)
        flow.field(self.password_input, 44)
        if self.is_creating:
            flow.field(self.repeat_input, 44)
        flow.gap(10)
        self._error_top = flow.y
        flow.gap(self._error_room(self.error))
        flow.place(self.submit_button, 52)
        flow.gap(30)
        flow.place(self.guest_button, 44)
        flow.note("Como convidado, as partidas não ficam guardadas no histórico.")
        flow.gap(10)
        flow.note("As contas ficam só neste computador. A senha nunca é gravada, só uma assinatura dela.")
        flow.gap(14)
        flow.place(self.quit_button, 36)
        self._notes = flow.notes
        return flow.y

    def shutdown(self) -> None:
        self.password_input.clear()
        self.repeat_input.clear()
