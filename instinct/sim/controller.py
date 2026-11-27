"""Fachada interna de simulación: carga, mapa, colocación y reinicio."""
from __future__ import annotations

from pathlib import Path

from ..lang.interpreter import Interpreter
from ..loaders.map_loader import build_world
from ..loaders.pipeline import LoadedWorld, load_all
from ..world.entities import Creature
from ..world.world import World
from .engine import Engine


class SimulationController:
    """Prepara el mundo y el motor para la interfaz y las pruebas.

    Toda su lógica recibe y devuelve texto o estado observable, así que puede
    usarse sin consola ni ventana. El avance de ticks lo hace quien posee el
    motor (`engine.step()`); la velocidad de reproducción vive en la interfaz.
    """

    #: Velocidades disponibles en ticks por segundo, seleccionables con 1-5.
    SPEEDS: tuple[float, ...] = (0.5, 1, 5, 10, 30)

    def __init__(self, base_dir: Path, seed: int = 42) -> None:
        """Crea la fachada sobre el directorio de contenido y la semilla dada.

        Args:
            base_dir: Carpeta que contiene terrains/, objects/, maps/ y creatures/.
            seed: Semilla del generador para reproducibilidad.
        """
        self._base_dir = base_dir
        self._seed = seed
        self.loaded: LoadedWorld | None = None
        self.world: World | None = None
        self.engine = None
        self.logs: list[str] = []

    # ------------------------------------------------------------------
    # Fase 1: carga
    # ------------------------------------------------------------------

    def load_content(self) -> str:
        """Carga todo el contenido del directorio base y devuelve el reporte.

        Returns:
            Texto con el resumen de lo cargado y los errores con su ruta.
        """
        self.loaded = load_all(
            self._base_dir / "terrains",
            self._base_dir / "objects",
            self._base_dir / "maps",
            self._base_dir / "creatures",
        )
        return self.load_report()

    def load_report(self) -> str:
        """Compone el texto del reporte de carga con errores y conteos."""
        assert self.loaded is not None
        lines = [
            f"Terrenos: {len(self.loaded.registry.terrains)}",
            f"Objetos: {len(self.loaded.registry.objects)}",
            f"Mapas: {', '.join(self.loaded.maps) or '(ninguno)'}",
            f"Criaturas: {', '.join(self.loaded.creatures) or '(ninguna)'}",
        ]
        if self.loaded.load_errors:
            lines.append("Errores de carga:")
            for error in self.loaded.load_errors:
                where = f"{error.path}" if error.path else f"línea {error.line}"
                lines.append(f"  [{where}] línea {error.line}: {error.message}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Fase 2: elegir mapa y construir mundo
    # ------------------------------------------------------------------

    def map_names(self) -> list[str]:
        """Devuelve los nombres de los mapas cargados."""
        assert self.loaded is not None
        return list(self.loaded.maps.keys())

    def select_map(self, name: str) -> str:
        """Selecciona el mapa, construye el mundo y arranca el motor.

        Args:
            name: Nombre del mapa tal como aparece en `map_names`.

        Returns:
            Mensaje de confirmación o error si el mapa no existe.
        """
        assert self.loaded is not None
        if name not in self.loaded.maps:
            return f"mapa {name!r} no existe"
        game_map = self.loaded.maps[name]
        self.world = build_world(game_map)
        self.engine = Engine(self.world, seed=self._seed)
        self.logs = []
        interpreter = Interpreter(self.world, self.engine, log=self.logs.append)
        self.engine.set_turn_runner(interpreter.run_turn)
        return f"mapa {name!r} listo ({game_map.width}x{game_map.height}), semilla {self._seed}"

    # ------------------------------------------------------------------
    # Fase 3: colocación de criaturas
    # ------------------------------------------------------------------

    def place_creature(self, species: str, x: int, y: int) -> str:
        """Coloca una criatura de la especie dada en (x, y).

        Args:
            species: Nombre de la criatura cargada.
            x: Columna.
            y: Fila.

        Returns:
            Mensaje de éxito o error explicando el rechazo.
        """
        assert self.loaded is not None and self.world is not None
        if species not in self.loaded.creatures:
            return f"especie {species!r} no existe"
        if not self.world.in_bounds(x, y):
            return f"({x}, {y}) está fuera del mapa"
        if not self.world.walkable(x, y):
            return f"({x}, {y}) está ocupada"
        creature = Creature(self.loaded.creatures[species], x, y)
        placed = self.world.place_creature(x, y, creature)
        if not placed:
            return f"no se pudo colocar en ({x}, {y})"
        return f"{species} colocada en ({x}, {y})"

    def remove_creature(self, x: int, y: int) -> str:
        """Quita la criatura de (x, y) si hay una.

        Args:
            x: Columna.
            y: Fila.

        Returns:
            Mensaje de éxito o error si no hay criatura.
        """
        assert self.world is not None
        removed = self.world.remove_creature(x, y)
        if removed is None:
            return f"no hay criatura en ({x}, {y})"
        return f"{removed.name} retirada de ({x}, {y})"

    # ------------------------------------------------------------------
    # Reinicio
    # ------------------------------------------------------------------

    def reset(self) -> str:
        """Reconstruye el mundo del mapa actual sin criaturas.

        Returns:
            Mensaje confirmando el reinicio.
        """
        assert self.loaded is not None
        assert self.engine is not None
        game_map = self._current_map()
        self.world = build_world(game_map)
        self.engine = Engine(self.world, seed=self._seed)
        self.logs = []
        interpreter = Interpreter(self.world, self.engine, log=self.logs.append)
        self.engine.set_turn_runner(interpreter.run_turn)
        return "reiniciado: criaturas retiradas, mundo reconstruido"

    def _current_map(self):
        """Devuelve el GameMap actualmente seleccionado."""
        assert self.loaded is not None and self.engine is not None
        for game_map in self.loaded.maps.values():
            if game_map.width == self.world.width and game_map.height == self.world.height:
                return game_map
        return next(iter(self.loaded.maps.values()))
