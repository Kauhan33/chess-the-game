"""Pré-carga dos fundos: não pode trocar a cena nem estragar a superfície compartilhada."""
import numpy as np
import pygame

from xadrez.graphics.backdrop import render_backdrop
from xadrez.ui.drawing import render_panel_ground

FRAME_SECONDS = 1.0 / 60.0


def test_painel_nao_escurece_o_fundo_compartilhado(app):
    before = pygame.surfarray.array3d(render_backdrop(64, 48)).copy()
    render_panel_ground((64, 48))
    assert np.array_equal(before, pygame.surfarray.array3d(render_backdrop(64, 48)))


def test_preload_mantem_o_menu_em_cena(app):
    menu = app.scene
    app.preload()
    app.step(FRAME_SECONDS)
    assert app.scene is menu
    assert app.scene.next_scene is None
