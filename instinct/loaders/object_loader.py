"""Carga de objetos desde texto con claves char y resource_max."""
from __future__ import annotations

from dataclasses import dataclass

from ..world.entities import WorldObject
from .definition import entry_char, entry_range, parse_definition
from .errors import LoadError

OBJECT_KEYS: tuple[str, ...] = ("char", "resource_max")


@dataclass(frozen=True)
class ObjectResult:
    """Representa el resultado de cargar un objeto: instancia o None más errores.

    Invariante: object es None si hubo errores; char_line es 1 cuando falla.
    """

    object: WorldObject | None
    char_line: int
    errors: list[LoadError]


def load_object(source: str) -> ObjectResult:
    """Carga un objeto desde su texto y devuelve el resultado con sus errores.

    Args:
        source: Texto con cabecera 'object Nombre' y claves char y resource_max.

    Returns:
        ObjectResult con object válido y errores vacíos, o object None y errores no vacíos.
    """
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
