"""Valida el programa y produce su forma resuelta con etiquetas y cabecera."""

from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import (
    ActionCall,
    Assign,
    Binary,
    Call,
    Expr,
    Goto,
    Group,
    HeaderEntry,
    IfGoto,
    Label,
    Logical,
    Node,
    Program,
    Stmt,
    Unary,
)
from .catalogs import ACTION_ARITY, CONSTANTS, FUNCTION_ARITY, HEADER_KEYS, PERCEPTIONS
from .errors import SemanticError


@dataclass(frozen=True)
class ResolvedProgram(Node):
    """Programa validado con cabecera tipada, cuerpo y tabla de etiquetas.

    Attributes:
        name: Nombre de la criatura declarado en la cabecera.
        faction: Facción declarada en la cabecera.
        health: Salud inicial, siempre mayor que 0.
        vision: Alcance de visión, siempre mayor o igual que 1.
        lifespan: Duración de vida, siempre mayor que 0.
        body: Sentencias del cuerpo en orden de ejecución.
        labels: Tabla de etiqueta a índice de sentencia en el cuerpo.
    """

    name: str
    faction: str
    health: int
    vision: int
    lifespan: int
    body: list[Stmt]
    labels: dict[str, int]


@dataclass(frozen=True)
class ResolveResult:
    """Resultado inmutable con programa resuelto o lista de errores.

    Attributes:
        resolved: Programa resuelto o None si hubo errores.
        errors: Errores semánticos; vacía si la resolución fue válida.
    """

    resolved: ResolvedProgram | None
    errors: list[SemanticError]


class _Resolver:
    """Valida cabecera, etiquetas y llamadas acumulando errores sin abortar."""

    def __init__(self, program: Program) -> None:
        """Inicializa el validador con el programa sintáctico a resolver.

        Args:
            program: Programa con cabecera y cuerpo salidos del analizador.
        """
        self._program = program
        self._errors: list[SemanticError] = []
        self._labels: dict[str, int] = {}

    def resolve(self) -> ResolveResult:
        """Valida todo el programa y devuelve su forma resuelta o los errores.

        Returns:
            Programa resuelto o None con los errores acumulados.
        """
        spec = self._check_header()
        self._collect_labels()
        self._check_body()
        if self._errors or spec is None:
            return ResolveResult(resolved=None, errors=self._errors)
        name, faction, health, vision, lifespan = spec
        return ResolveResult(
            resolved=ResolvedProgram(
                name=name,
                faction=faction,
                health=health,
                vision=vision,
                lifespan=lifespan,
                body=self._program.body,
                labels=self._labels,
                line=self._program.line,
            ),
            errors=[],
        )

    def _error(self, line: int, message: str) -> None:
        """Registra un error semántico con su línea.

        Args:
            line: Línea (1-based) donde se detectó el error.
            message: Descripción del fallo sin prefijo de línea.
        """
        self._errors.append(SemanticError(line, message))

    def _check_header(self) -> tuple[str, str, int, int, int] | None:
        """Valida claves, orden y rangos de la cabecera y extrae sus valores.

        Returns:
            Tupla (nombre, facción, salud, visión, vida) o None si hay errores.
        """
        entries = self._program.header.entries
        seen: dict[str, HeaderEntry] = {}
        for entry in entries:
            if entry.key not in HEADER_KEYS:
                self._error(entry.line, f"clave de cabecera desconocida {entry.key!r}")
            elif entry.key in seen:
                self._error(entry.line, f"clave de cabecera duplicada {entry.key!r}")
            else:
                seen[entry.key] = entry
        if entries and entries[0].key != "creature":
            self._error(entries[0].line, "la primera línea debe ser 'creature Nombre'")
        for key in HEADER_KEYS:
            if key not in seen:
                self._error(self._program.line, f"falta la clave {key!r} en la cabecera")
        name = self._header_text(seen.get("creature"))
        faction = self._header_text(seen.get("faction"))
        health = self._header_range(seen.get("health"), "health debe ser mayor que 0")
        vision = self._header_range(
            seen.get("vision"), "vision debe ser mayor o igual que 1"
        )
        lifespan = self._header_range(
            seen.get("lifespan"), "lifespan debe ser mayor que 0"
        )
        if (
            name is None
            or faction is None
            or health is None
            or vision is None
            or lifespan is None
        ):
            return None
        return (name, faction, health, vision, lifespan)

    def _header_text(self, entry: HeaderEntry | None) -> str | None:
        """Extrae un valor de texto de la cabecera o registra error.

        Args:
            entry: Entrada de cabecera o None si la clave falta.

        Returns:
            Texto de la entrada o None si falta o no es texto.
        """
        if entry is None:
            return None
        if not isinstance(entry.value, str):
            self._error(entry.line, "valor de cabecera inválido")
            return None
        return entry.value

    def _header_range(self, entry: HeaderEntry | None, message: str) -> int | None:
        """Extrae un entero mayor o igual que 1 de la cabecera o registra error.

        Args:
            entry: Entrada de cabecera o None si la clave falta.
            message: Mensaje a usar si el valor queda fuera de rango.

        Returns:
            Entero validado o None si falta, no es entero o es menor que 1.
        """
        if entry is None:
            return None
        if not isinstance(entry.value, int):
            self._error(entry.line, "valor de cabecera inválido")
            return None
        if entry.value < 1:
            self._error(entry.line, message)
            return None
        return entry.value

    def _collect_labels(self) -> None:
        """Construye la tabla de etiquetas y exige `start:` sin duplicados."""
        for index, statement in enumerate(self._program.body):
            if isinstance(statement, Label):
                if statement.name in self._labels:
                    self._error(
                        statement.line, f"etiqueta duplicada {statement.name!r}"
                    )
                else:
                    self._labels[statement.name] = index
        if "start" not in self._labels:
            self._error(self._program.line, "falta la etiqueta 'start:'")

    def _check_body(self) -> None:
        """Comprueba destinos de salto, asignaciones y acciones del cuerpo."""
        for statement in self._program.body:
            if isinstance(statement, Goto):
                self._check_target(statement.label, statement.line)
            elif isinstance(statement, IfGoto):
                self._check_target(statement.label, statement.line)
                self._check_expr(statement.condition)
            elif isinstance(statement, Assign):
                self._check_assign_target(statement.name, statement.line)
                self._check_expr(statement.value)
            elif isinstance(statement, ActionCall):
                self._check_action(statement)

    def _check_target(self, label: str, line: int) -> None:
        """Comprueba que la etiqueta destino exista.

        Args:
            label: Nombre de la etiqueta destino del salto.
            line: Línea (1-based) del salto a comprobar.
        """
        if label not in self._labels:
            self._error(line, f"salto a etiqueta inexistente {label!r}")

    def _check_assign_target(self, name: str, line: int) -> None:
        """Rechaza asignar a percepciones, constantes y funciones.

        Args:
            name: Nombre de la variable destino de la asignación.
            line: Línea (1-based) de la asignación.
        """
        if name in PERCEPTIONS:
            self._error(line, f"no se puede asignar a la percepción {name!r}")
        elif name in CONSTANTS:
            self._error(line, f"no se puede asignar a la constante {name!r}")
        elif name in FUNCTION_ARITY:
            self._error(line, f"no se puede asignar a la función {name!r}")

    def _check_action(self, action: ActionCall) -> None:
        """Comprueba que la acción exista y reciba el número de argumentos.

        Args:
            action: Llamada a acción como sentencia a validar.
        """
        expected = ACTION_ARITY.get(action.name)
        if expected is None:
            self._error(action.line, f"acción desconocida {action.name!r}")
        elif len(action.args) != expected:
            self._error(
                action.line,
                self._arity_message("acción", action.name, expected, len(action.args)),
            )
        for argument in action.args:
            self._check_expr(argument)

    def _check_expr(self, expr: Expr) -> None:
        """Comprueba funciones llamadas y recorre operandos de la expresión.

        Args:
            expr: Expresión a validar de forma recursiva.
        """
        if isinstance(expr, Call):
            expected = FUNCTION_ARITY.get(expr.callee)
            if expected is None:
                self._error(expr.line, f"función desconocida {expr.callee!r}")
            elif len(expr.args) != expected:
                self._error(
                    expr.line,
                    self._arity_message(
                        "función", expr.callee, expected, len(expr.args)
                    ),
                )
            for argument in expr.args:
                self._check_expr(argument)
        elif isinstance(expr, Unary):
            self._check_expr(expr.operand)
        elif isinstance(expr, (Binary, Logical)):
            self._check_expr(expr.left)
            self._check_expr(expr.right)
        elif isinstance(expr, Group):
            self._check_expr(expr.inner)

    def _arity_message(self, kind: str, name: str, expected: int, given: int) -> str:
        """Compone el mensaje de aridad esperada frente a recibida.

        Args:
            kind: Tipo de invocación, `acción` o `función`.
            name: Nombre de la acción o función comprobada.
            expected: Número de argumentos esperado (0 o más).
            given: Número de argumentos recibido (0 o más).

        Returns:
            Mensaje con la aridad esperada y la recibida.
        """
        noun = "argumento" if expected == 1 else "argumentos"
        return f"la {kind} {name!r} espera {expected} {noun}, no {given}"


def resolve(program: Program) -> ResolveResult:
    """Valida el programa y devuelve su forma resuelta o los errores.

    Args:
        program: Programa con cabecera y cuerpo salidos del analizador.

    Returns:
        Programa resuelto o None con los errores semánticos.
    """
    return _Resolver(program).resolve()
