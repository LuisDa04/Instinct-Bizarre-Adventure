"""Acción `move`: avanza casilla a casilla hasta un tope."""

from __future__ import annotations

from .base import Action, ActionContext


class Move(Action):
    """Avanza hasta `speed` casillas en dirección (dx, dy) deteniéndose ante lo impisable."""

    name = "move"
    arity = 3

    def validate(self, args: list[int | str], line: int) -> None:
        """Exige dx/dy en {-1, 0, 1} y un speed entero.

        Args:
            args: Argumentos [dx, dy, speed] ya evaluados.
            line: Línea (1-based) de la llamada para el mensaje de error.
        """
        self._require_direction(args, 0, line)
        self._require_direction(args, 1, line)
        self._require_number(args, 2, line)

    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Camina una a una hasta `speed` casillas o la primera no pisable.

        Con (0, 0) o speed no positivo no avanza; el turno se gasta igual
        porque toda acción salvo say lo consume.

        Args:
            ctx: Mundo y criatura que camina.
            args: [dx, dy, speed] ya validados.
        """
        dx, dy, speed = args
        for _ in range(speed):
            if not ctx.world.move_creature(
                ctx.creature, ctx.creature.x + dx, ctx.creature.y + dy
            ):
                break
