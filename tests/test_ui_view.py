"""Pruebas del renderizado: cada fase dibuja y expone sus puntos interactivos."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pytest.importorskip("pygame")

import pygame  # noqa: E402

from instinct.ui.assets import Assets  # noqa: E402
from instinct.ui.session import Session  # noqa: E402
from instinct.ui.view import View  # noqa: E402

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


@pytest.fixture()
def session(tmp_path: Path) -> Session:
    session = Session(build_content(tmp_path), seed=42)
    session.load()
    return session


@pytest.fixture(autouse=True)
def _pygame_ready():
    pygame.init()
    yield
    pygame.quit()


def render(state, size=(1280, 800)):
    screen = pygame.Surface(size)
    view = View(Assets())
    view.render(screen, state)
    return view


def test_render_loading_without_world() -> None:
    from instinct.ui.state import UIState

    view = render(UIState())
    assert view.hotspots == {}


def test_render_map_select_lists_maps(session: Session) -> None:
    view = render(session.state)
    assert "map:Prueba" in view.hotspots


def test_render_placement_offers_species_and_start(session: Session) -> None:
    session.select_map("Prueba")
    view = render(session.state)
    assert "species:Uruk" in view.hotspots
    assert "species:Hunter" in view.hotspots
    assert "start" in view.hotspots
    assert "grid" in view.hotspots


def test_render_start_disabled_without_creatures(session: Session) -> None:
    session.select_map("Prueba")
    view = render(session.state)
    assert "start" in view.hotspots


def test_render_simulation_shows_controls(session: Session) -> None:
    session.select_map("Prueba")
    session.pick_species("Uruk")
    session.cell(0, 0)
    session.start()
    view = render(session.state)
    for key in ("pause", "step", "speed", "reset", "repeat", "seed_input", "grid"):
        assert key in view.hotspots


def test_render_no_maps_shows_quit(tmp_path: Path) -> None:
    base = build_content(tmp_path)
    (base / "maps" / "prueba.map").unlink()
    session = Session(base, seed=42)
    session.load()
    view = render(session.state)
    assert "quit" in view.hotspots


def test_grid_hotspot_covers_first_cell(session: Session) -> None:
    session.select_map("Prueba")
    view = render(session.state, size=(640, 400))
    grid = view.hotspots["grid"]
    assert grid.topleft == (0, 0)
    assert grid.width == 640 - 300


def test_preview_is_cached(session: Session) -> None:
    session.select_map("Prueba")
    view = render(session.state)
    first = view._map_preview(session.state, "Prueba")
    again = view._map_preview(session.state, "Prueba")
    assert first is again
