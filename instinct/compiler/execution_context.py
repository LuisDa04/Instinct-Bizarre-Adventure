"""Contexto de ejecución y protocolos para evaluación polimórfica de nodos AST.

Este módulo define los contratos que permiten a los nodos AST evaluarse y
ejecutarse sin que el compilador dependa de `instinct.lang`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Protocol

from .runtime import ActionLike, RuntimeOps

if TYPE_CHECKING:
    from instinct.sim.engine import Engine
    from instinct.world.entities import Creature
    from instinct.world.world import World


class EnvironmentLike(Protocol):
    """Entorno mínimo que necesitan los nodos AST."""

    def get(self, name: str, line: int) -> int | str:
        """Resuelve un nombre."""

    def set(self, name: str, value: int | str) -> None:
        """Asigna una variable."""


@dataclass
class ExecutionContext:
    """Contexto mutable que se pasa a los nodos durante la evaluación/ejecución."""

    world: "World"
    engine: "Engine"
    creature: "Creature"
    environment: EnvironmentLike
    log: Callable[[str], None] | None
    pc: int
    runtime: RuntimeOps
    program_labels: dict[str, int] | None = None


class Evaluatable(Protocol):
    """Protocolo para nodos que pueden evaluarse a un valor (int | str)."""

    def eval(self, ctx: "ExecutionContext") -> int | str:
        """Evalúa la expresión y devuelve su valor."""
        ...


class Executable(Protocol):
    """Protocolo para nodos que pueden ejecutarse como sentencia."""

    def execute(self, ctx: "ExecutionContext") -> ActionLike | None:
        """Ejecuta la sentencia y devuelve la acción si consume turno."""
        ...