"""Sesión de la interfaz: acciones del usuario sobre la fachada de simulación."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from instinct.sim.controller import SimulationController
from instinct.loaders.creature_loader import load_creature

from .constants import (
    MAX_LOG_LINES,
    PHASE_MAP_SELECT,
    PHASE_NO_MAPS,
    PHASE_PLACEMENT,
    PHASE_SIMULATION,
)
from .state import UIState


@dataclass(frozen=True)
class ReloadResult:
    """Resultado de una recarga en caliente de criatura."""

    ok: bool
    name: str | None
    errors: list[str]


class Session:
    """Ejecuta las acciones de la interfaz sobre `SimulationController`.

    La fachada ya monta el motor y el intérprete al seleccionar un mapa, así
    que la sesión nunca habla con el intérprete: traduce acciones de usuario
    en llamadas al controlador y mantiene el estado que la vista renderiza.
    Recuerda las colocaciones para repetir una partida con otra semilla.
    """

    def __init__(self, base_dir: Path, seed: int = 42) -> None:
        """Crea la sesión sobre el directorio de contenido.

        Args:
            base_dir: Carpeta que contiene terrains/, objects/, maps/ y creatures/.
            seed: Semilla inicial; visible y editable desde la interfaz.
        """
        self._base_dir = base_dir
        self._controller = SimulationController(base_dir, seed=seed)
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
        self.state.load_report = self._controller.load_content()
        self.state.loaded = self._controller.loaded
        self.state.phase = (
            PHASE_MAP_SELECT if self._controller.map_names() else PHASE_NO_MAPS
        )
        return bool(self._controller.map_names())

    # ------------------------------------------------------------------
    # Mapa y colocación
    # ------------------------------------------------------------------

    def select_map(self, name: str) -> str:
        """Selecciona el mapa y prepara la fase de colocación.

        Args:
            name: Nombre tal como aparece en la lista de mapas.

        Returns:
            Mensaje de la fachada; si el mapa no existe la fase no cambia.
        """
        if name not in self._controller.map_names():
            return self._controller.select_map(name)
        message = self._controller.select_map(name)
        self.state.map_name = name
        self.state.world = self._controller.world
        self.state.engine = self._controller.engine
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
            message = self._controller.remove_creature(x, y)
            self._placements = [
                (species, px, py)
                for species, px, py in self._placements
                if (px, py) != (x, y)
            ]
        elif self.state.placement_species is not None:
            species = self.state.placement_species
            message = self._controller.place_creature(species, x, y)
            placed_creature = self.state.world.creature_at(x, y)
            if placed_creature is not None and placed_creature.name == species:
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
        if 0 <= index < len(SimulationController.SPEEDS):
            self.state.speed_index = index

    # ------------------------------------------------------------------
    # Reinicio y repetición
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reconstruye el mundo actual sin criaturas y vuelve a la colocación."""
        message = self._controller.reset()
        self.state.world = self._controller.world
        self.state.engine = self._controller.engine
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

        Crea un controlador nuevo con esa semilla sin releer el disco
        (reaprovecha lo ya cargado), recoloca las mismas criaturas en las
        mismas celdas y arranca la simulación en marcha. El motor nace con la
        semilla dada, así que cada repetición produce la misma traza.
        """
        seed = self._seed_from_input()
        controller = SimulationController(self._base_dir, seed=seed)
        controller.loaded = self._controller.loaded
        map_name = self.state.map_name or ""
        message = controller.select_map(map_name)
        if map_name not in controller.map_names():
            self.state.messages.append(message)
            return
        for species, x, y in self._placements:
            controller.place_creature(species, x, y)
        self._controller = controller
        self.state.seed = seed
        self.state.seed_input = str(seed)
        self.state.seed_focused = False
        self.state.world = controller.world
        self.state.engine = controller.engine
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
        logs = self._controller.logs
        self.state.messages.extend(logs[self._log_cursor:])
        self._log_cursor = len(logs)
        if len(self.state.messages) > MAX_LOG_LINES:
            extra = len(self.state.messages) - MAX_LOG_LINES
            del self.state.messages[:extra]

    def _seed_from_input(self) -> int:
        """Devuelve la semilla del campo si es numérica; si no, la vigente."""
        digits = self.state.seed_input.strip()
        return int(digits) if digits.isdigit() else self.state.seed

    def reload_from_source(
        self, source: str, expected_name: str | None = None
    ) -> ReloadResult:
        """Recompila y recarga una criatura usando el nombre de su cabecera.

        Args:
            source: Texto completo del .ins a compilar.
            expected_name: Nombre que se esperaba según el archivo recargado.
                Si se da y la cabecera declara otro nombre, se cancela la
                recarga sin tocar el catálogo ni las criaturas colocadas.
                La comparación no distingue mayúsculas de minúsculas y el
                programa se guarda con la clave ya existente del catálogo.

        Returns:
            Resultado con ok, nombre canónico de especie y errores formateados.
        """
        if self._controller.loaded is None:
            return ReloadResult(False, None, ["no hay contenido cargado"])

        result = load_creature(source)
        if result.creature is None:
            errors = [f"línea {e.line}: {e.message}" for e in result.errors]
            return ReloadResult(False, None, errors)

        name = result.creature.name
        if expected_name is not None and name.casefold() != expected_name.casefold():
            message = (
                f"la cabecera declara {name!r} pero se esperaba "
                f"{expected_name!r}; recarga cancelada"
            )
            return ReloadResult(False, None, [message])
        canonical_name = self._canonical_species_name(name, expected_name)
        program = result.creature
        if program.name != canonical_name:
            program = replace(program, name=canonical_name)
        self._apply_reload(canonical_name, program)
        return ReloadResult(True, canonical_name, [])

    def _canonical_species_name(
        self, header_name: str, expected_name: str | None
    ) -> str:
        """Devuelve la clave cargada que identifica la especie recargada.

        Si la cabecera solo cambia la capitalización, se conserva la clave ya
        existente para no duplicar la especie y para que las criaturas colocadas
        sigan coincidiendo por nombre al recolocarse.
        """
        assert self._controller.loaded is not None
        for candidate in (expected_name, header_name):
            if candidate is None:
                continue
            for key in self._controller.loaded.creatures:
                if key.casefold() == candidate.casefold():
                    return key
        return header_name

    def reload_creature(self, name: str, source: str) -> tuple[bool, list[str]]:
        """Recompila y recarga una criatura en la sesión activa.

        Mantiene compatibilidad con la API anterior. Un nombre vacío o un
        marcador entre ángulos no se considera real y no restringe la cabecera.

        Args:
            name: Nombre de la criatura (especie) a recargar, o marcador.
            source: Texto completo del .ins a compilar.

        Returns:
            Tupla (ok, errores). Si ok es False, errores contiene los mensajes.
        """
        expected = name.strip()
        if not expected or (expected.startswith("<") and expected.endswith(">")):
            expected = None
        result = self.reload_from_source(source, expected_name=expected)
        return result.ok, result.errors

    def _apply_reload(self, name: str, new_program) -> None:
        """Aplica un programa ya compilado al catálogo y al mundo activo."""
        assert self._controller.loaded is not None
        self._controller.loaded.creatures[name] = new_program
        if self.state.world is not None:
            self._reload_species_creatures(name, new_program)

    def _reload_species_creatures(self, name: str, new_program) -> None:
        """Recarga en sitio todas las criaturas de una especie.

        Mantiene su posición, salud, edad, variables y wait_remaining.
        Solo actualiza el programa y los atributos de cabecera que puedan haber cambiado.
        """
        if self.state.world is None:
            return
        world = self.state.world
        for y in range(world.height):
            for x in range(world.width):
                creature = world.creature_at(x, y)
                if creature is not None and creature.name == name:
                    # Actualizar programa y atributos de cabecera
                    creature.program = new_program
                    creature.faction = new_program.faction
                    creature.vision = new_program.vision
                    creature.lifespan = new_program.lifespan
                    # health, age, variables, wait_remaining se preservan
                    # pc se reinicia a start: por seguridad
                    creature.pc = new_program.labels["start"]
