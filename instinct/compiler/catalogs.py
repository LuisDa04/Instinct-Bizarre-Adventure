"""Catálogos fijos del lenguaje con nombres y aridades válidas.

ACTION_ARITY: acciones como sentencia con su número de argumentos.
FUNCTION_ARITY: funciones de expresión con su número de argumentos.
PERCEPTIONS: variables de solo lectura que describen estado y entorno.
CONSTANTS: valores simbólicos comparables en expresiones.
READ_ONLY_NAMES: unión de percepciones, constantes y funciones no asignables.
HEADER_KEYS: claves obligatorias de la cabecera en su orden esperado.
"""

from __future__ import annotations

ACTION_ARITY: dict[str, int] = {
    "wait": 1,
    "move": 3,
    "attack": 3,
    "consume": 4,
    "reproduce": 3,
    "roar": 1,
    "say": 1,
}

FUNCTION_ARITY: dict[str, int] = {
    "see": 2,
    "name": 2,
}

PERCEPTIONS: frozenset[str] = frozenset(
    {
        "health",
        "age",
        "lifespan",
        "vision",
        "species",
        "faction",
        "x",
        "y",
        "terrain_here",
        "reserve_here",
        "width",
        "height",
        "tick",
        "total_creatures",
        "total_allies",
        "total_enemies",
        "random",
        "allies_near",
        "enemies_near",
        "objects_near",
        "enemy_dist",
        "enemy_dx",
        "enemy_dy",
        "ally_dist",
        "ally_dx",
        "ally_dy",
        "object_dist",
        "object_dx",
        "object_dy",
        "roars_near",
        "last_roar",
    }
)

CONSTANTS: frozenset[str] = frozenset({"NONE", "GROUND", "OBJECT", "ALLY", "ENEMY"})

READ_ONLY_NAMES: frozenset[str] = PERCEPTIONS | CONSTANTS | frozenset(FUNCTION_ARITY)

HEADER_KEYS: tuple[str, ...] = ("creature", "faction", "health", "vision", "lifespan")
