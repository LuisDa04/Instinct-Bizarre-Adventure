"""Pruebas del contenido JoJo: carga limpia, mapa bien formado y batalla determinista."""
from __future__ import annotations

from pathlib import Path

from instinct.ui.session import Session

REPO = Path(__file__).resolve().parents[1]
ROSTER = [
    ("Jotaro", 2, 2),
    ("Kakyoin", 16, 2),
    ("Polnareff", 2, 9),
    ("Joseph", 16, 9),
    ("Dio", 9, 3),
]


def make_session(seed: int = 42) -> Session:
    """Crea una sesión con la batalla completa colocada y en marcha."""
    session = Session(REPO, seed=seed)
    assert session.load()
    session.select_map("Morioh Town")
    for species, x, y in ROSTER:
        session.pick_species(species)
        session.cell(x, y)
        session.pick_species(species)
    assert session.start()
    return session


def test_content_loads_without_errors() -> None:
    session = Session(REPO, seed=42)
    assert session.load() is True
    assert session.state.loaded.load_errors == []
    assert session.state.map_names == ["Morioh Town"]
    assert set(session.state.species_names) == {
        "Jotaro",
        "Dio",
        "Kakyoin",
        "Joseph",
        "Polnareff",
    }


def test_map_declares_every_cell() -> None:
    session = Session(REPO, seed=42)
    session.load()
    registry = session.state.loaded.registry
    assert {terrain.name for terrain in registry.terrains} == {"Adoquin", "Morioh"}
    assert {obj.name for obj in registry.objects} == {"Knives", "Steamroller"}
    game_map = session.state.loaded.maps["Morioh Town"]
    assert (game_map.width, game_map.height) == (20, 12)
    assert game_map.cells[5][4].object is not None
    assert game_map.cells[5][4].object.name == "Steamroller"
    assert game_map.cells[7][10].object is not None
    assert game_map.cells[7][10].object.name == "Knives"
    assert game_map.cells[2][2].terrain.name == "Morioh"
    assert game_map.cells[0][0].terrain.name == "Adoquin"


def test_battle_runs_and_logs() -> None:
    session = make_session(seed=42)
    for _ in range(100):
        session.step_once()
    assert session.state.tick == 100
    assert session.state.engine.state().creatures  # alguien sigue vivo
    assert any("dice:" in m for m in session.state.messages)
    assert any("ruge:" in m for m in session.state.messages)


def test_battle_is_deterministic_per_seed() -> None:
    first = make_session(seed=42)
    for _ in range(50):
        first.step_once()
    second = make_session(seed=42)
    for _ in range(50):
        second.step_once()
    assert second.state.engine.state().creatures == first.state.engine.state().creatures
    assert second.state.messages == first.state.messages
