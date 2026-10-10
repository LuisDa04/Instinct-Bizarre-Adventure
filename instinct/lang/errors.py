"""Error de ejecución con la línea del fuente donde falló la criatura."""

from __future__ import annotations

from instinct.compiler.errors import CompileError


class ExecutionError(CompileError):
    """Error en tiempo de ejecución que interrumpe el turno con un ictus."""
    pass
