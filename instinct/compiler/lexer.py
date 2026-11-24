"""Convierte texto fuente en tokens y recoge errores léxicos sin abortar."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import LexError
from .tokens import Token, TokenType

KEYWORDS: dict[str, TokenType] = {
    "if": TokenType.IF,
    "goto": TokenType.GOTO,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}

_DIGITS = frozenset("0123456789")
_IDENT = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
_WHITESPACE = " \t\r"
_SIMPLE: dict[str, TokenType] = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
    ":": TokenType.COLON,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
}


@dataclass(frozen=True)
class ScanResult:
    """Resultado inmutable del escaneo con tokens y errores acumulados.

    Attributes:
        tokens: Lista de tokens incluido EOF; vacía de NEWLINE si no hubo código.
        errors: Errores léxicos por línea; vacía si el texto es válido.
    """

    tokens: list[Token]
    errors: list[LexError]


class Scanner:
    """Convierte el texto fuente en tokens línea a línea con recuperación de errores."""

    def __init__(self, source: str) -> None:
        """Inicializa el escáner con el texto a analizar.

        Args:
            source: Texto fuente completo a convertir en tokens.
        """
        self._source = source
        self._tokens: list[Token] = []
        self._errors: list[LexError] = []
        self._index = 0
        self._line = 1
        self._line_start = 0
        self._line_has_tokens = False

    def scan(self) -> ScanResult:
        """Recorre el texto y devuelve tokens con errores acumulados.

        El cursor, la línea y las listas se mantienen en variables locales
        durante el barrido; las rebanadas del fuente evitan construir listas
        de caracteres y el despacho de puntuación simple es directo.

        Returns:
            Resultado con la lista de tokens (terminada en EOF) y los errores.
        """
        source = self._source
        tokens = self._tokens
        errors = self._errors
        append_token = tokens.append
        append_error = errors.append
        token_type = TokenType
        index = self._index
        length = len(source)
        line = self._line
        line_start = self._line_start
        line_has_tokens = self._line_has_tokens

        def fail(message: str, error_line: int | None = None) -> None:
            """Registra un error, descarta la línea y salta hasta su fin."""
            nonlocal index, line_has_tokens
            append_error(LexError(line if error_line is None else error_line, message))
            del tokens[line_start:]
            line_has_tokens = False
            while index < length and source[index] != "\n":
                index += 1

        while index < length:
            char = source[index]
            index += 1

            if char == "\n":
                if line_has_tokens:
                    append_token(Token(token_type.NEWLINE, "", None, line))
                line_has_tokens = False
                line_start = len(tokens)
                line += 1
                continue
            if char in _WHITESPACE:
                continue
            if char == "#":
                while index < length and source[index] != "\n":
                    index += 1
                continue

            if char in _DIGITS:
                start = index - 1
                while index < length and source[index] in _DIGITS:
                    index += 1
                text = source[start:index]
                append_token(Token(token_type.INT, text, int(text), line))
                line_has_tokens = True
                continue
            if char in _IDENT:
                start = index - 1
                while index < length and source[index] in _IDENT:
                    index += 1
                text = source[start:index]
                append_token(Token(KEYWORDS.get(text, token_type.IDENT), text, None, line))
                line_has_tokens = True
                continue
            if char == '"':
                start_line = line
                start = index
                while index < length and source[index] != '"' and source[index] != "\n":
                    index += 1
                if index >= length or source[index] == "\n":
                    fail("literal de texto sin cerrar", start_line)
                    continue
                value = source[start:index]
                index += 1
                append_token(Token(token_type.TEXT, '"' + value + '"', value, start_line))
                line_has_tokens = True
                continue

            simple = _SIMPLE.get(char)
            if simple is not None:
                append_token(Token(simple, char, None, line))
                line_has_tokens = True
                continue
            if char == "=":
                if index < length and source[index] == "=":
                    index += 1
                    append_token(Token(token_type.EQUAL_EQUAL, "==", None, line))
                else:
                    append_token(Token(token_type.EQUAL, "=", None, line))
                line_has_tokens = True
                continue
            if char == "!":
                if index < length and source[index] == "=":
                    index += 1
                    append_token(Token(token_type.BANG_EQUAL, "!=", None, line))
                else:
                    fail("carácter inesperado '!'")
                continue
            if char == "<":
                if index < length and source[index] == "=":
                    index += 1
                    append_token(Token(token_type.LESS_EQUAL, "<=", None, line))
                else:
                    append_token(Token(token_type.LESS, "<", None, line))
                line_has_tokens = True
                continue
            if char == ">":
                if index < length and source[index] == "=":
                    index += 1
                    append_token(Token(token_type.GREATER_EQUAL, ">=", None, line))
                else:
                    append_token(Token(token_type.GREATER, ">", None, line))
                line_has_tokens = True
                continue
            fail(f"carácter inesperado {char!r}")

        if line_has_tokens:
            append_token(Token(token_type.NEWLINE, "", None, line))
        append_token(Token(token_type.EOF, "", None, line))

        self._index = index
        self._line = line
        self._line_start = line_start
        self._line_has_tokens = line_has_tokens
        return ScanResult(tokens, errors)


def scan(source: str) -> ScanResult:
    """Escanea el texto y devuelve tokens con errores acumulados.

    Args:
        source: Texto fuente completo a convertir en tokens.

    Returns:
        Resultado con la lista de tokens y los errores léxicos.
    """
    return Scanner(source).scan()
