"""Aplicação: janela, relógio de 60 FPS e troca de cenas."""
from __future__ import annotations

import ctypes
import sys
import time

import pygame

from xadrez.core import GameEngine, Player
from xadrez.data import HistoryStore
from xadrez.graphics import IVORY, build_piece_meshes
from xadrez.ui.arena_scene import Tableau
from xadrez.ui.board_view import BoardView
from xadrez.ui.frame_pacer import FramePacer
from xadrez.ui.game_over_scene import GameOverScene
from xadrez.ui.game_scene import GameScene
from xadrez.ui.lobby_scene import LobbyScene
from xadrez.ui.login_scene import LoginScene
from xadrez.ui.match import MatchOptions
from xadrez.ui.menu_scene import MenuScene
from xadrez.ui.net_link import LanNetwork, NetLink
from xadrez.ui.scene import Scene
from xadrez.ui.theme import Theme

WINDOW_SIZE = (1280, 720)
WINDOW_TITLE = "Chess - The Game"
FPS = 60
# Quadro mais longo que isso (janela arrastada, por exemplo) não pode virar salto de relógio e animação.
MAX_FRAME_SECONDS = 0.1
_FRAME_SMOOTHING = 0.1
_WINDOW_ICON_SIZE = 64
_DOUBLE_CLICK_SECONDS = 0.25
# Um clique duplo de verdade quase não sai do lugar. Um clique rápido em outro botão, logo ao lado, tem de valer.
_DOUBLE_CLICK_PIXELS = 3


def _enable_dpi_awareness() -> None:
    """No Windows com escala de tela, sem isto a janela fica borrada e o mouse desalinhado."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def _bounded_frame_time(dt: float) -> float:
    """Zero para valor negativo ou NaN, porque `dt > 0` falha nos dois. Teto para o infinito e para saltos."""
    return min(dt, MAX_FRAME_SECONDS) if dt > 0 else 0.0


class App:
    """O jogo do jogador é `App(require_login=True)`: abre no login, com contas e rede.

    `App()` abre direto no menu, como convidado, sem contas e sem rede: é o que testes e ferramentas usam, e
    nada ali toca a pasta de dados nem abre uma porta. Os testes de rede passam a própria `network`.
    """

    def __init__(self, size: tuple[int, int] = WINDOW_SIZE, seed: int | None = None, require_login: bool = False,
                 network=None):
        _enable_dpi_awareness()
        pygame.init()
        self._flags = pygame.RESIZABLE
        self._windowed_size: tuple[int, int] | None = None
        self.seed = seed
        self.require_login = require_login
        self.network = network if network is not None or not require_login else LanNetwork()
        self.account: str | None = None
        self.screen = pygame.display.set_mode(size, self._flags)
        self.size = self.screen.get_size()
        pygame.display.set_caption(WINDOW_TITLE)
        self.pacer = FramePacer(FPS)
        self.theme = Theme()
        self.theme.set_window_size(self.size)
        self.meshes = build_piece_meshes()
        self.tableau = Tableau(self.meshes)
        self.running = True
        self.fps = 0.0
        self.frame_ms = 0.0
        self._last_press: tuple[int, int] | None = None
        self._last_press_age = 0.0
        self._echo_position: tuple[int, int] | None = None
        self._echo_guard_left = 0.0
        self.scene: Scene = self.login_scene() if require_login else self.menu_scene()
        self._set_window_icon()

    def _set_window_icon(self) -> None:
        icon = self.tableau.renderer.render_icon(self.meshes["knight"], IVORY, _WINDOW_ICON_SIZE)
        pygame.display.set_icon(icon)

    def history_store(self) -> HistoryStore | None:
        """O histórico de quem está logado. O convidado não tem."""
        return HistoryStore(self.account) if self.account else None

    # As cenas se chamam em ciclo (menu, partida e fim). Passar pelo App evita importação circular.

    def login_scene(self, start_creating: bool = False) -> LoginScene:
        return LoginScene(self, start_creating)

    def menu_scene(self, defaults: MatchOptions | None = None) -> MenuScene:
        return MenuScene(self, defaults)

    def lobby_scene(self, options: MatchOptions, role: str) -> LobbyScene:
        return LobbyScene(self, options, role)

    def game_scene(self, engine: GameEngine, options: MatchOptions, view: BoardView | None = None,
                   local_player: Player | None = None, link: NetLink | None = None) -> GameScene:
        return GameScene(self, engine, options, view, local_player, link)

    def game_over_scene(self, engine: GameEngine, options: MatchOptions, view: BoardView,
                        local_player: Player | None = None, link: NetLink | None = None) -> GameOverScene:
        return GameOverScene(self, engine, options, view, local_player, link)

    def step(self, dt: float) -> None:
        """Um quadro completo e determinístico: eventos, tempo e desenho. Quem chama controla o `dt`."""
        started = time.perf_counter()
        for event in pygame.event.get():
            self._dispatch(event)
        self._follow_window_size()
        frame_time = _bounded_frame_time(dt)
        self._echo_guard_left -= frame_time
        self._last_press_age += frame_time
        self.scene.update(frame_time)
        self._apply_scene_change()
        self.scene.draw(self.screen)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.frame_ms += (elapsed_ms - self.frame_ms) * _FRAME_SMOOTHING

    def _dispatch(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self._apply_resize(event.size)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self._toggle_fullscreen()
        elif not self._is_double_click_echo(event) and self.scene.next_scene is None:
            # Com a troca de tela já pedida, o resto do quadro não é mais dela: dois Enter abririam duas partidas.
            self.scene.handle_event(event)

    def _is_double_click_echo(self, event: pygame.event.Event) -> bool:
        """O 2º clique de um clique duplo não pode acertar o que apareceu ali na tela nova, como "Iniciar partida"."""
        if event.type != pygame.MOUSEBUTTONDOWN:
            return False
        self._last_press = event.pos
        self._last_press_age = 0.0
        echo = self._echo_position
        if self._echo_guard_left <= 0.0 or echo is None:
            return False
        return max(abs(event.pos[0] - echo[0]), abs(event.pos[1] - echo[1])) <= _DOUBLE_CLICK_PIXELS

    def _toggle_fullscreen(self) -> None:
        """Tela cheia para o projetor da apresentação, na resolução da tela. Volta ao tamanho de antes."""
        if self._windowed_size is None:
            self._windowed_size = self.size
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self._windowed_size, self._flags)
            # Saindo da tela cheia, o SDL pode manter o tamanho dela até a segunda chamada.
            if self.screen.get_size() != self._windowed_size:
                self.screen = pygame.display.set_mode(self._windowed_size, self._flags)
            self._windowed_size = None
        # O aviso de redimensionamento desta troca chegaria depois e forçaria o tamanho da troca anterior.
        pygame.event.clear(pygame.VIDEORESIZE)
        self._adopt_size(self.screen.get_size())

    def _apply_resize(self, requested: tuple[int, int]) -> None:
        size = (max(requested[0], 1), max(requested[1], 1))
        self.screen = pygame.display.get_surface()
        # Em janela real o SDL já redimensionou a superfície. Sem janela, quem muda é este set_mode.
        if self.screen.get_size() != size:
            self.screen = pygame.display.set_mode(size, self._flags)
        self._adopt_size(self.screen.get_size())

    def _follow_window_size(self) -> None:
        """Rede de segurança: alguns gerenciadores de janela mudam o tamanho sem gerar VIDEORESIZE."""
        surface = pygame.display.get_surface()
        if surface is not None and surface.get_size() != self.size:
            self.screen = surface
            self._adopt_size(surface.get_size())

    def _adopt_size(self, size: tuple[int, int]) -> None:
        self.size = size
        self.theme.set_window_size(size)
        self.scene.resize(size)

    def _apply_scene_change(self) -> None:
        if self.scene.next_scene is not None:
            self.scene = self.scene.next_scene
            # Só o clique que acabou de trocar a tela tem eco: um clique antigo no mesmo lugar não conta.
            self._echo_position = self._last_press if self._last_press_age <= _DOUBLE_CLICK_SECONDS else None
            self._echo_guard_left = _DOUBLE_CLICK_SECONDS
            # A janela pode ter mudado de tamanho no mesmo quadro em que a cena nova foi criada.
            self.scene.resize(self.size)
            self.scene.update(0.0)

    def run_frame(self) -> None:
        """Um quadro em tempo real: espera o prazo de 60 FPS, desenha e mostra na janela."""
        dt = self.pacer.wait()
        self.fps = self.pacer.fps
        self.step(dt)
        pygame.display.flip()

    def preload(self) -> None:
        """Desenha uma partida invisível: a primeira partida real já encontra os fundos prontos, sem quadro lento."""
        options = MatchOptions()
        self.game_scene(options.create_engine(), options).draw(self.screen)

    def run(self) -> None:
        self.preload()
        try:
            while self.running:
                self.run_frame()
        finally:
            # Nenhuma thread pode sobrar nem atrasar o fechamento: a cena aberta encerra as dela.
            self.scene.shutdown()
            pygame.quit()


def main() -> None:
    App(require_login=True).run()
