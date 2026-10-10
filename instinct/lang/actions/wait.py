"""Acción `wait`: deja pasar turnos sin ejecutar nada (§2.4)."""

from __future__ import annotations

from .base import Action, ActionContext
from ..errors import ExecutionError


class Wait(Action):
    """Espera `n` turnos seguidos; `n < 1` cuenta como 1."""

    name = "wait"
    arity = 1

    def validate(self, args: list[int | str], line: int) -> None:
        """Exige un número o lanza ictus (§2.8).

        Args:
            args: Argumento `n` ya evaluado.
            line: Línea (1-based) de la llamada para el mensaje de error.
        """
        if not isinstance(args[0], int):
            raise ExecutionError(line, "la acción 'wait' espera un número")

    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Programa los `n - 1` turnos siguientes sin ejecutar nada (ley 4).

        Args:
            ctx: Contexto con la criatura que duerme.
            args: `[n]` ya validado como entero.
        """
        n = args[0]
        assert isinstance(n, int)
        ctx.creature.wait_remaining = max(1, n) - 1
