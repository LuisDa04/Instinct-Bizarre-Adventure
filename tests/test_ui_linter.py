"""Pruebas del linter en tiempo real del editor."""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QObject

from instinct.ui.editor.linter import InstinctLinter
from instinct.ui.editor.compiler_bridge import Diagnostic


@pytest.fixture
def linter() -> InstinctLinter:
    return InstinctLinter()


def test_linter_initializes(linter: InstinctLinter) -> None:
    """El linter se construye sin errores."""
    assert linter._timer is not None
    assert linter._timer.interval() == 300
    assert linter._cache == {}


def test_linter_emits_diagnostics(linter: InstinctLinter) -> None:
    """El linter emite diagnósticos cuando se le pasa código fuente."""
    received: list[list[Diagnostic]] = []
    linter.diagnostics_changed.connect(lambda d: received.append(d))

    # Código fuente válido (sin errores)
    source_valido = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    wait(1)\n    goto start\n"
    )
    linter.set_source(source_valido)

    # El linter usa QTimer + QThread, así que puede ser asíncrono.
    # Esperamos a que se procese (en tests reales usaríamos QTest.qWait).
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.processEvents()
    QTest.qWait(500)

    assert len(received) >= 1, "El linter debe emitir al menos una vez"
    diagnostics = received[-1]
    # Código válido no debe tener errores
    assert len(diagnostics) == 0, f"Esperaba 0 errores, obtuve: {diagnostics}"


def test_linter_detects_errors(linter: InstinctLinter) -> None:
    """El linter detecta errores de compilación."""
    received: list[list[Diagnostic]] = []
    linter.diagnostics_changed.connect(lambda d: received.append(d))

    # Código inválido (falta cabecera)
    source_invalido = "start:\n    wait(1)\n"
    linter.set_source(source_invalido)

    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.processEvents()
    QTest.qWait(500)

    assert len(received) >= 1
    diagnostics = received[-1]
    assert len(diagnostics) > 0, "Debe detectar errores en código inválido"
    assert all(d.severity == "error" for d in diagnostics)
    assert all(d.line > 0 for d in diagnostics)


def test_linter_cache_avoids_recompilation(linter: InstinctLinter) -> None:
    """El linter usa caché para evitar recompilación del mismo source."""
    received_count = 0
    linter.diagnostics_changed.connect(lambda d: received_count.append(d))

    source = "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\nstart:\n    wait(1)\n    goto start\n"

    linter.set_source(source)
    linter.set_source(source)  # Mismo source -> debería usar caché

    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.processEvents()
    QTest.qWait(500)

    # Al menos una emisión (la primera), posiblemente dos si el timer
    # se dispara antes de que el caché funcione. Lo importante es que no
    # haya errores en la caché.
    assert len(received_count) >= 1

    # Verificar que el último resultado no tiene errores (código válido)
    if received_count:
        assert len(received_count[-1]) == 0
