"""Acción `say`: muestra un texto sin consumir turno (§2.4)."""

from __future__ import annotations

from .base import Action, ActionContext


class Say(Action):
    """Muestra un texto en el registro; la única acción que no gasta turno."""

    name = "say"
    arity = 1
    consumes_turn = False

    def validate(self, args: list[int | str], line: int) -> None:
        """Acepta cualquier valor: texto o número (§2.5)."""

    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Lleva el texto al registro (D23); sin registro se descarta.

        Args:
            ctx: Criatura que habla y registro destino.
            args: [value] ya evaluado; un número se muestra como cifra.
        """
        if ctx.log is not None:
            ctx.log(f"{ctx.creature.name} dice: {args[0]}")
