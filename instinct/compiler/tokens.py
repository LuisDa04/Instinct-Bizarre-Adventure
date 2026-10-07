"""Tipos de token y contenedor inmutable de token con línea y literal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Enumera los tipos de token que produce el escáner."""
    INT = auto()
    TEXT = auto()
    IDENT = auto()

    IF = auto()
    GOTO = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    COLON = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()

    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    EQUAL_EQUAL = auto()
    BANG_EQUAL = auto()
    EQUAL = auto()

    NEWLINE = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    """Token inmutable con tipo, texto original, valor y línea.

    Attributes:
        type: Tipo de token según el vocabulario del lenguaje.
        lexeme: Texto original tal como apareció en el fuente.
        literal: Valor convertido (int o str) o None si no aplica.
        line: Línea (1-based) donde aparece el token.
    """
    type: TokenType
    lexeme: str
    literal: object | None
    line: int
