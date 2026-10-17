"""Acción `attack`: golpea lo que hay en la casilla apuntada (§2.4)."""

from __future__ import annotations

from .base import Action, ActionContext
from .strike import attacked_entity, strike


class Attack(Action):
    """Golpea a la criatura, al objeto o al terreno de la casilla apuntada."""

    name = "attack"
    arity = 3

    def validate(self, args: list[int | str], line: int) -> None:
        """Exige dx/dy en {-1, 0, 1} y un damage entero (§2.8).

        Args:
            args: Argumentos [dx, dy, damage] ya evaluados.
            line: Línea (1-based) de la llamada para el mensaje de error.
        """
        self._require_direction(args, 0, line)
        self._require_direction(args, 1, line)
        self._require_number(args, 2, line)

    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Aplica el daño al objetivo; fuera del mapa no hace nada (§3.4).

        Args:
            ctx: Mundo, motor y criatura que golpea.
            args: [dx, dy, damage] ya validados.
        """
        target = attacked_entity(ctx, args[0], args[1])
        if target is not None:
            strike(ctx, target, args[2])
