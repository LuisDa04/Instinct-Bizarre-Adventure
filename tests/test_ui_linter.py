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


def test_linter_worker_emits_empty_on_exception(monkeypatch) -> None:
    """Si compile_source falla, el worker emite diagnósticos vacíos."""
    from instinct.ui.editor import linter as linter_mod

    def boom(_source: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(linter_mod, "compile_source", boom)
    worker = linter_mod._LintWorker("x")
    results: list[tuple[str, list]] = []
    worker.finished.connect(lambda s, d: results.append((s, d)))
    worker.run()
    assert results == [("x", [])]


def test_linter_shutdown_stops_timer(linter: InstinctLinter) -> None:
    """shutdown detiene el debounce y marca el linter como apagado."""
    linter._timer.start()
    linter.shutdown()
    assert linter._shutting_down is True
    assert not linter._timer.isActive()
    # Después de shutdown no se programa nuevo lint
    linter.set_source("new")
    assert not linter._timer.isActive()


def test_linter_single_flight_defers_when_running(linter: InstinctLinter) -> None:
    """Si ya hay un lint en curso, no se arranca otro hilo."""
    linter._running = True
    linter._pending_source = "source"
    linter._run_lint()
    assert linter._thread is None
    assert linter._worker is None


def test_linter_reruns_pending_after_thread_finished(
    linter: InstinctLinter, monkeypatch
) -> None:
    """Al terminar un hilo, relintea si el pending no está en caché."""
    calls: list[str] = []
    monkeypatch.setattr(linter, "_start_lint", lambda s: calls.append(s))
    linter._pending_source = "new"
    linter._cache["old"] = []
    linter._running = True
    linter._on_thread_finished()
    assert linter._running is False
    assert calls == ["new"]


def test_linter_no_rerun_when_shutting_down(
    linter: InstinctLinter, monkeypatch
) -> None:
    """Durante shutdown no se relanza lint pendiente."""
    calls: list[str] = []
    monkeypatch.setattr(linter, "_start_lint", lambda s: calls.append(s))
    linter._shutting_down = True
    linter._pending_source = "new"
    linter._on_thread_finished()
    assert calls == []