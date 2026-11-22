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
        """Ejecuta la compilación y emite siempre un resultado."""
        try:
            _, diagnostics = compile_source(self._source)
        except Exception:
            # No bloquear el ciclo de lint: el hilo debe poder terminar.
            diagnostics = []
        self.finished.emit(self._source, diagnostics)


class InstinctLinter(QObject):
    """Linter con debounce, caché y ejecución en hilo separado.

    Attributes:
        diagnostics_changed: Señal emitida con la lista de diagnósticos
            cada vez que se completa un análisis.
    """

    diagnostics_changed = pyqtSignal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)  # debounce de 300 ms
        self._timer.timeout.connect(self._run_lint)
        self._pending_source = ""
        self._cache: dict[str, list[Diagnostic]] = {}
        self._thread: QThread | None = None
        self._worker: _LintWorker | None = None
        self._running = False
        self._shutting_down = False

    def set_source(self, source: str) -> None:
        """Actualiza el fuente a analizar y programa el lint con debounce.

        Si el fuente ya fue analizado (caché), emite inmediatamente.
        """
        self._pending_source = source

        # Caché hit: emitir inmediatamente sin hilos
        if source in self._cache:
            self._timer.stop()
            self.diagnostics_changed.emit(self._cache[source])
            return

        if self._shutting_down:
            return

        self._timer.start()

    def shutdown(self, timeout_ms: int = 2000) -> None:
        """Detiene el linter y espera a que el hilo activo termine."""
        self._shutting_down = True
        self._timer.stop()
        thread = self._thread
        if thread is not None and thread.isRunning():
            thread.quit()
            if not thread.wait(timeout_ms):
                # Evitar destruir un QThread en ejecución.
                return
        self._running = False

    def _run_lint(self) -> None:
        """Ejecuta el lint en hilo separado (o usa caché)."""
        if self._shutting_down:
            return

        source = self._pending_source

        if source in self._cache:
            self.diagnostics_changed.emit(self._cache[source])
            return

        if self._running:
            # Single-flight: al terminar se re-linteará el último pending.
            return

        self._start_lint(source)

    def _start_lint(self, source: str) -> None:
        """Arranca un worker para lintar `source`."""
        worker = _LintWorker(source)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)

        self._worker = worker
        self._thread = thread
        self._running = True
        thread.start()

    def _on_finished(self, source: str, diagnostics: list[Diagnostic]) -> None:
        """Guarda en caché y emite solo si el resultado sigue vigente."""
        self._cache[source] = diagnostics
        if self._shutting_down:
            return
        if source == self._pending_source:
            self.diagnostics_changed.emit(diagnostics)

    def _on_thread_finished(self) -> None:
        """Limpia refs del hilo y relanza lint si quedó trabajo pendiente."""
        self._running = False
        self._worker = None
        self._thread = None

        if self._shutting_down:
            return

        source = self._pending_source
        if source and source not in self._cache:
            self._start_lint(source)
