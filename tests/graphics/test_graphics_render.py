"""CT-36: render, com corte de faces traseiras, ordem de pintura e pixels reais."""
import math

import numpy as np
import pygame
import pytest

from xadrez.graphics import (
    EBONY,
    IVORY,
    MARKER_CORNERS,
    MARKER_DOT,
    MARKER_RING,
    MARKER_TRIANGLE,
    Camera,
    CellState,
    ColorMatrix,
    DirectionalLight,
    ParticleSystem,
    Renderer3D,
    box,
    build_piece_meshes,
    compose,
    identity,
    piece_matrix,
    rotation_x,
    scaling,
    square_to_world,
    translation,
)
from xadrez.graphics.backdrop import render_backdrop
from xadrez.graphics.renderer import _build_geometry, _visible_polygons

ct36 = pytest.mark.ct("CT-36")
SIZE = (640, 360)
BRIGHT = (255, 255, 255)
MESHES = build_piece_meshes()


@pytest.fixture
def screen():
    pygame.init()
    pygame.display.set_mode(SIZE)
    surface = pygame.Surface(SIZE)
    surface.fill((1, 2, 3))
    return surface


def render_frames(renderer, screen, scene, frames=6):
    """Roda vários quadros com a câmera parada, para chegar à camada pronta e aos sprites."""
    for _ in range(frames):
        renderer.begin(screen)
        scene(renderer)
        renderer.flush()


def render_orbiting(renderer, screen, scene):
    """Um quadro em que a câmera conta como em movimento: modo por polígonos."""
    renderer.camera.orbit_by(0.0)
    render_frames(renderer, screen, scene, frames=1)


def render_in_mode(renderer, screen, scene, is_orbiting):
    if is_orbiting:
        render_orbiting(renderer, screen, scene)
    else:
        render_frames(renderer, screen, scene)


def pixel_at(screen, point):
    pixels, _ = screen_of(point)
    return screen.get_at((int(pixels[0]), int(pixels[1])))[:3]


def screen_of(point):
    pixels, depth = Camera((0, 0, *SIZE)).project([point])
    return pixels[0], depth[0]


def unlit_geometry(mesh):
    return _build_geometry(mesh, identity(), np.array(BRIGHT, dtype=float), DirectionalLight())


@ct36
def test_corte_descarta_as_faces_que_olham_para_longe():
    camera = Camera((0, 0, *SIZE))
    polygons = _visible_polygons(unlit_geometry(box(1, 1, 1)), camera, DirectionalLight())
    # A câmera padrão vê a tampa, a frente e, pela perspectiva, nada de trás nem de baixo.
    normals = unlit_geometry(box(1, 1, 1)).normals[polygons.faces]
    assert len(polygons.quads) < 6
    assert (normals @ (camera.eye - np.array((0.0, 0.5, 0.0))) > 0.0).all()
    assert not (normals[:, 1] < -0.5).any()


@ct36
def test_corte_troca_de_lado_com_a_camera():
    from_white = _visible_polygons(unlit_geometry(box(1, 1, 1)), Camera((0, 0, *SIZE)), DirectionalLight())
    from_black = _visible_polygons(unlit_geometry(box(1, 1, 1)), Camera((0, 0, *SIZE), yaw=math.pi), DirectionalLight())
    assert set(from_white.faces.tolist()) != set(from_black.faces.tolist())


@ct36
def test_face_atras_do_plano_near_e_descartada():
    camera = Camera((0, 0, *SIZE), distance=9.0)
    behind_eye = translation(*(camera.eye + np.array((0.0, 0.0, 0.0))))
    mesh = box(0.4, 0.4, 0.4)
    geometry = _build_geometry(mesh, behind_eye, np.array(BRIGHT, dtype=float), DirectionalLight())
    assert len(_visible_polygons(geometry, camera, DirectionalLight()).quads) == 0


@ct36
def test_silhueta_marca_face_com_vizinha_de_costas():
    camera = Camera((0, 0, *SIZE), pitch=math.radians(85))
    polygons = _visible_polygons(unlit_geometry(box(1, 1, 1)), camera, DirectionalLight())
    assert polygons.on_silhouette.any()


@pytest.mark.parametrize("frames", [1, 6])
@ct36
def test_ordem_de_pintura_objeto_da_frente_cobre_o_de_tras(screen, frames):
    # Cubos altos e alinhados no eixo da câmera. O da frente precisa ganhar nos dois modos.
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    tall = box(0.8, 2.5, 0.8)
    front_color, back_color = (250, 30, 30), (30, 30, 250)
    front = piece_matrix(4, 3)
    back = piece_matrix(4, 4)

    def scene(r):
        r.add_mesh(tall, back, back_color, cast_shadow=False)
        r.add_mesh(tall, front, front_color, cast_shadow=False)

    render_frames(renderer, screen, scene, frames)
    overlap = np.array(square_to_world(4, 3)) + (0.0, 2.0, 0.4)
    red, _, blue = pixel_at(screen, overlap)
    assert red > blue


@pytest.mark.parametrize("frames", [1, 6])
@ct36
def test_ordem_de_pintura_nao_depende_da_ordem_de_envio(screen, frames):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    tall = box(0.8, 2.5, 0.8)
    front_color, back_color = (250, 30, 30), (30, 30, 250)

    def scene(r):
        r.add_mesh(tall, piece_matrix(4, 3), front_color, cast_shadow=False)
        r.add_mesh(tall, piece_matrix(4, 4), back_color, cast_shadow=False)

    render_frames(renderer, screen, scene, frames)
    overlap = np.array(square_to_world(4, 3)) + (0.0, 2.0, 0.4)
    red, _, blue = pixel_at(screen, overlap)
    assert red > blue


@ct36
def test_a1_e_escura_e_a_matriz_de_cores_chega_na_tela(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()
    matrix.set(4, 4, CellState.PATH)
    render_frames(renderer, screen, lambda r: r.draw_board(matrix.rgb()))
    dark = pixel_at(screen, square_to_world(0, 0))
    light = pixel_at(screen, square_to_world(1, 0))
    path = pixel_at(screen, square_to_world(4, 4))
    assert sum(dark) < sum(light)
    assert path[1] > path[0] and path[1] > path[2]


@ct36
def test_modo_por_poligonos_tambem_pinta_as_casas(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()
    matrix.set(4, 4, CellState.PATH)
    render_frames(renderer, screen, lambda r: r.draw_board(matrix.rgb()), frames=1)
    path = pixel_at(screen, square_to_world(4, 4))
    assert path[1] > path[0]


@ct36
def test_cor_pulsando_atualiza_so_a_casa_com_a_camera_parada(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()
    matrix.set(4, 4, CellState.CHECK)
    states = {}
    for time in (0.0, 0.227, 0.68):
        def scene(r, t=time):
            r.draw_board(matrix.rgb(t))

        render_frames(renderer, screen, scene)
        states[time] = (pixel_at(screen, square_to_world(4, 4)), pixel_at(screen, square_to_world(1, 1)))
    assert len({state[0] for state in states.values()}) > 1
    assert len({state[1] for state in states.values()}) == 1


@ct36
def test_casa_que_perde_o_estado_volta_a_cor_base(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()
    plain = ColorMatrix()
    matrix.set(4, 4, CellState.SELECTED)
    render_frames(renderer, screen, lambda r: r.draw_board(matrix.rgb()))
    selected = pixel_at(screen, square_to_world(4, 4))
    render_frames(renderer, screen, lambda r: r.draw_board(plain.rgb()))
    assert pixel_at(screen, square_to_world(4, 4)) != selected


@ct36
def test_sombra_cai_no_sentido_da_luz_e_escurece_o_tabuleiro(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()
    tall = box(0.5, 2.0, 0.5)
    file, rank = 3, 3

    def lit_scene(r):
        r.draw_board(matrix.rgb())
        r.add_mesh(tall, piece_matrix(file, rank), (10, 200, 10))

    def empty_scene(r):
        r.draw_board(matrix.rgb())

    render_frames(renderer, screen, empty_scene)
    x, _, z = square_to_world(file, rank)
    # A luz viaja para +x e -z, logo a sombra fica ali.
    downstream = (x + 0.6, 0.0, z - 0.42)
    upstream = (x - 0.6, 0.0, z + 0.42)
    clean_down, clean_up = pixel_at(screen, downstream), pixel_at(screen, upstream)
    render_frames(renderer, screen, lit_scene)
    assert sum(pixel_at(screen, downstream)) < 0.8 * sum(clean_down)
    assert sum(pixel_at(screen, upstream)) == pytest.approx(sum(clean_up), abs=6)


@ct36
def test_sombras_sobrepostas_nao_escurecem_em_dobro(screen):
    matrix = ColorMatrix()
    tall = box(0.6, 2.0, 0.6)
    point = (0.3, 0.0, -0.3)

    def shadow_level(matrices):
        renderer = Renderer3D(Camera((0, 0, *SIZE)))

        def scene(r):
            r.draw_board(matrix.rgb())
            for model in matrices:
                r.add_mesh(tall, model, (10, 200, 10))

        render_frames(renderer, screen, scene)
        return sum(pixel_at(screen, point))

    one = shadow_level([translation(-0.1, 0.0, 0.1)])
    two = shadow_level([translation(-0.1, 0.0, 0.1), translation(-0.12, 0.0, 0.12)])
    assert two == pytest.approx(one, abs=12)


@ct36
def test_camera_em_movimento_desenha_por_poligonos_e_parada_por_sprites(screen):
    camera = Camera((0, 0, *SIZE))
    renderer = Renderer3D(camera)
    scene = lambda r: r.add_mesh(MESHES["pawn"], piece_matrix(4, 4), IVORY)
    renderer.begin(screen)
    scene(renderer)
    renderer.flush()
    assert renderer.sprites_built == 0
    assert renderer.polygons_drawn > 0
    render_frames(renderer, screen, scene, frames=3)
    assert renderer.sprites_built == 0
    assert renderer.polygons_drawn == 0
    camera.orbit_by(0.1)
    render_frames(renderer, screen, scene, frames=1)
    assert renderer.polygons_drawn > 0


@ct36
def test_sprites_sao_feitos_aos_poucos_depois_que_a_camera_para(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))

    def scene(r):
        for file in range(8):
            for rank in range(2, 6):
                r.add_mesh(MESHES["pawn"], piece_matrix(file, rank), IVORY)

    built = []
    for _ in range(8):
        renderer.begin(screen)
        scene(renderer)
        renderer.flush()
        built.append(renderer.sprites_built)
    assert built[0] == 0
    assert 0 < max(built) < 32
    assert sum(built) == 32


@ct36
def test_tint_desenha_a_peca_na_cor_pedida_nos_dois_modos(screen):
    for frames in (1, 7):
        renderer = Renderer3D(Camera((0, 0, *SIZE)))
        target = np.array(square_to_world(4, 4)) + (0.0, 1.0, 0.0)

        def scene(r):
            r.add_mesh(box(0.6, 2.0, 0.6), piece_matrix(4, 4), (200, 200, 200), tint=(255, 0, 0), tint_amount=0.9)

        render_frames(renderer, screen, scene, frames)
        red, green, blue = pixel_at(screen, target)
        assert red > 2 * green
        assert red > 2 * blue


@ct36
def test_tint_zero_nao_muda_a_peca(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    target = np.array(square_to_world(4, 4)) + (0.0, 1.0, 0.0)
    render_frames(renderer, screen, lambda r: r.add_mesh(box(0.6, 2.0, 0.6), piece_matrix(4, 4), (200, 200, 200)))
    plain = pixel_at(screen, target)
    render_frames(renderer, screen, lambda r: r.add_mesh(box(0.6, 2.0, 0.6), piece_matrix(4, 4), (200, 200, 200),
                                                         tint=(255, 0, 0), tint_amount=0.0))
    assert pixel_at(screen, target) == plain


@ct36
def test_peca_preta_contrasta_com_casa_escura(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()

    def scene(r):
        r.draw_board(matrix.rgb())
        r.add_mesh(MESHES["rook"], piece_matrix(4, 4), EBONY)

    render_frames(renderer, screen, scene)
    pixels, _ = Camera((0, 0, *SIZE)).project([(0.5, 0.45, -0.5)])
    piece = np.array(screen.get_at((int(pixels[0, 0]), int(pixels[0, 1])))[:3], dtype=float)
    square = np.array(pixel_at(screen, (0.5 + 0.42, 0.0, -0.5 + 0.42)), dtype=float)
    assert np.abs(piece - square).sum() > 40


@pytest.mark.parametrize("kind", [MARKER_DOT, MARKER_RING, MARKER_CORNERS, MARKER_TRIANGLE])
@pytest.mark.parametrize("is_orbiting", [True, False])
@ct36
def test_marcador_altera_so_os_pixels_da_propria_casa(screen, kind, is_orbiting):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()

    def base(r):
        r.draw_board(matrix.rgb())

    def marked(r):
        base(r)
        r.add_marker(2, 3, kind, (255, 0, 255, 200))

    render_in_mode(renderer, screen, base, is_orbiting)
    before = pygame.surfarray.array3d(screen).copy()
    render_in_mode(renderer, screen, marked, is_orbiting)
    after = pygame.surfarray.array3d(screen)
    changed = (before != after).any(axis=2)
    x, _, z = square_to_world(2, 3)
    corners, _ = Camera((0, 0, *SIZE)).project([(x - 0.5, 0.0, z - 0.5), (x + 0.5, 0.0, z + 0.5)])
    (left, top), (right, bottom) = corners.astype(int).tolist()
    assert changed.any()
    assert not changed[:left - 2].any() and not changed[right + 3:].any()
    assert not changed[:, :top - 2].any() and not changed[:, bottom + 3:].any()


@pytest.mark.parametrize("is_orbiting", [True, False])
@ct36
def test_anel_deixa_o_miolo_e_ponto_preenche_o_centro(screen, is_orbiting):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    matrix = ColorMatrix()
    center = square_to_world(2, 3)
    color = (255, 0, 255)

    def center_pixel_with(kind):
        def scene(r):
            r.draw_board(matrix.rgb())
            r.add_marker(2, 3, kind, color)

        render_in_mode(renderer, screen, scene, is_orbiting)
        return pixel_at(screen, center)

    assert center_pixel_with(MARKER_DOT) == pytest.approx(color, abs=4)
    assert center_pixel_with(MARKER_RING) != pytest.approx(color, abs=4)


@ct36
def test_marcador_desconhecido_avisa(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    renderer.begin(screen)
    renderer.add_marker(0, 0, "estrela", (1, 2, 3))
    with pytest.raises(ValueError):
        renderer.flush()


@pytest.mark.parametrize("is_orbiting", [True, False])
@ct36
def test_particula_soma_luz_e_nunca_escurece(screen, is_orbiting):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    system = ParticleSystem(seed=1, gravity=0.0)
    position = (0.0, 0.5, 0.0)
    matrix = ColorMatrix()

    def empty(r):
        r.draw_board(matrix.rgb())

    render_in_mode(renderer, screen, empty, is_orbiting)
    before = pygame.surfarray.array3d(screen).copy()
    system.emit(position, 5, (255, 180, 80), speed=0.0, life=5.0, size=0.2)

    def scene(r):
        empty(r)
        r.add_particles(system)

    render_in_mode(renderer, screen, scene, is_orbiting)
    after = pygame.surfarray.array3d(screen)
    x, y = screen_of(position)[0].astype(int)
    assert after[x, y].sum() > before[x, y].sum()
    assert (after.astype(int) >= before.astype(int)).all()


@ct36
def test_particula_atras_da_camera_nao_quebra_nem_desenha(screen):
    camera = Camera((0, 0, *SIZE))
    renderer = Renderer3D(camera)
    system = ParticleSystem(seed=1, gravity=0.0)
    system.emit(camera.eye + camera.eye, 3, (255, 255, 255), speed=0.0, life=5.0, size=0.2)
    before = pygame.surfarray.array3d(screen).copy()
    renderer.begin(screen)
    renderer.add_particles(system)
    renderer.flush()
    assert (pygame.surfarray.array3d(screen)[:, :, 0] >= before[:, :, 0]).all()


@ct36
def test_cache_de_sprites_de_particula_tem_limite(screen):
    from xadrez.graphics.renderer import _GLOW_MAX_ENTRIES, _GlowSprites

    sprites = _GlowSprites()
    for code in range(_GLOW_MAX_ENTRIES + 3):
        sprites[(code << 9) | (1 << 5) | 2]
    assert len(sprites) <= _GLOW_MAX_ENTRIES


@ct36
def test_viewport_deslocado_nao_desenha_fora_da_propria_area(screen):
    camera = Camera((200, 40, 400, 300))
    renderer = Renderer3D(camera)
    matrix = ColorMatrix()
    for frames in (1, 6):
        render_frames(renderer, screen, lambda r: (r.draw_board(matrix.rgb()),
                                                   r.add_mesh(MESHES["queen"], piece_matrix(4, 4), IVORY)), frames)
        assert screen.get_at((10, 10))[:3] == (1, 2, 3)
        assert screen.get_at((630, 350))[:3] == (1, 2, 3)
        assert screen.get_clip() == screen.get_rect()
    assert sum(screen.get_at((400, 190))[:3]) > 20


@ct36
def test_redimensionar_durante_o_jogo_nao_quebra(screen):
    camera = Camera((0, 0, *SIZE))
    renderer = Renderer3D(camera)
    matrix = ColorMatrix()

    def scene(r):
        r.draw_board(matrix.rgb())
        r.add_mesh(MESHES["king"], piece_matrix(4, 4), IVORY)

    render_frames(renderer, screen, scene, 3)
    for rect in ((0, 0, 320, 200), (0, 0, 1, 1), (50, 50, 590, 310)):
        camera.set_viewport(*rect)
        render_frames(renderer, screen, scene, 3)


@ct36
def test_quadro_sem_tabuleiro_nem_pecas_e_valido(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    renderer.flush()
    render_frames(renderer, screen, lambda r: None)
    matrix = ColorMatrix()
    render_frames(renderer, screen, lambda r: r.draw_board(matrix.rgb()))
    assert sum(pixel_at(screen, square_to_world(1, 0))) > 150


@ct36
def test_peca_em_escala_zero_nao_quebra(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    flattened = compose(piece_matrix(4, 4), scaling(0.0))
    render_frames(renderer, screen, lambda r: r.add_mesh(MESHES["bishop"], flattened, IVORY))
    render_frames(renderer, screen, lambda r: r.add_mesh(MESHES["bishop"], flattened, IVORY), frames=1)


@ct36
def test_peca_tombada_mostra_a_base(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    flipped = compose(translation(0.0, 0.5, 0.0), rotation_x(math.pi))
    render_frames(renderer, screen, lambda r: r.add_mesh(box(0.7, 0.5, 0.7), flipped, (200, 180, 160), cast_shadow=False))
    assert sum(pixel_at(screen, (0.0, 0.5, 0.0))) > 100


@ct36
def test_trocar_a_luz_invalida_os_caches(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    mesh = box(0.8, 0.8, 0.8)
    scene = lambda r: r.add_mesh(mesh, piece_matrix(4, 4), (200, 200, 200))
    render_frames(renderer, screen, scene)
    top = np.array(square_to_world(4, 4)) + (0.0, 0.8, 0.0)
    before = pixel_at(screen, top)
    renderer.light = DirectionalLight(ambient=0.05, diffuse=0.0)
    assert renderer.light.diffuse == 0.0
    render_frames(renderer, screen, scene)
    assert sum(pixel_at(screen, top)) < sum(before)


@ct36
def test_cache_de_instancia_reaproveita_a_geometria_da_peca_parada(screen):
    renderer = Renderer3D(Camera((0, 0, *SIZE)))
    mesh = MESHES["pawn"]
    matrix = piece_matrix(1, 1)
    render_frames(renderer, screen, lambda r: r.add_mesh(mesh, matrix, IVORY), 2)
    first = next(iter(renderer._instances.values()))
    render_frames(renderer, screen, lambda r: r.add_mesh(mesh, matrix, IVORY), 2)
    assert next(iter(renderer._instances.values())) is first


@ct36
def test_lote_troca_so_a_peca_que_se_moveu_e_recria_quando_a_cena_muda(screen):
    camera = Camera((0, 0, *SIZE))
    renderer = Renderer3D(camera)
    mesh = MESHES["pawn"]

    def scene_at(rank):
        def scene(r):
            r.add_mesh(mesh, piece_matrix(0, 0), IVORY)
            r.add_mesh(mesh, piece_matrix(1, rank), IVORY)

        return scene

    def single(r):
        r.add_mesh(mesh, piece_matrix(0, 0), IVORY)

    render_frames(renderer, screen, scene_at(1), 2)
    batch = renderer._batch
    render_frames(renderer, screen, scene_at(5), 2)
    assert renderer._batch is batch
    assert batch.anchors[1][2] == pytest.approx(3.5 - 5)
    render_frames(renderer, screen, single, 2)
    assert renderer._batch is not batch


@ct36
def test_icone_tem_alpha_no_canto_e_peca_no_centro(screen):
    renderer = Renderer3D(Camera())
    icon = renderer.render_icon(MESHES["knight"], IVORY, 48)
    assert icon.get_size() == (48, 48)
    assert icon.get_flags() & pygame.SRCALPHA
    assert icon.get_at((0, 0))[3] == 0
    alpha = pygame.surfarray.array_alpha(icon)
    assert (alpha > 200).sum() > 100
    assert renderer.render_icon(MESHES["knight"], IVORY, 48) is icon
    assert renderer.render_icon(MESHES["knight"], EBONY, 48) is not icon


@ct36
def test_fundo_e_deterministico_e_mais_claro_no_centro(screen):
    first = pygame.surfarray.array3d(render_backdrop(160, 90))
    second = pygame.surfarray.array3d(render_backdrop(160, 90))
    assert (first == second).all()
    center = first[60:100, 30:60].mean()
    corner = first[:15, :10].mean()
    assert center > corner
