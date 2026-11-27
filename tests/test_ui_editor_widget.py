"""Pruebas del widget de edición: pestañas móviles y autocompletado."""
from __future__ import annotations

from pathlib import Path

import pytest

from conftest import wait_until

pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QTextCursor  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit  # noqa: E402

import instinct.ui.editor.editor_widget as editor_widget_module  # noqa: E402
from instinct.ui.editor.editor_widget import EditorWidget  # noqa: E402
from instinct.ui.session import Session  # noqa: E402

GRASS = "terrain Grass\nchar .\nresource_max 100\nregen 2\n"
ROCK = "object Rock\nchar #\nresource_max 100\n"
MAP = "Prueba\n..\n.#\n"
URUK = """\
creature Uruk
faction isengard
health 80
vision 6
lifespan 400

start:
    wait(1)
    goto start
"""
SOURCE_FIRST = """\
creature First
faction prueba
health 50
vision 3
lifespan 100

start:
    wait(1)
"""
SOURCE_SECOND = """\
creature Second
faction prueba
health 60
vision 4
lifespan 200

start:
    wait(2)
"""
SOURCE_SECOND_EDIT = """\
creature Second
faction prueba
health 70
vision 5
lifespan 300

start:
    wait(3)
"""
BROKEN_SOURCE = """\
creature Roto
faction prueba
health 0
vision 3
lifespan 100

start:
    wait(1)
"""
OTHER_BROKEN_SOURCE = """\
creature Otro
faction prueba
health 50
vision 3
lifespan 100

start:
    wait(1)
    !
"""
BROKEN_DIAGNOSTIC = "Línea 3: health debe ser mayor que 0"
OTHER_DIAGNOSTIC = "Línea 9: carácter inesperado '!'"
RENAMED_URUK = """\
creature Orc
faction isengard
health 80
vision 6
lifespan 400

start:
    wait(1)
    goto start
"""


def _build_content(base: Path) -> None:
    """Crea el contenido mínimo que la sesión puede cargar."""
    for name, source in (
        ("terrains/grass.te", GRASS),
        ("objects/rock.ob", ROCK),
        ("maps/prueba.map", MAP),
        ("creatures/uruk.ins", URUK),
    ):
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


@pytest.fixture
def editor(tmp_path: Path, qapp) -> tuple[EditorWidget, Session]:
    """Crea un EditorWidget con una sesión sobre contenido temporal."""
    _build_content(tmp_path)
    session = Session(tmp_path)
    widget = EditorWidget(session)
    yield widget, session
    for tab in widget._file_manager.tabs:
        tab.dirty = False
    widget.shutdown()
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def _open_pair(widget: EditorWidget, tmp_path: Path) -> tuple[Path, Path]:
    """Abre dos archivos de criatura y devuelve sus rutas."""
    f1 = tmp_path / "f1.ins"
    f2 = tmp_path / "f2.ins"
    f1.write_text(SOURCE_FIRST, encoding="utf-8")
    f2.write_text(SOURCE_SECOND, encoding="utf-8")
    widget._open_path(f1)
    widget._open_path(f2)
    return f1, f2


def _visible_titles(widget: EditorWidget) -> list[str]:
    """Devuelve los títulos visibles sin el marcador de cambios."""
    return [
        widget._tabs.tabText(i).removesuffix("*")
        for i in range(widget._tabs.count())
    ]


def _current_with_completer(
    widget: EditorWidget,
) -> tuple[QPlainTextEdit, QCompleter]:
    """Devuelve el editor visible y su completer, comprobando que existen."""
    current = widget._current_editor()
    assert current is not None
    completer = current.property("_completer")
    assert completer is not None
    return current, completer


def _error_texts(widget: EditorWidget) -> list[str]:
    """Devuelve el texto de las entradas visibles en el panel de errores."""
    return [
        widget._error_list.item(index).text()
        for index in range(widget._error_list.count())
    ]


def _open_source(widget: EditorWidget, path: Path, source: str) -> QPlainTextEdit:
    """Escribe un archivo con `source` y lo abre en una pestaña nueva."""
    path.write_text(source, encoding="utf-8")
    widget._open_path(path)
    editor = widget._current_editor()
    assert editor is not None
    return editor


def _fail_write(*args, **kwargs) -> None:
    """Simula un error de escritura del sistema de archivos."""
    raise OSError("disco de solo lectura")


def _stub_save_dialog(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Sustituye el diálogo de guardar por una respuesta determinista."""
    class _DialogStub:
        @staticmethod
        def getSaveFileName(*args, **kwargs):
            return str(path), "Instinct (*.ins)"

    monkeypatch.setattr(editor_widget_module, "QFileDialog", _DialogStub)


def _capture_critical(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Captura los mensajes críticos sin mostrarlos en pantalla."""
    shown: list[tuple] = []

    def _critical(*args, **kwargs) -> None:
        shown.append(args)

    monkeypatch.setattr(editor_widget_module.QMessageBox, "critical", _critical)
    return shown


def _capture_warning(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Captura los avisos sin abrir ningún diálogo real."""
    shown: list[tuple] = []

    def _warning(*args, **kwargs) -> None:
        shown.append(args)

    monkeypatch.setattr(editor_widget_module.QMessageBox, "warning", _warning)
    return shown


def test_completer_is_attached_to_editor(
    editor: tuple[EditorWidget, Session],
) -> None:
    """El completer queda adjunto al editor con popup como modo de completado."""
    widget, _ = editor
    current, completer = _current_with_completer(widget)

    assert completer.widget() is current
    assert completer.completionMode() == QCompleter.CompletionMode.PopupCompletion


def test_completer_inserts_completion_at_cursor(
    editor: tuple[EditorWidget, Session],
) -> None:
    """Activar una completion sustituye el prefijo escrito sin duplicarlo."""
    widget, _ = editor
    current, completer = _current_with_completer(widget)
    current.setPlainText("vision 3\nhea")
    current.moveCursor(QTextCursor.MoveOperation.End)
    completer.setCompletionPrefix("hea")

    completer.activated[str].emit("health")

    assert current.toPlainText() == "vision 3\nhealth"
    assert current.toPlainText().count("health") == 1


def test_completer_popup_opens_with_known_prefix(
    editor: tuple[EditorWidget, Session], qapp
) -> None:
    """El popup aparece para 'hea' y se oculta para un prefijo desconocido."""
    widget, _ = editor
    current, completer = _current_with_completer(widget)
    widget.show()
    qapp.processEvents()
    current.setFocus()
    assert current.hasFocus()
    assert "health" in completer._model.stringList()

    current.setPlainText("")
    QTest.keyClicks(current, "hea")
    assert wait_until(lambda: completer.popup().isVisible())
    assert completer.completionCount() > 0

    current.setPlainText("")
    QTest.keyClicks(current, "zzzq")
    assert wait_until(lambda: not completer.popup().isVisible())


def test_backspace_with_empty_prefix_keeps_popup_closed(
    editor: tuple[EditorWidget, Session], qapp
) -> None:
    """Backspace sin prefijo resultante no abre el popup con todo el catálogo."""
    widget, _ = editor
    current, completer = _current_with_completer(widget)
    widget.show()
    qapp.processEvents()
    current.setFocus()

    current.setPlainText("")
    completer.popup().hide()
    QTest.keyClick(current, Qt.Key.Key_Backspace)
    qapp.processEvents()
    assert not completer.popup().isVisible()

    current.setPlainText("a")
    current.moveCursor(QTextCursor.MoveOperation.End)
    completer.popup().hide()
    QTest.keyClick(current, Qt.Key.Key_Backspace)
    qapp.processEvents()
    assert current.toPlainText() == ""
    assert not completer.popup().isVisible()


def test_double_shutdown_stops_context_timer(
    editor: tuple[EditorWidget, Session],
) -> None:
    """Dos llamadas a shutdown detienen el timer sin lanzar excepciones."""
    widget, _ = editor
    current, _ = _current_with_completer(widget)
    timer = current.property("_context_timer")
    assert timer is not None

    linter = current.property("_linter")
    assert linter is not None

    current.setPlainText("x = 1\n")
    assert timer.isActive()
    assert linter._timer.isActive()
    widget.shutdown()
    assert timer.isActive() is False
    assert linter._timer.isActive() is False
    widget.shutdown()
    assert timer.isActive() is False
    assert linter._timer.isActive() is False


def test_completion_context_refreshes_after_debounce(
    editor: tuple[EditorWidget, Session],
) -> None:
    """Las etiquetas nuevas entran al modelo tras el debounce del contexto."""
    widget, _ = editor
    current, completer = _current_with_completer(widget)
    assert "nuevo_label" not in completer._model.stringList()

    current.setPlainText("nuevo_label:\n    wait(1)\n")

    assert wait_until(lambda: "nuevo_label" in completer._model.stringList())


def test_opening_broken_file_reports_diagnostic_after_debounce(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """Abrir un archivo con error lo muestra en el panel sin editar."""
    widget, _ = editor
    _open_source(widget, tmp_path / "roto.ins", BROKEN_SOURCE)

    assert wait_until(lambda: BROKEN_DIAGNOSTIC in _error_texts(widget))


def test_standalone_widget_close_still_shuts_down(
    editor: tuple[EditorWidget, Session]
) -> None:
    """El widget suelto sigue apagando sus recursos al cerrarse."""
    widget, _ = editor
    current = widget._current_editor()
    assert current is not None
    linter = current.property("_linter")
    assert linter is not None

    widget.close()

    assert linter._shutting_down is True
    assert linter._timer.isActive() is False


def test_resume_restores_diagnostics_without_duplicates(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """Reactivar el editor vuelve a mostrar cada diagnóstico una sola vez."""
    widget, _ = editor
    first_editor = _open_source(widget, tmp_path / "roto.ins", BROKEN_SOURCE)
    assert wait_until(lambda: BROKEN_DIAGNOSTIC in _error_texts(widget))
    second_editor = _open_source(widget, tmp_path / "otro.ins", OTHER_BROKEN_SOURCE)
    assert wait_until(lambda: OTHER_DIAGNOSTIC in _error_texts(widget))

    widget._error_list.clear()
    widget.resume()

    assert wait_until(lambda: OTHER_DIAGNOSTIC in _error_texts(widget))
    assert _error_texts(widget) == [OTHER_DIAGNOSTIC]
    widget._tabs.setCurrentIndex(widget._tabs.indexOf(first_editor))
    assert _error_texts(widget) == [BROKEN_DIAGNOSTIC]
    widget._tabs.setCurrentIndex(widget._tabs.indexOf(second_editor))
    assert _error_texts(widget) == [OTHER_DIAGNOSTIC]


def test_resume_after_shutdown_does_not_reactivate(
    editor: tuple[EditorWidget, Session]
) -> None:
    """Un editor apagado definitivamente no se reactiva al reanudarlo."""
    widget, _ = editor
    current = widget._current_editor()
    assert current is not None
    linter = current.property("_linter")
    assert linter is not None

    widget.shutdown()
    assert linter._timer.isActive() is False
    widget.resume()

    assert linter._shutting_down is True
    assert linter._timer.isActive() is False


def test_opening_file_only_schedules_lint(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """La apertura deja el timer pendiente y no ejecuta el worker."""
    widget, _ = editor
    current = _open_source(widget, tmp_path / "roto.ins", BROKEN_SOURCE)
    linter = current.property("_linter")
    assert linter is not None

    assert linter._timer.isActive()
    assert linter._pending_source == BROKEN_SOURCE
    assert linter._thread is None
    assert BROKEN_SOURCE not in linter._cache
    assert _error_texts(widget) == []


def test_opening_several_tabs_lints_each_once_and_switching_keeps_errors(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """Cada pestaña analiza su fuente una vez y conserva sus errores al cambiar."""
    widget, _ = editor
    first_editor = _open_source(widget, tmp_path / "roto.ins", BROKEN_SOURCE)
    second_editor = _open_source(widget, tmp_path / "otro.ins", OTHER_BROKEN_SOURCE)
    first_linter = first_editor.property("_linter")
    second_linter = second_editor.property("_linter")
    assert first_linter is not None and second_linter is not None

    first_results: list = []
    second_results: list = []
    first_linter.diagnostics_changed.connect(first_results.append)
    second_linter.diagnostics_changed.connect(second_results.append)

    assert wait_until(lambda: bool(first_results) and bool(second_results))
    assert len(first_results) == 1
    assert len(second_results) == 1
    assert _error_texts(widget) == [OTHER_DIAGNOSTIC]

    widget._tabs.setCurrentIndex(widget._tabs.indexOf(first_editor))
    assert _error_texts(widget) == [BROKEN_DIAGNOSTIC]


def test_hot_reload_warns_and_rejects_renamed_header(
    editor: tuple[EditorWidget, Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recargar una cabecera renombrada avisa y no crea otra especie."""
    widget, session = editor
    assert session.load() is True
    _open_source(widget, tmp_path / "renombrado.ins", RENAMED_URUK)
    shown = _capture_warning(monkeypatch)
    status: list[str] = []
    monkeypatch.setattr(widget, "_show_status", status.append, raising=False)
    assert session._controller.loaded is not None
    before_catalog = dict(session._controller.loaded.creatures)

    widget._hot_reload_current()

    assert len(shown) == 1
    assert "recarga cancelada" in shown[0][2]
    assert status == []
    assert set(session._controller.loaded.creatures) == set(before_catalog)
    assert "Orc" not in session._controller.loaded.creatures
    assert session._controller.loaded.creatures["Uruk"] is before_catalog["Uruk"]


def test_typing_and_paste_keep_editor_usable(
    editor: tuple[EditorWidget, Session], qapp
) -> None:
    """Escribir 200 caracteres y pegar texto deja el editor abierto y con foco."""
    widget, _ = editor
    current, completer = _current_with_completer(widget)
    widget.show()
    qapp.processEvents()
    current.setFocus()
    assert current.hasFocus()

    typed = "abcdefghij" * 20
    QTest.keyClicks(current, typed)
    pasted = "creature Lobo\nhealth 90\n" * 3
    cursor = current.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText(pasted)
    qapp.processEvents()

    assert current.isVisible()
    assert current.hasFocus()
    assert current in widget._editors
    assert widget._current_editor() is current
    assert typed in current.toPlainText()
    assert "creature Lobo" in current.toPlainText()
    assert completer.widget() is current


def test_save_after_tab_move_writes_visible_tab(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """Guardar tras mover pestañas escribe el archivo de la pestaña visible."""
    widget, _ = editor
    f1, f2 = _open_pair(widget, tmp_path)
    widget._tabs.tabBar().moveTab(1, 2)

    visible = widget._current_editor()
    assert visible is not None
    visible.setPlainText(SOURCE_SECOND_EDIT)
    widget._save_current()

    assert f1.read_text(encoding="utf-8") == SOURCE_FIRST
    assert f2.read_text(encoding="utf-8") == SOURCE_SECOND_EDIT


def test_save_after_moving_current_tab_writes_visible_tab(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """Guardar tras mover la pestaña actual escribe el archivo visible."""
    widget, _ = editor
    f1, f2 = _open_pair(widget, tmp_path)
    assert widget._tabs.currentIndex() == 2

    widget._tabs.tabBar().moveTab(2, 0)
    visible = widget._tabs.currentWidget()
    assert visible is not None

    visible.setPlainText(SOURCE_SECOND_EDIT)
    widget._save_current()

    assert f2.read_text(encoding="utf-8") == SOURCE_SECOND_EDIT
    assert f1.read_text(encoding="utf-8") == SOURCE_FIRST
    saved_tab = widget._tab_for(visible)
    assert saved_tab is not None
    assert saved_tab.path == f2
    assert widget._file_manager.current_tab is saved_tab
    assert widget._file_manager.current_index == widget._tabs.currentIndex()
    assert [tab.name for tab in widget._file_manager.tabs] == _visible_titles(widget)


def test_close_after_tab_move_closes_visible_tab(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """Cerrar tras mover pestañas elimina la pestaña visible y su modelo."""
    widget, _ = editor
    f1, _ = _open_pair(widget, tmp_path)
    widget._tabs.tabBar().moveTab(1, 2)

    widget._close_tab(widget._tabs.currentIndex())
    assert wait_until(lambda: widget._tabs.count() == 2)

    names = [tab.name for tab in widget._file_manager.tabs]
    assert names == _visible_titles(widget)
    assert names == ["untitled.ins", "f1.ins"]
    current = widget._current_editor()
    assert current is not None
    assert widget._tab_for(current).path == f1


def test_title_updates_on_moved_dirty_tab(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """El asterisco de cambios aparece en la pestaña visible tras mover."""
    widget, _ = editor
    _, f2 = _open_pair(widget, tmp_path)
    widget._tabs.tabBar().moveTab(1, 2)

    visible = widget._current_editor()
    assert visible is not None
    visible.setPlainText(SOURCE_SECOND_EDIT)

    current_index = widget._tabs.currentIndex()
    assert widget._tabs.tabText(current_index) == "f2.ins*"
    f1_tab = next(tab for tab in widget._file_manager.tabs if tab.name == "f1.ins")
    f1_editor = widget._editor_for(f1_tab)
    assert f1_editor is not None
    f1_index = widget._tabs.indexOf(f1_editor)
    assert widget._tabs.tabText(f1_index) == "f1.ins"
    moved_tab = widget._tab_for(visible)
    assert moved_tab is not None
    assert moved_tab.path == f2
    assert moved_tab.dirty is True


def test_model_order_follows_tab_move(
    editor: tuple[EditorWidget, Session], tmp_path: Path
) -> None:
    """El orden del FileManager se reordena junto con las pestañas visibles."""
    widget, _ = editor
    _open_pair(widget, tmp_path)
    before = list(widget._file_manager.tabs)

    widget._tabs.tabBar().moveTab(1, 2)
    after = widget._file_manager.tabs

    assert after[0] is before[0]
    assert after[1] is before[2]
    assert after[2] is before[1]
    assert [tab.name for tab in after] == _visible_titles(widget)
    assert widget._file_manager.current_index == widget._tabs.currentIndex()
    for index in range(widget._tabs.count()):
        editor_at_index = widget._tabs.widget(index)
        assert widget._tab_for(editor_at_index) is after[index]


def test_save_as_after_move_uses_visible_tab(
    editor: tuple[EditorWidget, Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardar como tras mover renombra la pestaña visible, no otra."""
    widget, _ = editor
    f1, f2 = _open_pair(widget, tmp_path)
    widget._tabs.tabBar().moveTab(1, 2)
    f1_tab = next(tab for tab in widget._file_manager.tabs if tab.name == "f1.ins")

    new_path = tmp_path / "guardado.ins"

    class _DialogStub:
        @staticmethod
        def getSaveFileName(*args, **kwargs):
            return str(new_path), "Instinct (*.ins)"

    monkeypatch.setattr(editor_widget_module, "QFileDialog", _DialogStub)

    visible = widget._current_editor()
    assert visible is not None
    visible.setPlainText(SOURCE_SECOND_EDIT)
    widget._save_as()

    assert f1_tab.path == f1
    assert f1.read_text(encoding="utf-8") == SOURCE_FIRST
    assert f2.read_text(encoding="utf-8") == SOURCE_SECOND
    assert new_path.read_text(encoding="utf-8") == SOURCE_SECOND_EDIT
    saved_tab = widget._tab_for(visible)
    assert saved_tab is not None
    assert saved_tab.path == new_path
    assert widget._file_manager.current_tab is saved_tab


def test_save_as_failure_keeps_path_unset_and_dirty(
    editor: tuple[EditorWidget, Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardar como fallido conserva la ruta vacía y el estado sucio."""
    widget, _ = editor
    current = widget._current_editor()
    assert current is not None
    current.setPlainText(SOURCE_FIRST)
    tab = widget._tab_for(current)
    assert tab is not None
    assert tab.path is None

    shown = _capture_critical(monkeypatch)
    _stub_save_dialog(monkeypatch, tmp_path / "nuevo.ins")
    monkeypatch.setattr(Path, "write_text", _fail_write)

    widget._save_as()

    assert tab.path is None
    assert tab.dirty is True
    assert widget._tabs.tabText(0) == "untitled.ins*"
    assert len(shown) == 1
    assert shown[0][2] == "No se pudo guardar el archivo:\ndisco de solo lectura"


def test_save_failure_keeps_dirty(
    editor: tuple[EditorWidget, Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardar fallido sobre una ruta existente conserva el estado sucio."""
    widget, _ = editor
    _, f2 = _open_pair(widget, tmp_path)
    current = widget._current_editor()
    assert current is not None
    current.setPlainText(SOURCE_SECOND_EDIT)
    tab = widget._tab_for(current)
    assert tab is not None
    assert tab.path == f2

    shown = _capture_critical(monkeypatch)
    monkeypatch.setattr(Path, "write_text", _fail_write)

    widget._save_current()

    assert tab.path == f2
    assert tab.dirty is True
    assert widget._tabs.tabText(widget._tabs.currentIndex()) == "f2.ins*"
    assert len(shown) == 1
    assert shown[0][2] == "No se pudo guardar el archivo:\ndisco de solo lectura"


def test_ask_close_policy_maps_buttons(
    editor: tuple[EditorWidget, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cada botón del diálogo se traduce a su política sin abrir un exec real."""
    widget, _ = editor
    labels = iter(["Guardar todo", "Descartar", "Cancelar"])
    seen: list[str] = []

    def _fake_exec(dialog) -> int:
        label = next(labels)
        seen.append(dialog.text())
        assert {button.text() for button in dialog.buttons()} == {
            "Guardar todo", "Descartar", "Cancelar"
        }
        assert dialog.escapeButton().text() == "Cancelar"
        for button in dialog.buttons():
            if button.text() == label:
                button.click()
                return 99
        raise AssertionError(label)

    monkeypatch.setattr(editor_widget_module.QMessageBox, "exec", _fake_exec)

    policies = [widget._ask_close_policy(["a.ins", "b.ins"]) for _ in range(3)]

    assert policies == ["save_all", "discard", "cancel"]
    assert seen == ["Hay 2 pestañas con cambios sin guardar."] * 3


def test_confirm_close_clean_returns_true_without_dialog(
    editor: tuple[EditorWidget, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sin pestañas sucias se acepta el cierre sin preguntar."""
    widget, _ = editor

    def _unexpected(*args, **kwargs):
        raise AssertionError("no se debe preguntar si no hay cambios")

    monkeypatch.setattr(widget, "_ask_close_policy", _unexpected, raising=False)

    assert widget.confirm_close() is True


def test_confirm_close_cancel_returns_false(
    editor: tuple[EditorWidget, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelar el diálogo conserva las pestañas y rechaza el cierre."""
    widget, _ = editor
    current = widget._current_editor()
    assert current is not None
    current.setPlainText("cambios sin guardar\n")
    tab = widget._tab_for(current)
    assert tab is not None
    monkeypatch.setattr(widget, "_ask_close_policy", lambda names: "cancel", raising=False)

    assert widget.confirm_close() is False
    assert tab.dirty is True
    assert tab.content == "cambios sin guardar\n"
    assert widget._tabs.count() == 1


def test_confirm_close_discard_returns_true(
    editor: tuple[EditorWidget, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Descartar los cambios acepta el cierre sin escribir nada."""
    widget, _ = editor
    current = widget._current_editor()
    assert current is not None
    current.setPlainText("cambios que se descartan\n")
    tab = widget._tab_for(current)
    assert tab is not None
    monkeypatch.setattr(widget, "_ask_close_policy", lambda names: "discard", raising=False)

    assert widget.confirm_close() is True
    assert tab.dirty is True
    assert widget._tabs.count() == 1


def test_confirm_close_save_all_writes_all(
    editor: tuple[EditorWidget, Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardar todo escribe las pestañas sucias en orden visual."""
    widget, _ = editor
    f1, f2 = _open_pair(widget, tmp_path)
    first_tab = widget._file_manager.tabs[1]
    second_tab = widget._file_manager.tabs[2]
    first_editor = widget._editor_for(first_tab)
    second_editor = widget._editor_for(second_tab)
    assert first_editor is not None and second_editor is not None
    first_editor.setPlainText("creature First\ncambios\n")
    second_editor.setPlainText("creature Second\ncambios\n")

    asked: list[list[str]] = []

    def _policy(names: list[str]) -> str:
        asked.append(names)
        return "save_all"

    monkeypatch.setattr(widget, "_ask_close_policy", _policy, raising=False)

    assert widget.confirm_close() is True
    assert asked == [["f1.ins", "f2.ins"]]
    assert f1.read_text(encoding="utf-8") == "creature First\ncambios\n"
    assert f2.read_text(encoding="utf-8") == "creature Second\ncambios\n"
    assert first_tab.dirty is False and second_tab.dirty is False


def test_confirm_close_save_all_untitled_cancelled(
    editor: tuple[EditorWidget, Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelar la ruta de una pestaña sin nombre aborta el cierre."""
    widget, _ = editor
    untitled_editor = widget._current_editor()
    assert untitled_editor is not None
    untitled_editor.setPlainText("sin ruta\n")
    untitled_tab = widget._tab_for(untitled_editor)
    assert untitled_tab is not None

    f1, _ = _open_pair(widget, tmp_path)
    named_tab = widget._file_manager.tabs[1]
    named_editor = widget._editor_for(named_tab)
    assert named_editor is not None
    named_editor.setPlainText("creature First\ncambios\n")
    original = f1.read_text(encoding="utf-8")

    monkeypatch.setattr(widget, "_ask_close_policy", lambda names: "save_all", raising=False)

    class _CancelledDialog:
        @staticmethod
        def getSaveFileName(*args, **kwargs):
            return "", ""

    monkeypatch.setattr(editor_widget_module, "QFileDialog", _CancelledDialog)

    assert widget.confirm_close() is False
    assert untitled_tab.dirty is True
    assert untitled_tab.path is None
    assert named_tab.dirty is True
    assert f1.read_text(encoding="utf-8") == original
