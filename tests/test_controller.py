"""Pruebas de la fachada SimulationController: carga, selección de mapa y colocación."""
from __future__ import annotations

from pathlib import Path

from instinct.sim.controller import SimulationController

# Retiradas junto al bucle interactivo de terminal (IDs del inventario T0):
# - test_step_runs_one_tick: `step()` solo servía al bucle de terminal.
# - test_step_logs_ictus: ídem; el tick se prueba en test_engine/test_acceptance.
# - test_set_speed: `set_speed()` era interactivo; la velocidad vive en ui/state.py.
# - test_render_grid_shows_chars: `render_grid()` solo servía al bucle.
# - test_recent_logs: `recent_logs()` solo servía al bucle.

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


def make_controller(tmp_path: Path, seed: int = 42) -> SimulationController:
    controller = SimulationController(build_content(tmp_path), seed=seed)
    controller.load_content()
    controller.select_map("Prueba")
    return controller


def test_load_content_reports_counts(tmp_path) -> None:
    controller = SimulationController(build_content(tmp_path), seed=42)
    report = controller.load_content()
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
    controller = SimulationController(base, seed=42)
    report = controller.load_content()
    assert "Errores de carga:" in report
    assert "broken.ins" in report


def test_select_map_builds_world(tmp_path) -> None:
    controller = make_controller(tmp_path)
    assert controller.world is not None
    assert controller.world.width == 4
    assert controller.world.height == 3


def test_select_map_unknown(tmp_path) -> None:
    controller = SimulationController(build_content(tmp_path), seed=42)
    controller.load_content()
    assert "no existe" in controller.select_map("NoExiste")


def test_place_creature_success(tmp_path) -> None:
    controller = make_controller(tmp_path)
    result = controller.place_creature("Uruk", 0, 0)
    assert "colocada" in result
    assert controller.world.creature_at(0, 0) is not None


def test_place_creature_rejects_occupied(tmp_path) -> None:
    controller = make_controller(tmp_path)
    controller.place_creature("Uruk", 0, 0)
    result = controller.place_creature("Hunter", 0, 0)
    assert "ocupada" in result


def test_place_creature_rejects_object(tmp_path) -> None:
    controller = make_controller(tmp_path)
    result = controller.place_creature("Uruk", 1, 1)
    assert "ocupada" in result


def test_place_creature_rejects_outside(tmp_path) -> None:
    controller = make_controller(tmp_path)
    result = controller.place_creature("Uruk", 99, 99)
    assert "fuera" in result


def test_place_creature_rejects_unknown_species(tmp_path) -> None:
    controller = make_controller(tmp_path)
    result = controller.place_creature("Zombie", 0, 0)
    assert "no existe" in result


def test_remove_creature(tmp_path) -> None:
    controller = make_controller(tmp_path)
    controller.place_creature("Uruk", 0, 0)
    result = controller.remove_creature(0, 0)
    assert "retirada" in result
    assert controller.world.creature_at(0, 0) is None
    result = controller.remove_creature(0, 0)
    assert "no hay" in result


def test_reset_clears_creatures(tmp_path) -> None:
    controller = make_controller(tmp_path)
    controller.place_creature("Uruk", 0, 0)
    controller.engine.step()
    result = controller.reset()
    assert "reiniciado" in result
    assert list(controller.world.creatures()) == []


def test_speeds_constant() -> None:
    assert SimulationController.SPEEDS == (0.5, 1, 5, 10, 30)
    assert len(SimulationController.SPEEDS) >= 3
