"""Estado observable de la interfaz: lo único que el render lee en cada frame."""
from __future__ import annotations

from dataclasses import dataclass, field

from instinct.loaders.pipeline import LoadedWorld
from instinct.sim.engine import Engine
from instinct.world.world import World

from .constants import (
    BASE_TILE_SIZE,
    PHASE_LOADING,
    PHASE_SIMULATION,
    SPEEDS,
)


@dataclass
class UIState:
    """Reúne lo lógico (fase, mundo, mensajes) y lo visual (cámara, hover).

    La sesión muta la parte lógica y los controles la visual; la vista
    solo lee. Vive en un solo objeto para que render y entrada nunca
    desincronicen.
    """

    # Fase actual de la aplicación
    phase: str = PHASE_LOADING

    # Carga
    loaded: LoadedWorld | None = None
    load_report: str = ""

    # Mapa elegido y mundo/motor que montó el CLI
    map_name: str | None = None
    world: World | None = None
    engine: Engine | None = None

    # Colocación
    placement_species: str | None = None
    selected_cell: tuple[int, int] | None = None

    # Simulación
    paused: bool = False
    speed_index: int = 0
    tick: int = 0
    seed: int = 42
    seed_input: str = "42"
    seed_focused: bool = False

    # Registro de la sesión: mensajes de colocación y del motor
    messages: list[str] = field(default_factory=list)

    # Cámara y rejilla
    camera_x: int = 0
    camera_y: int = 0
    tile_size: int = BASE_TILE_SIZE
    hover_cell: tuple[int, int] | None = None

    @property
    def speed_tps(self) -> int:
        """Ticks por segundo de la velocidad seleccionada."""
        return SPEEDS[self.speed_index]

    @property
    def map_names(self) -> list[str]:
        """Nombres de los mapas válidos cargados."""
        if self.loaded is None:
            return []
        return list(self.loaded.maps)

    @property
    def species_names(self) -> list[str]:
        """Nombres de las criaturas válidas cargadas."""
        if self.loaded is None:
            return []
        return list(self.loaded.creatures)

    def in_simulation(self) -> bool:
        """Indica si la simulación está corriendo (en marcha o en pausa)."""
        return self.phase == PHASE_SIMULATION
