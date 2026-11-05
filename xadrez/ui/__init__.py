"""Interface do jogo: cenas, HUD e entrada. Liga o motor de regras ao pipeline gráfico."""
from xadrez.ui.app import App
from xadrez.ui.cpu_player import CpuPlayer
from xadrez.ui.game_over_scene import GameOverScene
from xadrez.ui.game_scene import GameScene
from xadrez.ui.hud import Hud
from xadrez.ui.lobby_scene import LobbyScene
from xadrez.ui.login_scene import LoginScene
from xadrez.ui.match import GameMode, MatchOptions
from xadrez.ui.menu_scene import MenuScene
from xadrez.ui.scene import Scene
from xadrez.ui.widgets import Button, SegmentedControl, Selector, TextInput

__all__ = [
    "App",
    "Button",
    "CpuPlayer",
    "GameMode",
    "GameOverScene",
    "GameScene",
    "Hud",
    "LobbyScene",
    "LoginScene",
    "MatchOptions",
    "MenuScene",
    "Scene",
    "SegmentedControl",
    "Selector",
    "TextInput",
]
