"""Pruebas del gestor de pestañas y archivos del editor."""
from __future__ import annotations

from pathlib import Path

from instinct.ui.editor.file_manager import FileManager, EditorTab


def test_file_manager_starts_empty() -> None:
    """El FileManager comienza sin pestañas."""
    fm = FileManager()
    assert fm.tabs == []
    assert fm.current_tab is None
    assert fm.current_index == -1


def test_file_manager_new_tab() -> None:
    """Se puede crear una pestaña nueva y se marca como actual."""
    fm = FileManager()
    idx = fm.new_tab()
    assert idx == 0
    tab = fm.current_tab
    assert tab is not None
    assert tab.path is None
    assert tab.content == ""
    assert tab.dirty is False
    assert tab.name == "untitled.ins"


def test_file_manager_open_file(tmp_path) -> None:
    """Se puede abrir un archivo .ins existente."""
    fm = FileManager()
    file_path = tmp_path / "test.ins"
    file_path.write_text("creature X\nfaction f\nhealth 50\nvision 1\nlifespan 100\n\nstart:\n    wait(1)\n", encoding="utf-8")
    idx = fm.open_file(file_path)
    assert idx == 0
    tab = fm.current_tab
    assert tab is not None
    assert tab.path == file_path
    assert "creature X" in tab.content
    assert tab.dirty is False
    assert tab.name == "test.ins"


def test_file_manager_save_current(tmp_path) -> None:
    """Se puede guardar la pestaña actual en su ruta existente."""
    fm = FileManager()
    file_path = tmp_path / "test.ins"
    file_path.write_text("contenido original\n", encoding="utf-8")
    fm.open_file(file_path)
    tab = fm.current_tab
    assert tab is not None
    tab.content = "contenido modificado\n"
    tab.dirty = True
    saved = fm.save_current()
    assert saved == file_path
    assert tab.dirty is False
    assert file_path.read_text(encoding="utf-8") == "contenido modificado\n"


def test_file_manager_save_as(tmp_path) -> None:
    """Se puede guardar la pestaña actual en una nueva ruta."""
    fm = FileManager()
    fm.new_tab()
    tab = fm.current_tab
    assert tab is not None
    tab.content = "nuevo contenido\n"
    tab.dirty = True
    new_path = tmp_path / "nuevo.ins"
    fm.save_as(new_path)
    assert new_path.read_text(encoding="utf-8") == "nuevo contenido\n"
    assert tab.path == new_path
    assert tab.dirty is False


def test_file_manager_close_tab() -> None:
    """Se pueden cerrar pestañas limpias."""
    fm = FileManager()
    fm.new_tab()
    fm.new_tab()
    assert len(fm.tabs) == 2
    assert fm.close_tab(0) is True
    assert len(fm.tabs) == 1


def test_file_manager_close_dirty_tab_refused() -> None:
    """No se puede cerrar una pestaña sucia sin guardar primero."""
    fm = FileManager()
    fm.new_tab()
    tab = fm.current_tab
    assert tab is not None
    tab.content = "cambios sin guardar\n"
    tab.dirty = True
    assert fm.close_tab(0) is False
    assert len(fm.tabs) == 1
