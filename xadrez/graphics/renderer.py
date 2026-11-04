"""Renderizador 3D em software: pipeline explícito sobre numpy e pygame.

Modelo -> Mundo -> Visão -> Recorte -> NDC -> Tela. Os vértices de todas as malhas passam
por matrizes 4x4 em um único array, faces traseiras são descartadas, e o algoritmo do pintor
ordena o que sobra de trás para a frente.

Há dois modos de desenho, escolhidos pelo que muda na tela (ver `flush`):

- Câmera em movimento: redesenha todos os polígonos a cada quadro, com anti-aliasing só nas
  faces de silhueta, onde o serrilhado aparece.
- Câmera parada: quase nada muda, então o tabuleiro vira uma camada pronta e cada peça vira
  um sprite. Os dois nascem de superamostragem, o que dá bordas melhores e custa só um blit.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import NamedTuple

import numpy as np
import pygame
import pygame.gfxdraw

from xadrez.graphics.backdrop import render_backdrop
from xadrez.graphics.board_model import build_board_geometry, build_frame_parts
from xadrez.graphics.camera import NEAR_PLANE, Camera
from xadrez.graphics.lighting import DirectionalLight
from xadrez.graphics.matrix import identity, planar_shadow, square_to_world, transform_points
from xadrez.graphics.mesh import Mesh, compute_face_centers, compute_face_normals
from xadrez.graphics.particles import ParticleSystem
from xadrez.graphics.vector import Vector2D

MARKER_DOT = "dot"
MARKER_RING = "ring"
MARKER_CORNERS = "corners"
MARKER_TRIANGLE = "triangle"

_SPRITE_SUPERSAMPLE = 3
_BOARD_SUPERSAMPLE = 2
_ICON_SUPERSAMPLE = 4
_SPRITE_PADDING = 2
_MAX_RASTER_COORD = 16000
_DEPTH_RANK_STEP = 1000.0
_SURFACE_DEPTH = 32

_RIM_LIGHT_COLOR = np.array((168.0, 150.0, 128.0))
_RIM_DARK_COLOR = np.array((100.0, 108.0, 138.0))
_RIM_EXPONENT = 3
_GLOSS_LIGHT = 22.0
_GLOSS_DARK = 70.0
_GLOSS_EXPONENT = 34

_SHADOW_GRAY = (112, 112, 112)
_SHADOW_LIMIT = 4.5
_SHADOW_Y = 0.0
_SHADOW_PAINT_DIVISOR = 2
_SHADOW_BLUR_DIVISOR = 6
_SHADOW_SUPPORT_ANGLES = np.arange(24) * (2.0 * math.pi / 24)
_SHADOW_SUPPORT_DIRECTIONS = np.c_[np.cos(_SHADOW_SUPPORT_ANGLES), np.sin(_SHADOW_SUPPORT_ANGLES)]

_GLOW_RADIUS_LEVELS = 24
_GLOW_ALPHA_LEVELS = 10
_GLOW_COLOR_SHIFT = 3
_GLOW_MAX_ENTRIES = 4096
_GLOW_REACH = 2.3

_MARKER_LIFT = 0.008
_CELL_SPRITE_LIMIT = 2048
_CELL_COLOR_QUANTUM = 2
_MAX_SPRITES_PER_FRAME = 8
_ICON_MIN_EXTENT = 1.0
# Vista que deixa o focinho do cavalo para a direita, quase de perfil, com a luz do lado do olho.
_ICON_YAW = math.radians(130)
_ICON_LIGHT = DirectionalLight(direction=(-0.2, -0.75, 0.65), ambient=0.5, diffuse=0.85)
_SQUARE_POINT_COUNT = 64 * 4


class _Geometry(NamedTuple):
    """Estrutura de arrays de um conjunto de faces, em coordenadas de mundo."""

    homogeneous: np.ndarray  # (V, 4)
    faces: np.ndarray  # (F, 4)
    neighbors: np.ndarray  # (F, 4): face vizinha por aresta
    normals: np.ndarray  # (F, 3)
    centers: np.ndarray  # (F, 3)
    lit: np.ndarray  # (F, 3): Lambert e oclusão, que não dependem da câmera
    rim: np.ndarray  # (F, 3)
    gloss: np.ndarray  # (F,)


class _Polygons(NamedTuple):
    """Faces visíveis, já em pixels e com cor final."""

    quads: np.ndarray  # (K, 4, 2)
    colors: np.ndarray  # (K, 3)
    distances: np.ndarray  # (K,)
    faces: np.ndarray  # (K,): índice de cada polígono na geometria de origem
    on_silhouette: np.ndarray  # (K,): a face tem uma vizinha virada para trás


def _surface_finish(color: np.ndarray) -> tuple[np.ndarray, float]:
    """Acabamento pela cor: quanto mais escura a peça, mais brilho e contorno frio.

    É o que impede a peça de ébano de sumir contra a casa escura: a borda dela reflete a
    sala, como uma madeira polida.
    """
    darkness = 1.0 - (0.3 * color[0] + 0.59 * color[1] + 0.11 * color[2]) / 255.0
    rim = _RIM_LIGHT_COLOR * 0.34 + (_RIM_DARK_COLOR - _RIM_LIGHT_COLOR * 0.34) * darkness
    return rim, _GLOSS_LIGHT + (_GLOSS_DARK - _GLOSS_LIGHT) * darkness


def _build_geometry(mesh: Mesh, model_matrix: np.ndarray, color: np.ndarray, light: DirectionalLight) -> _Geometry:
    """Etapa Modelo -> Mundo.

    As normais vêm dos vértices já transformados, e não de (M^-1)^T, porque a escala 0 é um
    estado válido das animações, e aí M não tem inversa.
    """
    vertices = transform_points(model_matrix, mesh.vertices)
    normals = compute_face_normals(vertices, mesh.faces)
    centers = compute_face_centers(vertices, mesh.faces)
    lit = light.shade(normals, color) * mesh.face_shades[:, None]
    rim, gloss = _surface_finish(color)
    count = len(mesh.faces)
    homogeneous = np.empty((len(vertices), 4))
    homogeneous[:, :3] = vertices
    homogeneous[:, 3] = 1.0
    return _Geometry(homogeneous, mesh.faces, mesh.face_neighbors, normals, centers, lit,
                     np.broadcast_to(rim, (count, 3)), np.broadcast_to(gloss, (count,)))


def _concatenate_geometry(geometries: list[_Geometry]) -> _Geometry:
    """Junta várias geometrias: índices de vértice e de face precisam somar o deslocamento."""
    vertex_offsets = np.cumsum([0] + [len(g.homogeneous) for g in geometries[:-1]])
    face_offsets = np.cumsum([0] + [len(g.faces) for g in geometries[:-1]])
    return _Geometry(
        np.vstack([g.homogeneous for g in geometries]),
        np.vstack([g.faces + offset for g, offset in zip(geometries, vertex_offsets)]),
        np.vstack([g.neighbors + offset for g, offset in zip(geometries, face_offsets)]),
        np.vstack([g.normals for g in geometries]),
        np.vstack([g.centers for g in geometries]),
        np.vstack([g.lit for g in geometries]),
        np.vstack([g.rim for g in geometries]),
        np.concatenate([g.gloss for g in geometries]),
    )


def _visible_polygons(geometry: _Geometry, camera: Camera, light: DirectionalLight, lit=None) -> _Polygons:
    """Etapas Visão -> Recorte -> NDC -> Tela, para todas as faces de uma vez.

    Corte de faces traseiras: a face só é visível se a normal aponta para o olho, ou seja,
    n.(olho - centro) > 0. Isso elimina cerca de metade dos polígonos.
    Plano near: a face inteira sai se algum vértice tiver w <= near. Dividir por w um ponto
    atrás da câmera inverteria a imagem.
    Divisão perspectiva: ndc = clip / w. É ela que encolhe o que está longe.
    """
    to_eye = camera.eye - geometry.centers
    is_front = (geometry.normals * to_eye).sum(axis=1) > 0.0
    front_faces = np.flatnonzero(is_front)
    faces = geometry.faces[front_faces]
    clip = geometry.homogeneous @ camera.view_projection_matrix.T
    w = clip[:, 3]
    if w.min() <= NEAR_PLANE:
        ahead = (w[faces] > NEAR_PLANE).all(axis=1)
        front_faces, faces = front_faces[ahead], faces[ahead]
    to_screen = camera.viewport_matrix
    scale = (to_screen[0, 0], to_screen[1, 1])
    offset = (to_screen[0, 3], to_screen[1, 3])
    pixels = clip[:, :2] / np.maximum(w, 1e-6)[:, None] * scale + offset
    front_to_eye = to_eye[front_faces]
    distances = np.sqrt((front_to_eye * front_to_eye).sum(axis=1))
    colors = _final_colors(geometry, front_faces, front_to_eye, distances, light, lit)
    on_silhouette = ~is_front[geometry.neighbors[front_faces]].all(axis=1)
    return _Polygons(pixels[faces], colors, distances, front_faces, on_silhouette)


def _final_colors(geometry: _Geometry, indices, to_eye, distances, light: DirectionalLight, lit) -> np.ndarray:
    """Soma à parte difusa os termos que dependem da câmera: borda e brilho.

    Borda (fresnel simplificado): (1 - n.v)^3 é forte onde a face está de raspão ao olho.
    Brilho (Blinn-Phong): (n.h)^k, em que h é o meio do caminho entre a luz e o olho.
    Separar estes termos permite reaproveitar `lit` enquanto a peça estiver parada.
    """
    view = to_eye / np.maximum(distances, 1e-9)[:, None]
    normals = geometry.normals[indices]
    n_dot_v = np.maximum((normals * view).sum(axis=1), 0.0)
    rim_amount = (1.0 - n_dot_v) ** _RIM_EXPONENT
    half_vector = view + light.to_light
    half_vector /= np.maximum(np.sqrt((half_vector * half_vector).sum(axis=1, keepdims=True)), 1e-9)
    gloss_amount = np.maximum((normals * half_vector).sum(axis=1), 0.0) ** _GLOSS_EXPONENT
    base = geometry.lit if lit is None else lit
    colors = base[indices] + geometry.rim[indices] * rim_amount[:, None]
    colors += (geometry.gloss[indices] * gloss_amount)[:, None]
    return np.clip(colors, 0.0, 255.0).astype(np.uint8)


def _rasterize(surface: pygame.Surface, quads: np.ndarray, colors: np.ndarray, smooth_edges=None) -> int:
    """Desenha polígonos na ordem dada. Este laço é o último gargalo do pipeline.

    `smooth_edges` marca os polígonos que ganham contorno anti-aliased logo depois do
    preenchimento, antes que o próximo polígono os cubra.
    """
    points = np.clip(np.rint(quads), -_MAX_RASTER_COORD, _MAX_RASTER_COORD).astype(np.int32).tolist()
    rgb = colors.tolist()
    draw_polygon = pygame.draw.polygon
    if smooth_edges is None:
        for corners, color in zip(points, rgb):
            draw_polygon(surface, color, corners)
        return len(points)
    draw_outline = pygame.gfxdraw.aapolygon
    for corners, color, is_smooth in zip(points, rgb, smooth_edges.tolist()):
        draw_polygon(surface, color, corners)
        if is_smooth:
            draw_outline(surface, corners, color)
    return len(points)


class _Sprite:
    """Peça já desenhada, com alpha nas bordas, e as silhuetas usadas para o tint."""

    __slots__ = ("surface", "topleft", "_tint_overlays")

    def __init__(self, surface: pygame.Surface, topleft: tuple[int, int]):
        self.surface = surface
        self.topleft = topleft
        self._tint_overlays: dict[tuple[int, int, int], pygame.Surface] = {}

    def tint_overlay(self, tint: tuple[int, int, int]) -> pygame.Surface:
        """Silhueta na cor do tint. Desenhar por cima com alpha a dá c' = c (1 - a) + t a.

        É a mesma mistura do modo por polígonos, mas custa um blit e não refaz a malha.
        """
        overlay = self._tint_overlays.get(tint)
        if overlay is None:
            overlay = self.surface.copy()
            overlay.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            overlay.fill((*tint, 0), special_flags=pygame.BLEND_RGBA_ADD)
            self._tint_overlays[tint] = overlay
        return overlay


class _Instance:
    """Malha posicionada no mundo. Enquanto a peça não se move, tudo aqui continua valendo."""

    __slots__ = ("layout", "geometry", "anchor", "_shadow_matrix", "_shadow_outline", "sprite", "sprite_revision")

    def __init__(self, mesh: Mesh, model_matrix: np.ndarray, color, light: DirectionalLight, shadow_matrix: np.ndarray):
        self.layout = (id(mesh), tuple(color))
        self.geometry = _build_geometry(mesh, model_matrix, np.asarray(color, dtype=float), light)
        self.anchor = self.geometry.homogeneous[:, :3].mean(axis=0)
        self._shadow_matrix = shadow_matrix
        self._shadow_outline: np.ndarray | None = None
        self.sprite: _Sprite | None = None
        self.sprite_revision = -1

    @property
    def shadow_outline(self) -> np.ndarray:
        """Contorno da sombra: vértices achatados pela matriz de sombra, reduzidos a um polígono.

        Em cada uma de K direções, fica o ponto de suporte, aquele de maior produto escalar
        com a direção. Em ordem de ângulo, eles formam um polígono convexo inscrito no fecho
        convexo. Desenhar um polígono por peça custa dezenas de vezes menos que um por face,
        e com a borda suavizada da máscara a forma fica praticamente a mesma.
        """
        if self._shadow_outline is None:
            flattened = transform_points(self._shadow_matrix, self.geometry.homogeneous[:, :3])
            support = (flattened[:, [0, 2]] @ _SHADOW_SUPPORT_DIRECTIONS.T).argmax(axis=0)
            self._shadow_outline = flattened[support]
        return self._shadow_outline


class _DrawItem(NamedTuple):
    instance: _Instance
    tint: tuple[int, int, int] | None
    tint_amount: float
    casts_shadow: bool


def _apply_tint(lit: np.ndarray, item: _DrawItem) -> np.ndarray:
    """Mistura o tint nas faces da peça marcada: c' = c (1 - a) + t a. Não refaz a malha."""
    return lit * (1.0 - item.tint_amount) + np.array(item.tint, dtype=float) * item.tint_amount


class _SceneBatch:
    """Todas as peças do quadro em um único array, para gastar só uma chamada de numpy.

    Quando a composição da cena é a mesma e só uma peça se moveu, basta sobrescrever o
    trecho dela: refazer a concatenação inteira custaria dez vezes mais.
    """

    def __init__(self, instances: list[_Instance]):
        geometries = [instance.geometry for instance in instances]
        face_counts = [len(g.faces) for g in geometries]
        self.instances = list(instances)
        self.layout = [instance.layout for instance in instances]
        self.geometry = _concatenate_geometry(geometries)
        self.face_object = np.repeat(np.arange(len(geometries)), face_counts)
        self.face_starts = np.cumsum(np.r_[0, face_counts])
        self.vertex_starts = np.cumsum(np.r_[0, [len(g.homogeneous) for g in geometries]])
        self.anchors = np.array([instance.anchor for instance in instances])

    def refresh(self, instances: list[_Instance]) -> None:
        for index, instance in enumerate(instances):
            if instance is not self.instances[index]:
                self._overwrite(index, instance)

    def _overwrite(self, index: int, instance: _Instance) -> None:
        source, target = instance.geometry, self.geometry
        vertices = slice(self.vertex_starts[index], self.vertex_starts[index + 1])
        faces = slice(self.face_starts[index], self.face_starts[index + 1])
        target.homogeneous[vertices] = source.homogeneous
        target.normals[faces] = source.normals
        target.centers[faces] = source.centers
        target.lit[faces] = source.lit
        self.anchors[index] = instance.anchor
        self.instances[index] = instance


class _ShadowLayer:
    """Máscara de sombras em tons de cinza, multiplicada de uma vez sobre o tabuleiro.

    Polígonos que se sobrepõem na máscara pintam o mesmo cinza, e cada pixel é multiplicado
    uma só vez. Logo, duas sombras nunca escurecem em dobro.
    Suavização: pinta em meia resolução, reduz (média) e amplia de volta (bilinear). A última
    ampliação até o tamanho final é por vizinho mais próximo, porque o gradiente já está
    suave e isso custa bem menos que filtrar a área inteira.
    As superfícies têm o tamanho do viewport e só o recorte necessário é usado, para não
    alocar memória quando a área do tabuleiro muda enquanto a câmera gira.
    """

    def __init__(self):
        self._capacity = (0, 0)
        self._painted: pygame.Surface | None = None
        self._blurred: pygame.Surface | None = None
        self._soft: pygame.Surface | None = None
        self._full: pygame.Surface | None = None
        self.mask: pygame.Surface | None = None

    def _ensure_surfaces(self, capacity: tuple[int, int]) -> None:
        if capacity == self._capacity:
            return
        half = _divided_size(capacity, _SHADOW_PAINT_DIVISOR)
        self._painted = pygame.Surface(half, 0, _SURFACE_DEPTH)
        self._blurred = pygame.Surface(_divided_size(capacity, _SHADOW_BLUR_DIVISOR), 0, _SURFACE_DEPTH)
        self._soft = pygame.Surface(half, 0, _SURFACE_DEPTH)
        self._full = pygame.Surface(capacity, 0, _SURFACE_DEPTH)
        self._capacity = capacity

    def paint(self, outlines_on_screen: np.ndarray, bounds: pygame.Rect, capacity: tuple[int, int]) -> None:
        """Recebe (N, K, 2) em pixels de tela. O resultado fica em `mask`."""
        self._ensure_surfaces(capacity)
        half = _divided_size(bounds.size, _SHADOW_PAINT_DIVISOR)
        painted = self._painted.subsurface((0, 0), half)
        blurred = self._blurred.subsurface((0, 0), _divided_size(bounds.size, _SHADOW_BLUR_DIVISOR))
        soft = self._soft.subsurface((0, 0), half)
        self.mask = self._full.subsurface((0, 0), bounds.size)
        painted.fill((255, 255, 255))
        for polygon in ((outlines_on_screen - bounds.topleft) / _SHADOW_PAINT_DIVISOR).tolist():
            pygame.draw.polygon(painted, _SHADOW_GRAY, polygon)
        pygame.transform.smoothscale(painted, blurred.get_size(), blurred)
        pygame.transform.smoothscale(blurred, half, soft)
        pygame.transform.scale(soft, bounds.size, self.mask)


def _divided_size(size: tuple[int, int], divisor: int) -> tuple[int, int]:
    return max(size[0] // divisor, 1), max(size[1] // divisor, 1)


class _GlowSprites(dict):
    """Sprites de partícula sob demanda: um para cada raio, alpha e cor discretos."""

    def __missing__(self, code: int) -> pygame.Surface:
        if len(self) >= _GLOW_MAX_ENTRIES:
            self.clear()
        radius = code & 0x1F
        alpha = ((code >> 5) & 0xF) / (_GLOW_ALPHA_LEVELS - 1)
        color = np.array(((code >> 19) & 0x1F, (code >> 14) & 0x1F, (code >> 9) & 0x1F)) << _GLOW_COLOR_SHIFT
        sprite = self[code] = _render_glow(radius, color * alpha)
        return sprite


def _render_glow(radius: int, color: np.ndarray) -> pygame.Surface:
    """Brilho radial exp(-d^2) somado a um miolo claro, desenhado depois em blend aditivo."""
    span = np.arange(-radius, radius + 1, dtype=float)
    squared = (span[:, None] ** 2 + span[None, :] ** 2) / max(radius, 1) ** 2
    halo = np.exp(-squared * _GLOW_REACH)
    core = np.exp(-squared * 12.0) * 0.5 * color.max()
    pixels = color[None, None, :] * halo[..., None] + core[..., None]
    return pygame.surfarray.make_surface(np.clip(pixels, 0.0, 255.0).astype(np.uint8))


class Renderer3D:
    """Recebe a cena de um quadro com `add_*` e desenha tudo em `flush`."""

    def __init__(self, camera: Camera, light: DirectionalLight | None = None):
        self.camera = camera
        self._light = light or DirectionalLight()
        self._shadow_matrix = planar_shadow(self._light.direction, _SHADOW_Y)
        self._board = build_board_geometry()
        self._board_points = np.vstack(
            (self._board.square_corners.reshape(-1, 3), self._board.grain_corners.reshape(-1, 3))
        )
        self._frame_parts = build_frame_parts()
        self._frame_geometry: _Geometry | None = None
        self._target: pygame.Surface | None = None
        self._board_rgb: np.ndarray | None = None
        self._items: list[_DrawItem] = []
        self._markers: list[tuple[int, int, str, tuple]] = []
        self._particle_systems: list[ParticleSystem] = []
        self._instances: dict[tuple, _Instance] = {}
        self._used_instances: dict[tuple, _Instance] = {}
        self._batch: _SceneBatch | None = None
        self._backdrop: pygame.Surface | None = None
        self._board_layer: pygame.Surface | None = None
        self._board_layer_rgb: np.ndarray | None = None
        self._layer_revision = -1
        self._last_revision = -1
        self._shadow_layer = _ShadowLayer()
        self._shadow_key: tuple | None = None
        self._cell_masks: dict[tuple[int, int], tuple[pygame.Surface, tuple[int, int]]] = {}
        self._cell_sprites: dict[tuple, pygame.Surface] = {}
        self._cell_cache_revision = -1
        self._marker_sprites: dict[tuple, tuple[pygame.Surface, tuple[int, int]]] = {}
        self._marker_cache_revision = -1
        self._glow_sprites = _GlowSprites()
        self._icons: dict[tuple, pygame.Surface] = {}
        self.polygons_drawn = 0
        self.sprites_built = 0

    @property
    def light(self) -> DirectionalLight:
        return self._light

    @light.setter
    def light(self, value: DirectionalLight) -> None:
        self._light = value
        self._shadow_matrix = planar_shadow(value.direction, _SHADOW_Y)
        self._instances.clear()
        self._frame_geometry = None
        self._layer_revision = -1
        self._shadow_key = None

    def begin(self, surface: pygame.Surface) -> None:
        self._target = surface
        self._board_rgb = None
        self._items.clear()
        self._markers.clear()
        self._particle_systems.clear()
        self._used_instances = {}
        self.polygons_drawn = 0
        self.sprites_built = 0

    def draw_board(self, rgb_matrix: np.ndarray) -> None:
        """Define a matriz (8, 8, 3) de cores das casas neste quadro."""
        self._board_rgb = rgb_matrix

    def add_mesh(self, mesh: Mesh, model_matrix: np.ndarray, color, tint=None, tint_amount: float = 0.0,
                 cast_shadow: bool = True) -> None:
        """Agenda uma malha. Se a mesma peça já estava no mesmo lugar, reaproveita o que calculou."""
        key = (id(mesh), model_matrix.tobytes(), tuple(color))
        instance = self._instances.get(key)
        if instance is None:
            instance = _Instance(mesh, model_matrix, color, self._light, self._shadow_matrix)
        self._used_instances[key] = instance
        tint = (int(tint[0]), int(tint[1]), int(tint[2])) if tint is not None and tint_amount > 0.0 else None
        self._items.append(_DrawItem(instance, tint, float(tint_amount), cast_shadow))

    def add_marker(self, file: int, rank: int, kind: str, color) -> None:
        """Agenda uma forma sobre a casa: o estado não depende só de cor (RNF04)."""
        self._markers.append((file, rank, kind, tuple(color)))

    def add_particles(self, system: ParticleSystem) -> None:
        self._particle_systems.append(system)

    def flush(self) -> None:
        """Desenha o quadro, de trás para a frente: fundo, casas, sombras, marcadores, peças e partículas.

        Se a câmera não mudou desde o último quadro, usa camadas e sprites prontos. Enquanto ela
        se move, os dois caches seriam jogados fora a cada quadro, então desenha polígonos.
        """
        target = self._target
        if target is None:
            return
        previous_clip = target.get_clip()
        target.set_clip(pygame.Rect(self.camera.viewport))
        is_parked = self.camera.revision == self._last_revision
        self._last_revision = self.camera.revision
        if is_parked:
            has_baked = self._draw_parked_board()
            self._draw_shadows()
            # Refazer a camada já consome o quadro: os sprites começam no próximo.
            if has_baked:
                self._draw_marker_polygons()
                self._draw_objects_as_polygons()
            else:
                self._draw_marker_sprites()
                self._draw_objects_as_sprites()
        else:
            self._draw_board_polygons()
            self._draw_shadows()
            self._draw_marker_polygons()
            self._draw_objects_as_polygons()
        self._draw_particles()
        target.set_clip(previous_clip)
        self._instances = self._used_instances

    def _viewport_backdrop(self) -> pygame.Surface:
        _, _, width, height = self.camera.viewport
        if self._backdrop is None or self._backdrop.get_size() != (width, height):
            self._backdrop = render_backdrop(width, height)
        return self._backdrop

    def _frame(self) -> _Geometry:
        """Moldura de madeira fosca: sem borda nem brilho, que lavariam a cor nas faces de raspão."""
        if self._frame_geometry is None:
            matte = _concatenate_geometry([
                _build_geometry(mesh, identity(), np.asarray(color, dtype=float), self._light)
                for mesh, color in self._frame_parts
            ])
            self._frame_geometry = matte._replace(rim=np.zeros_like(matte.rim), gloss=np.zeros_like(matte.gloss))
        return self._frame_geometry

    def _board_polygons(self, rgb: np.ndarray | None, with_grain: bool) -> tuple[np.ndarray, np.ndarray]:
        """Polígonos do tabuleiro, na ordem de pintura: moldura, casas e, por cima, os veios.

        Nada nessa lista se cobre, exceto o veio sobre a sua casa, então a ordem fixa basta e
        não gasta ordenação.
        """
        frame = _visible_polygons(self._frame(), self.camera, self._light)
        if rgb is None:
            return frame.quads, frame.colors
        points = self._board_points if with_grain else self._board_points[:_SQUARE_POINT_COUNT]
        pixels, _ = self.camera.project(points)
        square_rgb = rgb * self._board.square_light[..., None]
        colors = [frame.colors, np.clip(square_rgb.reshape(-1, 3), 0.0, 255.0)]
        if with_grain:
            owner = self._board.grain_square
            grain_rgb = square_rgb[owner[:, 0], owner[:, 1]] * self._board.grain_shades[:, None]
            colors.append(np.clip(grain_rgb, 0.0, 255.0))
        return np.vstack((frame.quads, pixels.reshape(-1, 4, 2))), np.vstack(colors).astype(np.uint8)

    def _draw_board_polygons(self) -> None:
        """Em movimento, os veios ficam de fora: são finos demais para serem vistos."""
        x, y, _, _ = self.camera.viewport
        self._target.blit(self._viewport_backdrop(), (x, y))
        quads, colors = self._board_polygons(self._board_rgb, with_grain=False)
        self.polygons_drawn += _rasterize(self._target, quads, colors, np.ones(len(quads), dtype=bool))

    def _draw_parked_board(self) -> bool:
        """Desenha a camada estática e devolve se ela precisou ser refeita neste quadro."""
        is_stale = self._layer_revision != self.camera.revision or self._board_layer is None
        needs_bake = is_stale or (self._board_rgb is None) != (self._board_layer_rgb is None)
        if needs_bake:
            self._bake_board_layer()
        x, y, _, _ = self.camera.viewport
        self._target.blit(self._board_layer, (x, y))
        self._draw_changed_squares()
        return needs_bake

    def _bake_board_layer(self) -> None:
        """Camada estática: fundo e tabuleiro, superamostrados só na região do tabuleiro.

        Ampliar o fundo pelo vizinho mais próximo e depois reduzir com média devolve os
        mesmos pixels, então nenhuma borda aparece onde a região termina.
        """
        backdrop = self._viewport_backdrop()
        if self._board_layer is None or self._board_layer.get_size() != backdrop.get_size():
            self._board_layer = backdrop.copy()
        else:
            self._board_layer.blit(backdrop, (0, 0))
        layer = self._board_layer
        quads, colors = self._board_polygons(self._board_rgb, with_grain=True)
        quads = quads - self.camera.viewport[:2]
        bounds = _pixel_bounds(quads, layer.get_rect())
        if bounds.w > 0 and bounds.h > 0:
            region = layer.subsurface(bounds)
            scale = _BOARD_SUPERSAMPLE
            canvas = pygame.transform.scale(region, (bounds.w * scale, bounds.h * scale))
            self.polygons_drawn += _rasterize(canvas, (quads - bounds.topleft) * scale, colors)
            pygame.transform.smoothscale(canvas, bounds.size, region)
        self._board_layer_rgb = None if self._board_rgb is None else np.array(self._board_rgb)
        self._layer_revision = self.camera.revision

    def _draw_changed_squares(self) -> None:
        """Casas cuja cor mudou desde a camada: em geral poucas, mesmo com o pulso ativo."""
        rgb, baked = self._board_rgb, self._board_layer_rgb
        if rgb is None:
            return
        changed = np.argwhere((rgb != baked).any(axis=2))
        if changed.size == 0:
            return
        if self._cell_cache_revision != self.camera.revision:
            self._cell_masks.clear()
            self._cell_sprites.clear()
            self._cell_cache_revision = self.camera.revision
        for file, rank in changed.tolist():
            sprite, topleft = self._square_sprite(file, rank, rgb[file, rank])
            self._target.blit(sprite, topleft)

    def _square_sprite(self, file: int, rank: int, color: np.ndarray) -> tuple[pygame.Surface, tuple[int, int]]:
        """Casa na cor pedida: máscara com veios e borda suave, multiplicada pela cor.

        A cor é discretizada para que o pulso, depois de um ciclo, só leia do cache.
        """
        lit = np.clip(color * self._board.square_light[file, rank], 0, 255).astype(np.uint8) // _CELL_COLOR_QUANTUM
        key = (file, rank, *lit.tolist())
        mask, topleft = self._square_mask(file, rank)
        sprite = self._cell_sprites.get(key)
        if sprite is None:
            if len(self._cell_sprites) >= _CELL_SPRITE_LIMIT:
                self._cell_sprites.clear()
            sprite = mask.copy()
            sprite.fill((*(lit * _CELL_COLOR_QUANTUM).tolist(), 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._cell_sprites[key] = sprite
        return sprite, topleft

    def _square_mask(self, file: int, rank: int) -> tuple[pygame.Surface, tuple[int, int]]:
        cached = self._cell_masks.get((file, rank))
        if cached is not None:
            return cached
        corners = self._board.square_corners[file, rank]
        owned = np.all(self._board.grain_square == (file, rank), axis=1)
        grain_corners = self._board.grain_corners[owned].reshape(-1, 3)
        pixels, _ = self.camera.project(np.vstack((corners, grain_corners)))
        grain_gray = np.rint(255.0 * self._board.grain_shades[owned])[:, None] * np.ones((1, 3))
        colors = np.vstack(((255, 255, 255), grain_gray)).astype(np.uint8)
        cached = self._cell_masks[(file, rank)] = _render_alpha_sprite(pixels.reshape(-1, 4, 2), colors, (255, 255, 255))
        return cached

    def _shadow_bounds(self) -> pygame.Rect:
        limit = _SHADOW_LIMIT
        corners = np.array([(-limit, 0.0, -limit), (limit, 0.0, -limit), (limit, 0.0, limit), (-limit, 0.0, limit)])
        pixels, _ = self.camera.project(corners)
        return _pixel_bounds(pixels[None, ...], pygame.Rect(self.camera.viewport))

    def _draw_shadows(self) -> None:
        """Só repinta a máscara quando a câmera ou alguma peça que projeta sombra muda."""
        casters = [item.instance for item in self._items if item.casts_shadow]
        if not casters:
            return
        bounds = self._shadow_bounds()
        if bounds.w <= 0 or bounds.h <= 0:
            return
        key = (self.camera.revision, tuple(map(id, casters)))
        if key != self._shadow_key:
            # Recorta no limite da moldura: a sombra não cai para fora do tabuleiro.
            outlines = np.clip([caster.shadow_outline for caster in casters], -_SHADOW_LIMIT, _SHADOW_LIMIT)
            pixels, _ = self.camera.project(outlines.reshape(-1, 3))
            capacity = self.camera.viewport[2:]
            self._shadow_layer.paint(pixels.reshape(len(casters), -1, 2), bounds, capacity)
            self._shadow_key = key
            self.polygons_drawn += len(casters)
        self._target.blit(self._shadow_layer.mask, bounds.topleft, None, pygame.BLEND_RGB_MULT)

    def _marker_polygons(self, file: int, rank: int, kind: str) -> list[np.ndarray]:
        return [self.camera.project(polygon)[0] for polygon in _marker_world_polygons(file, rank, kind)]

    def _draw_marker_polygons(self) -> None:
        for file, rank, kind, color in self._markers:
            for polygon in self._marker_polygons(file, rank, kind):
                points = np.rint(polygon).astype(np.int32).tolist()
                pygame.gfxdraw.filled_polygon(self._target, points, color)
                self.polygons_drawn += 1

    def _draw_marker_sprites(self) -> None:
        if not self._markers:
            return
        if self._marker_cache_revision != self.camera.revision:
            self._marker_sprites.clear()
            self._marker_cache_revision = self.camera.revision
        for marker in self._markers:
            cached = self._marker_sprites.get(marker)
            if cached is None:
                cached = self._marker_sprites[marker] = self._render_marker(*marker)
            self._target.blit(*cached)

    def _render_marker(self, file: int, rank: int, kind: str, color: tuple) -> tuple[pygame.Surface, tuple[int, int]]:
        sprite, topleft = _render_flat_sprite(self._marker_polygons(file, rank, kind), color[:3])
        if len(color) > 3:
            sprite.set_alpha(int(color[3]))
        return sprite, topleft

    def _object_paint_ranks(self, batch: _SceneBatch) -> np.ndarray:
        """Posto de cada objeto na pintura: 0 é o mais distante do olho."""
        offset = batch.anchors - self.camera.eye
        order = np.argsort(-(offset * offset).sum(axis=1))
        ranks = np.empty(len(order), dtype=np.int64)
        ranks[order] = np.arange(len(order))
        return ranks

    def _current_batch(self) -> _SceneBatch | None:
        if not self._items:
            return None
        instances = [item.instance for item in self._items]
        batch = self._batch
        if batch is not None and batch.layout == [instance.layout for instance in instances]:
            batch.refresh(instances)
        else:
            batch = self._batch = _SceneBatch(instances)
        return batch

    def _tinted_lit(self, batch: _SceneBatch) -> np.ndarray | None:
        tinted = [(i, item) for i, item in enumerate(self._items) if item.tint is not None]
        if not tinted:
            return None
        lit = batch.geometry.lit.copy()
        for index, item in tinted:
            faces = slice(batch.face_starts[index], batch.face_starts[index + 1])
            lit[faces] = _apply_tint(lit[faces], item)
        return lit

    def _draw_objects_as_polygons(self) -> None:
        """Modo de câmera em movimento: um único array para a cena toda.

        Ordem do pintor em dois níveis: primeiro o objeto, pela distância do centro dele ao
        olho, depois a face dentro do objeto. Olhar só a distância de cada face erraria
        quando a peça alta de trás tem o topo mais perto do olho que a base da peça da frente.
        """
        batch = self._current_batch()
        if batch is None:
            return
        polygons = _visible_polygons(batch.geometry, self.camera, self._light, self._tinted_lit(batch))
        object_rank = self._object_paint_ranks(batch)[batch.face_object[polygons.faces]]
        order = np.argsort(object_rank * _DEPTH_RANK_STEP - polygons.distances)
        self.polygons_drawn += _rasterize(
            self._target, polygons.quads[order], polygons.colors[order], polygons.on_silhouette[order]
        )

    def _draw_objects_as_sprites(self) -> None:
        """Modo de câmera parada: um blit por peça, na ordem do pintor.

        Logo depois que a câmera para, nenhuma peça tem sprite. Refazer todos de uma vez
        travaria o quadro, então cada quadro faz só alguns, e as outras peças seguem por
        polígonos, com aparência quase igual. A nitidez chega em poucos quadros.
        """
        batch = self._current_batch()
        if batch is None:
            return
        budget = _MAX_SPRITES_PER_FRAME
        for index in np.argsort(self._object_paint_ranks(batch)).tolist():
            item = self._items[index]
            if item.instance.sprite_revision == self.camera.revision:
                self._blit_item(item)
            elif budget > 0:
                budget -= 1
                self._blit_item(item)
            else:
                self._draw_item_polygons(item)

    def _draw_item_polygons(self, item: _DrawItem) -> None:
        geometry = item.instance.geometry
        lit = None if item.tint is None else _apply_tint(geometry.lit, item)
        polygons = _visible_polygons(geometry, self.camera, self._light, lit)
        order = np.argsort(-polygons.distances)
        self.polygons_drawn += _rasterize(
            self._target, polygons.quads[order], polygons.colors[order], polygons.on_silhouette[order]
        )

    def _blit_item(self, item: _DrawItem) -> None:
        sprite = self._sprite_of(item.instance)
        if sprite is None:
            return
        self._target.blit(sprite.surface, sprite.topleft)
        if item.tint is not None:
            overlay = sprite.tint_overlay(item.tint)
            overlay.set_alpha(int(255 * min(item.tint_amount, 1.0)))
            self._target.blit(overlay, sprite.topleft)

    def _sprite_of(self, instance: _Instance) -> _Sprite | None:
        if instance.sprite_revision != self.camera.revision:
            instance.sprite = self._build_sprite(instance)
            instance.sprite_revision = self.camera.revision
            self.sprites_built += 1
        return instance.sprite

    def _build_sprite(self, instance: _Instance) -> _Sprite | None:
        """Desenha a peça maior e reduz com filtro de média: cada pixel final é a média de 9."""
        polygons = _visible_polygons(instance.geometry, self.camera, self._light)
        if len(polygons.quads) == 0:
            return None
        order = np.argsort(-polygons.distances)
        average_color = polygons.colors.mean(axis=0).astype(int).tolist()
        surface, topleft = _render_alpha_sprite(polygons.quads[order], polygons.colors[order], average_color)
        self.polygons_drawn += len(polygons.quads)
        return _Sprite(surface, topleft)

    def _draw_particles(self) -> None:
        for system in self._particle_systems:
            if system.alive_count > 0:
                self._draw_particle_system(system)

    def _draw_particle_system(self, system: ParticleSystem) -> None:
        """Cada partícula é um sprite de brilho em blend aditivo: luz soma, nunca escurece.

        Tamanho em perspectiva: raio_em_pixels = tamanho f / profundidade. Os sprites vêm de
        um cache indexado por raio, alpha e cor discretos, então o custo de cada partícula é
        só uma entrada na lista de `Surface.blits`.
        """
        pixels, depth = self.camera.project(system.positions)
        ahead = np.flatnonzero(depth > NEAR_PLANE)
        radius_world = system.sizes[ahead] * self.camera.focal_pixels / depth[ahead]
        radius = np.clip(np.rint(radius_world), 1, _GLOW_RADIUS_LEVELS).astype(np.int64)
        alpha = np.clip(system.alphas[ahead] * (_GLOW_ALPHA_LEVELS - 1), 0, _GLOW_ALPHA_LEVELS - 1).astype(np.int64)
        color = np.clip(system.colors[ahead], 0, 255).astype(np.int64) >> _GLOW_COLOR_SHIFT
        codes = radius | alpha << 5 | color[:, 0] << 19 | color[:, 1] << 14 | color[:, 2] << 9
        topleft = (pixels[ahead] - radius[:, None]).astype(np.int64).tolist()
        sprites = self._glow_sprites
        add = pygame.BLEND_RGB_ADD
        self._target.blits([(sprites[code], corner, None, add) for code, corner in zip(codes.tolist(), topleft)], False)

    def render_icon(self, mesh: Mesh, color, size: int) -> pygame.Surface:
        """Peça isolada em uma Surface com alpha, para o HUD. O resultado fica em cache."""
        key = (id(mesh), tuple(color), size)
        icon = self._icons.get(key)
        if icon is None:
            icon = self._icons[key] = _render_icon(mesh, np.asarray(color, dtype=float), size)
        return icon


def _render_icon(mesh: Mesh, color: np.ndarray, size: int) -> pygame.Surface:
    """Vista de perfil com pouca perspectiva, onde as seis peças têm a silhueta mais clara."""
    canvas_size = size * _ICON_SUPERSAMPLE
    fov = math.radians(16)
    half_extent = max(mesh.height, 2.0 * mesh.radius, _ICON_MIN_EXTENT) * 0.56
    distance = half_extent / math.tan(fov / 2.0)
    camera = Camera((0, 0, canvas_size, canvas_size), yaw=_ICON_YAW, pitch=math.radians(18),
                    distance=distance, fov_y=fov, target=(0.0, mesh.height / 2.0, 0.0))
    geometry = _build_geometry(mesh, identity(), color, _ICON_LIGHT)
    polygons = _visible_polygons(geometry, camera, _ICON_LIGHT)
    order = np.argsort(-polygons.distances)
    canvas = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
    canvas.fill((*polygons.colors.mean(axis=0).astype(int).tolist(), 0))
    _rasterize(canvas, polygons.quads[order], polygons.colors[order])
    return pygame.transform.smoothscale(canvas, (size, size))


def _pixel_bounds(quads: np.ndarray, limit: pygame.Rect) -> pygame.Rect:
    """Menor retângulo inteiro que contém os polígonos, com folga, recortado em `limit`."""
    low = np.floor(quads.min(axis=(0, 1))).astype(int) - _SPRITE_PADDING
    high = np.ceil(quads.max(axis=(0, 1))).astype(int) + _SPRITE_PADDING
    return pygame.Rect(int(low[0]), int(low[1]), int(high[0] - low[0]), int(high[1] - low[1])).clip(limit)


def _sprite_canvas(points: np.ndarray) -> tuple[pygame.Surface, np.ndarray, tuple[int, int]]:
    """Tela superamostrada que cabe nos pontos: devolve a tela, a origem e o tamanho final."""
    low = np.floor(points.min(axis=0)).astype(int) - _SPRITE_PADDING
    high = np.ceil(points.max(axis=0)).astype(int) + _SPRITE_PADDING
    width, height = (high - low).clip(1, _MAX_RASTER_COORD // _SPRITE_SUPERSAMPLE).tolist()
    canvas = pygame.Surface((width * _SPRITE_SUPERSAMPLE, height * _SPRITE_SUPERSAMPLE), pygame.SRCALPHA)
    return canvas, low, (width, height)


def _render_alpha_sprite(quads: np.ndarray, colors: np.ndarray, clear_color) -> tuple[pygame.Surface, tuple[int, int]]:
    """Polígonos em superamostragem sobre fundo transparente, reduzidos com média.

    O fundo tem a cor média da peça com alpha 0. Se fosse preto, a média escureceria as bordas.
    """
    canvas, low, size = _sprite_canvas(quads.reshape(-1, 2))
    canvas.fill((*clear_color, 0))
    _rasterize(canvas, (quads - low) * _SPRITE_SUPERSAMPLE, colors)
    return pygame.transform.smoothscale(canvas, size), (int(low[0]), int(low[1]))


def _render_flat_sprite(polygons: list[np.ndarray], color: tuple) -> tuple[pygame.Surface, tuple[int, int]]:
    """Polígonos de uma só cor e número livre de vértices, com a mesma suavização."""
    canvas, low, size = _sprite_canvas(np.vstack(polygons))
    canvas.fill((*color, 0))
    for polygon in polygons:
        pygame.draw.polygon(canvas, color, ((polygon - low) * _SPRITE_SUPERSAMPLE).tolist())
    return pygame.transform.smoothscale(canvas, size), (int(low[0]), int(low[1]))


def _circle_points(radius: float, segments: int, phase: float = 0.0) -> np.ndarray:
    start = Vector2D(radius, 0.0).rotated(phase)
    points = [start.rotated(2.0 * math.pi * i / segments) for i in range(segments)]
    return np.array([(p.x, p.y) for p in points])


@lru_cache(maxsize=512)
def _marker_world_polygons(file: int, rank: int, kind: str) -> list[np.ndarray]:
    center = np.array(square_to_world(file, rank)) + (0.0, _MARKER_LIFT, 0.0)
    return [center + np.column_stack((s[:, 0], np.zeros(len(s)), s[:, 1])) for s in _marker_shapes(kind)]


def _marker_shapes(kind: str) -> list[np.ndarray]:
    """Formas no plano da casa (x, z), em unidades de mundo."""
    if kind == MARKER_DOT:
        return [_circle_points(0.15, 18)]
    if kind == MARKER_RING:
        return [_ring_polygon(outer=0.47, inner=0.385, segments=28)]
    if kind == MARKER_CORNERS:
        return _corner_brackets(reach=0.47, arm=0.15, thickness=0.05)
    if kind == MARKER_TRIANGLE:
        return [_circle_points(0.19, 3, phase=-math.pi / 2.0) + (0.0, 0.03)]
    raise ValueError(f"Marcador desconhecido: {kind}")


def _ring_polygon(outer: float, inner: float, segments: int) -> np.ndarray:
    """Anel em um único polígono: contorno de fora, ponte e contorno de dentro ao contrário.

    O preenchimento por varredura segue a regra par-ímpar, então o miolo fica vazio.
    """
    outer_loop = _circle_points(outer, segments)
    inner_loop = _circle_points(inner, segments)
    return np.vstack((outer_loop, outer_loop[:1], inner_loop[:1], inner_loop[::-1]))


def _corner_brackets(reach: float, arm: float, thickness: float) -> list[np.ndarray]:
    """Quatro cantos em L, para o cursor e a seleção se destacarem em qualquer cor de casa."""
    inner = reach - thickness
    bracket = np.array([
        (reach, reach), (reach - arm, reach), (reach - arm, inner), (inner, inner), (inner, reach - arm), (reach, reach - arm),
    ])
    return [bracket * sign for sign in ((1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0))]
