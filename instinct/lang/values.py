"""Valores del lenguaje con sus reglas de tipo y verdad."""

from __future__ import annotations

from instinct.compiler.tokens import TokenType
from .errors import ExecutionError

CONSTANT_VALUES: dict[str, int] = {
    "NONE": -1,
    "GROUND": 0,
    "OBJECT": 1,
    "ALLY": 2,
    "ENEMY": 3,
}

_EQUALITY_OPS = frozenset({TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL})
_DIVISION_OPS = frozenset({TokenType.SLASH, TokenType.PERCENT})


def truthy(value: int | str) -> bool:
    """Indica si el valor cuenta como verdadero: todo salvo 0 y ""."""
    return not (value == 0 or value == "")


def negate(value: int | str, line: int) -> int:
    """Devuelve el opuesto del entero o lanza ictus si es texto.

    Args:
        value: Operando del menos unario ya evaluado.
        line: Línea (1-based) del nodo para el mensaje de error.

    Returns:
        El entero con el signo cambiado.

    Raises:
        ExecutionError: Si el operando es texto.
    """
    if not isinstance(value, int):
        raise ExecutionError(line, "el menos unario solo admite números")
    return -value


def apply_binary(op: TokenType, left: int | str, right: int | str, line: int) -> int:
    """Aplica un operador binario no lógico con las reglas de tipo de §2.5.

    Args:
        op: Operador a aplicar.
        left: Operando izquierdo ya evaluado.
        right: Operando derecho ya evaluado.
        line: Línea (1-based) del nodo para el mensaje de error.

    Returns:
        Entero con el resultado (las comparaciones valen 1 o 0).

    Raises:
        ExecutionError: Si se mezclan tipos, el texto usa otra operación
            que `==`/`!=`, o hay división o resto por cero.
    """
    if type(left) is not type(right):
        raise ExecutionError(line, "no se pueden mezclar entero y texto")
    if isinstance(left, str):
        if op not in _EQUALITY_OPS:
            raise ExecutionError(line, "el texto solo admite '==' y '!='")
        if op is TokenType.EQUAL_EQUAL:
            return 1 if left == right else 0
        return 1 if left != right else 0
    if op in _DIVISION_OPS and right == 0:
        if op is TokenType.SLASH:
            raise ExecutionError(line, "división por cero")
        raise ExecutionError(line, "resto por cero")
    if op is TokenType.PLUS:
        return left + right
    if op is TokenType.MINUS:
        return left - right
    if op is TokenType.STAR:
        return left * right
    if op is TokenType.SLASH:
        return left // right
    if op is TokenType.PERCENT:
        return left % right
    if op is TokenType.LESS:
        return 1 if left < right else 0
    if op is TokenType.LESS_EQUAL:
        return 1 if left <= right else 0
    if op is TokenType.GREATER:
        return 1 if left > right else 0
    if op is TokenType.GREATER_EQUAL:
        return 1 if left >= right else 0
    if op is TokenType.EQUAL_EQUAL:
        return 1 if left == right else 0
    return 1 if left != right else 0
