"""Área de transferência: copiar nunca derruba o jogo. Se não der, quem chamou mostra um aviso.

Isolado aqui para testar sem janela: os testes trocam `pygame.scrap` por uma imitação.
"""
from __future__ import annotations

import sys

import pygame

COPY_FAILED_MESSAGE = "Não foi possível copiar para a área de transferência neste computador."


def _encoded(text: str) -> bytes:
    """No Windows, o tipo de texto do pygame é o ANSI do sistema: UTF-8 ali vira "JoÃ£o" (conferido em janela real)."""
    if sys.platform == "win32":
        return text.replace("\n", "\r\n").encode("mbcs", "replace")
    return text.encode("utf-8")


def copy_text(text: str) -> bool:
    """Devolve se o texto chegou à área de transferência. Sem janela de verdade, a resposta é não."""
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, _encoded(text))
    except (pygame.error, NotImplementedError, OSError, ValueError):
        return False
    return True
