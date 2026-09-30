from __future__ import annotations

from dataclasses import dataclass, field

from .tokens import TokenType


@dataclass(frozen=True)
class Node:
    line: int = field(kw_only=True)


class Expr(Node):
    pass


@dataclass(frozen=True)
class Literal(Expr):
    value: int | str


@dataclass(frozen=True)
class Variable(Expr):
    name: str


@dataclass(frozen=True)
class Unary(Expr):
    op: TokenType
    operand: Expr


@dataclass(frozen=True)
class Binary(Expr):
    left: Expr
    op: TokenType
    right: Expr


@dataclass(frozen=True)
class Logical(Expr):
    left: Expr
    op: TokenType
    right: Expr


@dataclass(frozen=True)
class Call(Expr):
    callee: str
    args: list[Expr]


@dataclass(frozen=True)
class Group(Expr):
    inner: Expr


class Stmt(Node):
    pass


@dataclass(frozen=True)
class Label(Stmt):
    name: str


@dataclass(frozen=True)
class Goto(Stmt):
    label: str


@dataclass(frozen=True)
class IfGoto(Stmt):
    condition: Expr
    label: str


@dataclass(frozen=True)
class Assign(Stmt):
    name: str
    value: Expr


@dataclass(frozen=True)
class ActionCall(Stmt):
    name: str
    args: list[Expr]


@dataclass(frozen=True)
class HeaderEntry(Node):
    key: str
    value: int | str


@dataclass(frozen=True)
class Header(Node):
    entries: list[HeaderEntry]


@dataclass(frozen=True)
class Program(Node):
    header: Header
    body: list[Stmt]
