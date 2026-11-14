"""Pruebas del autocompletado del editor Instinct."""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import Qt

from instinct.ui.editor.completer import InstinctCompleter
from instinct.ui.editor.compiler_bridge import get_catalogs


@pytest.fixture
def completer() -> InstinctCompleter:
    return InstinctCompleter()


def test_completer_initializes(completer: InstinctCompleter) -> None:
    """El completer se construye con catálogos cargados."""
    assert completer._catalogs is not None
    assert completer._model is not None
    assert completer.filterMode() == Qt.MatchFlag.MatchContains
    assert completer.caseSensitivity() == Qt.CaseSensitivity.CaseInsensitive


def test_completer_has_catalog_items(completer: InstinctCompleter) -> None:
    """El modelo contiene todos los elementos de los catálogos."""
    cats = get_catalogs()
    model_items = set(completer._model.stringList())

    # Todas las keywords deben estar
    for kw in cats["keywords"]:
        assert kw in model_items, f"Keyword '{kw}' no está en el completer"

    # Todas las acciones deben estar
    for action in cats["actions"]:
        assert action in model_items, f"Acción '{action}' no está en el completer"

    # Todas las funciones deben estar
    for fn in cats["functions"]:
        assert fn in model_items, f"Función '{fn}' no está en el completer"

    # Todas las percepciones deben estar
    for perc in cats["perceptions"]:
        assert perc in model_items, f"Percepción '{perc}' no está en el completer"

    # Todas las constantes deben estar
    for const in cats["constants"]:
        assert const in model_items, f"Constante '{const}' no está en el completer"


def test_completer_detects_local_variables(completer: InstinctCompleter) -> None:
    """El completer detecta variables asignadas con 'x = ...'."""
    source = """
creature Test
faction test
health 50
vision 5
lifespan 100

start:
    my_var = 10
    another_var = health + 5
    wait(my_var)
    goto start
"""
    completer.update_context(source)

    assert "my_var" in completer._local_vars
    assert "another_var" in completer._local_vars
    assert "my_var" in set(completer._model.stringList())
    assert "another_var" in set(completer._model.stringList())


def test_completer_detects_labels(completer: InstinctCompleter) -> None:
    """El completer detecta etiquetas 'label:'."""
    source = """
start:
    if health < 20 goto flee
    wait(1)
    goto start

flee:
    wait(5)
    goto start
"""
    completer.update_context(source)

    assert "start" in completer._labels
    assert "flee" in completer._labels
    assert "start" in set(completer._model.stringList())
    assert "flee" in set(completer._model.stringList())


def test_completer_updates_dynamically(completer: InstinctCompleter) -> None:
    """El completer se actualiza cuando cambia el source."""
    # Estado inicial
    completer.update_context("start:\n    wait(1)\n")
    assert "start" in completer._labels

    # Cambiar a otro source
    completer.update_context("loop:\n    wait(2)\n    goto loop\n")
    assert "loop" in completer._labels
    assert "start" not in completer._labels  # El label anterior ya no está

    model_items = set(completer._model.stringList())
    assert "loop" in model_items
    assert "start" not in model_items
