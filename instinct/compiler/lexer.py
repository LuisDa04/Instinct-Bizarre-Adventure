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

_WHITESPACE = " \t\r"
_DIGITS = "0123456789"
_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


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

        Returns:
            Resultado con la lista de tokens (terminada en EOF) y los errores.
        """
        while not self._at_end():
            char = self._advance()
            if char == "\n":
                self._end_line()
            elif char in _WHITESPACE:
                continue
            elif char == "#":
                self._skip_comment()
            else:
                self._scan_token(char)
        if self._line_has_tokens:
            self._add(TokenType.NEWLINE, "")
        self._tokens.append(Token(TokenType.EOF, "", None, self._line))
        return ScanResult(self._tokens, self._errors)

    def _scan_token(self, char: str) -> None:
        """Clasifica un carácter inicial y emite el token correspondiente.

        Args:
            char: Primer carácter del posible token ya consumido.
        """
        if char in _DIGITS:
            self._scan_number(char)
        elif char in _LETTERS or char == "_":
            self._scan_identifier(char)
        elif char == '"':
            self._scan_text()
            return
        elif char == "(":
            self._add(TokenType.LPAREN, char)
        elif char == ")":
            self._add(TokenType.RPAREN, char)
        elif char == ",":
            self._add(TokenType.COMMA, char)
        elif char == ":":
            self._add(TokenType.COLON, char)
        elif char == "+":
            self._add(TokenType.PLUS, char)
        elif char == "-":
            self._add(TokenType.MINUS, char)
        elif char == "*":
            self._add(TokenType.STAR, char)
        elif char == "/":
            self._add(TokenType.SLASH, char)
        elif char == "%":
            self._add(TokenType.PERCENT, char)
        elif char == "=":
            if self._match("="):
                self._add(TokenType.EQUAL_EQUAL, "==")
            else:
                self._add(TokenType.EQUAL, "=")
        elif char == "!":
            if self._match("="):
                self._add(TokenType.BANG_EQUAL, "!=")
            else:
                self._error("carácter inesperado '!'")
        elif char == "<":
            if self._match("="):
                self._add(TokenType.LESS_EQUAL, "<=")
            else:
                self._add(TokenType.LESS, "<")
        elif char == ">":
            if self._match("="):
                self._add(TokenType.GREATER_EQUAL, ">=")
            else:
                self._add(TokenType.GREATER, ">")
        else:
            self._error(f"carácter inesperado {char!r}")

    def _scan_number(self, first: str) -> None:
        """Consume un entero decimal y emite un token INT.

        Args:
            first: Primer dígito ya consumido del número.
        """
        lexeme = [first]
        while not self._at_end() and self._peek() in _DIGITS:
            lexeme.append(self._advance())
        text = "".join(lexeme)
        self._add(TokenType.INT, text, int(text))

    def _scan_identifier(self, first: str) -> None:
        """Consume un identificador o palabra clave y emite su token.

        Args:
            first: Primera letra o guion bajo ya consumido.
        """
        lexeme = [first]
        while not self._at_end() and (self._peek() in _LETTERS or self._peek() in _DIGITS or self._peek() == "_"):
            lexeme.append(self._advance())
        text = "".join(lexeme)
        self._add(KEYWORDS.get(text, TokenType.IDENT), text)

    def _scan_text(self) -> None:
        """Consume un literal entre comillas en una sola línea o registra error."""
        start_line = self._line
        value: list[str] = []
        while not self._at_end() and self._peek() not in ('"', "\n"):
            value.append(self._advance())
        if self._at_end() or self._peek() == "\n":
            self._error("literal de texto sin cerrar", start_line)
            return
        self._advance()
        self._add(TokenType.TEXT, '"' + "".join(value) + '"', "".join(value), line=start_line)

    def _skip_comment(self) -> None:
        """Descarta caracteres hasta el salto de línea sin emitir tokens."""
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _end_line(self) -> None:
        """Cierra la línea lógica emitiendo NEWLINE solo si hubo tokens."""
        if self._line_has_tokens:
            self._add(TokenType.NEWLINE, "")
        self._line_has_tokens = False
        self._line_start = len(self._tokens)
        self._line += 1

    def _add(
        self,
        type_: TokenType,
        lexeme: str,
        literal: object | None = None,
        line: int | None = None,
    ) -> None:
        """Añade un token marcando la línea actual como no vacía.

        Args:
            type_: Tipo del token a emitir.
            lexeme: Texto original del token.
            literal: Valor convertido o None si no aplica.
            line: Línea a usar o None para usar la actual.
        """
        self._tokens.append(Token(type_, lexeme, literal, self._line if line is None else line))
        self._line_has_tokens = True

    def _error(self, message: str, line: int | None = None) -> None:
        """Registra un error léxico, descarta la línea y salta hasta su fin.

        Args:
            message: Descripción del fallo sin prefijo de línea.
            line: Línea a usar o None para usar la actual.
        """
        self._errors.append(LexError(self._line if line is None else line, message))
        del self._tokens[self._line_start:]
        self._line_has_tokens = False
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _at_end(self) -> bool:
        """Indica si se consumió todo el texto fuente.

        Returns:
            True cuando el cursor alcanzó el final del texto.
        """
        return self._index >= len(self._source)

    def _peek(self) -> str:
        """Devuelve el carácter actual sin consumirlo.

        Returns:
            Carácter bajo el cursor sin avanzar la posición.
        """
        return self._source[self._index]

    def _advance(self) -> str:
        """Consume y devuelve el carácter actual avanzando el cursor.

        Returns:
            Carácter consumido en esta llamada.
        """
        char = self._source[self._index]
        self._index += 1
        return char

    def _match(self, expected: str) -> bool:
        """Consume el carácter esperado si coincide con el actual.

        Args:
            expected: Carácter que se espera encontrar bajo el cursor.

        Returns:
            True si coincidió y se consumió, False en caso contrario.
        """
        if self._at_end() or self._source[self._index] != expected:
            return False
        self._index += 1
        return True


def scan(source: str) -> ScanResult:
    """Escanea el texto y devuelve tokens con errores acumulados.

    Args:
        source: Texto fuente completo a convertir en tokens.

    Returns:
        Resultado con la lista de tokens y los errores léxicos.
    """
    return Scanner(source).scan()
