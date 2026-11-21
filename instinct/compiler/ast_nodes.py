"""Nodos inmutables del árbol de sintaxis para cabecera, sentencias y expresiones."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .tokens import TokenType
from instinct.lang.values import truthy

if TYPE_CHECKING:
    from instinct.compiler.execution_context import ExecutionContext
    from instinct.lang.actions import Action


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

    def eval(self, ctx: ExecutionContext) -> int | str:
        return self.value


@dataclass(frozen=True)
class Variable(Expr):
    """Referencia a variable, percepción o constante por nombre.

    Attributes:
        name: Nombre tal como aparece en el fuente.
    """

    name: str

    def eval(self, ctx: ExecutionContext) -> int | str:
        return ctx.environment.get(self.name, self.line)


@dataclass(frozen=True)
class Unary(Expr):
    """Operación unaria con operador y operando.

    Attributes:
        op: Operador (menos o negación).
        operand: Expresión sobre la que se aplica.
    """

    op: TokenType
    operand: Expr

    def eval(self, ctx: ExecutionContext) -> int | str:
        operand = self.operand.eval(ctx)
        if self.op is TokenType.MINUS:
            from instinct.lang.values import negate
            return negate(operand, self.line)
        return 1 if not truthy(operand) else 0


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

    def eval(self, ctx: ExecutionContext) -> int | str:
        left = self.left.eval(ctx)
        right = self.right.eval(ctx)
        from instinct.lang.values import apply_binary
        return apply_binary(self.op, left, right, self.line)


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

    def eval(self, ctx: ExecutionContext) -> int | str:
        left = self.left.eval(ctx)
        from instinct.lang.values import truthy
        if self.op is TokenType.AND:
            if not truthy(left):
                return 0
            return 1 if truthy(self.right.eval(ctx)) else 0
        if truthy(left):
            return 1
        return 1 if truthy(self.right.eval(ctx)) else 0


@dataclass(frozen=True)
class Call(Expr):
    """Llamada a función dentro de expresiones con argumentos evaluables.

    Attributes:
        callee: Nombre de la función invocada.
        args: Argumentos ya analizados en orden.
    """

    callee: str
    args: list[Expr]

    def eval(self, ctx: ExecutionContext) -> int | str:
        args = [arg.eval(ctx) for arg in self.args]
        from instinct.lang.functions import FUNCTIONS
        return FUNCTIONS[self.callee](args, ctx.creature, ctx.world, self.line)


@dataclass(frozen=True)
class Group(Expr):
    """Expresión entre paréntesis que conserva su posición.

    Attributes:
        inner: Expresión contenida dentro del paréntesis.
    """

    inner: Expr

    def eval(self, ctx: ExecutionContext) -> int | str:
        return self.inner.eval(ctx)


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

    def execute(self, ctx: ExecutionContext) -> None:
        ctx.pc += 1


@dataclass(frozen=True)
class Goto(Stmt):
    """Salto incondicional a una etiqueta del mismo programa.

    Attributes:
        label: Nombre de la etiqueta destino.
    """

    label: str

    def execute(self, ctx: ExecutionContext) -> None:
        if ctx.program_labels is not None and self.label in ctx.program_labels:
            ctx.pc = ctx.program_labels[self.label]
        else:
            # El resolver semántico ya validó que la etiqueta existe
            pass


@dataclass(frozen=True)
class IfGoto(Stmt):
    """Salto condicional a una etiqueta cuando la condición es verdadera.

    Attributes:
        condition: Expresión evaluada para decidir el salto.
        label: Nombre de la etiqueta destino.
    """

    condition: Expr
    label: str

    def execute(self, ctx: ExecutionContext) -> None:
        from instinct.lang.values import truthy
        if truthy(self.condition.eval(ctx)):
            if ctx.program_labels is not None and self.label in ctx.program_labels:
                ctx.pc = ctx.program_labels[self.label]
            else:
                pass
        else:
            ctx.pc += 1


@dataclass(frozen=True)
class Assign(Stmt):
    """Asignación de una expresión a una variable del programa.

    Attributes:
        name: Nombre de la variable que recibe el valor.
        value: Expresión cuyo valor se asigna.
    """

    name: str
    value: Expr

    def execute(self, ctx: ExecutionContext) -> None:
        ctx.environment.set(self.name, self.value.eval(ctx))
        ctx.pc += 1


@dataclass(frozen=True)
class ActionCall(Stmt):
    """Invocación de una acción del juego como sentencia independiente.

    Attributes:
        name: Nombre de la acción invocada.
        args: Argumentos ya analizados en orden.
    """

    name: str
    args: list[Expr]

    def execute(self, ctx: ExecutionContext) -> "Action | None":
        from instinct.lang.actions import ACTIONS, Action
        args = [arg.eval(ctx) for arg in self.args]
        ctx.pc += 1
        action = ACTIONS.get(self.name)
        if action is None:
            from instinct.lang.errors import ExecutionError
            raise ExecutionError(self.line, f"acción no implementada {self.name!r}")
        action.validate(args, self.line)
        from instinct.lang.actions import ActionContext
        action.apply(
            ActionContext(
                world=ctx.world,
                engine=ctx.engine,
                creature=ctx.creature,
                log=ctx.log,
            ),
            args,
            self.line,
        )
        return action


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
