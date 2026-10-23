"""Pruebas de la entrada: teclado y ratón se traducen en acciones correctas."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pytest.importorskip("pygame")

import pygame  # noqa: E402

from instinct.ui.controls import Controls, UIAction  # noqa: E402
from instinct.ui.session import Session  # noqa: E402

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


def build_content(tmp_path: Path) -> Path:
    """Crea el directorio base con contenido mínimo cargable."""
    for name, source in (
        ("terrains/grass.te", GRASS),
        ("objects/rock.ob", ROCK),
        ("maps/prueba.map", MAP),
        ("creatures/uruk.ins", URUK),
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return tmp_path


@pytest.fixture(autouse=True)
def _pygame_ready():
    pygame.init()
    yield
    pygame.quit()


def make_state(tmp_path: Path, seed: int = 42):
    session = Session(build_content(tmp_path), seed=seed)
    session.load()
    session.select_map("Prueba")
    return session.state


def key_event(key: int, unicode: str = ""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


def click(pos: tuple[int, int], button: int = 1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def test_quit_on_escape_or_q(tmp_path) -> None:
    controls = Controls(make_state(tmp_path))
    assert controls.handle(key_event(pygame.K_ESCAPE), {}) == [UIAction("quit")]
    assert controls.handle(key_event(pygame.K_q), {}) == [UIAction("quit")]


def test_simulation_hotkeys(tmp_path) -> None:
    state = make_state(tmp_path)
    state.phase = "simulation"
    controls = Controls(state)
    assert controls.handle(key_event(pygame.K_SPACE), {}) == [UIAction("pause")]
    assert controls.handle(key_event(pygame.K_s), {}) == [UIAction("step")]
    assert controls.handle(key_event(pygame.K_r), {}) == [UIAction("reset")]
    assert controls.handle(key_event(pygame.K_3), {}) == [UIAction("speed", "2")]


def test_speed_keys_do_nothing_outside_simulation(tmp_path) -> None:
    controls = Controls(make_state(tmp_path))
    assert controls.handle(key_event(pygame.K_3), {}) == []


def test_click_on_map_hotspot(tmp_path) -> None:
    controls = Controls(make_state(tmp_path))
    hotspots = {"map:Prueba": pygame.Rect(10, 10, 200, 30)}
    assert controls.handle(click((50, 20)), hotspots) == [UIAction("map", "Prueba")]


def test_click_on_species_and_start(tmp_path) -> None:
    controls = Controls(make_state(tmp_path))
    hotspots = {
        "species:Uruk": pygame.Rect(10, 10, 200, 30),
        "start": pygame.Rect(10, 50, 200, 30),
    }
    assert controls.handle(click((20, 20)), hotspots) == [UIAction("species", "Uruk")]
    assert controls.handle(click((20, 60)), hotspots) == [UIAction("start")]


def test_click_grid_maps_to_cell(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    hotspots = {"grid": pygame.Rect(0, 0, 400, 400)}
    assert controls.handle(click((70, 3)), hotspots) == [UIAction("cell", "2,0")]
    state.phase = "simulation"
    assert controls.handle(click((70, 3)), hotspots) == [UIAction("select_cell", "2,0")]


def test_click_outside_world_is_ignored(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    hotspots = {"grid": pygame.Rect(0, 0, 400, 400)}
    assert controls.handle(click((390, 390)), hotspots) == []


def test_right_button_drags_camera(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    hotspots = {"grid": pygame.Rect(0, 0, 400, 400)}
    controls.handle(click((100, 100), button=3), hotspots)
    motion = pygame.event.Event(pygame.MOUSEMOTION, pos=(140, 90))
    controls.handle(motion, hotspots)
    assert state.camera_x == 40
    assert state.camera_y == -10
    controls.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(140, 90), button=3), hotspots)
    controls.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=(200, 200)), hotspots)
    assert state.camera_x == 40


def test_hover_tracks_cell(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    hotspots = {"grid": pygame.Rect(0, 0, 400, 400)}
    controls.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=(33, 65)), hotspots)
    assert state.hover_cell == (1, 2)
    controls.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=(390, 390)), hotspots)
    assert state.hover_cell is None


def test_wheel_zooms_with_clamp(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    controls.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=1), {})
    assert state.tile_size == 36
    for _ in range(20):
        controls.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=1), {})
    assert state.tile_size == 64
    for _ in range(30):
        controls.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-1), {})
    assert state.tile_size == 16


def test_seed_field_edits_and_repeats(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    state.seed_focused = True
    controls.handle(key_event(pygame.K_7, "7"), {})
    assert state.seed_input == "427"
    controls.handle(key_event(pygame.K_BACKSPACE), {})
    assert state.seed_input == "42"
    actions = controls.handle(key_event(pygame.K_RETURN), {})
    assert actions == [UIAction("repeat")]
    assert state.seed_focused is False


def test_seed_field_ignores_letters_and_escape_releases(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    state.seed_focused = True
    assert controls.handle(key_event(pygame.K_a, "a"), {}) == []
    assert state.seed_input == "42"
    assert controls.handle(key_event(pygame.K_ESCAPE), {}) == []
    assert state.seed_focused is False


def test_click_outside_seed_releases_focus(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    state.seed_focused = True
    hotspots = {"seed_input": pygame.Rect(0, 0, 100, 30), "grid": pygame.Rect(0, 100, 400, 400)}
    controls.handle(click((50, 150)), hotspots)
    assert state.seed_focused is False
    state.seed_focused = True
    controls.handle(click((50, 10)), hotspots)
    assert state.seed_focused is True


def test_click_on_seed_box_gains_focus(tmp_path) -> None:
    state = make_state(tmp_path)
    controls = Controls(state)
    hotspots = {"seed_input": pygame.Rect(0, 0, 100, 30)}
    assert controls.handle(click((50, 10)), hotspots) == []
    assert state.seed_focused is True
