"""Pruebas del creature_loader: compilación de .ins y escaneo de carpeta."""
from __future__ import annotations

from instinct.compiler.semantic import ResolvedProgram
from instinct.loaders.creature_loader import load_creature, load_creatures
from instinct.loaders.errors import LoadError

URUK = """\
creature Uruk
faction isengard
health 80
vision 6
lifespan 400

start:
    if health < 20 goto flee
    if enemy_dist == 1 goto bite
    if enemy_dist > 0 goto hunt
    wait(1)
    goto start
flee:
    move(-enemy_dx, -enemy_dy, 3)
    goto start
bite:
    consume(enemy_dx, enemy_dy, 15, 15)
    goto start
hunt:
    move(enemy_dx, enemy_dy, 2)
    goto start
"""

HOBBIT = """\
creature Hobbit
faction shire
health 60
vision 5
lifespan 300

start:
    if enemy_dist >= 0 goto flee
    wait(1)
    goto start
flee:
    move(-enemy_dx, -enemy_dy, 2)
    goto start
"""


def load_errors(source: str) -> list[tuple[int, str]]:
    result = load_creature(source)
    assert result.creature is None
    return [(e.line, e.message) for e in result.errors]


def test_valid_creature_loads() -> None:
    result = load_creature(URUK)
    assert result.errors == []
    assert result.creature is not None
    assert result.creature.name == "Uruk"
    assert result.creature.faction == "isengard"
    assert result.creature.health == 80
    assert result.creature.vision == 6
    assert result.creature.lifespan == 400


def test_valid_creature_has_start_label() -> None:
    result = load_creature(URUK)
    assert result.creature is not None
    assert "start" in result.creature.labels


def test_lexical_error_becomes_load_error() -> None:
    source = URUK.replace("wait(1)", "wait(1) !")
    assert load_errors(source) == [(11, "carácter inesperado '!'")]


def test_parse_error_becomes_load_error() -> None:
    source = URUK.replace("if health < 20 goto flee", "if health < goto flee")
    assert load_errors(source) == [(8, "se esperaba una expresión")]


def test_semantic_error_becomes_load_error() -> None:
    source = URUK.replace("faction isengard", "faction isengard\nhealth 80")
    assert load_errors(source) == [(4, "clave de cabecera duplicada 'health'")]


def test_missing_start_becomes_load_error() -> None:
    source = URUK.replace("start:", "wander:")
    assert "falta la etiqueta 'start:'" in [e[1] for e in load_errors(source)]


def test_empty_source_reports_errors() -> None:
    result = load_creature("")
    assert result.creature is None
    assert len(result.errors) > 0
    assert any("falta la clave" in e.message for e in result.errors)


def test_load_creatures_from_directory(tmp_path) -> None:
    (tmp_path / "a_uruk.ins").write_text(URUK, encoding="utf-8")
    (tmp_path / "b_hobbit.ins").write_text(HOBBIT, encoding="utf-8")
    creatures, errors = load_creatures(tmp_path)
    assert errors == []
    assert sorted(creatures.keys()) == ["Hobbit", "Uruk"]
    assert isinstance(creatures["Uruk"], ResolvedProgram)
    assert creatures["Uruk"].name == "Uruk"


def test_load_creatures_skips_broken_file(tmp_path) -> None:
    (tmp_path / "a_uruk.ins").write_text(URUK, encoding="utf-8")
    (tmp_path / "z_broken.ins").write_text("this is not valid", encoding="utf-8")
    creatures, errors = load_creatures(tmp_path)
    assert "Uruk" in creatures
    assert "this" not in creatures
    assert len(errors) > 0
    assert all(e.path for e in errors)


def test_load_creatures_rejects_duplicate_name(tmp_path) -> None:
    (tmp_path / "a_first.ins").write_text(URUK, encoding="utf-8")
    (tmp_path / "b_second.ins").write_text(URUK, encoding="utf-8")
    creatures, errors = load_creatures(tmp_path)
    assert list(creatures.keys()) == ["Uruk"]
    assert len(errors) == 1
    assert "ya está declarada" in errors[0].message
    assert errors[0].path.endswith("b_second.ins")


def test_load_creatures_empty_directory(tmp_path) -> None:
    creatures, errors = load_creatures(tmp_path)
    assert creatures == {}
    assert errors == []
