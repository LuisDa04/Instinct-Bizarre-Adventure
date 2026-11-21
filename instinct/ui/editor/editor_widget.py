"""Widget principal del editor de código Instinct.

Proporciona una interfaz con pestañas para editar ficheros .ins, con:
- Resaltado de sintaxis (InstinctHighlighter)
- Autocompletado (InstinctCompleter)
- Linting en tiempo real (InstinctLinter)
- Panel de errores navegable
- Hot-reload al guardar (HotReloadManager)

Este widget es puro PyQt6 y no contiene lógica de simulación;
toda la lógica vive en Session (compartida con App).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter,
    QTabWidget, QPlainTextEdit, QListWidget, QListWidgetItem,
    QToolBar, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor

from instinct.ui.editor.highlighter import InstinctHighlighter
from instinct.ui.editor.completer import InstinctCompleter
from instinct.ui.editor.linter import InstinctLinter
from instinct.ui.editor.file_manager import FileManager, EditorTab
from instinct.ui.editor.hot_reload import HotReloadManager
from instinct.ui.session import Session


class EditorWidget(QWidget):
    """Editor principal de ficheros .ins para la simulación Instinct.

    Integra:
    - Pestañas múltiples de edición
    - Resaltado de sintaxis, autocompletado y linting en tiempo real
    - Panel de errores navegable (clic para saltar a la línea)
    - Toolbar con acciones de archivo y hot-reload
    - Integración con Session para recarga en caliente de criaturas
    """

    def __init__(self, session: Session, parent=None) -> None:
        """Crea el editor vinculado a una sesión de simulación.

        Args:
            session: Sesión activa (compartida con App) que contiene
                el CLI, el mundo y el motor de simulación.
        """
        super().__init__(parent)
        self._session = session
        self._file_manager = FileManager()
        self._hot_reload = HotReloadManager(session)

        self._setup_ui()
        self._new_tab()  # Tab inicial vacío

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Construye la jerarquía de widgets del editor."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar superior
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.addAction("Nuevo", self._new_tab)
        toolbar.addAction("Abrir", self._open_file)
        toolbar.addAction("Guardar", self._save_current)
        toolbar.addAction("Guardar como", self._save_as)
        toolbar.addSeparator()
        toolbar.addAction("Recargar (Ctrl+R)", self._hot_reload_current)
        layout.addWidget(toolbar)

        # Splitter: editor (izquierda) + panel de errores (derecha)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Pestañas de editor
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self._tabs)

        # Panel de errores (derecha)
        self._error_list = QListWidget()
        self._error_list.setMaximumWidth(250)
        self._error_list.itemClicked.connect(self._goto_error)
        splitter.addWidget(self._error_list)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # Gestión de pestañas y editor
    # ------------------------------------------------------------------

    def _new_tab(self) -> None:
        """Crea una pestaña vacía y la selecciona."""
        idx = self._file_manager.new_tab()
        editor = self._create_editor()
        tab = self._file_manager.tabs[-1]
        self._tabs.addTab(editor, tab.name)
        self._tabs.setCurrentIndex(idx)
        self._setup_editor_connections(editor)

    def _create_editor(self) -> QPlainTextEdit:
        """Crea un QPlainTextEdit con highlighter, completer y linter."""
        editor = QPlainTextEdit()
        font = QFont("Consolas", 11)
        editor.setFont(font)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Instalar componentes
        highlighter = InstinctHighlighter(editor.document())
        completer = InstinctCompleter(editor)
        completer.setWidget(editor)
        linter = InstinctLinter()
        linter.diagnostics_changed.connect(lambda d: self._update_errors(d))

        # Guardar referencias como propiedades para acceso rápido
        editor.setProperty("_highlighter", highlighter)
        editor.setProperty("_completer", completer)
        editor.setProperty("_linter", linter)
        return editor

    def _setup_editor_connections(self, editor: QPlainTextEdit) -> None:
        """Conecta las señales del editor para actualizar estado."""
        editor.textChanged.connect(lambda: self._on_text_changed(editor))

    def _on_text_changed(self, editor: QPlainTextEdit) -> None:
        """Se llama cuando el usuario modifica el texto del editor."""
        tab = self._file_manager.current_tab
        if tab is None:
            return

        # Actualizar modelo de datos
        tab.content = editor.toPlainText()
        tab.dirty = True
        self._update_tab_title()

        # Notificar al completer y al linter
        completer = editor.property("_completer")
        if completer is not None:
            completer.update_context(tab.content)

        linter = editor.property("_linter")
        if linter is not None:
            linter.set_source(tab.content)

    def _update_tab_title(self) -> None:
        """Actualiza el título de la pestaña actual (añade * si está sucia)."""
        idx = self._tabs.currentIndex()
        if idx < 0:
            return
        tab = self._file_manager.tabs[idx]
        title = tab.name + ("*" if tab.dirty else "")
        self._tabs.setTabText(idx, title)

    def _current_editor(self) -> Optional[QPlainTextEdit]:
        """Devuelve el widget de editor de la pestaña actual, o None."""
        return self._tabs.currentWidget()  # type: ignore[no-any-return]

    def _on_tab_changed(self, index: int) -> None:
        """Se llama cuando el usuario cambia de pestaña."""
        self._file_manager.set_current_index(index)

    def _close_tab(self, index: int) -> None:
        """Cierra la pestaña en el índice dado, preguntando si está sucia."""
        tab = self._file_manager.tabs[index]
        if tab.dirty:
            reply = QMessageBox.question(
                self,
                "Cambios sin guardar",
                f"¿Guardar cambios en '{tab.name}' antes de cerrar?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                self._save_current()
                if tab.dirty:  # El usuario canceló el guardar
                    return

        if self._file_manager.close_tab(index):
            self._tabs.removeTab(index)

    # ------------------------------------------------------------------
    # Archivo: abrir, guardar, guardar como
    # ------------------------------------------------------------------

    def _open_file(self) -> None:
        """Abre un fichero .ins desde el sistema de archivos."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir fichero .ins", "", "Instinct (*.ins)"
        )
        if not path:
            return
        p = Path(path)
        self._file_manager.open_file(p)
        self._new_tab()  # Crea pestaña y carga contenido
        editor = self._current_editor()
        tab = self._file_manager.current_tab
        if editor is not None and tab is not None:
            editor.setPlainText(tab.content)
            tab.dirty = False
            self._update_tab_title()

    def _save_current(self) -> None:
        """Guarda la pestaña actual en su ruta existente."""
        tab = self._file_manager.current_tab
        if tab is None:
            return
        if tab.path is None:
            self._save_as()
            return
        tab.path.write_text(tab.content, encoding="utf-8")
        tab.dirty = False
        self._update_tab_title()

    def _save_as(self) -> None:
        """Guarda la pestaña actual en una nueva ruta."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar fichero .ins como", "", "Instinct (*.ins)"
        )
        if not path:
            return
        p = Path(path)
        tab = self._file_manager.current_tab
        if tab is None:
            return
        tab.path = p
        self._save_current()
        self._update_tab_title()

    # ------------------------------------------------------------------
    # Hot-reload
    # ------------------------------------------------------------------

    def _hot_reload_current(self) -> None:
        """Recompila y recarga la criatura de la pestaña actual."""
        tab = self._file_manager.current_tab
        if tab is None or tab.path is None:
            QMessageBox.warning(
                self, "Sin archivo",
                "Guarda el archivo antes de recargar."
            )
            return

        # Compilar primero para obtener el nombre real de la especie
        from instinct.loaders.creature_loader import load_creature
        result = load_creature(tab.content)
        if result.creature is None:
            errors = [f"línea {e.line}: {e.message}" for e in result.errors]
            QMessageBox.warning(self, "Error de compilación", "\n".join(errors))
            return

        name = result.creature.name
        ok, errors = self._hot_reload.reload_creature(name, tab.content)

        if ok:
            self._show_status(f"Recargado: {name}")
        else:
            QMessageBox.warning(self, "Error de compilación", "\n".join(errors))

    def _show_status(self, msg: str) -> None:
        """Muestra un mensaje temporal (por ahora por consola)."""
        print(f"[Editor] {msg}")

    # ------------------------------------------------------------------
    # Panel de errores
    # ------------------------------------------------------------------

    def _update_errors(self, diagnostics) -> None:
        """Rellena el panel de errores con los diagnósticos del linter."""
        self._error_list.clear()
        for d in diagnostics:
            item = QListWidgetItem(f"Línea {d.line}: {d.message}")
            item.setData(Qt.ItemDataRole.UserRole, d.line)
            self._error_list.addItem(item)

    def _goto_error(self, item: QListWidgetItem) -> None:
        """Salta a la línea de un error seleccionado en la lista."""
        line = item.data(Qt.ItemDataRole.UserRole)
        editor = self._current_editor()
        if editor is None or line is None:
            return
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(
            QTextCursor.MoveOperation.Down,
            QTextCursor.MoveMode.MoveAnchor,
            max(0, line - 1),
        )
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()
