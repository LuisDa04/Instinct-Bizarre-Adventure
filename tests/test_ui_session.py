"""Pruebas de la sesión de la interfaz: carga, colocación, simulación y repetición."""
from __future__ import annotations

from pathlib import Path

from instinct.ui.session import Session

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


def make_session(tmp_path: Path, seed: int = 42) -> Session:
    session = Session(build_content(tmp_path), seed=seed)
    session.load()
    session.select_map("Prueba")
    return session


def test_load_with_maps_enters_selection(tmp_path) -> None:
    session = Session(build_content(tmp_path), seed=42)
    assert session.load() is True
    assert session.state.phase == "map_select"
    assert session.state.map_names == ["Prueba"]


def test_load_without_maps_stays_stuck(tmp_path) -> None:
    base = build_content(tmp_path)
    (base / "maps" / "prueba.map").unlink()
    session = Session(base, seed=42)
    assert session.load() is False
    assert session.state.phase == "no_maps"


def test_select_map_enters_placement(tmp_path) -> None:
    session = make_session(tmp_path)
    assert session.state.phase == "placement"
    assert session.state.world is not None
    assert session.state.engine is not None


def test_select_map_unknown_keeps_phase(tmp_path) -> None:
    session = Session(build_content(tmp_path), seed=42)
    session.load()
    session.select_map("Prueba")
    message = session.select_map("NoExiste")
    assert "no existe" in message
    assert session.state.phase == "placement"
    assert session.state.map_name == "Prueba"


def test_pick_species_toggles(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    assert session.state.placement_species == "Uruk"
    session.pick_species("Uruk")
    assert session.state.placement_species is None


def test_cell_places_then_removes(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    assert session.state.world.creature_at(0, 0) is not None
    session.pick_species("Uruk")
    session.cell(0, 0)
    assert session.state.world.creature_at(0, 0) is None
    assert any("retirada" in m for m in session.state.messages)


def test_cell_over_object_reports_occupied(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(1, 1)
    assert session.state.world.creature_at(1, 1) is None
    assert any("ocupada" in m for m in session.state.messages)


def test_cell_without_species_does_nothing(tmp_path) -> None:
    session = make_session(tmp_path)
    session.cell(0, 0)
    assert session.state.messages == []
    assert session.state.world.creature_at(0, 0) is None


def test_start_requires_creatures(tmp_path) -> None:
    session = make_session(tmp_path)
    assert session.start() is False
    assert session.state.phase == "placement"
    assert "coloca al menos una criatura" in session.state.messages[-1]


def test_start_runs_simulation(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    assert session.start() is True
    assert session.state.phase == "simulation"
    assert session.state.paused is False


def test_step_once_advances_tick(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()
    session.step_once()
    assert session.state.tick == 1


def test_toggle_pause_flips(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()
    session.toggle_pause()
    assert session.state.paused is True
    session.toggle_pause()
    assert session.state.paused is False


def test_set_speed_ignores_out_of_range(tmp_path) -> None:
    session = make_session(tmp_path)
    session.set_speed(3)
    assert session.state.speed_tps == 10
    session.set_speed(4)
    assert session.state.speed_tps == 30
    session.set_speed(9)
    assert session.state.speed_tps == 30


def test_select_cell_marks_without_editing(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()
    session.select_cell(2, 2)
    assert session.state.selected_cell == (2, 2)
    assert session.state.world.creature_at(2, 2) is None


def test_reset_returns_to_placement(tmp_path) -> None:
    session = make_session(tmp_path)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()
    session.step_once()
    session.reset()
    assert session.state.phase == "placement"
    assert list(session.state.world.creatures()) == []
    assert session.state.tick == 0


def test_repeat_seed_replays_same_trace(tmp_path) -> None:
    session = make_session(tmp_path, seed=7)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.pick_species("Hunter")
    session.cell(3, 0)
    session.start()
    for _ in range(3):
        session.step_once()
    first = list(session.state.engine.state().creatures)

    session.state.seed_input = "7"
    session.repeat_seed()
    assert session.state.phase == "simulation"
    assert session.state.world.creature_at(0, 0) is not None
    assert session.state.world.creature_at(3, 0) is not None
    for _ in range(3):
        session.step_once()
    second = list(session.state.engine.state().creatures)
    assert first == second


def test_repeat_seed_changes_seed_value(tmp_path) -> None:
    session = make_session(tmp_path, seed=7)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()
    session.state.seed_input = "99"
    session.repeat_seed()
    assert session.state.seed == 99
    assert session.state.world.creature_at(0, 0) is not None


def test_repeat_seed_with_garbage_input_keeps_seed(tmp_path) -> None:
    session = make_session(tmp_path, seed=7)
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()
    session.state.seed_input = "siete"
    session.repeat_seed()
    assert session.state.seed == 7
