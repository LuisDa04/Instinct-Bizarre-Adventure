"""Aplicación Pygame: une sesión, render y entrada en un bucle a 60 fps.

Integra un editor de código PyQt6 (ventana separada, F4) que comparte la
misma sesión con el motor de simulación. El editor permite escribir .ins,
validar en tiempo real y recargar criaturas en caliente sin reiniciar.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

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

# Editor opcional (requiere PyQt6 instalado)
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from instinct.ui.editor import EditorWidget

    _HAS_QT = True
except ImportError:
    QApplication = None  # type: ignore
    QMainWindow = None  # type: ignore
    EditorWidget = None  # type: ignore
    _HAS_QT = False


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

        # Editor PyQt6 (ventana separada, compartida sesión)
        self._qt_app = None
        self._editor_window: Optional[QMainWindow] = None
        self._editor_widget: Optional[EditorWidget] = None
        if _HAS_QT:
            self._qt_app = QApplication.instance() or QApplication([])
            self._editor_widget = EditorWidget(self.session)
            self._editor_window = QMainWindow()
            self._editor_window.setCentralWidget(self._editor_widget)
            self._editor_window.setWindowTitle("Instinct - Editor de código")
            self._editor_window.resize(600, 700)
            self._editor_window.hide()  # Inicia oculta, se abre con F4

    def run(self) -> None:
        """Ejecuta el bucle principal hasta que el usuario salga."""
        self.session.load()
        self._running = True
        self._last_step = time.monotonic()
        while self._running:
            # 1. Eventos Pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    continue
                for action in self.controls.handle(event, self.view.hotspots):
                    self._execute(action)

            # 2. Procesar eventos Qt UNA VEZ por frame (fuera del for)
            if self._qt_app is not None:
                self._qt_app.processEvents()

            # 2. Actualización simulación (desacoplada del render)
            self._advance_simulation()

            # 3. Render
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
        # ----- Acciones del editor -----
        elif action.type == "editor_save":
            self._editor_save_current()
        elif action.type == "editor_reload":
            self._editor_reload_current()
        elif action.type == "editor_new":
            self._editor_new_tab()
        elif action.type == "editor_open":
            self._editor_open_file()
        elif action.type == "toggle_editor":
            self._toggle_editor_window()

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

    # ------------------------------------------------------------------
    # Acciones del editor
    # ------------------------------------------------------------------

    def _editor_save_current(self) -> None:
        """Guarda la pestaña actual del editor."""
        if self._editor_widget is not None:
            self._editor_widget.save_current()

    def _editor_reload_current(self) -> None:
        """Recarga la criatura de la pestaña actual del editor."""
        if self._editor_widget is not None:
            self._editor_widget.hot_reload_current()

    def _editor_new_tab(self) -> None:
        """Crea una nueva pestaña en el editor."""
        if self._editor_widget is not None:
            self._editor_widget.new_tab()

    def _editor_open_file(self) -> None:
        """Abre un archivo .ins en el editor."""
        if self._editor_widget is not None:
            self._editor_widget.open_file()

    def _toggle_editor_window(self) -> None:
        """Muestra u oculta la ventana del editor."""
        if self._editor_window is not None:
            if self._editor_window.isVisible():
                self._editor_window.hide()
            else:
                self._editor_window.show()
                self._editor_window.raise_()
                self._editor_window.activateWindow()


def main() -> None:
    """Lanza la aplicación sobre el directorio raíz del proyecto."""
    base_dir = Path(__file__).resolve().parents[2]
    App(base_dir, seed=42).run()
