"""Acción `roar`: emite un rugido que se oirá en el tick siguiente (§2.4)."""

from __future__ import annotations

from .base import Action, ActionContext


class Roar(Action):
    """Ruge un texto audible al tick siguiente dentro de la visión (D5, D20)."""

    name = "roar"
    arity = 1

    def validate(self, args: list[int | str], line: int) -> None:
        """Acepta cualquier valor: texto o número (§2.5)."""

    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Encola el rugido en el motor y lo lleva al registro (D23).

        Args:
            ctx: Mundo, motor y criatura que ruge.
            args: [value] ya evaluado; un número se muestra como cifra.
        """
        text = str(args[0])
        ctx.engine.emit_roar(ctx.creature.x, ctx.creature.y, text)
        if ctx.log is not None:
            ctx.log(f"{ctx.creature.name} ruge: {text}")
