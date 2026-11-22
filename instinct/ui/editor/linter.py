"""Linter en tiempo real usando el compilador existente (creature_loader).

Reutiliza ``compiler_bridge.compile_source`` para no duplicar lógica de
scan/parse/resolve. Ejecuta en hilo separado con debounce para no bloquear
la UI mientras se edita.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer

from instinct.ui.editor.compiler_bridge import compile_source, Diagnostic


class _LintWorker(QObject):
    """Worker que corre en hilo separado: compila el source y emite diagnósticos."""

    finished = pyqtSignal(str, list)  # (source, list[Diagnostic])

    def __init__(self, source: str) -> None:
        super().__init__()
        self._source = source

    def run(self) -> None:
        """Ejecuta la compilación y emite el resultado."""
        _, diagnostics = compile_source(self._source)
        self.finished.emit(self._source, diagnostics)


class InstinctLinter(QObject):
    """Linter con debounce, caché y ejecución en hilo separado.

    Attributes:
        diagnostics_changed: Señal emitida con la lista de diagnósticos
            cada vez que se completa un análisis.
    """

    diagnostics_changed = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)  # debounce de 300 ms
        self._timer.timeout.connect(self._run_lint)
        self._pending_source = ""
        self._cache: dict[str, list[Diagnostic]] = {}
        self._thread: QThread | None = None
        self._worker: _LintWorker | None = None

    def set_source(self, source: str) -> None:
        """Actualiza el fuente a analizar y programa el lint con debounce.

        Si el fuente ya fue analizado (caché), emite inmediatamente.
        """
        self._pending_source = source

        # Caché hit: emitir inmediatamente sin hilos
        if source in self._cache:
            self.diagnostics_changed.emit(self._cache[source])
            return

        self._timer.start()

    def _run_lint(self) -> None:
        """Ejecuta el lint en hilo separado (o usa caché)."""
        source = self._pending_source

        if source in self._cache:
            self.diagnostics_changed.emit(self._cache[source])
            return

        self._worker = _LintWorker(source)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, source: str, diagnostics: list[Diagnostic]) -> None:
        """Guarda en caché y emite solo si el resultado sigue vigente."""
        self._cache[source] = diagnostics
        if source == self._pending_source:
            self.diagnostics_changed.emit(diagnostics)
