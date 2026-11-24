"""Gestión de pestañas y archivos .ins para el editor.

Mantiene el estado de cada pestaña (ruta, contenido, sucio) y permite
crear, abrir, guardar y cerrar pestañas de forma independiente de la UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class EditorTab:
    """Representa una pestaña del editor.

    Attributes:
        path: Ruta del archivo en disco, o None si es un archivo nuevo
            aún sin guardar.
        content: Contenido actual del editor para esta pestaña.
        dirty: True si el contenido ha cambiado desde la última guarda.
    """

    path: Optional[Path] = None
    content: str = ""
    dirty: bool = False

    @property
    def name(self) -> str:
        """Nombre para mostrar en la pestaña (nombre de archivo o 'untitled.ins')."""
        if self.path is not None:
            return self.path.name
        return "untitled.ins"


class FileManager:
    """Gestiona la lista de pestañas abiertas y el archivo activo.

    No depende de Qt; es pura lógica de datos. La UI (editor_widget)
    es la responsable de renderizar las pestañas y leer/escribir
    el contenido de cada una.
    """

    def __init__(self) -> None:
        self._tabs: list[EditorTab] = []
        self._current: int = -1

    # ------------------------------------------------------------------
    # Crear / abrir pestañas
    # ------------------------------------------------------------------

    def new_tab(self) -> int:
        """Crea una pestaña vacía y la marca como actual.

        Returns:
            Índice de la nueva pestaña.
        """
        tab = EditorTab()
        self._tabs.append(tab)
        self._current = len(self._tabs) - 1
        return self._current

    def open_file(self, path: Path) -> int:
        """Abre un archivo .ins existente y crea una pestaña para él.

        Args:
            path: Ruta al archivo .ins.

        Returns:
            Índice de la pestaña creada.
        """
        content = path.read_text(encoding="utf-8")
        tab = EditorTab(path=path, content=content)
        self._tabs.append(tab)
        self._current = len(self._tabs) - 1
        return self._current

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def save_current(self) -> Optional[Path]:
        """Guarda la pestaña actual en su ruta existente.

        Returns:
            Ruta guardada, o None si no hay pestaña actual o si no tiene
            ruta asignada (usar ``save_as`` en ese caso).
        """
        tab = self.current_tab
        if tab is None:
            return None
        if tab.path is None:
            return None
        tab.path.write_text(tab.content, encoding="utf-8")
        tab.dirty = False
        return tab.path

    def save_as(self, path: Path) -> None:
        """Guarda la pestaña actual en una nueva ruta.

        La ruta solo se adopta después de escribir: si la escritura falla,
        la pestaña conserva su ruta anterior y sigue sucia.

        Args:
            path: Nueva ruta donde guardar el archivo.
        """
        tab = self.current_tab
        if tab is None:
            return
        path.write_text(tab.content, encoding="utf-8")
        tab.path = path
        tab.dirty = False

    # ------------------------------------------------------------------
    # Cerrar pestañas
    # ------------------------------------------------------------------

    def close_tab(self, index: int) -> bool:
        """Cierra la pestaña en el índice dado.

        Args:
            index: Índice de la pestaña a cerrar.

        Returns:
            True si se cerró correctamente, False si el índice no existe o
            la pestaña está sucia (el llamador debe preguntar al usuario).
        """
        if not (0 <= index < len(self._tabs)):
            return False
        return self.close_tab_for(self._tabs[index])

    def close_tab_for(self, tab: EditorTab) -> bool:
        """Cierra una pestaña concreta identificada por objeto.

        Args:
            tab: Pestaña que se desea cerrar.

        Returns:
            True si se cerró correctamente, False si no pertenece al gestor
            o si está sucia.
        """
        index = self._index_of(tab)
        if index < 0 or tab.dirty:
            return False
        current = self.current_tab
        self._tabs.pop(index)
        if current is tab:
            self._current = min(index, len(self._tabs) - 1)
        elif current is not None:
            self._current = self._index_of(current)
        else:
            self._current = -1
        return True

    # ------------------------------------------------------------------
    # Reordenación
    # ------------------------------------------------------------------

    def move_tab(self, from_index: int, to_index: int) -> None:
        """Reordena una pestaña conservando la actual por identidad.

        Args:
            from_index: Posición original de la pestaña.
            to_index: Posición de destino tras el movimiento.
        """
        if not (0 <= from_index < len(self._tabs)):
            return
        if not (0 <= to_index < len(self._tabs)):
            return
        current = self.current_tab
        tab = self._tabs.pop(from_index)
        self._tabs.insert(to_index, tab)
        if current is not None:
            self._current = self._index_of(current)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def _index_of(self, tab: EditorTab) -> int:
        """Devuelve el índice de una pestaña comparando identidad."""
        for index, candidate in enumerate(self._tabs):
            if candidate is tab:
                return index
        return -1

    @property
    def current_tab(self) -> Optional[EditorTab]:
        """Devuelve la pestaña actualmente activa, o None si no hay ninguna."""
        if 0 <= self._current < len(self._tabs):
            return self._tabs[self._current]
        return None

    @property
    def tabs(self) -> list[EditorTab]:
        """Devuelve la lista de todas las pestañas."""
        return self._tabs

    @property
    def current_index(self) -> int:
        """Devuelve el índice de la pestaña actual."""
        return self._current

    def set_current_index(self, index: int) -> None:
        """Cambia la pestaña actual."""
        if 0 <= index < len(self._tabs):
            self._current = index
