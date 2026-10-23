"""Aplicación Pygame: une sesión, render y entrada en un bucle a 60 fps."""
from __future__ import annotations

import time
from pathlib import Path

import pygame

from .assets import Assets
from .constants import (
    DEFAULT_WINDOW_SIZE,
    LOG_HEIGHT,
    PANEL_WIDTH,
    STATUS_BAR_HEIGHT,
    TARGET_FPS,
    WINDOW_TITLE,
)
from .controls import Controls, UIAction
from .session import Session
from .view import View


class App:
    """Arranca la ventana, carga el contenido y corre el bucle de simulación.

    El bucle dibuja a 60 fps y avanza ticks según la velocidad elegida; la
    lógica vive en la sesión, el dibujo en la vista y la traducción de eventos
    en los controles, así que esta clase solo reparte y sincroniza.
    """

    def __init__(self, base_dir: Path, seed: int = 42) -> None:
        """Crea la ventana y sus componentes; la carga sucede al arrancar.

        Args:
            base_dir: Carpeta que contiene terrains/, objects/, maps/ y creatures/.
            seed: Semilla inicial del generador de la simulación.
        """
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode(DEFAULT_WINDOW_SIZE, pygame.RESIZABLE)
        self.session = Session(base_dir, seed=seed)
        self.assets = Assets()
        self.view = View(self.assets)
        self.controls = Controls(self.session.state)
        self.clock = pygame.time.Clock()
        self._running = False
        self._last_step = 0.0

    def run(self) -> None:
        """Ejecuta el bucle principal hasta que el usuario salga."""
        self.session.load()
        self._running = True
        self._last_step = time.monotonic()
        while self._running:
            for event in pygame.event.get():
                for action in self.controls.handle(event, self.view.hotspots):
                    self._execute(action)
            self._advance_simulation()
            self.view.render(self.screen, self.session.state)
            pygame.display.flip()
            self.clock.tick(TARGET_FPS)
        pygame.quit()

    # ------------------------------------------------------------------
    # Simulación temporizada
    # ------------------------------------------------------------------

    def _advance_simulation(self) -> None:
        """Avanza un tick cuando toca según la velocidad y sin pausa."""
        state = self.session.state
        if not state.in_simulation() or state.paused:
            return
        now = time.monotonic()
        if now - self._last_step >= 1.0 / state.speed_tps:
            self.session.step_once()
            self._last_step = now

    # ------------------------------------------------------------------
    # Ejecución de acciones
    # ------------------------------------------------------------------

    def _execute(self, action: UIAction) -> None:
        """Aplica sobre la sesión una acción producida por los controles."""
        session = self.session
        if action.type == "quit":
            self._running = False
        elif action.type == "map":
            session.select_map(action.value)
            self._center_camera()
        elif action.type == "species":
            session.pick_species(action.value)
        elif action.type == "start":
            session.start()
        elif action.type == "cell":
            x, y = (int(part) for part in action.value.split(","))
            session.cell(x, y)
        elif action.type == "select_cell":
            x, y = (int(part) for part in action.value.split(","))
            session.select_cell(x, y)
        elif action.type == "pause":
            session.toggle_pause()
        elif action.type == "step":
            session.step_once()
        elif action.type == "speed":
            session.set_speed(int(action.value))
        elif action.type == "reset":
            session.reset()
        elif action.type == "repeat":
            session.repeat_seed()

    def _center_camera(self) -> None:
        """Centra la rejilla del mapa actual en el área visible."""
        state = self.session.state
        if state.world is None:
            return
        width, height = self.screen.get_size()
        grid_w = width - PANEL_WIDTH
        grid_h = height - LOG_HEIGHT - STATUS_BAR_HEIGHT
        state.camera_x = (grid_w - state.world.width * state.tile_size) // 2
        state.camera_y = (grid_h - state.world.height * state.tile_size) // 2


def main() -> None:
    """Lanza la aplicación sobre el directorio raíz del proyecto."""
    base_dir = Path(__file__).resolve().parents[2]
    App(base_dir, seed=42).run()
