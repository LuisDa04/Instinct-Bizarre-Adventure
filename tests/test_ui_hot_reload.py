"""Pruebas del hot-reload de criaturas en el editor."""
from __future__ import annotations

from pathlib import Path

from instinct.ui.editor.hot_reload import HotReloadManager
from instinct.ui.session import Session


def test_hot_reload_initializes(tmp_path) -> None:
    """El HotReloadManager se construye sobre una sesión."""
    session = Session(tmp_path, seed=42)
    mgr = HotReloadManager(session)
    assert mgr._session is session


def test_hot_reload_valid_creature(tmp_path) -> None:
    """Se puede recargar una criatura válida sin errores."""
    session = Session(tmp_path, seed=42)
    session.load()
    session.select_map("Morioh Town")

    mgr = HotReloadManager(session)

    # Código válido de criatura
    source = """creature TestReload
faction test
health 50
vision 5
lifespan 100

start:
    wait(1)
    goto start
"""
    ok, errors = mgr.reload_creature("TestReload", source)
    assert ok is True
    assert errors == []
    # La criatura debe estar en el registro
    assert "TestReload" in session._cli.loaded.creatures


def test_hot_reload_invalid_creature(tmp_path) -> None:
    """Un .ins inválido devuelve errores y no recarga."""
    session = Session(tmp_path, seed=42)
    session.load()
    session.select_map("Morioh Town")

    mgr = HotReloadManager(session)

    # Código inválido (falta cabecera)
    source_invalido = "start:\n    wait(1)\n"
    ok, errors = mgr.reload_creature("BadCreature", source_invalido)
    assert ok is False
    assert len(errors) > 0
    assert "línea" in errors[0]
    # La criatura no debe estar registrada
    assert "BadCreature" not in session._cli.loaded.creatures
