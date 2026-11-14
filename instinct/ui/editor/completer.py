"""Autocompletado para el editor Instinct.

Reutiliza los catálogos centrales de ``instinct.compiler.catalogs`` y añade
detección dinámica de variables locales y etiquetas del archivo actual.
"""
from __future__ import annotations

import re

from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import QStringListModel, Qt

from instinct.ui.editor.compiler_bridge import get_catalogs


class InstinctCompleter(QCompleter):
    """Completer con catálogos estáticos + variables locales y etiquetas dinámicas.

    Los elementos estáticos (keywords, acciones, funciones, percepciones,
    constantes) vienen de los catálogos del compilador. Los elementos
    dinámicos (variables asignadas con ``x = ...`` y etiquetas ``label:``)
    se extraen del archivo abierto en tiempo real.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._catalogs = get_catalogs()
        self._local_vars: set[str] = set()
        self._labels: set[str] = set()
        self._model = QStringListModel()
        self.setModel(self._model)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        self._rebuild_model()

    def update_context(self, source: str) -> None:
        """Extrae variables locales y etiquetas del source actual.

        Args:
            source: Texto completo del fichero .ins abierto.
        """
        self._local_vars = set(
            re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", source, re.MULTILINE)
        )
        self._labels = set(
            re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*):", source, re.MULTILINE)
        )
        self._rebuild_model()

    def _rebuild_model(self) -> None:
        """Reconstruye el modelo combinando elementos estáticos y dinámicos."""
        items: set[str] = set()

        # Elementos estáticos de los catálogos del compilador
        items.update(self._catalogs["keywords"])
        items.update(self._catalogs["actions"].keys())
        items.update(self._catalogs["functions"].keys())
        items.update(self._catalogs["perceptions"])
        items.update(self._catalogs["constants"])

        # Elementos dinámicos del archivo actual
        items.update(self._local_vars)
        items.update(self._labels)

        self._model.setStringList(sorted(items))
