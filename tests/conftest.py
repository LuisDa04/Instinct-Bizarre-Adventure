"""Fixtures compartidas para las pruebas de interfaz con PyQt6.

La plataforma ``offscreen`` se selecciona antes de crear cualquier
``QApplication`` para que las pruebas puedan ejecutarse sin monitor.
"""
from __future__ import annotations

import os
from collections.abc import Callable

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    """Devuelve la QApplication compartida, creándola si no existe."""
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def wait_until(predicate: Callable[[], bool], timeout_ms: int = 2000) -> bool:
    """Sondea ``predicate`` procesando eventos hasta que sea cierto o venza.

    Args:
        predicate: Comprobación sin argumentos que se evalúa repetidamente.
        timeout_ms: Tiempo máximo de espera en milisegundos.

    Returns:
        True si el predicado llegó a cumplirse; False si se agotó el tiempo.
    """
    from PyQt6.QtTest import QTest

    elapsed = 0
    while elapsed < timeout_ms:
        if predicate():
            return True
        QTest.qWait(50)
        elapsed += 50
    return predicate()
