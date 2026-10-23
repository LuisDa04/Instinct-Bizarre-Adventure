"""Sesión de la interfaz: acciones del usuario ejecutadas sobre el CLI."""
from __future__ import annotations

from pathlib import Path

from instinct.sim.cli import CLI

from .constants import (
    MAX_LOG_LINES,
    PHASE_MAP_SELECT,
    PHASE_NO_MAPS,
    PHASE_PLACEMENT,
    PHASE_SIMULATION,
    SPEEDS,
)
from .state import UIState


class Session:
    """Ejecuta las acciones de la interfaz reutilizando el CLI como fachada.

    El CLI ya monta el motor y el intérprete al seleccionar un mapa, así que
    la sesión nunca habla con el intérprete: traduce acciones de usuario en
    llamadas al CLI y mantiene el estado que la vista renderiza. Recuerda las
    colocaciones para poder repetir una partida entera con otra semilla.
    """

    def __init__(self, base_dir: Path, seed: int = 42) -> None:
        """Crea la sesión sobre el directorio de contenido.

        Args:
            base_dir: Carpeta que contiene terrains/, objects/, maps/ y creatures/.
            seed: Semilla inicial; visible y editable desde la interfaz.
        """
        self._base_dir = base_dir
        self._cli = CLI(base_dir, seed=seed)
        self.state = UIState(seed=seed, seed_input=str(seed))
        self._placements: list[tuple[str, int, int]] = []
        self._log_cursor = 0

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """Carga el contenido del directorio y pasa a la elección de mapa.

        Returns:
            True si hay al menos un mapa válido; False si la lista queda vacía.
        """
        self.state.load_report = self._cli.load_content()
        self.state.loaded = self._cli.loaded
        self.state.phase = (
            PHASE_MAP_SELECT if self._cli.map_names() else PHASE_NO_MAPS
        )
        return bool(self._cli.map_names())

    # ------------------------------------------------------------------
    # Mapa y colocación
    # ------------------------------------------------------------------

    def select_map(self, name: str) -> str:
        """Selecciona el mapa y prepara la fase de colocación.

        Args:
            name: Nombre tal como aparece en la lista de mapas.

        Returns:
            Mensaje del CLI; si el mapa no existe la fase no cambia.
        """
        message = self._cli.select_map(name)
        if "no existe" in message:
            return message
        self.state.map_name = name
        self.state.world = self._cli.world
        self.state.engine = self._cli.engine
        self.state.phase = PHASE_PLACEMENT
        self.state.placement_species = None
        self.state.selected_cell = None
        self.state.tick = 0
        self.state.messages = []
        self._placements = []
        self._log_cursor = 0
        return message

    def pick_species(self, name: str) -> None:
        """Activa la especie en modo colocar; repetirla la desactiva.

        Args:
            name: Nombre de una criatura cargada.
        """
        if self.state.placement_species == name:
            self.state.placement_species = None
        else:
            self.state.placement_species = name

    def cell(self, x: int, y: int) -> None:
        """Actúa sobre la celda clicada durante la colocación.

        Con una especie activa intenta colocarla; sin especie quita la
        criatura que haya en la celda. El resultado siempre va al registro.

        Args:
            x: Columna.
            y: Fila.
        """
        assert self.state.world is not None
        creature = self.state.world.creature_at(x, y)
        if creature is not None:
            message = self._cli.remove_creature(x, y)
            self._placements = [
                (species, px, py)
                for species, px, py in self._placements
                if (px, py) != (x, y)
            ]
        elif self.state.placement_species is not None:
            species = self.state.placement_species
            message = self._cli.place_creature(species, x, y)
            if "colocada" in message:
                self._placements.append((species, x, y))
        else:
            return
        self.state.messages.append(message)

    def select_cell(self, x: int, y: int) -> None:
        """Resalta la celda durante la simulación; no edita nada.

        Args:
            x: Columna.
            y: Fila.
        """
        self.state.selected_cell = (x, y)

    # ------------------------------------------------------------------
    # Simulación
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Arranca la simulación si hay criaturas colocadas.

        Returns:
            True si arrancó; False si no había ninguna criatura.
        """
        assert self.state.world is not None
        if not any(True for _ in self.state.world.creatures()):
            self.state.messages.append(
                "coloca al menos una criatura antes de empezar"
            )
            return False
        self.state.phase = PHASE_SIMULATION
        self.state.paused = False
        return True

    def toggle_pause(self) -> None:
        """Alterna la pausa; solo hace algo durante la simulación."""
        if self.state.in_simulation():
            self.state.paused = not self.state.paused

    def step_once(self) -> None:
        """Avanza un tick y recoge los mensajes nuevos del motor."""
        if not self.state.in_simulation() or self.state.engine is None:
            return
        self.state.engine.step()
        self.state.tick = self.state.engine.tick
        self._pull_logs()

    def set_speed(self, index: int) -> None:
        """Fija la velocidad por posición del catálogo; ignora índices fuera de rango.

        Args:
            index: Posición en el catálogo de velocidades.
        """
        if 0 <= index < len(SPEEDS):
            self.state.speed_index = index

    # ------------------------------------------------------------------
    # Reinicio y repetición
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reconstruye el mundo actual sin criaturas y vuelve a la colocación."""
        message = self._cli.reset()
        self.state.world = self._cli.world
        self.state.engine = self._cli.engine
        self.state.phase = PHASE_PLACEMENT
        self.state.paused = False
        self.state.tick = 0
        self.state.placement_species = None
        self.state.selected_cell = None
        self.state.messages = [message]
        self._placements = []
        self._log_cursor = 0

    def repeat_seed(self) -> None:
        """Repite la partida con la semilla del campo visible.

        Crea un CLI nuevo con esa semilla sin releer el disco (reaprovecha
        lo ya cargado), recoloca las mismas criaturas en las mismas celdas y
        arranca la simulación en marcha. El motor nace con la semilla dada,
        así que cada repetición produce exactamente la misma traza.
        """
        seed = self._seed_from_input()
        cli = CLI(self._base_dir, seed=seed)
        cli.loaded = self._cli.loaded
        message = cli.select_map(self.state.map_name or "")
        if "no existe" in message:
            self.state.messages.append(message)
            return
        for species, x, y in self._placements:
            cli.place_creature(species, x, y)
        self._cli = cli
        self.state.seed = seed
        self.state.seed_input = str(seed)
        self.state.seed_focused = False
        self.state.world = cli.world
        self.state.engine = cli.engine
        self.state.phase = PHASE_SIMULATION
        self.state.paused = False
        self.state.tick = 0
        self.state.selected_cell = None
        self.state.messages = []
        self._log_cursor = 0

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def _pull_logs(self) -> None:
        """Añade al registro los mensajes del motor escritos desde la última vez."""
        logs = self._cli.logs
        self.state.messages.extend(logs[self._log_cursor:])
        self._log_cursor = len(logs)
        if len(self.state.messages) > MAX_LOG_LINES:
            extra = len(self.state.messages) - MAX_LOG_LINES
            del self.state.messages[:extra]

    def _seed_from_input(self) -> int:
        """Devuelve la semilla del campo si es numérica; si no, la vigente."""
        digits = self.state.seed_input.strip()
        return int(digits) if digits.isdigit() else self.state.seed
