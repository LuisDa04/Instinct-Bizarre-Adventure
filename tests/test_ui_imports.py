"""Pruebas de regresión: los módulos de UI deben importarse sin errores."""
from __future__ import annotations

import importlib

import pytest


MODULES = [
    "instinct.ui.state",
    "instinct.ui.session",
    "instinct.ui.controls",
    "instinct.ui.app",
    "instinct.ui.editor.compiler_bridge",
]

OPTIONAL_QT_MODULES = [
    "instinct.ui.editor.hot_reload",
    "instinct.ui.editor.editor_widget",
    "instinct.ui.editor.linter",
]


def test_ui_modules_import() -> None:
    for module in MODULES:
        importlib.import_module(module)


def test_ui_editor_modules_import_when_qt_available() -> None:
    pytest.importorskip("PyQt6")
    for module in OPTIONAL_QT_MODULES:
        importlib.import_module(module)
