"""Interface do jogo: cenas, HUD e entrada. Liga o motor de regras ao pipeline gráfico."""
from xadrez.ui.app import App
from xadrez.ui.game_over_scene import GameOverScene
from xadrez.ui.game_scene import GameScene
from xadrez.ui.hud import Hud
from xadrez.ui.match import MatchOptions
from xadrez.ui.menu_scene import MenuScene
from xadrez.ui.scene import Scene
from xadrez.ui.widgets import Button, Selector, TextInput

__all__ = [
    "App",
    "Button",
    "GameOverScene",
    "GameScene",
    "Hud",
    "MatchOptions",
    "MenuScene",
    "Scene",
    "Selector",
    "TextInput",
]
