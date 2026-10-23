"""Entrada de la interfaz: convierte eventos de teclado y ratón en acciones."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from .constants import (
    MAX_TILE_SIZE,
    MIN_TILE_SIZE,
    PHASE_PLACEMENT,
    SPEEDS,
    ZOOM_STEP,
)
from .state import UIState

#: Acciones de un solo nombre; el resto lleva dato en `value`.
SIMPLE_ACTIONS = frozenset({"start", "pause", "step", "reset", "repeat", "quit"})


@dataclass(frozen=True)
class UIAction:
    """Acción que los controles piden ejecutar sobre la sesión.

    Attributes:
        type: Nombre de la acción: "quit", "map", "species", "start", "cell",
            "select_cell", "pause", "step", "speed", "reset" o "repeat".
        value: Dato que acompaña a la acción: un nombre, "x,y" o el índice
            de velocidad; vacío cuando la acción no necesita nada.
    """

    type: str
    value: str = ""


class Controls:
    """Traduce teclado y ratón en acciones; solo muta la parte visual del estado.

    La parte lógica (fase, mundo, mensajes) es territorio de la sesión: los
    controles se limitan a cámara, hover, zoom y el campo de semilla. Los
    clics se resuelven contra la tabla de hotspots del último frame renderizado.
    """

    def __init__(self, state: UIState) -> None:
        self.state = state
        self._panning = False
        self._pan_last = (0, 0)

    def handle(self, event: pygame.event.Event, hotspots: dict[str, pygame.Rect]) -> list[UIAction]:
        """Procesa un evento Pygame y devuelve las acciones que provoca."""
        if event.type == pygame.QUIT:
            return [UIAction("quit")]
        if event.type == pygame.KEYDOWN:
            return self._key_down(event)
        if event.type == pygame.MOUSEMOTION:
            self._motion(event, hotspots)
            return []
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._button_down(event, hotspots)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self._panning = False
        if event.type == pygame.MOUSEWHEEL:
            self._zoom(event.y)
        return []

    # ------------------------------------------------------------------
    # Teclado
    # ------------------------------------------------------------------

    def _key_down(self, event: pygame.event.Event) -> list[UIAction]:
        """Atiende las teclas según la fase; el campo de semilla se traga las letras."""
        state = self.state
        if state.seed_focused:
            return self._seed_key(event)
        if event.key in (pygame.K_ESCAPE, pygame.K_q):
            return [UIAction("quit")]
        if state.in_simulation():
            if event.key == pygame.K_SPACE:
                return [UIAction("pause")]
            if event.key == pygame.K_s:
                return [UIAction("step")]
            if event.key == pygame.K_r:
                return [UIAction("reset")]
            if pygame.K_1 <= event.key <= pygame.K_4:
                return [UIAction("speed", str(event.key - pygame.K_1))]
        return []

    def _seed_key(self, event: pygame.event.Event) -> list[UIAction]:
        """Edita el campo de semilla: dígitos, borrar, Enter repite, Escape suelta el foco."""
        state = self.state
        if event.key == pygame.K_RETURN:
            state.seed_focused = False
            return [UIAction("repeat")]
        if event.key == pygame.K_ESCAPE:
            state.seed_focused = False
            return []
        if event.key == pygame.K_BACKSPACE:
            state.seed_input = state.seed_input[:-1]
            return []
        if event.unicode.isdigit():
            state.seed_input = (state.seed_input + event.unicode)[:10]
        return []

    # ------------------------------------------------------------------
    # Ratón
    # ------------------------------------------------------------------

    def _button_down(self, event: pygame.event.Event, hotspots: dict[str, pygame.Rect]) -> list[UIAction]:
        """Resuelve un clic: botón derecho arrastra la cámara, izquierdo actúa."""
        if event.button == 3:
            self._panning = True
            self._pan_last = event.pos
            return []
        if event.button != 1:
            return []
        seed_box = hotspots.get("seed_input")
        if self.state.seed_focused and (seed_box is None or not seed_box.collidepoint(event.pos)):
            self.state.seed_focused = False
        for key, rect in hotspots.items():
            if key != "grid" and rect.collidepoint(event.pos):
                return self._hotspot_action(key)
        grid = hotspots.get("grid")
        if grid is not None and grid.collidepoint(event.pos):
            cell = self._cell_at(event.pos, grid)
            if cell is None:
                return []
            value = f"{cell[0]},{cell[1]}"
            if self.state.in_simulation():
                return [UIAction("select_cell", value)]
            if self.state.phase == PHASE_PLACEMENT:
                return [UIAction("cell", value)]
        return []

    def _hotspot_action(self, key: str) -> list[UIAction]:
        """Convierte la clave de un hotspot en la acción que representa."""
        if key.startswith("map:"):
            return [UIAction("map", key[4:])]
        if key.startswith("species:"):
            return [UIAction("species", key[8:])]
        if key == "seed_input":
            self.state.seed_focused = True
            return []
        if key == "speed":
            next_index = (self.state.speed_index + 1) % len(SPEEDS)
            return [UIAction("speed", str(next_index))]
        if key in SIMPLE_ACTIONS:
            return [UIAction(key)]
        return []

    def _motion(self, event: pygame.event.Event, hotspots: dict[str, pygame.Rect]) -> None:
        """Actualiza la celda bajo el ratón y arrastra la cámara si hay botón derecho."""
        if self._panning:
            self.state.camera_x += event.pos[0] - self._pan_last[0]
            self.state.camera_y += event.pos[1] - self._pan_last[1]
            self._pan_last = event.pos
        self.state.hover_cell = None
        grid = hotspots.get("grid")
        if grid is not None and grid.collidepoint(event.pos):
            self.state.hover_cell = self._cell_at(event.pos, grid)

    def _cell_at(self, pos: tuple[int, int], grid: pygame.Rect) -> tuple[int, int] | None:
        """Devuelve la celda del mundo bajo el píxel, o None si cae fuera."""
        tile = self.state.tile_size
        x = (pos[0] - grid.x - self.state.camera_x) // tile
        y = (pos[1] - grid.y - self.state.camera_y) // tile
        world = self.state.world
        if world is None or not world.in_bounds(x, y):
            return None
        return (int(x), int(y))

    def _zoom(self, direction: int) -> None:
        """Ajusta el tamaño de celda con tope en ambos extremos."""
        new_size = self.state.tile_size + direction * ZOOM_STEP
        self.state.tile_size = max(MIN_TILE_SIZE, min(MAX_TILE_SIZE, new_size))
