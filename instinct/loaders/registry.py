"""Registro de terrenos y objetos con control de chars únicos."""
from __future__ import annotations

from pathlib import Path

from ..world.entities import Terrain, WorldObject
from .errors import LoadError
from .object_loader import load_object
from .terrain_loader import load_terrain


class Registry:
    """Representa el catálogo de terrenos y objetos con chars únicos entre ambos tipos.

    Invariante: cada char solo pertenece a un nombre y el primer terreno es la base.
    """

    def __init__(self) -> None:
        """Crea un registro vacío sin terrenos ni objetos."""
        self.terrains: list[Terrain] = []
        self.objects: list[WorldObject] = []
        self._chars: dict[str, str] = {}

    @property
    def base_terrain(self) -> Terrain:
        """Devuelve el primer terreno registrado como base del mapa.

        Raises:
            IndexError: Si aún no se registró ningún terreno.
        """
        return self.terrains[0]

    def terrain_for(self, char: str) -> Terrain | None:
        """Devuelve el terreno con ese char o None si no existe."""
        for terrain in self.terrains:
            if terrain.char == char:
                return terrain
        return None

    def object_for(self, char: str) -> WorldObject | None:
        """Devuelve el objeto con ese char o None si no existe."""
        for obj in self.objects:
            if obj.char == char:
                return obj
        return None

    def add_terrain(self, terrain: Terrain, char_line: int) -> LoadError | None:
        """Registra un terreno si su char está libre; si no, devuelve el conflicto.

        Args:
            terrain: Se guarda por referencia, no se clona.
            char_line: Línea del char para ubicar el posible error.

        Returns:
            None si se registró, o LoadError con el dueño previo del char.
        """
        conflict = self._claim(terrain.char, terrain.name, char_line)
        if conflict is not None:
            return conflict
        self.terrains.append(terrain)
        return None

    def add_object(self, obj: WorldObject, char_line: int) -> LoadError | None:
        """Registra un objeto si su char está libre; si no, devuelve el conflicto.

        Args:
            obj: Se guarda por referencia, no se clona.
            char_line: Línea del char para ubicar el posible error.

        Returns:
            None si se registró, o LoadError con el dueño previo del char.
        """
        conflict = self._claim(obj.char, obj.name, char_line)
        if conflict is not None:
            return conflict
        self.objects.append(obj)
        return None

    def _claim(self, char: str, name: str, line: int) -> LoadError | None:
        """Reserva un char para un nombre o devuelve el error de duplicado.

        Returns:
            None si el char quedó reservado, o LoadError si ya tenía dueño.
        """
        if char in self._chars:
            return LoadError(
                line, f"el char {char!r} ya está declarado por {self._chars[char]!r}"
            )
        self._chars[char] = name
        return None


def load_definitions(
    terrains_dir: Path, objects_dir: Path
) -> tuple[Registry, list[LoadError]]:
    """Carga todos los .te y .ob de dos carpetas y devuelve registro y errores.

    Recorre cada carpeta en orden alfabético, conserva lo válido y acumula errores con su ruta.

    Args:
        terrains_dir: Carpeta con ficheros *.te.
        objects_dir: Carpeta con ficheros *.ob.

    Returns:
        Tupla (registro, errores): el primer terreno válido gana ante un char repetido.
    """
    registry = Registry()
    errors: list[LoadError] = []
    for path in sorted(terrains_dir.glob("*.te")):
        result = load_terrain(path.read_text(encoding="utf-8"))
        errors.extend(_tagged(result.errors, path))
        if result.terrain is not None:
            conflict = registry.add_terrain(result.terrain, result.char_line)
            if conflict is not None:
                errors.append(_tagged([conflict], path)[0])
    for path in sorted(objects_dir.glob("*.ob")):
        result = load_object(path.read_text(encoding="utf-8"))
        errors.extend(_tagged(result.errors, path))
        if result.object is not None:
            conflict = registry.add_object(result.object, result.char_line)
            if conflict is not None:
                errors.append(_tagged([conflict], path)[0])
    return registry, errors


def _tagged(errors: list[LoadError], path: Path) -> list[LoadError]:
    """Etiqueta cada error con la ruta del fichero que lo produjo.

    Returns:
        Nueva lista de errores con path informado; la lista original no se modifica.
    """
    return [LoadError(error.line, error.message, str(path)) for error in errors]
