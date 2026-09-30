from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .ast_nodes import (
    ActionCall,
    Assign,
    Binary,
    Call,
    Expr,
    Goto,
    Group,
    Header,
    HeaderEntry,
    IfGoto,
    Label,
    Literal,
    Logical,
    Program,
    Stmt,
    Unary,
    Variable,
)
from .errors import ParseError
from .tokens import Token, TokenType

_OR = 1
_AND = 2
_COMPARISON = 3
_TERM = 4
_FACTOR = 5
_UNARY = 6


@dataclass(frozen=True)
class ParseResult:
    program: Program | None
    errors: list[ParseError]


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0
        self._errors: list[ParseError] = []

    def parse(self) -> ParseResult:
        first_line = self._tokens[0].line if self._tokens else 1
        header = self._parse_header()
        body: list[Stmt] = []
        while not self._at_end():
            try:
                body.append(self._parse_statement())
            except ParseError as error:
                self._errors.append(error)
                self._synchronize()
        if self._errors:
            return ParseResult(program=None, errors=self._errors)
        return ParseResult(
            program=Program(header=header, body=body, line=first_line),
            errors=[],
        )

    def _parse_header(self) -> Header:
        entries: list[HeaderEntry] = []
        while not self._at_end() and not self._is_label_start():
            try:
                key = self._consume(TokenType.IDENT, "se esperaba una clave de cabecera")
                value = self._parse_header_value()
                self._consume_end_of_line("token inesperado tras una entrada de cabecera")
                entries.append(HeaderEntry(key=key.lexeme, value=value, line=key.line))
            except ParseError as error:
                self._errors.append(error)
                self._synchronize()
        first_line = entries[0].line if entries else self._peek().line
        return Header(entries=entries, line=first_line)

    def _parse_header_value(self) -> int | str:
        token = self._peek()
        if token.type is TokenType.IDENT:
            self._advance()
            return token.lexeme
        if token.type is TokenType.INT:
            self._advance()
            value = token.literal
            assert isinstance(value, int)
            return value
        if token.type is TokenType.MINUS:
            self._advance()
            number = self._consume(TokenType.INT, "valor de cabecera inválido")
            assert isinstance(number.literal, int)
            return -number.literal
        raise ParseError(token.line, "valor de cabecera inválido")

    def _is_label_start(self) -> bool:
        return (
            self._peek().type is TokenType.IDENT
            and self._peek_next().type is TokenType.COLON
        )

    def _parse_statement(self) -> Stmt:
        token = self._peek()
        if token.type is TokenType.IDENT and self._peek_next().type is TokenType.COLON:
            return self._parse_label()
        if token.type is TokenType.GOTO:
            return self._parse_goto()
        if token.type is TokenType.IF:
            return self._parse_if_goto()
        if token.type is TokenType.IDENT and self._peek_next().type is TokenType.EQUAL:
            return self._parse_assign()
        if token.type is TokenType.IDENT and self._peek_next().type is TokenType.LPAREN:
            return self._parse_action_call()
        raise ParseError(token.line, "línea inválida")

    def _parse_label(self) -> Label:
        name = self._consume(TokenType.IDENT, "se esperaba el nombre de una etiqueta")
        self._consume(TokenType.COLON, "se esperaba ':' tras el nombre de la etiqueta")
        self._consume_end_of_line()
        return Label(name=name.lexeme, line=name.line)

    def _parse_goto(self) -> Goto:
        keyword = self._consume(TokenType.GOTO, "se esperaba 'goto'")
        label = self._consume(TokenType.IDENT, "se esperaba el nombre de una etiqueta tras 'goto'")
        self._consume_end_of_line()
        return Goto(label=label.lexeme, line=keyword.line)

    def _parse_if_goto(self) -> IfGoto:
        keyword = self._consume(TokenType.IF, "se esperaba 'if'")
        condition = self._parse_expression()
        self._consume(TokenType.GOTO, "se esperaba 'goto' tras la condición")
        label = self._consume(TokenType.IDENT, "se esperaba el nombre de una etiqueta tras 'goto'")
        self._consume_end_of_line()
        return IfGoto(condition=condition, label=label.lexeme, line=keyword.line)

    def _parse_assign(self) -> Assign:
        name = self._consume(TokenType.IDENT, "se esperaba el nombre de una variable")
        self._consume(TokenType.EQUAL, "se esperaba '=' tras el nombre de la variable")
        value = self._parse_expression()
        self._consume_end_of_line()
        return Assign(name=name.lexeme, value=value, line=name.line)

    def _parse_action_call(self) -> ActionCall:
        name = self._consume(TokenType.IDENT, "se esperaba el nombre de una acción")
        self._consume(TokenType.LPAREN, "se esperaba '(' tras el nombre de la acción")
        args = _parse_argument_list(self)
        self._consume_end_of_line()
        return ActionCall(name=name.lexeme, args=args, line=name.line)

    def _parse_expression(self) -> Expr:
        return self._parse_precedence(_OR)

    def _parse_precedence(self, level: int) -> Expr:
        token = self._advance()
        prefix = _PREFIX.get(token.type)
        if prefix is None:
            raise ParseError(token.line, "se esperaba una expresión")
        left = prefix(self, token)
        while level <= self._infix_level():
            operator = self._advance()
            operator_level, infix = _INFIX[operator.type]
            left = infix(self, left, operator, operator_level)
        return left

    def _infix_level(self) -> int:
        rule = _INFIX.get(self._peek().type)
        return rule[0] if rule is not None else 0

    def _synchronize(self) -> None:
        while not self._at_end() and not self._check(TokenType.NEWLINE):
            self._advance()
        self._match(TokenType.NEWLINE)

    def _consume_end_of_line(self, message: str = "token inesperado tras la instrucción") -> None:
        if self._at_end():
            return
        self._consume(TokenType.NEWLINE, message)

    def _consume(self, type_: TokenType, message: str) -> Token:
        if self._check(type_):
            return self._advance()
        raise ParseError(self._peek().line, message)

    def _match(self, type_: TokenType) -> bool:
        if self._check(type_):
            self._advance()
            return True
        return False

    def _check(self, type_: TokenType) -> bool:
        return self._peek().type is type_

    def _advance(self) -> Token:
        token = self._peek()
        if not self._at_end():
            self._index += 1
        return token

    def _peek(self) -> Token:
        return self._tokens[self._index]

    def _peek_next(self) -> Token:
        if self._index + 1 < len(self._tokens):
            return self._tokens[self._index + 1]
        return self._tokens[-1]

    def _at_end(self) -> bool:
        return self._peek().type is TokenType.EOF


def _prefix_literal(parser: _Parser, token: Token) -> Expr:
    value = token.literal
    assert isinstance(value, (int, str))
    return Literal(value=value, line=token.line)


def _prefix_variable(parser: _Parser, token: Token) -> Expr:
    if parser._check(TokenType.LPAREN):
        parser._advance()
        args = _parse_argument_list(parser)
        return Call(callee=token.lexeme, args=args, line=token.line)
    return Variable(name=token.lexeme, line=token.line)


def _prefix_grouping(parser: _Parser, token: Token) -> Expr:
    inner = parser._parse_expression()
    parser._consume(TokenType.RPAREN, "se esperaba ')' tras la expresión")
    return Group(inner=inner, line=token.line)


def _prefix_unary(parser: _Parser, token: Token) -> Expr:
    operand = parser._parse_precedence(_UNARY)
    return Unary(op=token.type, operand=operand, line=token.line)


def _infix_binary(parser: _Parser, left: Expr, token: Token, level: int) -> Expr:
    right = parser._parse_precedence(level + 1)
    return Binary(left=left, op=token.type, right=right, line=token.line)


def _infix_logical(parser: _Parser, left: Expr, token: Token, level: int) -> Expr:
    right = parser._parse_precedence(level + 1)
    return Logical(left=left, op=token.type, right=right, line=token.line)


def _parse_argument_list(parser: _Parser) -> list[Expr]:
    args: list[Expr] = []
    if not parser._check(TokenType.RPAREN):
        args.append(parser._parse_expression())
        while parser._match(TokenType.COMMA):
            args.append(parser._parse_expression())
    parser._consume(TokenType.RPAREN, "se esperaba ')' tras los argumentos")
    return args


_PREFIX: dict[TokenType, Callable[[_Parser, Token], Expr]] = {
    TokenType.INT: _prefix_literal,
    TokenType.TEXT: _prefix_literal,
    TokenType.IDENT: _prefix_variable,
    TokenType.MINUS: _prefix_unary,
    TokenType.NOT: _prefix_unary,
    TokenType.LPAREN: _prefix_grouping,
}

_INFIX: dict[TokenType, tuple[int, Callable[[_Parser, Expr, Token, int], Expr]]] = {
    TokenType.OR: (_OR, _infix_logical),
    TokenType.AND: (_AND, _infix_logical),
    TokenType.LESS: (_COMPARISON, _infix_binary),
    TokenType.LESS_EQUAL: (_COMPARISON, _infix_binary),
    TokenType.GREATER: (_COMPARISON, _infix_binary),
    TokenType.GREATER_EQUAL: (_COMPARISON, _infix_binary),
    TokenType.EQUAL_EQUAL: (_COMPARISON, _infix_binary),
    TokenType.BANG_EQUAL: (_COMPARISON, _infix_binary),
    TokenType.PLUS: (_TERM, _infix_binary),
    TokenType.MINUS: (_TERM, _infix_binary),
    TokenType.STAR: (_FACTOR, _infix_binary),
    TokenType.SLASH: (_FACTOR, _infix_binary),
    TokenType.PERCENT: (_FACTOR, _infix_binary),
}


def parse(tokens: list[Token]) -> ParseResult:
    return _Parser(tokens).parse()
