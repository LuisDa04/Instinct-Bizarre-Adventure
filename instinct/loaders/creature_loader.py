"""Carga de criaturas .ins compilando con el front-end y escaneando la carpeta."""
from __future__ import annotations

from pathlib import Path

from ..compiler.errors import CompileError
from ..compiler.lexer import scan
from ..compiler.parser import parse
from ..compiler.semantic import ResolvedProgram, resolve
from .errors import LoadError, tag_errors
from dataclasses import dataclass


@dataclass(frozen=True)
class CreatureResult:
    """Resultado de compilar una criatura: programa resuelto o None más errores.

    Invariante: creature es None si y solo si errors no está vacío.
    """

    creature: ResolvedProgram | None
    errors: list[LoadError]


def load_creature(source: str) -> CreatureResult:
    """Compila un .ins de principio a fin y devuelve el programa o los errores.

    Recorre las tres etapas del front-end en orden: escaneo, análisis
    sintáctico y resolución semántica. Cada etapa aborta si la anterior
    acumuló errores, y todos los errores se convierten a LoadError con su
    línea para que el registro de la aplicación los muestre igual que los
    de terrenos, objetos y mapas.

    Args:
        source: Texto completo del .ins (cabecera + cuerpo).

    Returns:
        CreatureResult con creature válido y errores vacíos, o creature None y errores no vacíos.
    """
    errors: list[LoadError] = []
    scanned = scan(source)
    if scanned.errors:
        errors.extend(_as_load_errors(scanned.errors))
        return CreatureResult(creature=None, errors=errors)
    parsed = parse(scanned.tokens)
    if parsed.errors:
        errors.extend(_as_load_errors(parsed.errors))
        return CreatureResult(creature=None, errors=errors)
    if parsed.program is None:
        return CreatureResult(creature=None, errors=errors)
    resolved = resolve(parsed.program)
    if resolved.errors or resolved.resolved is None:
        errors.extend(_as_load_errors(resolved.errors))
        return CreatureResult(creature=None, errors=errors)
    return CreatureResult(creature=resolved.resolved, errors=[])


def load_creatures(
    creatures_dir: Path,
) -> tuple[dict[str, ResolvedProgram], list[LoadError]]:
    """Carga todos los .ins de una carpeta y devuelve los válidos y los errores.

    Recorre la carpeta en orden alfabético, conserva lo válido y acumula los
    errores etiquetados con su ruta. Una criatura cuyo nombre ya fue declarado
    por otro archivo se rechaza con un error en vez de sobrescribir.

    Args:
        creatures_dir: Carpeta con ficheros *.ins.

    Returns:
        Tupla (criaturas, errores): dict nombre → programa; solo las válidas entran.
    """
    creatures: dict[str, ResolvedProgram] = {}
    errors: list[LoadError] = []
    for path in sorted(creatures_dir.glob("*.ins")):
        result = load_creature(path.read_text(encoding="utf-8"))
        errors.extend(tag_errors(result.errors, path))
        if result.creature is None:
            continue
        if result.creature.name in creatures:
            errors.append(
                tag_errors(
                    [LoadError(1, f"la criatura {result.creature.name!r} ya está declarada")],
                    path,
                )[0]
            )
            continue
        creatures[result.creature.name] = result.creature
    return creatures, errors


def _as_load_errors(errors: list[CompileError]) -> list[LoadError]:
    """Convierte errores del front-end a errores de carga con su línea.

    Args:
        errors: Errores de cualquier etapa del compilador.

    Returns:
        Lista nueva de LoadError con la misma línea y mensaje.
    """
    return [LoadError(error.line, error.message) for error in errors]
