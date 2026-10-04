from __future__ import annotations

from pathlib import Path

from ..world.entities import Terrain, WorldObject
from .errors import LoadError
from .object_loader import load_object
from .terrain_loader import load_terrain


class Registry:
    def __init__(self) -> None:
        self.terrains: list[Terrain] = []
        self.objects: list[WorldObject] = []
        self._chars: dict[str, str] = {}

    @property
    def base_terrain(self) -> Terrain:
        return self.terrains[0]

    def terrain_for(self, char: str) -> Terrain | None:
        for terrain in self.terrains:
            if terrain.char == char:
                return terrain
        return None

    def object_for(self, char: str) -> WorldObject | None:
        for obj in self.objects:
            if obj.char == char:
                return obj
        return None

    def add_terrain(self, terrain: Terrain, char_line: int) -> LoadError | None:
        conflict = self._claim(terrain.char, terrain.name, char_line)
        if conflict is not None:
            return conflict
        self.terrains.append(terrain)
        return None

    def add_object(self, obj: WorldObject, char_line: int) -> LoadError | None:
        conflict = self._claim(obj.char, obj.name, char_line)
        if conflict is not None:
            return conflict
        self.objects.append(obj)
        return None

    def _claim(self, char: str, name: str, line: int) -> LoadError | None:
        if char in self._chars:
            return LoadError(
                line, f"el char {char!r} ya está declarado por {self._chars[char]!r}"
            )
        self._chars[char] = name
        return None


def load_definitions(
    terrains_dir: Path, objects_dir: Path
) -> tuple[Registry, list[LoadError]]:
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
    return [LoadError(error.line, error.message, str(path)) for error in errors]
