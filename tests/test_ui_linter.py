"""Pruebas del linter en tiempo real del editor."""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from instinct.ui.editor.linter import InstinctLinter


@pytest.fixture
def linter() -> InstinctLinter:
    return InstinctLinter()


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


def test_linter_ignores_stale_result(linter: InstinctLinter) -> None:
    """Un resultado viejo se cachea pero no se emite como actual."""
    from instinct.ui.editor.compiler_bridge import Diagnostic

    emitted: list[list[Diagnostic]] = []
    linter.diagnostics_changed.connect(emitted.append)

    linter._pending_source = "nuevo"
    stale = [Diagnostic(line=1, column=0, severity="error", message="x", code="SYNTAX")]
    fresh = [Diagnostic(line=2, column=0, severity="error", message="y", code="SYNTAX")]

    linter._on_finished("viejo", stale)
    assert linter._cache["viejo"] == stale
    assert emitted == []

    linter._on_finished("nuevo", fresh)
    assert linter._cache["nuevo"] == fresh
    assert emitted == [fresh]