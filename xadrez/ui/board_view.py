"""Apresentação 3D da partida: peças, destaques, animações, partículas e câmera.

Traduz os tipos do motor para os valores simples que `xadrez.graphics` espera. Decidir o que
destacar é da `GameScene`. Aqui só se desenha.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pygame

from xadrez.core import Board, Color, MoveOutcome
from xadrez.graphics import (
    EBONY,
    FACING_BLACK,
    FACING_WHITE,
    IVORY,
    MARKER_RING,
    Camera,
    CaptureAnimation,
    ColorMatrix,
    KingFallAnimation,
    Mesh,
    ParticleSystem,
    PieceAnimation,
    Renderer3D,
    SpawnAnimation,
    piece_matrix,
    square_to_world,
    translation,
)
from xadrez.ui import theme as tokens

Cell = tuple[int, int]

PIECE_COLORS = {Color.WHITE: IVORY, Color.BLACK: EBONY}
PIECE_FACING = {Color.WHITE: FACING_WHITE, Color.BLACK: FACING_BLACK}
SIDE_YAW = {Color.WHITE: 0.0, Color.BLACK: math.pi}

DEFAULT_PITCH = math.radians(52)
DEFAULT_DISTANCE = 16.5

_CAPTURE_MOMENT = 0.62
_LANDING_DUST_COLOR = (214, 186, 142)
# As lascas somam luz, então a cor de ébano sumiria sem este clareamento.
_SPARK_COLORS = {Color.WHITE: (240, 228, 200), Color.BLACK: (170, 140, 116)}
_ORBIT_SENSITIVITY_YAW = 0.006
_ORBIT_SENSITIVITY_PITCH = 0.004
_ZOOM_STEP = 0.92
_VIEW_RESET_SECONDS = 0.6
_SHAKE_SECONDS = 0.34
_SHAKE_AMPLITUDE = 0.07
_SHAKE_HERTZ = 15.0
_SELECTED_LIFT = translation(0.0, 0.09, 0.0)
_TINT_PULSE_HERTZ = 1.1
_TINT_LOW, _TINT_HIGH = 0.18, 0.5
_FIREWORK_HEIGHT = (2.4, 4.2)
_FIREWORK_SPREAD = 3.0
_BOARD_SQUARE_COUNT = 64
_FACING_TOLERANCE = 1e-6


@dataclass
class _Flight:
    """Peça no ar. A posição do motor já mudou, então a casa de destino fica escondida até o pouso."""

    mesh: Mesh
    color: tuple
    target: Cell
    animation: PieceAnimation


@dataclass
class _WaitingPiece:
    """Peça que espera o voo chegar: a capturada continua em pé, a promovida ainda não nasceu."""

    mesh: Mesh
    side: Color
    square: Cell

    @property
    def color(self) -> tuple:
        return PIECE_COLORS[self.side]


@dataclass
class _Effect:
    """Animação presa a uma casa. `hides_square` esconde a peça parada que o motor diz estar nela."""

    mesh: Mesh
    color: tuple
    square: Cell
    animation: CaptureAnimation | SpawnAnimation | KingFallAnimation
    hides_square: bool


@dataclass
class _PlacedPiece:
    square: Cell
    mesh: Mesh
    matrix: np.ndarray
    color: tuple


class _ViewReset:
    """Volta à vista padrão com giro, inclinação e zoom juntos, em um só movimento."""

    def __init__(self, camera: Camera, yaw: float):
        self._yaw_start = camera.yaw
        self._yaw_travel = (yaw - camera.yaw + math.pi) % (2.0 * math.pi) - math.pi
        self._pitch_start = camera.pitch
        self._distance_start = camera.distance
        self._elapsed = 0.0

    def advance(self, camera: Camera, dt: float) -> bool:
        """Aplica o trecho deste quadro e devolve se terminou."""
        self._elapsed = min(self._elapsed + dt, _VIEW_RESET_SECONDS)
        t = self._elapsed / _VIEW_RESET_SECONDS
        eased = t * t * (3.0 - 2.0 * t)
        yaw = self._yaw_start + self._yaw_travel * eased
        pitch = self._pitch_start + (DEFAULT_PITCH - self._pitch_start) * eased
        distance = self._distance_start + (DEFAULT_DISTANCE - self._distance_start) * eased
        camera.orbit_by(yaw - camera.yaw, pitch - camera.pitch)
        camera.zoom_by(distance / camera.distance)
        return t >= 1.0


class BoardView:
    def __init__(self, meshes: Mapping[str, Mesh], viewport=(0, 0, 1280, 720), seed: int | None = None):
        self.meshes = meshes
        self.camera = Camera(viewport)
        self.renderer = Renderer3D(self.camera)
        self.matrix = ColorMatrix(palette=tokens.BOARD_STATE_PALETTE)
        self.particles = ParticleSystem(seed=seed)
        self.time = 0.0
        self.markers: list[tuple] = []
        self.tints: dict[Cell, tuple] = {}
        self.lifted_square: Cell | None = None
        self.scene_polygons = _BOARD_SQUARE_COUNT
        self._rng = np.random.default_rng(seed)
        self._board: Board | None = None
        self._placed: list[_PlacedPiece] = []
        self._pickable: list[tuple[int, int, float]] = []
        self._view_reset: _ViewReset | None = None
        self.shake_square: Cell | None = None
        self._shake_elapsed = 0.0
        self._clear_animations()

    def _clear_animations(self) -> None:
        self._flights: list[_Flight] = []
        self._effects: list[_Effect] = []
        self._waiting_capture: _WaitingPiece | None = None
        self._waiting_spawn: _WaitingPiece | None = None
        self._fallen_king: _Effect | None = None
        self._has_landed = False

    def reset(self) -> None:
        """Esvazia o que sobrou da partida anterior, para reiniciar ou pedir revanche."""
        self._clear_animations()
        self.particles.alive_count = 0
        self.markers = []
        self.tints = {}
        self.lifted_square = None
        self.shake_square = None
        self.matrix.clear()

    # Posição -------------------------------------------------------------------------------------

    def sync(self, board: Board) -> None:
        """Refaz a lista de peças. Só precisa ser chamado quando a posição ou as animações mudam."""
        self._board = board
        hidden = self._hidden_squares()
        self._placed = []
        self._pickable = []
        for color in Color:
            for square, piece in board.pieces(color):
                self._place(tuple(square), self.meshes[piece.kind.value], color, hidden)
        self.scene_polygons = _BOARD_SQUARE_COUNT + sum(len(piece.mesh.faces) for piece in self._placed)

    def _place(self, cell: Cell, mesh: Mesh, color: Color, hidden: set[Cell]) -> None:
        self._pickable.append((*cell, mesh.height))
        if cell not in hidden:
            self._placed.append(_PlacedPiece(cell, mesh, piece_matrix(*cell, PIECE_FACING[color]), PIECE_COLORS[color]))

    def _hidden_squares(self) -> set[Cell]:
        hidden = {flight.target for flight in self._flights}
        hidden.update(effect.square for effect in self._effects if effect.hides_square)
        if self._waiting_spawn is not None:
            hidden.add(self._waiting_spawn.square)
        if self._fallen_king is not None:
            hidden.add(self._fallen_king.square)
        return hidden

    def piece_height_at(self, square: Cell) -> float:
        """Altura da peça na casa, ou zero se a casa estiver vazia."""
        cell = tuple(square)
        return next((height for file, rank, height in self._pickable if (file, rank) == cell), 0.0)

    def _resync(self) -> None:
        if self._board is not None:
            self.sync(self._board)

    # Câmera --------------------------------------------------------------------------------------

    def set_viewport(self, rect: pygame.Rect) -> None:
        self.camera.set_viewport(rect.x, rect.y, rect.width, rect.height)

    @property
    def is_camera_moving(self) -> bool:
        return self.camera.is_moving or self._view_reset is not None

    def face(self, color: Color) -> None:
        self._view_reset = None
        if not self._is_facing(SIDE_YAW[color]):
            self.camera.orbit_to(SIDE_YAW[color])

    def restore_default_view(self, color: Color) -> None:
        camera = self.camera
        is_default = math.isclose(camera.pitch, DEFAULT_PITCH) and math.isclose(camera.distance, DEFAULT_DISTANCE)
        self._view_reset = None if is_default and self._is_facing(SIDE_YAW[color]) else _ViewReset(camera, SIDE_YAW[color])

    def _is_facing(self, yaw: float) -> bool:
        """Girar para onde já se está só gastaria quadros refazendo a camada do tabuleiro."""
        travel = (yaw - self.camera.yaw + math.pi) % (2.0 * math.pi) - math.pi
        return not self.camera.is_moving and abs(travel) < _FACING_TOLERANCE

    def drag_orbit(self, dx: int, dy: int) -> None:
        self._view_reset = None
        self.camera.orbit_by(-dx * _ORBIT_SENSITIVITY_YAW, dy * _ORBIT_SENSITIVITY_PITCH)

    def zoom(self, wheel_steps: int) -> None:
        self._view_reset = None
        self.camera.zoom_by(_ZOOM_STEP**wheel_steps)

    def pick(self, position: tuple[int, int]) -> Cell | None:
        """Casa sob o pixel: testa o volume das peças e, se nada for tocado, o plano do tabuleiro."""
        return self.camera.pick_piece(position[0], position[1], self._pickable)

    # Animações -----------------------------------------------------------------------------------

    @property
    def is_flying(self) -> bool:
        return bool(self._flights)

    def start_move(self, outcome: MoveOutcome) -> None:
        move, side = outcome.move, outcome.piece.color
        self._flights = [self._flight(self.meshes[outcome.piece.kind.value], side, move.origin, move.target)]
        if outcome.rook_path is not None:
            self._flights.append(self._flight(self.meshes["rook"], side, *outcome.rook_path))
        if outcome.captured is not None:
            mesh = self.meshes[outcome.captured.kind.value]
            self._waiting_capture = _WaitingPiece(mesh, outcome.captured.color, tuple(outcome.captured_square))
        if outcome.promoted_to is not None:
            self._waiting_spawn = _WaitingPiece(self.meshes[outcome.promoted_to.value], side, tuple(move.target))
        self._resync()

    @staticmethod
    def _flight(mesh: Mesh, side: Color, origin, target) -> _Flight:
        animation = PieceAnimation(tuple(origin), tuple(target), facing=PIECE_FACING[side])
        return _Flight(mesh, PIECE_COLORS[side], tuple(target), animation)

    def start_king_fall(self, square: Cell, side: Color, away_from: Cell | None) -> None:
        """Tomba o rei derrotado para o lado oposto ao da peça que deu o mate."""
        cell = tuple(square)
        direction = _fall_direction(cell, away_from)
        animation = KingFallAnimation(cell, direction=direction, facing=PIECE_FACING[side])
        self._fallen_king = _Effect(self.meshes["king"], PIECE_COLORS[side], cell, animation, hides_square=True)
        self._resync()

    def launch_fireworks(self, colors: Sequence[tuple[int, int, int]]) -> None:
        spread = self._rng.uniform(-_FIREWORK_SPREAD, _FIREWORK_SPREAD, 2)
        height = self._rng.uniform(*_FIREWORK_HEIGHT)
        self.particles.victory_fireworks((spread[0], height, spread[1]), colors)

    def shake(self, square: Cell | None) -> None:
        """Tremor curto na casa recusada: a peça treme, e a casa ganha um anel de recusa."""
        self.shake_square = None if square is None else tuple(square)
        self._shake_elapsed = 0.0

    def consume_landing(self) -> bool:
        """Diz, uma vez só, que o voo terminou. Quem chama reage ao fim do lance."""
        has_landed, self._has_landed = self._has_landed, False
        return has_landed

    def update(self, dt: float) -> None:
        self.time += dt
        self.camera.update(dt)
        self._advance_view_reset(dt)
        self._advance_flights(dt)
        self._advance_effects(dt)
        self._advance_shake(dt)
        self.particles.update(dt)

    def _advance_view_reset(self, dt: float) -> None:
        if self._view_reset is not None and self._view_reset.advance(self.camera, dt):
            self._view_reset = None

    def _advance_flights(self, dt: float) -> None:
        if not self._flights:
            return
        for flight in self._flights:
            flight.animation.update(dt)
            self.particles.trail(flight.animation.position, tokens.MOVE_TRAIL_COLOR)
        self._release_capture_if_reached()
        if all(flight.animation.is_done for flight in self._flights):
            self._land()

    def _release_capture_if_reached(self) -> None:
        waiting = self._waiting_capture
        if waiting is None or self._flights[0].animation.progress < _CAPTURE_MOMENT:
            return
        self._waiting_capture = None
        animation = CaptureAnimation(waiting.square, facing=PIECE_FACING[waiting.side])
        self._effects.append(_Effect(waiting.mesh, waiting.color, waiting.square, animation, hides_square=False))
        x, _, z = square_to_world(*waiting.square)
        self.particles.capture_burst((x, 0.3, z), _SPARK_COLORS[waiting.side])

    def _land(self) -> None:
        for flight in self._flights:
            x, _, z = flight.animation.position
            self.particles.emit((x, 0.05, z), 8, _LANDING_DUST_COLOR, speed=(0.3, 1.0), life=(0.2, 0.4),
                                size=(0.02, 0.04), bias=(0.0, 0.7, 0.0))
        self._flights = []
        self._has_landed = True
        self._release_spawn()
        self._resync()

    def _release_spawn(self) -> None:
        waiting = self._waiting_spawn
        if waiting is None:
            return
        self._waiting_spawn = None
        animation = SpawnAnimation(waiting.square, facing=PIECE_FACING[waiting.side])
        self._effects.append(_Effect(waiting.mesh, waiting.color, waiting.square, animation, hides_square=True))
        x, _, z = square_to_world(*waiting.square)
        self.particles.capture_burst((x, 0.4, z), tokens.BRASS_BRIGHT)

    def _advance_effects(self, dt: float) -> None:
        if self._fallen_king is not None:
            self._fallen_king.animation.update(dt)
        for effect in self._effects:
            effect.animation.update(dt)
        unfinished = [effect for effect in self._effects if not effect.animation.is_done]
        if len(unfinished) != len(self._effects):
            self._effects = unfinished
            self._resync()

    def _advance_shake(self, dt: float) -> None:
        if self.shake_square is None:
            return
        self._shake_elapsed += dt
        if self._shake_elapsed >= _SHAKE_SECONDS:
            self.shake_square = None

    # Desenho -------------------------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        renderer = self.renderer
        renderer.begin(surface)
        renderer.draw_board(self.matrix.rgb(self.time))
        self._add_placed_pieces()
        self._add_moving_pieces()
        for marker in self.markers:
            renderer.add_marker(*marker)
        if self.shake_square is not None:
            renderer.add_marker(*self.shake_square, MARKER_RING, tokens.MARKER_REFUSED_COLOR)
        renderer.add_particles(self.particles)
        renderer.flush()

    def _tint_amount(self) -> float:
        pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * _TINT_PULSE_HERTZ * self.time)
        return _TINT_LOW + (_TINT_HIGH - _TINT_LOW) * pulse

    def _add_placed_pieces(self) -> None:
        add_mesh = self.renderer.add_mesh
        amount = self._tint_amount() if self.tints else 0.0
        for piece in self._placed:
            tint = self.tints.get(piece.square)
            matrix = self._adjusted_matrix(piece)
            if tint is None:
                add_mesh(piece.mesh, matrix, piece.color)
            else:
                add_mesh(piece.mesh, matrix, piece.color, tint=tint, tint_amount=amount)

    def _adjusted_matrix(self, piece: _PlacedPiece) -> np.ndarray:
        matrix = piece.matrix
        if piece.square == self.lifted_square:
            matrix = _SELECTED_LIFT @ matrix
        if piece.square == self.shake_square:
            matrix = self._shake_offset() @ matrix
        return matrix

    def _shake_offset(self) -> np.ndarray:
        """Tremor na horizontal da tela, em qualquer ângulo de câmera, com amplitude que decai."""
        decay = 1.0 - self._shake_elapsed / _SHAKE_SECONDS
        amount = _SHAKE_AMPLITUDE * decay * math.sin(2.0 * math.pi * _SHAKE_HERTZ * self._shake_elapsed)
        yaw = self.camera.yaw
        return translation(amount * math.cos(yaw), 0.0, -amount * math.sin(yaw))

    def _add_moving_pieces(self) -> None:
        add_mesh = self.renderer.add_mesh
        for flight in self._flights:
            add_mesh(flight.mesh, flight.animation.model_matrix(), flight.color)
        for effect in self._effects:
            add_mesh(effect.mesh, effect.animation.model_matrix(), effect.color)
        waiting = self._waiting_capture
        if waiting is not None:
            add_mesh(waiting.mesh, piece_matrix(*waiting.square, PIECE_FACING[waiting.side]), waiting.color)
        if self._fallen_king is not None:
            add_mesh(self._fallen_king.mesh, self._fallen_king.animation.model_matrix(), self._fallen_king.color)


def _fall_direction(square: Cell, away_from: Cell | None) -> tuple[float, float]:
    if away_from is None:
        return (1.0, 0.0)
    king_x, _, king_z = square_to_world(*square)
    other_x, _, other_z = square_to_world(*away_from)
    direction = (king_x - other_x, king_z - other_z)
    return direction if any(direction) else (1.0, 0.0)
