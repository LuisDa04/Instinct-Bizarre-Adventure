"""Error de carga de definiciones con línea y ruta del fichero."""
from __future__ import annotations

from ..compiler.errors import CompileError


class LoadError(CompileError):
    """Representa un error de carga con línea, mensaje y ruta opcional del fichero."""

    def __init__(self, line: int, message: str, path: str = "") -> None:
        """Crea un error de carga con línea, mensaje y ruta opcional.

        Args:
            line: Número de línea (1-based); 1 es la primera línea con contenido.
            message: Descripción del problema.
            path: Ruta del fichero; "" significa origen no etiquetado.
        """
        super().__init__(line, message)
        self.path = path
