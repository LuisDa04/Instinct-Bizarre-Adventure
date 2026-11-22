"""Puertos de runtime para que el compilador no dependa de `instinct.lang`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .tokens import TokenType

if TYPE_CHECKING:
    from .execution_context import ExecutionContext


class ActionLike(Protocol):
    """Acción ejecutada que puede consumir el turno."""

    consumes_turn: bool


class RuntimeOps(Protocol):
    """Operaciones del lenguaje inyectadas al evaluar/ejecutar nodos AST."""

    def truthy(self, value: int | str) -> bool:
        """Devuelve si el valor cuenta como verdadero."""

    def negate(self, value: int | str, line: int) -> int:
        """Aplica el menos unario."""

    def apply_binary(
        self, op: TokenType, left: int | str, right: int | str, line: int
    ) -> int:
        """Aplica un operador binario."""

    def call_function(
        self,
        name: str,
        args: list[int | str],
        creature: object,
        world: object,
        line: int,
    ) -> int | str:
        """Invoca una función reservada del lenguaje."""

    def execute_action(
        self, name: str, args: list[int | str], ctx: "ExecutionContext", line: int
    ) -> ActionLike:
        """Valida y aplica una acción del lenguaje."""