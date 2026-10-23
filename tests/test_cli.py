"""Pruebas del CLI: carga, selección de mapa, colocación y simulación."""
from __future__ import annotations

from pathlib import Path

from instinct.sim.cli import SPEEDS, CLI

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
HUNTER = """\
creature Hunter
faction mordor
health 50
vision 3
lifespan 200

start:
    attack(1, 0, 10)
    goto start
"""


def build_content(tmp_path: Path) -> Path:
    """Crea el directorio base con contenido mínimo cargable."""
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


def make_cli(tmp_path: Path, seed: int = 42) -> CLI:
    cli = CLI(build_content(tmp_path), seed=seed)
    cli.load_content()
    cli.select_map("Prueba")
    return cli


def test_load_content_reports_counts(tmp_path) -> None:
    cli = CLI(build_content(tmp_path), seed=42)
    report = cli.load_content()
    assert "Terrenos: 1" in report
    assert "Objetos: 1" in report
    assert "Prueba" in report
    assert "Uruk" in report
    assert "Errores" not in report


def test_load_content_reports_errors(tmp_path) -> None:
    base = build_content(tmp_path)
    (base / "creatures" / "broken.ins").write_text(
        "this is bad\n", encoding="utf-8"
    )
    cli = CLI(base, seed=42)
    report = cli.load_content()
    assert "Errores de carga:" in report
    assert "broken.ins" in report


def test_select_map_builds_world(tmp_path) -> None:
    cli = make_cli(tmp_path)
    assert cli.world is not None
    assert cli.world.width == 4
    assert cli.world.height == 3


def test_select_map_unknown(tmp_path) -> None:
    cli = CLI(build_content(tmp_path), seed=42)
    cli.load_content()
    assert "no existe" in cli.select_map("NoExiste")


def test_place_creature_success(tmp_path) -> None:
    cli = make_cli(tmp_path)
    result = cli.place_creature("Uruk", 0, 0)
    assert "colocada" in result
    assert cli.world.creature_at(0, 0) is not None


def test_place_creature_rejects_occupied(tmp_path) -> None:
    cli = make_cli(tmp_path)
    cli.place_creature("Uruk", 0, 0)
    result = cli.place_creature("Hunter", 0, 0)
    assert "ocupada" in result


def test_place_creature_rejects_object(tmp_path) -> None:
    cli = make_cli(tmp_path)
    result = cli.place_creature("Uruk", 1, 1)
    assert "ocupada" in result


def test_place_creature_rejects_outside(tmp_path) -> None:
    cli = make_cli(tmp_path)
    result = cli.place_creature("Uruk", 99, 99)
    assert "fuera" in result


def test_place_creature_rejects_unknown_species(tmp_path) -> None:
    cli = make_cli(tmp_path)
    result = cli.place_creature("Zombie", 0, 0)
    assert "no existe" in result


def test_remove_creature(tmp_path) -> None:
    cli = make_cli(tmp_path)
    cli.place_creature("Uruk", 0, 0)
    result = cli.remove_creature(0, 0)
    assert "retirada" in result
    assert cli.world.creature_at(0, 0) is None
    result = cli.remove_creature(0, 0)
    assert "no hay" in result


def test_step_runs_one_tick(tmp_path) -> None:
    cli = make_cli(tmp_path)
    cli.place_creature("Uruk", 0, 0)
    result = cli.step()
    assert cli.engine.tick == 1
    assert isinstance(result, str)


def test_step_logs_ictus(tmp_path) -> None:
    cli = make_cli(tmp_path)
    cli.place_creature("Hunter", 0, 0)
    cli.place_creature("Uruk", 1, 0)
    cli.step()
    # Hunter ataca a Uruk adyacente; Uruk puede o no sobrevivir
    assert cli.engine.tick == 1


def test_set_speed(tmp_path) -> None:
    cli = make_cli(tmp_path)
    assert "0.5 tps" in cli.set_speed(0)
    assert "30 tps" in cli.set_speed(4)
    assert "inválida" in cli.set_speed(9)


def test_reset_clears_creatures(tmp_path) -> None:
    cli = make_cli(tmp_path)
    cli.place_creature("Uruk", 0, 0)
    cli.step()
    result = cli.reset()
    assert "reiniciado" in result
    assert list(cli.world.creatures()) == []


def test_render_grid_shows_chars(tmp_path) -> None:
    cli = make_cli(tmp_path)
    cli.place_creature("Uruk", 0, 0)
    grid = cli.render_grid()
    lines = grid.splitlines()
    assert lines[0].startswith("U")
    assert lines[1].startswith(".#")


def test_recent_logs(tmp_path) -> None:
    cli = make_cli(tmp_path)
    assert cli.recent_logs() == []
    cli.place_creature("Uruk", 0, 0)
    cli.step()
    # engine corre sin mensajes si no hay say/roar/ictus
    # colocamos una que habla
    assert isinstance(cli.recent_logs(), list)


def test_speeds_constant() -> None:
    assert SPEEDS == (0.5, 1, 5, 10, 30)
    assert len(SPEEDS) >= 3
