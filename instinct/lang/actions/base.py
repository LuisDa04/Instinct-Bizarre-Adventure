"""Base de las acciones del lenguaje y contexto para aplicarlas (§5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from instinct.world.entities import Creature
from instinct.world.world import World

if TYPE_CHECKING:
    from instinct.sim.engine import Engine


@dataclass(frozen=True)
class ActionContext:
    """Todo lo que una acción necesita para tocar el mundo.

    Attributes:
        world: Rejilla donde está colocada la criatura.
        engine: Motor para encolar nacidas o rugidos.
        creature: Criatura que ejecuta la acción.
        log: Destino de textos o None para descartarlos.
    """

    world: World
    engine: Engine
    creature: Creature
    log: Callable[[str], None] | None = None


class Action(ABC):
    """Una acción del lenguaje: valida sus argumentos y aplica su efecto.

    El intérprete llama primero a `validate` y después a `apply`, así que
    `apply` puede suponer argumentos del tipo correcto.
    """

    name: str
    arity: int
    consumes_turn: bool = True

    @abstractmethod
    def validate(self, args: list[int | str], line: int) -> None:
        """Comprueba los argumentos ya evaluados o lanza ictus.

        Args:
            args: Argumentos evaluados (la aridad la garantiza el resolver).
            line: Línea (1-based) de la llamada para el mensaje de error.
        """

    @abstractmethod
    def apply(self, ctx: ActionContext, args: list[int | str]) -> None:
        """Aplica el efecto de la acción sobre el mundo.

        Args:
            ctx: Mundo, motor, criatura y log.
            args: Argumentos ya validados por `validate`.
        """
