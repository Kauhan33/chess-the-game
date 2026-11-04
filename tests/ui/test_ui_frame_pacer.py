"""Controle de framerate (RNF01), com relógio falso para não depender de tempo real."""
import pytest

from xadrez.ui.frame_pacer import FramePacer

PERIOD = 1.0 / 60.0
SPIN_STEP = 0.0001


class FakeTime:
    """Cada leitura avança um pouco, como a espera ativa de verdade. O sono acorda com atraso fixo."""

    def __init__(self, oversleep=0.001):
        self.current = 100.0
        self.oversleep = oversleep
        self.slept = []

    def now(self):
        self.current += SPIN_STEP
        return self.current

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.current += seconds + self.oversleep


def make_pacer(clock):
    return FramePacer(60, now=clock.now, sleep=clock.sleep)


def test_media_fica_em_60_fps_mesmo_com_sono_atrasado():
    clock = FakeTime(oversleep=0.001)
    pacer = make_pacer(clock)
    elapsed = [pacer.wait() for _ in range(600)]
    assert sum(elapsed) / len(elapsed) == pytest.approx(PERIOD, rel=0.01)


def test_atraso_de_um_quadro_e_compensado_no_seguinte():
    clock = FakeTime(oversleep=0.0)
    pacer = make_pacer(clock)
    pacer.wait()
    clock.current += PERIOD * 1.5  # trabalho maior que um período, mas dentro de dois prazos
    late = pacer.wait()
    following = pacer.wait()
    assert late > PERIOD
    assert following < PERIOD
    assert late + following == pytest.approx(2 * PERIOD, rel=0.05)


def test_atraso_longo_nao_vira_rajada_de_quadros():
    clock = FakeTime(oversleep=0.0)
    pacer = make_pacer(clock)
    pacer.wait()
    clock.current += 2.0
    assert pacer.wait() == pytest.approx(2.0, rel=0.05)
    assert pacer.wait() == pytest.approx(PERIOD, rel=0.05)


def test_dorme_so_ate_perto_do_prazo():
    clock = FakeTime(oversleep=0.0)
    pacer = make_pacer(clock)
    pacer.wait()
    assert clock.slept and max(clock.slept) < PERIOD


def test_fps_estimado_converge_para_o_alvo():
    clock = FakeTime()
    pacer = make_pacer(clock)
    for _ in range(300):
        pacer.wait()
    assert pacer.fps == pytest.approx(60.0, abs=1.0)
