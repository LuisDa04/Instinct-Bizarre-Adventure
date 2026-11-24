"""Error de carga de definiciones con línea y ruta del fichero."""
from __future__ import annotations

from pathlib import Path

from ..compiler.errors import CompileError


class LoadError(CompileError):
    """Representa un error de carga con línea, mensaje y ruta opcional del fichero."""

    code = "LOAD"

    def __init__(
        self, line: int, message: str, path: str = "", code: str | None = None
    ) -> None:
        """Crea un error de carga con línea, mensaje y ruta opcional.

        Args:
            line: Número de línea (1-based); 1 es la primera línea con contenido.
            message: Descripción del problema.
            path: Ruta del fichero; "" significa origen no etiquetado.
            code: Categoría estable del error; si es None, se usa la del tipo.
        """
        super().__init__(line, message)
        self.path = path
        if code is not None:
            self.code = code


def read_source(path: Path) -> tuple[str | None, LoadError | None]:
    """Lee un fichero como UTF-8 devolviendo su texto o un error con la ruta.

    Los fallos de lectura y decodificación no se propagan: cada archivo se
    informa por separado para que el resto de la carga continúe.

    Args:
        path: Ruta del fichero a leer.

    Returns:
        Tupla (texto, error): el texto y None si la lectura funciona; None y
        un LoadError de línea 1 con la ruta si el archivo es ilegible.
    """
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, LoadError(1, "el archivo no está codificado en UTF-8", str(path))
    except OSError:
        return None, LoadError(1, "no se pudo leer el archivo", str(path))


def tag_errors(errors: list[LoadError], path: Path) -> list[LoadError]:
    """Etiqueta cada error con la ruta del fichero que lo produjo.

    Args:
        errors: Errores sin etiquetar; la lista no se modifica.
        path: Ruta del fichero que generó los errores.

    Returns:
        Nueva lista de errores con path informado; la lista original queda intacta.
    """
    return [
        LoadError(error.line, error.message, str(path), code=error.code)
        for error in errors
    ]
