"""Pruebas del hot-reload de criaturas en la sesión."""
from __future__ import annotations

from pathlib import Path

from instinct.ui.session import ReloadResult, Session


GRASS = "terrain Grass\nchar .\nresource_max 100\nregen 2\n"
ROCK = "object Rock\nchar #\nresource_max 100\n"
MAP = "Prueba\n....\n.##.\n....\n"
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
URUK_V2 = """\
creature Uruk
faction mordor
health 80
vision 9
lifespan 500

start:
    wait(2)
    goto start
"""
HUNTER = """\
creature Hunter
faction mordor
health 50
vision 3
lifespan 200

start:
    wait(1)
    goto start
"""


def build_content(tmp_path: Path) -> Path:
    for name, source in (
        ("terrains/grass.te", GRASS),
        ("objects/rock.ob", ROCK),
        ("maps/prueba.map", MAP),
        ("creatures/uruk.ins", URUK),
        ("creatures/hunter.ins", HUNTER),
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return tmp_path


def build_session(tmp_path: Path) -> Session:
    session = Session(build_content(tmp_path), seed=42)
    assert session.load() is True
    session.select_map("Prueba")
    return session


def test_reload_from_source_updates_placed_creatures(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.cell(3, 0)
    session.start()

    world = session.state.world
    assert world is not None
    first = world.creature_at(0, 0)
    second = world.creature_at(3, 0)
    assert first is not None and second is not None

    first.health = 33
    first.age = 7
    first.variables["x"] = 9
    first.wait_remaining = 2
    second.health = 44
    second.age = 8
    second.variables["y"] = 5
    second.wait_remaining = 3

    result = session.reload_from_source(URUK_V2)
    assert result == ReloadResult(True, "Uruk", [])
    assert session._cli.loaded is not None
    assert session._cli.loaded.creatures["Uruk"].faction == "mordor"

    for creature, health, age, var_key, var_val, wait in (
        (world.creature_at(0, 0), 33, 7, "x", 9, 2),
        (world.creature_at(3, 0), 44, 8, "y", 5, 3),
    ):
        assert creature is not None
        assert creature.health == health
        assert creature.age == age
        assert creature.variables[var_key] == var_val
        assert creature.wait_remaining == wait
        assert creature.faction == "mordor"
        assert creature.vision == 9
        assert creature.lifespan == 500
        assert creature.pc == creature.program.labels["start"]


def test_reload_from_source_invalid_does_not_mutate(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()

    world = session.state.world
    assert world is not None
    before = world.creature_at(0, 0)
    assert before is not None
    before_health = before.health
    before_program = before.program
    assert session._cli.loaded is not None
    before_catalog = session._cli.loaded.creatures["Uruk"]

    result = session.reload_from_source("start:\n    wait(1)\n")
    assert result.ok is False
    assert result.name is None
    assert result.errors
    assert "línea" in result.errors[0]

    after = world.creature_at(0, 0)
    assert after is not None
    assert after.health == before_health
    assert after.program is before_program
    assert session._cli.loaded.creatures["Uruk"] is before_catalog


def test_reload_from_source_without_loaded_content(tmp_path: Path) -> None:
    session = Session(tmp_path, seed=42)
    result = session.reload_from_source(URUK)
    assert result.ok is False
    assert result.name is None
    assert result.errors == ["no hay contenido cargado"]


def test_reload_creature_legacy_wrapper(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    ok, errors = session.reload_creature("Uruk", URUK_V2)
    assert ok is True
    assert errors == []
    assert session._cli.loaded is not None
    assert session._cli.loaded.creatures["Uruk"].vision == 9


def test_reload_from_source_compiles_once(tmp_path: Path, monkeypatch) -> None:
    import instinct.ui.session as session_mod

    session = build_session(tmp_path)
    calls: list[str] = []
    real_load = session_mod.load_creature

    def counting(source: str):
        calls.append(source)
        return real_load(source)

    monkeypatch.setattr(session_mod, "load_creature", counting)
    result = session.reload_from_source(URUK_V2)
    assert result.ok is True
    assert len(calls) == 1
