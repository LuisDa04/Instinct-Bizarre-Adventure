"""Sensores del mundo: conteos y criaturas u objetos más cercanos por radio."""

from __future__ import annotations

from dataclasses import dataclass

from .entities import Creature
from .world import World

#: Tripleta (distancia, dx, dy) cuando no hay ningún candidato visible.
MISSING: tuple[int, int, int] = (-1, 0, 0)


@dataclass(frozen=True)
class WorldSense:
    """Foto de lo que una criatura percibe del mundo al empezar su turno.

    Attributes:
        total_creatures: Criaturas vivas en el mapa sin contarse a sí misma.
        total_allies: De ellas, las de su misma facción.
        total_enemies: De ellas, las de otra facción.
        allies_near: Aliados dentro del radio de visión, sin contarse.
        enemies_near: Enemigos dentro del radio de visión.
        objects_near: Objetos dentro del radio de visión.
        enemy: (distancia, dx, dy) al enemigo más cercano o MISSING.
        ally: (distancia, dx, dy) al aliado más cercano o MISSING.
        object: (distancia, dx, dy) al objeto más cercano o MISSING.
    """

    total_creatures: int
    total_allies: int
    total_enemies: int
    allies_near: int
    enemies_near: int
    objects_near: int
    enemy: tuple[int, int, int]
    ally: tuple[int, int, int]
    object: tuple[int, int, int]


def _sign(step: int) -> int:
    """Devuelve -1, 0 o 1 según el signo del desplazamiento."""
    return (step > 0) - (step < 0)


def sense(world: World, creature: Creature) -> WorldSense:
    """Recorre el radio de visión y resume conteos y candidatos más cercanos.

    Args:
        world: Rejilla donde la criatura está colocada.
        creature: Criatura que percibe, con su posición y visión.

    Returns:
        WorldSense con la foto congelada; los empates se rompen por
        (distancia, y, x) para que sean estables (decisión D4).
    """
    total_allies = 0
    total_enemies = 0
    for other in world.creatures():
        if other is creature:
            continue
        if other.faction == creature.faction:
            total_allies += 1
        else:
            total_enemies += 1

    allies_near = 0
    enemies_near = 0
    objects_near = 0
    best_enemy: tuple[int, int, int, int] | None = None
    best_ally: tuple[int, int, int, int] | None = None
    best_object: tuple[int, int, int, int] | None = None
    for dy in range(-creature.vision, creature.vision + 1):
        for dx in range(-creature.vision, creature.vision + 1):
            dist = max(abs(dx), abs(dy))
            if dist == 0 or dist > creature.vision:
                continue
            x = creature.x + dx
            y = creature.y + dy
            seen = world.creature_at(x, y)
            if seen is not None:
                if seen.faction == creature.faction:
                    allies_near += 1
                    key = (dist, y, x)
                    if best_ally is None or key < best_ally[0]:
                        best_ally = (key, dist, _sign(dx), _sign(dy))
                else:
                    enemies_near += 1
                    key = (dist, y, x)
                    if best_enemy is None or key < best_enemy[0]:
                        best_enemy = (key, dist, _sign(dx), _sign(dy))
            elif world.object_at(x, y) is not None:
                objects_near += 1
                key = (dist, y, x)
                if best_object is None or key < best_object[0]:
                    best_object = (key, dist, _sign(dx), _sign(dy))

    return WorldSense(
        total_creatures=total_allies + total_enemies,
        total_allies=total_allies,
        total_enemies=total_enemies,
        allies_near=allies_near,
        enemies_near=enemies_near,
        objects_near=objects_near,
        enemy=best_enemy[1:] if best_enemy is not None else MISSING,
        ally=best_ally[1:] if best_ally is not None else MISSING,
        object=best_object[1:] if best_object is not None else MISSING,
    )
