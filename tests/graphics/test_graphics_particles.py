"""CT-33: partículas, com gravidade, reflexão no piso e tempo de vida."""
import numpy as np
import pytest

from xadrez.graphics import ParticleSystem

ct33 = pytest.mark.ct("CT-33")


def single_particle(position=(0.0, 5.0, 0.0), velocity=(0.0, 0.0, 0.0), life=10.0, **options):
    options.setdefault("drag", 0.0)
    system = ParticleSystem(seed=1, **options)
    system.emit(position, 1, (255, 255, 255), speed=0.0, life=life, size=0.1)
    system.velocities[0] = velocity
    return system


@ct33
def test_gravidade_acelera_para_baixo():
    system = single_particle()
    system.update(0.1)
    assert system.velocities[0] == pytest.approx((0.0, -0.98, 0.0))
    assert system.positions[0] == pytest.approx((0.0, 5.0 - 0.098, 0.0))


@ct33
def test_arrasto_reduz_a_velocidade_exponencialmente():
    system = single_particle(velocity=(2.0, 0.0, 0.0), gravity=0.0, drag=1.0)
    system.update(1.0)
    assert system.velocities[0][0] == pytest.approx(2.0 * np.exp(-1.0))


@ct33
def test_colisao_reflete_o_vetor_velocidade_com_restituicao():
    system = single_particle(position=(0.0, 0.01, 0.0), velocity=(1.0, -4.0, 2.0), gravity=0.0, restitution=0.5)
    system.update(0.1)
    # v' = v - (1 + e)(v.n)n: só a componente normal inverte e perde energia.
    assert system.velocities[0] == pytest.approx((1.0, 2.0, 2.0))
    assert system.positions[0][1] == pytest.approx(0.0)


@ct33
def test_restituicao_um_e_a_reflexao_perfeita():
    system = single_particle(position=(0.0, 0.01, 0.0), velocity=(0.0, -3.0, 0.0), gravity=0.0, restitution=1.0)
    system.update(0.1)
    assert system.velocities[0][1] == pytest.approx(3.0)


@ct33
def test_piso_pode_ficar_em_outra_altura_e_nada_atravessa():
    system = single_particle(position=(0.0, 3.0, 0.0), velocity=(0.0, -5.0, 0.0), floor_y=2.0, life=50.0)
    for _ in range(300):
        system.update(1.0 / 60.0)
    assert system.positions[0][1] >= 2.0


@ct33
def test_particula_morre_ao_fim_da_vida_e_a_restante_segue_viva():
    system = ParticleSystem(seed=1)
    system.emit((0, 1, 0), 1, (255, 0, 0), speed=0.0, life=0.5, size=0.1)
    system.emit((0, 1, 0), 1, (0, 255, 0), speed=0.0, life=2.0, size=0.1)
    system.update(0.6)
    assert system.alive_count == 1
    assert system.colors[0] == pytest.approx((0, 255, 0))
    system.update(2.0)
    assert system.alive_count == 0


@ct33
def test_fade_e_tamanho_diminuem_com_a_idade():
    system = single_particle(life=1.0, gravity=0.0)
    assert system.alphas[0] == pytest.approx(1.0)
    size_at_birth = system.sizes[0]
    system.update(0.5)
    assert system.alphas[0] == pytest.approx(0.75)
    assert system.sizes[0] == pytest.approx(0.75 * size_at_birth)


@ct33
def test_capacidade_nunca_e_ultrapassada():
    system = ParticleSystem(capacity=10, seed=1)
    system.emit((0, 0, 0), 25, (255, 255, 255), speed=1.0, life=1.0, size=0.1)
    assert system.alive_count == 10
    system.emit((0, 0, 0), 5, (255, 255, 255), speed=1.0, life=1.0, size=0.1)
    assert system.alive_count == 10


@ct33
def test_cor_por_particula_tambem_respeita_a_capacidade():
    system = ParticleSystem(capacity=4, seed=1)
    system.emit((0, 0, 0), 3, (255, 255, 255), speed=1.0, life=1.0, size=0.1)
    system.victory_fireworks((0, 3, 0), [(255, 0, 0), (0, 255, 0)])
    assert system.alive_count == 4
    assert tuple(system.colors[3]) in {(255.0, 0.0, 0.0), (0.0, 255.0, 0.0)}


@ct33
def test_mesma_semente_da_a_mesma_simulacao():
    first, second = ParticleSystem(seed=42), ParticleSystem(seed=42)
    for system in (first, second):
        system.capture_burst((0, 0.5, 0), (200, 100, 50))
        for _ in range(10):
            system.update(1.0 / 60.0)
    assert first.positions == pytest.approx(second.positions)


@ct33
def test_presets_emitem_com_a_forma_certa():
    system = ParticleSystem(seed=3)
    system.capture_burst((0, 0.5, 0), (200, 100, 50))
    burst = system.alive_count
    assert burst > 30
    assert (system.velocities[:, 1].mean()) > 0.0
    system.trail((0, 0.5, 0), (255, 255, 255))
    assert system.alive_count == burst + 2
    before = system.alive_count
    palette = [(255, 0, 0), (0, 255, 0)]
    system.victory_fireworks((0, 3, 0), palette)
    assert system.alive_count > before
    assert {tuple(color) for color in system.colors[before:].tolist()} <= {(255.0, 0.0, 0.0), (0.0, 255.0, 0.0)}


@ct33
def test_atualizar_sem_particulas_ou_com_tempo_nulo_nao_faz_nada():
    system = ParticleSystem(seed=3)
    system.update(0.1)
    assert system.alive_count == 0
    system = single_particle()
    before = system.positions.copy()
    system.update(0.0)
    assert system.positions == pytest.approx(before)
