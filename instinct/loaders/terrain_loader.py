from __future__ import annotations

from dataclasses import dataclass

from ..world.entities import Terrain
from .definition import entry_char, entry_range, parse_definition
from .errors import LoadError

TERRAIN_KEYS: tuple[str, ...] = ("char", "resource_max", "regen")


@dataclass(frozen=True)
class TerrainResult:
    terrain: Terrain | None
    char_line: int
    errors: list[LoadError]


def load_terrain(source: str) -> TerrainResult:
    name, entries, errors = parse_definition(source, "terrain", TERRAIN_KEYS)
    char = entry_char(entries.get("char"), errors)
    resource_max = entry_range(entries.get("resource_max"), errors)
    regen = entry_range(entries.get("regen"), errors)
    if errors or name is None or char is None or resource_max is None or regen is None:
        return TerrainResult(terrain=None, char_line=1, errors=errors)
    return TerrainResult(
        terrain=Terrain(name, char, resource_max, regen),
        char_line=entries["char"].line,
        errors=[],
    )
