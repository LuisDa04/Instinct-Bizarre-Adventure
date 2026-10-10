"""Entorno de nombres de una criatura: variables, percepciones y constantes."""

from __future__ import annotations

from .errors import ExecutionError
from .perceptions import PERCEPTION_RESOLVERS, TurnFrame, perception_value
from .values import CONSTANT_VALUES


class Environment:
    """Resuelve un nombre a su valor con el orden percepción, constante, variable.

    El diccionario de variables es el de la criatura: lo que se guarda aquí
    sobrevive entre turnos (ley 7 de §2.7).
    """

    def __init__(self, variables: dict[str, int | str], frame: TurnFrame) -> None:
        """Crea el entorno sobre el dict vivo de la criatura y su foto del turno.

        Args:
            variables: Diccionario de la criatura; se guarda por referencia.
            frame: Foto de percepciones tomada al empezar el turno.
        """
        self._variables = variables
        self._frame = frame

    def get(self, name: str, line: int) -> int | str:
        """Devuelve el valor del nombre o lanza ictus si nunca se asignó.

        Args:
            name: Variable propia, percepción o constante.
            line: Línea (1-based) de la lectura para el mensaje de error.

        Returns:
            Entero o texto del nombre.

        Raises:
            ExecutionError: Si es una variable que se lee antes de asignarse.
        """
        if name in PERCEPTION_RESOLVERS:
            return perception_value(name, self._frame)
        if name in CONSTANT_VALUES:
            return CONSTANT_VALUES[name]
        if name in self._variables:
            return self._variables[name]
        raise ExecutionError(line, f"variable no asignada {name!r}")

    def set(self, name: str, value: int | str) -> None:
        """Guarda la variable, creándola si no existía (§2.3).

        Args:
            name: Variable propia (el resolver prohíbe percepciones y constantes).
            value: Entero o texto a guardar.
        """
        self._variables[name] = value
