"""Puente fino entre el compilador existente y la UI del editor.

Reutiliza ``instinct.loaders.creature_loader.load_creature`` (que ya hace
scan + parse + resolve) y los catálogos de ``instinct.compiler.catalogs``.
No duplica ninguna lógica de compilación.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from instinct.compiler.catalogs import (
    ACTION_ARITY,
    FUNCTION_ARITY,
    HEADER_KEYS,
    CONSTANTS,
    PERCEPTIONS,
    READ_ONLY_NAMES,
)
from instinct.compiler.lexer import KEYWORDS
from instinct.loaders.creature_loader import CreatureResult, load_creature


@dataclass(frozen=True)
class Diagnostic:
    """Error/warning unificado para la UI del editor.

    Attributes:
        line: Línea 1-based donde ocurre el error.
        column: Columna 0-based (reservada para futuro; siempre 0 por ahora).
        severity: "error" o "warning".
        message: Texto legible del error en español.
        code: Categoría estable del error: "LEXICAL", "SYNTAX", "SEMANTIC",
            "LOAD" o "RUNTIME". "UNKNOWN" solo como fallback defensivo.
    """

    line: int
    column: int
    severity: str
    message: str
    code: str


def compile_source(source: str) -> tuple[Optional[object], list[Diagnostic]]:
    """Compila un fichero .ins completo reutilizando ``load_creature``.

    Args:
        source: Texto fuente completo del .ins (cabecera + cuerpo).

    Returns:
        Tupla (programa_resuelto, diagnosticos). Si hay errores,
        ``programa_resuelto`` es ``None`` y los diagnósticos contienen
        todos los problemas encontrados.
    """
    result: CreatureResult = load_creature(source)
    diagnostics = [
        Diagnostic(
            line=error.line,
            column=0,
            severity="error",
            message=error.message,
            code=getattr(error, "code", "UNKNOWN"),
        )
        for error in result.errors
    ]
    if result.creature is not None:
        return result.creature, diagnostics
    return None, diagnostics


def get_catalogs() -> dict:
    """Catálogos unificados para highlighter, completer y linter.

    Todos los nombres vienen de ``instinct.compiler.catalogs`` para que
    cualquier cambio ahí se refleje automáticamente en el editor.
    """
    return {
        "keywords": list(KEYWORDS.keys()),
        "actions": dict(ACTION_ARITY),
        "functions": dict(FUNCTION_ARITY),
        "perceptions": set(PERCEPTIONS),
        "constants": set(CONSTANTS),
        "read_only": set(READ_ONLY_NAMES),
        "header_keys": list(HEADER_KEYS),
    }
