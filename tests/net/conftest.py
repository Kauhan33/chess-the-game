"""Nenhum teste de rede pode travar a suíte nem deixar thread ou socket para trás."""
import faulthandler
import sys
import threading
import time

import pytest

from xadrez.net.session import THREAD_NAME_PREFIX

_WATCHDOG_SECONDS = 180
_THREAD_EXIT_SECONDS = 5.0


def session_threads():
    return [thread for thread in threading.enumerate() if thread.name.startswith(THREAD_NAME_PREFIX)]


@pytest.fixture(autouse=True)
def no_session_thread_left_behind():
    """Sem pytest-timeout no projeto, o cão de guarda encerra o processo se algo escapar dos timeouts dos testes."""
    faulthandler.dump_traceback_later(_WATCHDOG_SECONDS, exit=True, file=sys.__stderr__)
    yield
    faulthandler.cancel_dump_traceback_later()
    deadline = time.monotonic() + _THREAD_EXIT_SECONDS
    while session_threads() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not session_threads(), "thread de sessão ficou viva depois do teste"


@pytest.fixture
def opened():
    """Fecha tudo que o teste abriu, mesmo se ele falhar no meio."""
    resources = []

    def track(resource):
        resources.append(resource)
        return resource

    yield track
    for resource in reversed(resources):
        resource.close()
