"""Contexto de ejecución y protocolos para evaluación polimórfica de nodos AST.

Este módulo define los protocolos y el contexto de ejecución que permiten
a los nodos AST evaluarse/ejecutarse por sí mismos (polimorfismo)
sin que el intérprete necesite cadenas de isinstance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from instinct.world.world import World
    from instinct.sim.engine import Engine
    from instinct.world.entities import Creature
    from instinct.lang.environment import Environment
    from instinct.lang.perceptions import TurnFrame
    from instinct.lang.actions import Action


@dataclass
class ExecutionContext:
    """Contexto mutable que se pasa a los nodos durante la evaluación/ejecución.

    Atributos:
        world: Mundo donde ocurre la simulación.
        engine: Motor de simulación (RNG, rugidos, etc.).
        creature: Criatura que está ejecutando el turno actual.
        environment: Entorno de nombres (variables, percepciones, constantes).
        frame: Foto del turno para percepciones.
        log: Callable opcional para registrar mensajes.
        pc: Contador de programa (índice en body). Se modifica in-place.
        max_lines: Límite de líneas por turno (default 100).
        lines_executed: Contador de líneas ejecutadas en el turno actual.
        program_labels: Tabla de etiquetas -> índice en body.
    """

    world: "World"
    engine: "Engine"
    creature: "Creature"
    environment: "Environment"
    frame: "TurnFrame"
    log: Callable[[str], None] | None
    pc: int
    max_lines: int = 100
    lines_executed: int = 0
    program_labels: dict[str, int] | None = None


class Evaluatable(Protocol):
    """Protocolo para nodos que pueden evaluarse a un valor (int | str)."""

    def eval(self, ctx: "ExecutionContext") -> int | str:
        """Evalúa la expresión y devuelve su valor."""
        ...


class Executable(Protocol):
    """Protocolo para nodos que pueden ejecutarse como sentencia.

    Devuelve una acción si la sentencia consume el turno, o None si no.
    """

    def execute(self, ctx: "ExecutionContext") -> "Action | None":
        """Ejecuta la sentencia y devuelve la acción si consume turno."""
        ...


class ExecutableStmt(Protocol):
    """Protocolo unificado para sentencias ejecutables."""

    def execute(self, ctx: "ExecutionContext") -> "Action | None":
        """Ejecuta la sentencia. Retorna acción si consume turno."""
        ...