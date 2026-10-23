"""Pruebas del pipeline: cadena de carga completa con fallo parcial."""
from __future__ import annotations

from instinct.loaders.pipeline import LoadedWorld, load_all

GRASS = "terrain Grass\nchar .\nresource_max 100\nregen 2\n"
ROCK = "object Rock\nchar #\nresource_max 100\n"
MAP = "Prueba\n..\n.#\n"
BROKEN_MAP = "Roto\n..?\n"
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
BROKEN_CREATURE = "creature Bad\nfaction x\nhealth 0\nvision 1\nlifespan 10\nstart:\nwait(1)\n"


def fill_dirs(tmp_path, *, grass=True, rock=True, game_map=True,
              broken_map=False, uruk=True, broken_creature=False):
    """Crea las cuatro carpetas con el contenido indicado."""
    terrains = tmp_path / "terrains"; terrains.mkdir()
    objects = tmp_path / "objects"; objects.mkdir()
    maps = tmp_path / "maps"; maps.mkdir()
    creatures = tmp_path / "creatures"; creatures.mkdir()
    if grass:
        (terrains / "grass.te").write_text(GRASS, encoding="utf-8")
    if rock:
        (objects / "rock.ob").write_text(ROCK, encoding="utf-8")
    if game_map:
        (maps / "mapa.map").write_text(MAP, encoding="utf-8")
    if broken_map:
        (maps / "roto.map").write_text(BROKEN_MAP, encoding="utf-8")
    if uruk:
        (creatures / "uruk.ins").write_text(URUK, encoding="utf-8")
    if broken_creature:
        (creatures / "bad.ins").write_text(BROKEN_CREATURE, encoding="utf-8")
    return terrains, objects, maps, creatures


def test_load_all_returns_everything(tmp_path) -> None:
    dirs = fill_dirs(tmp_path)
    loaded = load_all(*dirs)
    assert isinstance(loaded, LoadedWorld)
    assert len(loaded.registry.terrains) == 1
    assert loaded.registry.terrains[0].name == "Grass"
    assert len(loaded.registry.objects) == 1
    assert loaded.registry.objects[0].name == "Rock"
    assert list(loaded.maps.keys()) == ["Prueba"]
    assert list(loaded.creatures.keys()) == ["Uruk"]
    assert loaded.load_errors == []


def test_load_all_broken_map_does_not_break_creatures(tmp_path) -> None:
    dirs = fill_dirs(tmp_path, broken_map=True, broken_creature=True)
    loaded = load_all(*dirs)
    assert "Prueba" in loaded.maps
    assert "Uruk" in loaded.creatures
    assert len(loaded.load_errors) == 2
    messages = [e.message for e in loaded.load_errors]
    assert any("char desconocido" in m for m in messages)
    assert any("health" in m for m in messages)


def test_load_all_empty_directories(tmp_path) -> None:
    dirs = fill_dirs(tmp_path, grass=False, rock=False, game_map=False, uruk=False)
    loaded = load_all(*dirs)
    assert loaded.maps == {}
    assert loaded.creatures == {}
    assert len(loaded.registry.terrains) == 0
    assert len(loaded.load_errors) == 0


def test_load_all_no_terrains_rejects_maps(tmp_path) -> None:
    dirs = fill_dirs(tmp_path, grass=False)
    loaded = load_all(*dirs)
    assert loaded.maps == {}
    assert "Uruk" in loaded.creatures
    assert any("terreno" in e.message for e in loaded.load_errors)


def test_load_all_errors_have_paths(tmp_path) -> None:
    dirs = fill_dirs(tmp_path, broken_map=True)
    loaded = load_all(*dirs)
    assert loaded.load_errors
    assert all(e.path for e in loaded.load_errors)


def test_load_all_map_dict_keyed_by_name(tmp_path) -> None:
    dirs = fill_dirs(tmp_path)
    loaded = load_all(*dirs)
    game_map = loaded.maps["Prueba"]
    assert game_map.width == 2
    assert game_map.height == 2
