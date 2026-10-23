"""Interfaz de texto: elegir mapa, colocar criaturas y correr la simulación."""
from __future__ import annotations

import time
from pathlib import Path

from ..lang.interpreter import Interpreter
from ..loaders.map_loader import build_world
from ..loaders.pipeline import LoadedWorld, load_all
from ..world.entities import Creature
from ..world.world import World
from .engine import Engine

#: Velocidades disponibles en ticks por segundo, seleccionables con 1-5.
SPEEDS: tuple[float, ...] = (0.5, 1, 5, 10, 30)


class CLI:
    """Controla la sesión interactiva por terminal sobre el motor.

    La lógica vive en métodos que reciben y devuelven texto para poder
    probarlos sin consola; `run` es el único que habla con input/print.
    """

    def __init__(self, base_dir: Path, seed: int = 42) -> None:
        """Crea el CLI sobre el directorio de contenido y la semilla dada.

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
        self._speed_index = 0

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
        self._speed_index = 0
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
    # Fase 4: simulación
    # ------------------------------------------------------------------

    def step(self) -> str:
        """Avanza un tick y devuelve el estado con los logs nuevos.

        Returns:
            Grid renderizado más los mensajes del registro del tick.
        """
        assert self.engine is not None
        prior = len(self.logs)
        self.engine.step()
        new_logs = self.logs[prior:]
        parts = [self.render_grid()]
        if new_logs:
            parts.extend(new_logs)
        return "\n".join(parts)

    def run_ticks(self, count: int) -> str:
        """Avanza varios ticks con pausa entre cada uno según la velocidad.

        Args:
            count: Número de ticks a ejecutar.

        Returns:
            Grid final con los logs del último tick.
        """
        assert self.engine is not None
        interval = 1.0 / SPEEDS[self._speed_index]
        for _ in range(count):
            self.engine.step()
            time.sleep(interval)
        return self.step()

    def set_speed(self, index: int) -> str:
        """Ajusta la velocidad a la posición indicada del catálogo.

        Args:
            index: Posición 0-4 en SPEEDS (0.5, 1, 5, 10 o 30 tps).

        Returns:
            Mensaje confirmando la nueva velocidad.
        """
        if not 0 <= index < len(SPEEDS):
            return f"velocidad inválida: {index + 1}"
        self._speed_index = index
        return f"velocidad: {SPEEDS[index]} tps"

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
        self._speed_index = 0
        interpreter = Interpreter(self.world, self.engine, log=self.logs.append)
        self.engine.set_turn_runner(interpreter.run_turn)
        return "reiniciado: criaturas retiradas, mundo reconstruido"

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render_grid(self) -> str:
        """Devuelve el mapa como texto: char de terreno/objeto o inicial de criatura."""
        assert self.world is not None
        rows: list[str] = []
        for y in range(self.world.height):
            chars: list[str] = []
            for x in range(self.world.width):
                creature = self.world.creature_at(x, y)
                if creature is not None:
                    chars.append(creature.name[0].upper())
                    continue
                obj = self.world.object_at(x, y)
                if obj is not None:
                    chars.append(obj.char)
                    continue
                terrain = self.world.terrain_at(x, y)
                chars.append(terrain.char if terrain is not None else " ")
            rows.append("".join(chars))
        return "\n".join(rows)

    def recent_logs(self, count: int = 20) -> list[str]:
        """Devuelve los últimos `count` mensajes del registro."""
        return self.logs[-count:]

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Ejecuta la sesión interactiva completa por terminal."""
        print(self.load_content())
        if not self.map_names():
            print("No hay mapas válidos. Saliendo.")
            return
        name = self._prompt_map()
        if name is None:
            return
        print(self.select_map(name))
        self._placement_loop()
        self._simulation_loop()

    def _prompt_map(self) -> str | None:
        """Pide al usuario que elija un mapa por número."""
        names = self.map_names()
        print("\nMapas disponibles:")
        for i, name in enumerate(names, start=1):
            print(f"  {i}. {name}")
        raw = input("Elige un mapa (número o nombre, vacío para salir): ").strip()
        if not raw:
            return None
        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(names):
                return names[index]
            print("Número fuera de rango.")
            return self._prompt_map()
        if raw in names:
            return raw
        print("Mapa no encontrado.")
        return self._prompt_map()

    def _placement_loop(self) -> None:
        """Fase de colocación: place/remove/list/grid/done."""
        print("\n=== Colocación ===")
        print("Comandos: place <especie> <x> <y> | remove <x> <y> | list | grid | done")
        while True:
            print(self.render_grid())
            print("Especies:", ", ".join(self.loaded.creatures.keys()) if self.loaded else "")
            raw = input("> ").strip()
            parts = raw.split()
            if not parts:
                continue
            cmd = parts[0].lower()
            if cmd == "done":
                if any(True for _ in self.world.creatures()):
                    return
                print("Coloca al menos una criatura antes de empezar.")
            elif cmd == "place" and len(parts) == 4:
                try:
                    x, y = int(parts[2]), int(parts[3])
                except ValueError:
                    print("Coordenadas inválidas.")
                    continue
                print(self.place_creature(parts[1], x, y))
            elif cmd == "remove" and len(parts) == 3:
                try:
                    x, y = int(parts[1]), int(parts[2])
                except ValueError:
                    print("Coordenadas inválidas.")
                    continue
                print(self.remove_creature(x, y))
            elif cmd == "list":
                print("Especies:", ", ".join(self.loaded.creatures.keys()) if self.loaded else "")
            elif cmd == "grid":
                print(self.render_grid())
            else:
                print("Comando no reconocido.")

    def _simulation_loop(self) -> None:
        """Fase de simulación: Enter=1 tick | run N | speed N | grid | logs | reset | quit."""
        print("\n=== Simulación ===")
        print("Comandos: Enter=1 tick | run N | speed 1-5 | grid | logs | reset | quit")
        while True:
            raw = input("> ").strip()
            if raw == "quit" or raw == "q":
                return
            if raw == "" or raw == "s":
                print(self.step())
            elif raw.startswith("run"):
                count = int(raw.split()[1]) if len(raw.split()) > 1 and raw.split()[1].isdigit() else 10
                print(self.run_ticks(count))
            elif raw.startswith("speed"):
                n = int(raw.split()[1]) if len(raw.split()) > 1 else 1
                print(self.set_speed(n - 1))
            elif raw == "grid":
                print(self.render_grid())
            elif raw == "logs":
                for line in self.recent_logs():
                    print(line)
                if not self.logs:
                    print("(sin mensajes)")
            elif raw == "reset":
                print(self.reset())
                self._placement_loop()
            else:
                print("Comando no reconocido.")

    def _current_map(self):
        """Devuelve el GameMap actualmente seleccionado."""
        assert self.loaded is not None and self.engine is not None
        for game_map in self.loaded.maps.values():
            if game_map.width == self.world.width and game_map.height == self.world.height:
                return game_map
        return next(iter(self.loaded.maps.values()))
