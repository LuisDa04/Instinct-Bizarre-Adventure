"""Acción `consume`: golpea como attack y además cura a quien consume (§2.4)."""

from __future__ import annotations

from .base import Action, ActionContext
from .strike import attacked_entity, strike


class Consume(Action):
    """Golpea el objetivo y gana heal puntos de vida sin tope (I5)."""

    name = "consume"
    arity = 4

    def validate(self, args: list[int | str], line: int) -> None:
        """Exige dx/dy en {-1, 0, 1} y damage/heal enteros (§2.8).

        Args:
            args: Argumentos [dx, dy, damage, heal] ya evaluados.
            line: Línea (1-based) de la llamada para el mensaje de error.
        """
        self._require_direction(args, 0, line)
        self._require_direction(args, 1, line)
        self._require_number(args, 2, line)
        self._require_number(args, 3, line)

    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Golpea como attack y cura; sin objetivo no hace nada (§3.4).

        La cura no se relaciona con el daño ni con el objetivo (§2.4); un
        heal negativo daña a la propia criatura y, si la deja en 0 o menos,
        muere en el acto (§3.4, D22).

        Args:
            ctx: Mundo, motor y criatura que consume.
            args: [dx, dy, damage, heal] ya validados.
        """
        target = attacked_entity(ctx, args[0], args[1])
        if target is None:
            return
        strike(ctx, target, args[2])
        ctx.creature.health += args[3]
        if ctx.creature.health <= 0:
            ctx.engine.kill(ctx.creature)
