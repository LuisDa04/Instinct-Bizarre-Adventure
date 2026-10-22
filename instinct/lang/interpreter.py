"""Intérprete que recorre el AST instrucción a instrucción."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from instinct.compiler.ast_nodes import (
    ActionCall,
    Assign,
    Binary,
    Call,
    Expr,
    Goto,
    Group,
    IfGoto,
    Label,
    Literal,
    Logical,
    Stmt,
    Unary,
    Variable,
)
from instinct.compiler.tokens import TokenType
from instinct.world.entities import Creature
from instinct.world.world import World
from .actions import ACTIONS, Action, ActionContext
from .environment import Environment
from .errors import ExecutionError
from .functions import FUNCTIONS
from .perceptions import TurnFrame, refresh
from .values import apply_binary, negate, truthy

if TYPE_CHECKING:
    from instinct.sim.engine import Engine

#: Máximo de líneas ejecutadas por turno; sin acción equivale a `wait(1)`.
MAX_LINES = 100


class Interpreter:
    """Ejecuta el turno de cada criatura sobre su programa resuelto.

    Se enchufa al motor con `engine.set_turn_runner(interpreter.run_turn)`.
    """

    def __init__(
        self,
        world: World,
        engine: Engine,
        log: Callable[[str], None] | None = None,
    ) -> None:
        """Crea el intérprete sobre el mundo y el motor dados.

        Args:
            world: Rejilla donde están colocadas las criaturas.
            engine: Motor que aporta tick, aleatoriedad y rugidos.
            log: Destino de textos o None para descartarlos.
        """
        self._world = world
        self._engine = engine
        self._log = log

    def run_turn(self, creature: Creature) -> None:
        """Ejecuta un turno: refresca percepciones y avanza hasta una acción.

        Un error de ejecución es un ictus: la criatura muere en el acto y el
        mensaje con su línea va al registro.

        Args:
            creature: Criatura viva y despierta que recibe el turno.
        """
        try:
            frame = refresh(creature, self._world, self._engine)
            env = Environment(creature.variables, frame)
            body = creature.program.body
            for _ in range(MAX_LINES):
                if creature.pc >= len(body):
                    creature.pc = creature.program.labels["start"]
                    return
                action = self._run_stmt(body[creature.pc], creature, env, frame)
                if action is not None and action.consumes_turn:
                    return
        except ExecutionError as error:
            self._engine.kill(creature)
            if self._log is not None:
                self._log(f"{creature.name}: {error}")

    def _run_stmt(
        self, stmt: Stmt, creature: Creature, env: Environment, frame: TurnFrame
    ) -> Action | None:
        """Ejecuta una instrucción y devuelve la acción si fue una llamada.

        Args:
            stmt: Instrucción en `creature.pc`.
            creature: Criatura que ejecuta; su `pc` siempre queda actualizado.
            env: Entorno con sus variables y la foto del turno.
            frame: Foto de percepciones para `see` y `name`.

        Returns:
            La acción ejecutada o None si la instrucción fue gratis.
        """
        if isinstance(stmt, Label):
            creature.pc += 1
            return None
        if isinstance(stmt, Goto):
            creature.pc = creature.program.labels[stmt.label]
            return None
        if isinstance(stmt, IfGoto):
            if truthy(self._eval(stmt.condition, creature, env, frame)):
                creature.pc = creature.program.labels[stmt.label]
            else:
                creature.pc += 1
            return None
        if isinstance(stmt, Assign):
            env.set(stmt.name, self._eval(stmt.value, creature, env, frame))
            creature.pc += 1
            return None
        return self._run_action(stmt, creature, env, frame)

    def _run_action(
        self, stmt: ActionCall, creature: Creature, env: Environment, frame: TurnFrame
    ) -> Action:
        """Evalúa los argumentos, avanza el PC y aplica la acción.

        Args:
            stmt: Llamada a una acción del catálogo.
            creature: Criatura que actúa; su `pc` apunta a lo siguiente.
            env: Entorno con sus variables y la foto del turno.
            frame: Foto de percepciones para `see` y `name`.

        Returns:
            La acción aplicada para que `run_turn` decida si el turno sigue.

        Raises:
            ExecutionError: Si la acción no está registrada (rama defensiva:
                el registro y el catálogo se comprueban en sincronía al
                importar, así que un programa resuelto no puede llegar aquí).
        """
        args = [self._eval(arg, creature, env, frame) for arg in stmt.args]
        creature.pc += 1
        action = ACTIONS.get(stmt.name)
        if action is None:
            raise ExecutionError(stmt.line, f"acción no implementada {stmt.name!r}")
        action.validate(args, stmt.line)
        action.apply(
            ActionContext(
                world=self._world,
                engine=self._engine,
                creature=creature,
                log=self._log,
            ),
            args,
        )
        return action

    def _eval(
        self, expr: Expr, creature: Creature, env: Environment, frame: TurnFrame
    ) -> int | str:
        """Evalúa una expresión a entero o texto con las reglas de tipos del lenguaje.

        Args:
            expr: Expresión del AST ya analizada.
            creature: Criatura que evalúa (para `see` y `name`).
            env: Entorno con sus variables y la foto del turno.
            frame: Foto de percepciones para `see` y `name`.

        Returns:
            Entero o texto; `and`/`or`/`not` y comparaciones dan 0 o 1.
        """
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, Variable):
            return env.get(expr.name, expr.line)
        if isinstance(expr, Group):
            return self._eval(expr.inner, creature, env, frame)
        if isinstance(expr, Unary):
            operand = self._eval(expr.operand, creature, env, frame)
            if expr.op is TokenType.MINUS:
                return negate(operand, expr.line)
            return 1 if not truthy(operand) else 0
        if isinstance(expr, Binary):
            left = self._eval(expr.left, creature, env, frame)
            right = self._eval(expr.right, creature, env, frame)
            return apply_binary(expr.op, left, right, expr.line)
        if isinstance(expr, Logical):
            return self._eval_logical(expr, creature, env, frame)
        return self._eval_call(expr, creature, env, frame)

    def _eval_logical(
        self, expr: Logical, creature: Creature, env: Environment, frame: TurnFrame
    ) -> int:
        """Evalúa `and`/`or` con cortocircuito y resultado siempre 0 o 1.

        Args:
            expr: Combinación lógica ya analizada.
            creature: Criatura que evalúa.
            env: Entorno con sus variables y la foto del turno.
            frame: Foto de percepciones para `see` y `name`.

        Returns:
            1 si la combinación es verdadera y 0 si no.
        """
        left = self._eval(expr.left, creature, env, frame)
        if expr.op is TokenType.AND:
            if not truthy(left):
                return 0
            return 1 if truthy(self._eval(expr.right, creature, env, frame)) else 0
        if truthy(left):
            return 1
        return 1 if truthy(self._eval(expr.right, creature, env, frame)) else 0

    def _eval_call(
        self, expr: Call, creature: Creature, env: Environment, frame: TurnFrame
    ) -> int | str:
        """Evalúa los argumentos y despacha a `see` o `name`.

        Args:
            expr: Llamada a función reservada (el resolver garantiza el nombre).
            creature: Criatura que pregunta.
            env: Entorno con sus variables y la foto del turno.
            frame: Foto de percepciones (no usada: las funciones miran el mundo).

        Returns:
            Entero (`see`) o texto (`name`).
        """
        args = [self._eval(arg, creature, env, frame) for arg in expr.args]
        return FUNCTIONS[expr.callee](args, creature, self._world, expr.line)
