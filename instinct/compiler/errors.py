"""Errores de compilación que siempre conservan la línea donde se detectaron."""

from __future__ import annotations


class CompileError(Exception):
    """Error base de compilación que guarda línea y mensaje del fallo.

    Attributes:
        line: Línea (1-based) donde se detectó el error.
        message: Descripción del fallo sin prefijo de línea.
    """
    def __init__(self, line: int, message: str) -> None:
        """Crea el error componiendo el mensaje con su línea.

        Args:
            line: Línea (1-based) donde se detectó el error.
            message: Descripción del fallo sin prefijo de línea.
        """
        super().__init__(f"línea {line}: {message}")
        self.line = line
        self.message = message


class LexError(CompileError):
    """Error léxico detectado al convertir el texto en tokens."""
    pass


class ParseError(CompileError):
    """Error sintáctico detectado al construir el programa desde los tokens."""
    pass


class SemanticError(CompileError):
    """Error semántico detectado al validar cabecera, etiquetas y llamadas."""
    pass
