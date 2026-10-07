"""Nodos inmutables del árbol de sintaxis para cabecera, sentencias y expresiones."""

from __future__ import annotations

from dataclasses import dataclass, field

from .tokens import TokenType


@dataclass(frozen=True)
class Node:
    """Nodo base inmutable del árbol que siempre guarda su línea.

    Attributes:
        line: Línea (1-based) del fuente donde aparece el nodo.
    """

    line: int = field(kw_only=True)


class Expr(Node):
    """Expresión base de la que heredan literales, variables y operaciones."""
    pass


@dataclass(frozen=True)
class Literal(Expr):
    """Literal entero o de texto con su valor ya convertido.

    Attributes:
        value: Valor entero o cadena del literal.
    """

    value: int | str


@dataclass(frozen=True)
class Variable(Expr):
    """Referencia a variable, percepción o constante por nombre.

    Attributes:
        name: Nombre tal como aparece en el fuente.
    """

    name: str


@dataclass(frozen=True)
class Unary(Expr):
    """Operación unaria con operador y operando.

    Attributes:
        op: Operador (menos o negación).
        operand: Expresión sobre la que se aplica.
    """

    op: TokenType
    operand: Expr


@dataclass(frozen=True)
class Binary(Expr):
    """Operación binaria aritmética o de comparación.

    Attributes:
        left: Operando izquierdo de la operación.
        op: Operador binario aplicado.
        right: Operando derecho de la operación.
    """

    left: Expr
    op: TokenType
    right: Expr


@dataclass(frozen=True)
class Logical(Expr):
    """Combinación lógica con `and`/`or` entre dos expresiones.

    Attributes:
        left: Operando izquierdo de la conjunción.
        op: Operador lógico aplicado.
        right: Operando derecho de la conjunción.
    """

    left: Expr
    op: TokenType
    right: Expr


@dataclass(frozen=True)
class Call(Expr):
    """Llamada a función dentro de expresiones con argumentos evaluables.

    Attributes:
        callee: Nombre de la función invocada.
        args: Argumentos ya analizados en orden.
    """

    callee: str
    args: list[Expr]


@dataclass(frozen=True)
class Group(Expr):
    """Expresión entre paréntesis que conserva su posición.

    Attributes:
        inner: Expresión contenida dentro del paréntesis.
    """

    inner: Expr


class Stmt(Node):
    """Sentencia base del cuerpo del programa."""
    pass


@dataclass(frozen=True)
class Label(Stmt):
    """Etiqueta que marca un destino de salto dentro del cuerpo.

    Attributes:
        name: Nombre de la etiqueta sin los dos puntos.
    """

    name: str


@dataclass(frozen=True)
class Goto(Stmt):
    """Salto incondicional a una etiqueta del mismo programa.

    Attributes:
        label: Nombre de la etiqueta destino.
    """

    label: str


@dataclass(frozen=True)
class IfGoto(Stmt):
    """Salto condicional a una etiqueta cuando la condición es verdadera.

    Attributes:
        condition: Expresión evaluada para decidir el salto.
        label: Nombre de la etiqueta destino.
    """

    condition: Expr
    label: str


@dataclass(frozen=True)
class Assign(Stmt):
    """Asignación de una expresión a una variable del programa.

    Attributes:
        name: Nombre de la variable que recibe el valor.
        value: Expresión cuyo valor se asigna.
    """

    name: str
    value: Expr


@dataclass(frozen=True)
class ActionCall(Stmt):
    """Invocación de una acción del juego como sentencia independiente.

    Attributes:
        name: Nombre de la acción invocada.
        args: Argumentos ya analizados en orden.
    """

    name: str
    args: list[Expr]


@dataclass(frozen=True)
class HeaderEntry(Node):
    """Entrada `clave valor` de la cabecera con su línea.

    Attributes:
        key: Clave de la entrada tal como aparece en el fuente.
        value: Valor entero o de texto ya convertido.
    """

    key: str
    value: int | str


@dataclass(frozen=True)
class Header(Node):
    """Cabecera con la lista de entradas que describen a la criatura.

    Attributes:
        entries: Entradas de cabecera en orden de aparición.
    """

    entries: list[HeaderEntry]


@dataclass(frozen=True)
class Program(Node):
    """Programa completo con cabecera validada y cuerpo de sentencias.

    Attributes:
        header: Cabecera con los datos de la criatura.
        body: Sentencias del cuerpo en orden de ejecución.
    """

    header: Header
    body: list[Stmt]
