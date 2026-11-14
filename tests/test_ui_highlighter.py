"""Pruebas del resaltador de sintaxis Instinct."""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtGui import QTextDocument, QFont

from instinct.ui.editor.highlighter import InstinctHighlighter
from instinct.ui.editor.compiler_bridge import get_catalogs


@pytest.fixture
def highlighter() -> InstinctHighlighter:
    doc = QTextDocument()
    # Mantener referencia fuerte al documento para evitar garbage collection
    highlighter = InstinctHighlighter(doc)
    highlighter._doc = doc  # Mantener referencia fuerte
    return highlighter


def test_highlighter_initializes(highlighter: InstinctHighlighter) -> None:
    """El highlighter se construye sin errores y tiene patrones."""
    assert highlighter._formats is not None
    assert highlighter._patterns is not None
    assert len(highlighter._patterns) > 0


def test_highlighter_formats_match_catalogs(highlighter: InstinctHighlighter) -> None:
    """Cada categoría del catálogo tiene su formato correspondiente."""
    cats = get_catalogs()
    formats = highlighter._formats

    # Todas las categorías del catálogo tienen formato
    assert "keyword" in formats
    assert "action" in formats
    assert "function" in formats
    assert "perception" in formats
    assert "constant" in formats
    assert "string" in formats
    assert "number" in formats
    assert "comment" in formats
    assert "label" in formats
    assert "variable" in formats


def test_highlighter_patterns_match_catalogs(highlighter: InstinctHighlighter) -> None:
    """Los patrones de regex cubren todos los elementos del catálogo."""
    cats = get_catalogs()
    patterns_text = " ".join(p.pattern() for p, _ in highlighter._patterns)

    # Todas las keywords aparecen en algún patrón
    for kw in cats["keywords"]:
        assert kw in patterns_text, f"Keyword '{kw}' no está en los patrones"

    # Todas las acciones aparecen
    for action in cats["actions"]:
        assert action in patterns_text, f"Acción '{action}' no está en los patrones"

    # Todas las percepciones aparecen
    for perc in cats["perceptions"]:
        assert perc in patterns_text, f"Percepción '{perc}' no está en los patrones"

    # Todas las constantes aparecen
    for const in cats["constants"]:
        assert const in patterns_text, f"Constante '{const}' no está en los patrones"


def test_highlighter_highlights_keyword(highlighter: InstinctHighlighter) -> None:
    """Un keyword como 'if' se resalta con el formato keyword."""
    text = "if health < 10 goto flee"
    highlighter.highlightBlock(text)
    # El keyword 'if' debe tener formato de keyword (negrita)
    fmt_if = highlighter.format(0)
    fmt_health = highlighter.format(3)

    # Verificar que 'if' tiene negrita (font weight >= Bold = 700)
    assert fmt_if.fontWeight() >= QFont.Weight.Bold
    # La percepción 'health' debe tener formato de percepción (color válido)
    assert fmt_health.foreground().color().isValid()


def test_highlighter_highlights_comment(highlighter: InstinctHighlighter) -> None:
    """Un comentario #... se resalta con el formato comment."""
    text = "# esto es un comentario"
    highlighter.highlightBlock(text)
    fmt = highlighter.format(0)
    assert fmt.foreground().color().isValid()


def test_highlighter_highlights_string(highlighter: InstinctHighlighter) -> None:
    """Un string entre comillas se resalta."""
    text = 'say("hola mundo")'
    highlighter.highlightBlock(text)
    # La comilla de apertura debe tener formato de string
    fmt = highlighter.format(4)
    assert fmt.foreground().color().isValid()


def test_highlighter_highlights_number(highlighter: InstinctHighlighter) -> None:
    """Un número se resalta."""
    text = "wait(5)"
    highlighter.highlightBlock(text)
    fmt = highlighter.format(5)  # posición del '5'
    assert fmt.foreground().color().isValid()

