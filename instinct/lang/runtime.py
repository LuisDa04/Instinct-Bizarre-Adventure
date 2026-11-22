"""Adaptador que implementa el puerto de runtime del compilador."""

from __future__ import annotations

from instinct.compiler.execution_context import ExecutionContext
from instinct.compiler.tokens import TokenType

from .actions import ACTIONS, ActionContext
from .errors import ExecutionError
from .functions import FUNCTIONS
from .values import apply_binary, negate, truthy


class LangRuntime:
    """Implementación concreta de las operaciones del lenguaje Instinct."""

    def truthy(self, value: int | str) -> bool:
        return truthy(value)

    def negate(self, value: int | str, line: int) -> int:
        return negate(value, line)

    def apply_binary(
        self, op: TokenType, left: int | str, right: int | str, line: int
    ) -> int:
        return apply_binary(op, left, right, line)

    def call_function(
        self,
        name: str,
        args: list[int | str],
        creature: object,
        world: object,
        line: int,
    ) -> int | str:
        return FUNCTIONS[name](args, creature, world, line)

    def execute_action(
        self, name: str, args: list[int | str], ctx: ExecutionContext, line: int
    ):
        action = ACTIONS.get(name)
        if action is None:
            raise ExecutionError(line, f"acción no implementada {name!r}")
        action.validate(args, line)
        action.apply(
            ActionContext(
                world=ctx.world,
                engine=ctx.engine,
                creature=ctx.creature,
                log=ctx.log,
            ),
            args,
            line,
        )
        return action


LANG_RUNTIME = LangRuntime()