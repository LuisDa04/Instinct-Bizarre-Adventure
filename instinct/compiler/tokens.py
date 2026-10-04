from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
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
    type: TokenType
    lexeme: str
    literal: object | None
    line: int
