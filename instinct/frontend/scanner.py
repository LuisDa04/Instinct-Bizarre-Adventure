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
    tokens: list[Token]
    errors: list[LexError]


class Scanner:
    def __init__(self, source: str) -> None:
        self._source = source
        self._tokens: list[Token] = []
        self._errors: list[LexError] = []
        self._index = 0
        self._line = 1
        self._line_start = 0
        self._line_has_tokens = False

    def scan(self) -> ScanResult:
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
        lexeme = [first]
        while not self._at_end() and self._peek() in _DIGITS:
            lexeme.append(self._advance())
        text = "".join(lexeme)
        self._add(TokenType.INT, text, int(text))

    def _scan_identifier(self, first: str) -> None:
        lexeme = [first]
        while not self._at_end() and (self._peek() in _LETTERS or self._peek() in _DIGITS or self._peek() == "_"):
            lexeme.append(self._advance())
        text = "".join(lexeme)
        self._add(KEYWORDS.get(text, TokenType.IDENT), text)

    def _scan_text(self) -> None:
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
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _end_line(self) -> None:
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
        self._tokens.append(Token(type_, lexeme, literal, self._line if line is None else line))
        self._line_has_tokens = True

    def _error(self, message: str, line: int | None = None) -> None:
        self._errors.append(LexError(self._line if line is None else line, message))
        del self._tokens[self._line_start:]
        self._line_has_tokens = False
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _at_end(self) -> bool:
        return self._index >= len(self._source)

    def _peek(self) -> str:
        return self._source[self._index]

    def _advance(self) -> str:
        char = self._source[self._index]
        self._index += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._at_end() or self._source[self._index] != expected:
            return False
        self._index += 1
        return True


def scan(source: str) -> ScanResult:
    return Scanner(source).scan()
