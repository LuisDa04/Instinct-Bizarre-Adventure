"""Pruebas de los recursos gráficos: colores, fuentes y caché de celdas."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pytest.importorskip("pygame")

import pygame  # noqa: E402

from instinct.ui.assets import Assets  # noqa: E402
from instinct.ui.constants import (  # noqa: E402
    FACTION_DEFAULT,
    OBJECT_DEFAULT,
    TERRAIN_DEFAULT,
)


@pytest.fixture(autouse=True)
def _pygame_ready():
    pygame.init()
    yield
    pygame.quit()


def test_terrain_color_known_and_unknown() -> None:
    assets = Assets()
    assert assets.terrain_color("Grass") == (34, 139, 34)
    assert assets.terrain_color("Volcano") == TERRAIN_DEFAULT


def test_faction_color_ignores_case() -> None:
    assets = Assets()
    assert assets.faction_color("joestar") == assets.faction_color("Joestar")


def test_jojo_palette_covers_shipped_content() -> None:
    assets = Assets()
    for name in ("Morioh", "Adoquin"):
        assert assets.terrain_color(name) != TERRAIN_DEFAULT
    for name in ("Steamroller", "Knives"):
        assert assets.object_color(name) != OBJECT_DEFAULT
    for faction in ("joestar", "dio", "hamon"):
        assert assets.faction_color(faction) != FACTION_DEFAULT


def test_tile_is_cached_and_resizes() -> None:
    assets = Assets(tile_size=32)
    first = assets.tile((255, 0, 0))
    assert assets.tile((255, 0, 0)) is first
    assert first.get_size() == (32, 32)

    assets.ensure_tile_size(64)
    big = assets.tile((255, 0, 0))
    assert big.get_size() == (64, 64)
    assert big is not first


def test_ensure_tile_size_same_keeps_cache() -> None:
    assets = Assets(tile_size=32)
    first = assets.tile((0, 255, 0))
    assets.ensure_tile_size(32)
    assert assets.tile((0, 255, 0)) is first


def test_fonts_exist_after_zoom() -> None:
    assets = Assets(tile_size=16)
    assets.ensure_tile_size(64)
    assert assets.font_mono.size("#") != (0, 0)
    assert assets.font_ui.size("texto") != (0, 0)


def test_terrain_tile_is_cached_case_insensitive() -> None:
    assets = Assets(tile_size=32)
    first = assets.terrain_tile("Morioh", 1)
    assert assets.terrain_tile("morioh", 1) is first
    assert first.get_size() == (32, 32)


def test_terrain_tile_rebuilds_after_zoom() -> None:
    assets = Assets(tile_size=32)
    first = assets.terrain_tile("Adoquin", 2)
    assets.ensure_tile_size(48)
    big = assets.terrain_tile("Adoquin", 2)
    assert big is not first
    assert big.get_size() == (48, 48)


def test_procedural_art_predicates() -> None:
    assets = Assets()
    assert assets.has_terrain_art("Morioh")
    assert assets.has_terrain_art("GRASS")
    assert not assets.has_terrain_art("Volcano")
    assert assets.has_object_art("Steamroller")
    assert assets.has_object_art("knives")
    assert not assets.has_object_art("Rock")


def test_object_tile_is_transparent_and_cached() -> None:
    assets = Assets()
    first = assets.object_tile("Steamroller")
    assert assets.object_tile("steamroller") is first
    assert first.get_at((0, 0)).a == 0
    assert assets.object_tile("Rock").get_at((0, 0)).a == 0


def test_creature_token_is_transparent_and_cached() -> None:
    assets = Assets()
    first = assets.creature_token("joestar")
    assert assets.creature_token("Joestar") is first
    assert first.get_at((0, 0)).a == 0
