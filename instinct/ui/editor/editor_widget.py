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
    QApplication, QWidget, QVBoxLayout, QSplitter,
    QTabWidget, QPlainTextEdit, QListWidget, QListWidgetItem,
    QToolBar, QFileDialog, QMessageBox, QCompleter,
)
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QTextCursor, QKeyEvent

from instinct.ui.editor.highlighter import InstinctHighlighter
from instinct.ui.editor.completer import InstinctCompleter
from instinct.ui.editor.linter import InstinctLinter
from instinct.ui.editor.file_manager import EditorTab, FileManager
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
        self._editors: dict[QPlainTextEdit, EditorTab] = {}
        self._shutting_down = False

        self._setup_ui()
        self._setup_shortcuts()
        self._new_tab()  # Tab inicial vacío

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

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
        self._tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        splitter.addWidget(self._tabs)

        # Panel de errores (derecha)
        self._error_list = QListWidget()
        self._error_list.setMaximumWidth(250)
        self._error_list.itemClicked.connect(self._goto_error)
        splitter.addWidget(self._error_list)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def _setup_shortcuts(self) -> None:
        """Registra atajos de teclado del editor."""
        QShortcut(QKeySequence.StandardKey.New, self, self.new_tab)
        QShortcut(QKeySequence.StandardKey.Open, self, self.open_file)
        QShortcut(QKeySequence.StandardKey.Save, self, self.save_current)
        QShortcut(QKeySequence("Ctrl+R"), self, self.hot_reload_current)

    # ------------------------------------------------------------------
    # API pública (usada por App)
    # ------------------------------------------------------------------

    def new_tab(self) -> None:
        """Crea una pestaña vacía."""
        self._new_tab()

    def open_file(self) -> None:
        """Abre un fichero .ins desde el sistema de archivos."""
        self._open_file()

    def save_current(self) -> None:
        """Guarda la pestaña actual."""
        self._save_current()

    def hot_reload_current(self) -> None:
        """Recarga la criatura de la pestaña actual."""
        self._hot_reload_current()

    def shutdown(self) -> None:
        """Detiene linters y recursos de todas las pestañas."""
        self._shutting_down = True
        for i in range(self._tabs.count()):
            self._shutdown_editor(self._tabs.widget(i))

    def resume(self) -> None:
        """Reactiva el análisis y el contexto al volver a mostrar el editor."""
        if self._shutting_down:
            return
        for index in range(self._tabs.count()):
            editor = self._tabs.widget(index)
            tab = self._tab_for(editor)
            if tab is None:
                continue
            self._update_completion_context(editor)
            linter = editor.property("_linter")
            if linter is not None:
                linter.set_source(tab.content)

    def confirm_close(self) -> bool:
        """Comprueba los cambios pendientes antes de cerrar el editor."""
        dirty: list[tuple[QPlainTextEdit, EditorTab]] = []
        for index in range(self._tabs.count()):
            editor = self._tabs.widget(index)
            tab = self._tab_for(editor)
            if tab is not None and tab.dirty:
                dirty.append((editor, tab))
        if not dirty:
            return True

        policy = self._ask_close_policy([tab.name for _, tab in dirty])
        if policy == "discard":
            return True
        if policy != "save_all":
            return False

        for editor, tab in dirty:
            path = tab.path
            if path is None:
                selected, _ = QFileDialog.getSaveFileName(
                    self, "Guardar fichero .ins como", "", "Instinct (*.ins)"
                )
                if not selected:
                    return False
                path = Path(selected)
            tab.content = editor.toPlainText()
            if not self._write_tab(tab, path):
                return False
        return True

    def _ask_close_policy(self, names: list[str]) -> str:
        """Pregunta qué hacer con las pestañas sucias y devuelve la política."""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Cambios sin guardar")
        dialog.setText(f"Hay {len(names)} pestañas con cambios sin guardar.")
        dialog.setInformativeText("\n".join(names))
        save_all = dialog.addButton("Guardar todo", QMessageBox.ButtonRole.AcceptRole)
        discard = dialog.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        cancel = dialog.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(save_all)
        dialog.setEscapeButton(cancel)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is save_all:
            return "save_all"
        if clicked is discard:
            return "discard"
        return "cancel"

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self.confirm_close():
            event.ignore()
            return
        self.shutdown()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Gestión de pestañas y editor
    # ------------------------------------------------------------------

    def _new_tab(self) -> None:
        """Crea una pestaña vacía y la selecciona."""
        self._file_manager.new_tab()
        tab = self._file_manager.current_tab
        if tab is None:
            return
        self._add_editor_tab(tab)

    def _open_path(self, path: Path) -> None:
        """Abre un archivo en una pestaña nueva del editor."""
        self._file_manager.open_file(path)
        tab = self._file_manager.current_tab
        if tab is None:
            return
        self._add_editor_tab(tab)

    def _add_editor_tab(self, tab: EditorTab) -> None:
        """Crea el widget de editor para una pestaña y programa su lint inicial."""
        editor = self._create_editor()
        editor.setPlainText(tab.content)
        self._editors[editor] = tab
        self._update_completion_context(editor)
        self._tabs.addTab(editor, tab.name)
        self._tabs.setCurrentIndex(self._tabs.count() - 1)
        self._setup_editor_connections(editor)
        linter = editor.property("_linter")
        if linter is not None:
            linter.set_source(tab.content)
        tab.dirty = False
        self._refresh_tab_title(editor)

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
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.activated[str].connect(
            lambda text: self._insert_completion(editor, text)
        )
        linter = InstinctLinter(editor)
        linter.diagnostics_changed.connect(self._update_errors)
        context_timer = QTimer(editor)
        context_timer.setSingleShot(True)
        context_timer.setInterval(200)
        context_timer.timeout.connect(
            lambda: self._update_completion_context(editor)
        )
        editor.installEventFilter(self)

        # Guardar referencias como propiedades para acceso rápido
        editor.setProperty("_highlighter", highlighter)
        editor.setProperty("_completer", completer)
        editor.setProperty("_linter", linter)
        editor.setProperty("_context_timer", context_timer)
        return editor

    def _tab_for(self, editor: QPlainTextEdit | None) -> Optional[EditorTab]:
        """Devuelve la pestaña asociada a un editor, o None."""
        if editor is None:
            return None
        return self._editors.get(editor)

    def _editor_for(self, tab: EditorTab) -> Optional[QPlainTextEdit]:
        """Devuelve el editor asociado a una pestaña, o None."""
        for editor, candidate in self._editors.items():
            if candidate is tab:
                return editor
        return None

    def _setup_editor_connections(self, editor: QPlainTextEdit) -> None:
        """Conecta las señales del editor para actualizar estado."""
        editor.textChanged.connect(lambda: self._on_text_changed(editor))

    def _on_text_changed(self, editor: QPlainTextEdit) -> None:
        """Se llama cuando el usuario modifica el texto del editor."""
        tab = self._tab_for(editor)
        if tab is None:
            return

        # Actualizar modelo de datos
        tab.content = editor.toPlainText()
        tab.dirty = True
        self._refresh_tab_title(editor)

        # El contexto se reescanea con debounce para no reconstruir el modelo
        # en cada pulsación de tecla.
        timer = editor.property("_context_timer")
        if timer is not None:
            timer.start()
        linter = editor.property("_linter")
        if linter is not None:
            linter.set_source(tab.content)

    def _update_completion_context(self, editor: QPlainTextEdit) -> None:
        """Actualiza el contexto del completer con el fuente actual de la pestaña."""
        tab = self._tab_for(editor)
        completer = editor.property("_completer")
        if tab is None or completer is None:
            return
        completer.update_context(tab.content)

    @staticmethod
    def _prefix_at_cursor(editor: QPlainTextEdit) -> str:
        """Devuelve el identificador que termina justo antes del cursor."""
        cursor = editor.textCursor()
        if cursor.hasSelection():
            cursor.setPosition(cursor.selectionStart())
        text = cursor.block().text()
        position = cursor.positionInBlock()
        start = position
        while start > 0:
            char = text[start - 1]
            if not (char.isascii() and (char.isalnum() or char == "_")):
                break
            start -= 1
        return text[start:position]

    def _insert_completion(self, editor: QPlainTextEdit, text: str) -> None:
        """Sustituye el prefijo bajo el cursor por la completion elegida."""
        if self._tab_for(editor) is None:
            return
        prefix = self._prefix_at_cursor(editor)
        cursor = editor.textCursor()
        if prefix:
            cursor.movePosition(
                QTextCursor.MoveOperation.Left,
                QTextCursor.MoveMode.KeepAnchor,
                len(prefix),
            )
        cursor.insertText(text)
        editor.setTextCursor(cursor)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt override
        """Gestiona el popup del completer sin consumir teclas del editor."""
        if not isinstance(obj, QPlainTextEdit) or self._tab_for(obj) is None:
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.FocusOut:
            # El popup toma el foco al completar; eso no debe cerrarlo.
            if event.reason() != Qt.FocusReason.PopupFocusReason:
                self._hide_completion(obj)
        elif event.type() == QEvent.Type.KeyPress:
            self._on_editor_key_press(obj, event)
        return super().eventFilter(obj, event)

    def _on_editor_key_press(self, editor: QPlainTextEdit, event: QKeyEvent) -> None:
        """Muestra u oculta el popup según la tecla pulsada en el editor."""
        completer = editor.property("_completer")
        if completer is None:
            return
        key = event.key()
        if key in (
            Qt.Key.Key_Enter,
            Qt.Key.Key_Return,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Backtab,
            Qt.Key.Key_Escape,
        ):
            return
        if event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
        ):
            return
        if key == Qt.Key.Key_Backspace:
            cursor = editor.textCursor()
            prefix = self._prefix_at_cursor(editor)
            if not cursor.hasSelection():
                prefix = prefix[:-1]
            if not prefix:
                # Con MatchContains, un prefijo vacío mostraría todo el catálogo.
                self._hide_completion(editor)
                return
        else:
            text = event.text()
            if len(text) != 1 or not (
                text.isascii() and (text.isalnum() or text == "_")
            ):
                return
            prefix = self._prefix_at_cursor(editor) + text
        completer.setCompletionPrefix(prefix)
        if completer.completionCount() > 0:
            completer.complete()
        else:
            self._hide_completion(editor)

    @staticmethod
    def _hide_completion(editor: QPlainTextEdit) -> None:
        """Oculta el popup de completado asociado al editor."""
        completer = editor.property("_completer")
        if completer is not None:
            completer.popup().hide()

    def _refresh_tab_title(self, editor: QPlainTextEdit) -> None:
        """Actualiza el título visual del editor (añade * si está sucio)."""
        tab = self._tab_for(editor)
        index = self._tabs.indexOf(editor)
        if tab is None or index < 0:
            return
        title = tab.name + ("*" if tab.dirty else "")
        self._tabs.setTabText(index, title)

    def _current_editor(self) -> Optional[QPlainTextEdit]:
        """Devuelve el widget de editor de la pestaña actual, o None."""
        return self._tabs.currentWidget()  # type: ignore[no-any-return]

    def _on_tab_changed(self, index: int) -> None:
        """Se llama cuando el usuario cambia de pestaña."""
        self._file_manager.set_current_index(index)
        self._refresh_error_panel_for_index(index)

    def _on_tab_moved(self, from_index: int, to_index: int) -> None:
        """Sincroniza el modelo cuando el usuario mueve una pestaña."""
        self._file_manager.move_tab(from_index, to_index)
        self._file_manager.set_current_index(self._tabs.currentIndex())

    def _refresh_error_panel_for_index(self, index: int) -> None:
        """Muestra diagnósticos cacheados de la pestaña indicada."""
        editor = self._tabs.widget(index)
        if not isinstance(editor, QPlainTextEdit) or self._tab_for(editor) is None:
            self._error_list.clear()
            return
        linter = editor.property("_linter")
        if linter is None:
            self._error_list.clear()
            return
        diagnostics = linter._cache.get(editor.toPlainText())
        self._render_diagnostics(diagnostics if diagnostics is not None else [])

    def _shutdown_editor(self, editor) -> None:
        """Detiene recursos asociados a un editor de pestaña."""
        if not isinstance(editor, QPlainTextEdit):
            return
        timer = editor.property("_context_timer")
        if timer is not None:
            timer.stop()
        self._hide_completion(editor)
        linter = editor.property("_linter")
        shutdown = getattr(linter, "shutdown", None)
        if callable(shutdown):
            try:
                linter.diagnostics_changed.disconnect(self._update_errors)
            except (TypeError, RuntimeError):
                pass
            shutdown()

    def _close_tab(self, index: int) -> None:
        """Cierra la pestaña visible en el índice dado, preguntando si está sucia."""
        editor = self._tabs.widget(index)
        tab = self._tab_for(editor)
        if tab is None:
            return
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
                self._tabs.setCurrentWidget(editor)
                self._save_current()
                if tab.dirty:  # El usuario canceló el guardar
                    return

        if not self._file_manager.close_tab_for(tab):
            return
        self._editors.pop(editor, None)
        self._shutdown_editor(editor)
        self._tabs.removeTab(index)
        if isinstance(editor, QWidget):
            editor.deleteLater()

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
        try:
            self._open_path(Path(path))
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.warning(
                self, "Error al abrir", f"No se pudo abrir el archivo:\n{exc}"
            )

    def _write_tab(self, tab: EditorTab, path: Path) -> bool:
        """Escribe una pestaña conservando su estado si falla la escritura."""
        try:
            path.write_text(tab.content, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(
                self, "Error al guardar",
                f"No se pudo guardar el archivo:\n{exc}",
            )
            return False
        tab.path = path
        tab.dirty = False
        editor = self._editor_for(tab)
        if editor is not None:
            self._refresh_tab_title(editor)
        return True

    def _save_current(self) -> None:
        """Guarda la pestaña visible en su ruta existente."""
        editor = self._current_editor()
        tab = self._tab_for(editor)
        if editor is None or tab is None:
            return
        if tab.path is None:
            self._save_as()
            return
        tab.content = editor.toPlainText()
        self._write_tab(tab, tab.path)

    def _save_as(self) -> None:
        """Guarda la pestaña visible en una nueva ruta."""
        editor = self._current_editor()
        tab = self._tab_for(editor)
        if editor is None or tab is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar fichero .ins como", "", "Instinct (*.ins)"
        )
        if not path:
            return
        tab.content = editor.toPlainText()
        self._write_tab(tab, Path(path))

    # ------------------------------------------------------------------
    # Hot-reload
    # ------------------------------------------------------------------

    def _hot_reload_current(self) -> None:
        """Recompila y recarga la criatura de la pestaña visible."""
        tab = self._tab_for(self._current_editor())
        if tab is None or tab.path is None:
            QMessageBox.warning(
                self, "Sin archivo",
                "Guarda el archivo antes de recargar."
            )
            return

        expected_name = tab.path.stem.capitalize()
        result = self._hot_reload.reload_from_source(
            tab.content, expected_name=expected_name
        )
        if result.ok:
            self._show_status(f"Recargado: {result.name}")
        else:
            QMessageBox.warning(self, "Error de compilación", "\n".join(result.errors))

    def _show_status(self, msg: str) -> None:
        """Muestra un mensaje temporal (por ahora por consola)."""
        print(f"[Editor] {msg}")

    # ------------------------------------------------------------------
    # Panel de errores
    # ------------------------------------------------------------------

    def _update_errors(self, diagnostics) -> None:
        """Rellena el panel de errores con los diagnósticos del linter."""
        sender = self.sender()
        current = self._current_editor()
        if current is not None:
            current_linter = current.property("_linter")
            if sender is not None and current_linter is not sender:
                return
        self._render_diagnostics(diagnostics)

    def _render_diagnostics(self, diagnostics) -> None:
        """Renderiza diagnósticos en el panel de errores."""
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
