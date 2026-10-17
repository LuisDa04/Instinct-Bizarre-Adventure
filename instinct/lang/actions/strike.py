"""Resolución de objetivos y golpe compartido por attack y consume (§2.4, §3.4)."""

from __future__ import annotations

from instinct.world.entities import Creature, Entity

from .base import ActionContext


def attacked_entity(ctx: ActionContext, dx: int, dy: int) -> Entity | None:
    """Devuelve lo que golpea la acción según su dirección.

    Con (0, 0) el objetivo es el terreno bajo la propia criatura (§2.4);
    fuera del mapa no hay objetivo: la acción no hace nada (§3.4).

    Args:
        ctx: Mundo, motor y criatura que golpea.
        dx: Desplazamiento de columna en {-1, 0, 1}.
        dy: Desplazamiento de fila en {-1, 0, 1}.

    Returns:
        La entidad golpeada o None si la casilla cae fuera del mapa.
    """
    creature = ctx.creature
    if dx == 0 and dy == 0:
        terrain = ctx.world.terrain_at(creature.x, creature.y)
        assert terrain is not None  # una criatura colocada siempre está dentro
        return terrain
    x, y = creature.x + dx, creature.y + dy
    target = ctx.world.creature_at(x, y)
    if target is None:
        target = ctx.world.object_at(x, y)
    if target is None:
        target = ctx.world.terrain_at(x, y)
    return target


def strike(ctx: ActionContext, target: Entity, damage: int) -> None:
    """Aplica el daño al objetivo y entierra en el acto a la criatura muerta (§3.4).

    Args:
        ctx: Mundo, motor y criatura que golpea.
        target: Entidad golpeada; su reserva pierde el daño.
        damage: Cantidad a restar; negativo repone hasta el tope (D22).
    """
    target.hit(damage)
    if isinstance(target, Creature) and target.health <= 0:
        ctx.engine.kill(target)
