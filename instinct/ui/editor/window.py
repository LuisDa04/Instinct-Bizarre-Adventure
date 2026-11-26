"""Ventana del editor con confirmación de cierre.

El widget hijo decide si hay cambios sin guardar; la ventana respeta su
respuesta para que la X de la ventana no pierda trabajo.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow


class EditorWindow(QMainWindow):
    """Ventana principal del editor que protege los cambios sin guardar."""

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Confirma con el editor antes de ocultar la ventana sin apagarlo."""
        widget = self.centralWidget()
        confirm_close = getattr(widget, "confirm_close", None)
        if callable(confirm_close) and not confirm_close():
            event.ignore()
            return
        self.hide()
        event.ignore()
