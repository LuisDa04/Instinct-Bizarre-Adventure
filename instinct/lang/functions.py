"""Funciones reservadas `see` y `name` con coordenadas absolutas."""

from __future__ import annotations

from collections.abc import Callable

from instinct.compiler.catalogs import FUNCTION_ARITY
from instinct.world.entities import Creature
from instinct.world.world import World
from .errors import ExecutionError
from .values import CONSTANT_VALUES

#: Implementación de función reservada: recibe argumentos evaluados y devuelve un valor.
FunctionImpl = Callable[[list[int | str], Creature, World, int], int | str]


def _coords(callee: str, args: list[int | str], line: int) -> tuple[int, int]:
    """Extrae las dos coordenadas absolutas o lanza ictus si hay texto.

    Args:
        callee: Nombre de la función para el mensaje de error.
        args: Argumentos ya evaluados (la aridad la garantiza el resolver).
        line: Línea (1-based) de la llamada para el mensaje de error.

    Returns:
        Tupla (x, y) con las coordenadas pedidas.

    Raises:
        ExecutionError: Si alguna coordenada es texto.
    """
    x, y = args[0], args[1]
    if not isinstance(x, int) or not isinstance(y, int):
        raise ExecutionError(line, f"la función {callee!r} espera números")
    return x, y


def _distance(creature: Creature, x: int, y: int) -> int:
    """Devuelve la distancia de Chebyshev entre la criatura y la casilla."""
    return max(abs(x - creature.x), abs(y - creature.y))


def see(args: list[int | str], creature: Creature, world: World, line: int) -> int:
    """Devuelve qué hay en la casilla con el orden de comprobación de R8.

    Args:
        args: Coordenadas absolutas `[x, y]` ya evaluadas.
        creature: Criatura que pregunta, con su posición, facción y visión.
        world: Rejilla donde está colocada.
        line: Línea (1-based) de la llamada para el mensaje de error.

    Returns:
        Entero de la constante avistada (`NONE` se comprueba primero).
    """
    x, y = _coords("see", args, line)
    if _distance(creature, x, y) > creature.vision:
        return CONSTANT_VALUES["NONE"]
    if not world.in_bounds(x, y):
        return CONSTANT_VALUES["OBJECT"]
    seen = world.creature_at(x, y)
    if seen is not None:
        if seen.faction == creature.faction:
            return CONSTANT_VALUES["ALLY"]
        return CONSTANT_VALUES["ENEMY"]
    if world.object_at(x, y) is not None:
        return CONSTANT_VALUES["OBJECT"]
    return CONSTANT_VALUES["GROUND"]


def name_at(args: list[int | str], creature: Creature, world: World, line: int) -> str:
    """Devuelve el nombre de lo que hay en la casilla o "" si no se ve.

    Args:
        args: Coordenadas absolutas `[x, y]` ya evaluadas.
        creature: Criatura que pregunta, con su posición y visión.
        world: Rejilla donde está colocada.
        line: Línea (1-based) de la llamada para el mensaje de error.

    Returns:
        Especie, objeto o terreno; "" fuera del radio de visión o del mapa.
    """
    x, y = _coords("name", args, line)
    if _distance(creature, x, y) > creature.vision or not world.in_bounds(x, y):
        return ""
    seen = world.creature_at(x, y)
    if seen is not None:
        return seen.name
    found = world.object_at(x, y)
    if found is not None:
        return found.name
    ground = world.terrain_at(x, y)
    assert ground is not None
    return ground.name


#: Una implementación por función reservada: la alternativa al `if nombre == ...`.
FUNCTIONS: dict[str, FunctionImpl] = {
    "see": see,
    "name": name_at,
}

assert set(FUNCTIONS) == set(FUNCTION_ARITY)
