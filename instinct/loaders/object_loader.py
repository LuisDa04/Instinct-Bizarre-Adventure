from __future__ import annotations

from dataclasses import dataclass

from ..world.entities import WorldObject
from .definition import entry_char, entry_range, parse_definition
from .errors import LoadError

OBJECT_KEYS: tuple[str, ...] = ("char", "resource_max")


@dataclass(frozen=True)
class ObjectResult:
    object: WorldObject | None
    char_line: int
    errors: list[LoadError]


def load_object(source: str) -> ObjectResult:
    name, entries, errors = parse_definition(source, "object", OBJECT_KEYS)
    char = entry_char(entries.get("char"), errors)
    resource_max = entry_range(entries.get("resource_max"), errors)
    if errors or name is None or char is None or resource_max is None:
        return ObjectResult(object=None, char_line=1, errors=errors)
    return ObjectResult(
        object=WorldObject(name, char, resource_max),
        char_line=entries["char"].line,
        errors=[],
    )
