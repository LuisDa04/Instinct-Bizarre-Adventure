"""Pruebas del pipeline: cadena de carga completa con fallo parcial."""
from __future__ import annotations

from pathlib import Path

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


class ReversedGlobDir:
    """Carpeta simulada que entrega los mapas en orden inverso al alfabético."""

    def __init__(self, real_dir: Path) -> None:
        """Guarda la carpeta real sobre la que consulta los archivos."""
        self._real_dir = real_dir

    def glob(self, pattern: str):
        """Devuelve los archivos en orden inverso al de la carpeta real."""
        return reversed(sorted(self._real_dir.glob(pattern)))


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


def test_load_all_duplicate_map_keeps_first_and_reports_second(tmp_path) -> None:
    terrains, objects, maps, creatures = fill_dirs(tmp_path, game_map=False)
    # Se escribe primero el archivo que va después en orden alfabético.
    duplicate = maps / "z_mapa.map"
    duplicate.write_text("Prueba\n##\n", encoding="utf-8")
    (maps / "mapa.map").write_text(MAP, encoding="utf-8")
    loaded = load_all(terrains, objects, ReversedGlobDir(maps), creatures)
    assert list(loaded.maps) == ["Prueba"]
    survivor = loaded.maps["Prueba"]
    assert survivor.cells[0][0].object is None
    assert list(loaded.creatures) == ["Uruk"]
    assert [(error.line, error.message, error.path) for error in loaded.load_errors] == [
        (1, "nombre de mapa duplicado 'Prueba'", str(duplicate))
    ]


def test_load_all_non_utf8_files_report_and_keep_valid(tmp_path) -> None:
    terrains, objects, maps, creatures = fill_dirs(tmp_path)
    bad_files = (
        (terrains / "z_mal.te", b"terrain \xf1\n"),
        (objects / "z_mal.ob", b"object \xf1\n"),
        (maps / "z_mal.map", b"Mapa\n..\xf1\n"),
        (creatures / "z_mal.ins", b"creature \xf1\n"),
    )
    for path, content in bad_files:
        path.write_bytes(content)
    loaded = load_all(terrains, objects, maps, creatures)
    assert [terrain.name for terrain in loaded.registry.terrains] == ["Grass"]
    assert [obj.name for obj in loaded.registry.objects] == ["Rock"]
    assert list(loaded.maps) == ["Prueba"]
    assert list(loaded.creatures) == ["Uruk"]
    assert [(error.line, error.message, error.path) for error in loaded.load_errors] == [
        (1, "el archivo no está codificado en UTF-8", str(path))
        for path, _ in bad_files
    ]


def test_load_all_directory_named_map_is_reported(tmp_path) -> None:
    terrains, objects, maps, creatures = fill_dirs(tmp_path)
    bad_path = maps / "bad.map"
    bad_path.mkdir()
    loaded = load_all(terrains, objects, maps, creatures)
    assert list(loaded.maps) == ["Prueba"]
    assert list(loaded.creatures) == ["Uruk"]
    assert [(error.line, error.message, error.path) for error in loaded.load_errors] == [
        (1, "no se pudo leer el archivo", str(bad_path))
    ]
