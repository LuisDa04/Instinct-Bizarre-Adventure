"""Acción `reproduce`: crea una cría adyacente a costa de vida."""

from __future__ import annotations

from instinct.world.entities import Creature

from .base import Action, ActionContext


class Reproduce(Action):
    """Crea una cría de la misma especie en la casilla adyacente indicada."""

    name = "reproduce"
    arity = 3

    def validate(self, args: list[int | str], line: int) -> None:
        """Exige dx/dy en {-1, 0, 1} y un health entero.

        Args:
            args: Argumentos [dx, dy, health] ya evaluados.
            line: Línea (1-based) de la llamada para el mensaje de error.
        """
        self._require_direction(args, 0, line)
        self._require_direction(args, 1, line)
        self._require_number(args, 2, line)

    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Nace una cría si la casilla está libre y la madre puede pagarla.

        Requiere dirección real (distancia 1), casilla con solo terreno,
        cría viable (health >= 1) y madre con más vida que ese costo; cualquier
        fallo es un aborto natural que igualmente gasta el turno.

        Args:
            ctx: Mundo, motor y madre.
            args: [dx, dy, health] ya validados.
        """
        dx, dy, health = args
        if dx == 0 and dy == 0:
            return
        if health < 1:
            return
        x, y = ctx.creature.x + dx, ctx.creature.y + dy
        if not ctx.world.walkable(x, y):
            return
        if ctx.creature.health <= health:
            return
        ctx.creature.health -= health
        child = Creature(ctx.creature.program)
        child.health = health
        assert ctx.world.place_creature(x, y, child)
        ctx.engine.queue_newborn(child)
