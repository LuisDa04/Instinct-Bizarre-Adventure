"""Pruebas del puente compilador-UI sin depender de PyQt6."""
from __future__ import annotations

from instinct.ui.editor.compiler_bridge import compile_source


def test_compile_source_valid() -> None:
    source = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    wait(1)\n    goto start\n"
    )
    program, diagnostics = compile_source(source)
    assert program is not None
    assert diagnostics == []


def test_compile_source_lexical_code() -> None:
    source = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    wait(1) !\n    goto start\n"
    )
    program, diagnostics = compile_source(source)
    assert program is None
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "LEXICAL"
    assert diagnostics[0].severity == "error"
    assert diagnostics[0].line > 0


def test_compile_source_syntax_code() -> None:
    source = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    if health < goto flee\n    goto start\nflee:\n    goto start\n"
    )
    program, diagnostics = compile_source(source)
    assert program is None
    assert len(diagnostics) > 0
    assert diagnostics[0].code == "SYNTAX"
    assert diagnostics[0].severity == "error"


def test_compile_source_semantic_code() -> None:
    source = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    unknown_action(1)\n    goto start\n"
    )
    program, diagnostics = compile_source(source)
    assert program is None
    assert len(diagnostics) > 0
    assert diagnostics[0].code == "SEMANTIC"
    assert any("acción desconocida" in d.message for d in diagnostics)


def test_compile_source_preserves_line() -> None:
    source = (
        "creature Test\nfaction test\nhealth 50\nvision 5\nlifespan 100\n\n"
        "start:\n    unknown_action(1)\n    goto start\n"
    )
    _, diagnostics = compile_source(source)
    assert diagnostics[0].line == 8
