"""Pruebas del linter en tiempo real del editor."""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QCoreApplication

from instinct.ui.editor.linter import InstinctLinter
from instinct.ui.editor.compiler_bridge import Diagnostic, compile_source


@pytest.fixture
def linter() -> InstinctLinter:
    return InstinctLinter()


def test_compile_source_valid() -> None:
    """Compilación de código válido no produce errores."""
    source = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    wait(1)\n    goto start\n"
    )
    program, diagnostics = compile_source(source)
    assert program is not None
    assert diagnostics == []


def test_compile_source_invalid_syntax() -> None:
    """Código con error de sintaxis produce diagnósticos."""
    source = "start:\n    wait(1)\n"  # falta cabecera
    program, diagnostics = compile_source(source)
    assert program is None
    assert len(diagnostics) > 0
    assert all(d.severity == "error" for d in diagnostics)
    assert all(d.line > 0 for d in diagnostics)


def test_compile_source_invalid_semantic() -> None:
    """Código con error semántico (acción desconocida) produce diagnósticos."""
    source = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    unknown_action(1)\n    goto start\n"
    )
    program, diagnostics = compile_source(source)
    assert program is None
    assert len(diagnostics) > 0
    assert any("acción desconocida" in d.message for d in diagnostics)


def test_linter_initializes(linter: InstinctLinter) -> None:
    """El linter se construye sin errores."""
    assert linter._timer is not None
    assert linter._timer.interval() == 300
    assert linter._cache == {}


def test_linter_set_source_updates_pending(linter: InstinctLinter) -> None:
    """set_source actualiza el fuente pendiente."""
    source = "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\nstart:\n    wait(1)\n"
    linter.set_source(source)
    assert linter._pending_source == source