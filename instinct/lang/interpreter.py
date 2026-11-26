from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from instinct.compiler.execution_context import ExecutionContext
from instinct.compiler.runtime import RuntimeOps
from instinct.world.entities import Creature
from instinct.world.world import World
from .environment import Environment
from .errors import ExecutionError
from .perceptions import refresh
from .runtime import LANG_RUNTIME

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
        runtime: RuntimeOps | None = None,
    ) -> None:
        """Crea el intérprete sobre el mundo y el motor dados.

        Args:
            world: Rejilla donde están colocadas las criaturas.
            engine: Motor que aporta tick, aleatoriedad y rugidos.
            log: Destino de textos o None para descartarlos.
            runtime: Operaciones del lenguaje inyectadas; por defecto LangRuntime.
        """
        self._world = world
        self._engine = engine
        self._log = log
        self._runtime = runtime or LANG_RUNTIME

    def run_turn(self, creature: Creature) -> None:
        """Ejecuta un turno: refresca percepciones y avanza hasta una acción.

        Un error de ejecución o un `RuntimeError` inesperado es un ictus: la
        criatura muere en el acto y el mensaje va al registro. `ExecutionError`
        ya incluye su línea; el `RuntimeError` se registra tal cual.

        Args:
            creature: Criatura viva y despierta que recibe el turno.
        """
        try:
            frame = refresh(creature, self._world, self._engine)
            body = creature.program.body

            ctx = ExecutionContext(
                world=self._world,
                engine=self._engine,
                creature=creature,
                environment=Environment(creature.variables, frame),
                log=self._log,
                pc=creature.pc,
                runtime=self._runtime,
                program_labels=creature.program.labels,
            )

            for _ in range(MAX_LINES):
                if ctx.pc >= len(body):
                    ctx.pc = creature.program.labels["start"]
                    creature.pc = ctx.pc
                    return

                stmt = body[ctx.pc]
                action = stmt.execute(ctx)

                if action is not None and action.consumes_turn:
                    creature.pc = ctx.pc
                    return

                creature.pc = ctx.pc

        except (ExecutionError, RuntimeError) as error:
            self._engine.kill(creature)
            if self._log is not None:
                self._log(f"{creature.name}: {error}")