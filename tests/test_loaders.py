from instinct.loaders.errors import LoadError
from instinct.loaders.object_loader import load_object
from instinct.loaders.registry import Registry, load_definitions
from instinct.loaders.terrain_loader import TerrainResult, load_terrain

GRASS = "terrain Grass\nchar .\nresource_max 100\nregen 2\n"
ROCK = "object Rock\nchar #\nresource_max 100\n"


def terrain_errors(source: str) -> list[LoadError]:
    result = load_terrain(source)
    assert result.terrain is None
    return result.errors


def object_errors(source: str) -> list[LoadError]:
    result = load_object(source)
    assert result.object is None
    return result.errors


def test_valid_grass_loads() -> None:
    result = load_terrain(GRASS)
    assert result.errors == []
    assert result.terrain is not None
    assert result.terrain.name == "Grass"
    assert result.terrain.char == "."
    assert result.terrain.resource_max == 100
    assert result.terrain.regen == 2
    assert result.terrain.reserve == 100


def test_valid_rock_loads_with_hash_char() -> None:
    result = load_object(ROCK)
    assert result.errors == []
    assert result.object is not None
    assert result.object.name == "Rock"
    assert result.object.char == "#"
    assert result.object.resource_max == 100
    assert result.object.reserve == 100


def test_error_string_includes_line() -> None:
    assert str(LoadError(3, "char debe ser un solo carácter")) == (
        "línea 3: char debe ser un solo carácter"
    )


def test_comments_and_blank_lines_are_skipped() -> None:
    result = load_terrain("# grass.te\n\n" + GRASS)
    assert result.errors == []
    assert result.terrain is not None
    assert result.terrain.name == "Grass"


def test_first_line_kind_mismatch_in_terrain() -> None:
    assert [(error.line, error.message) for error in terrain_errors(ROCK)] == [
        (1, "la primera línea debe ser 'terrain Nombre'"),
        (1, "falta la clave 'regen'"),
    ]


def test_first_line_kind_mismatch_in_object() -> None:
    assert [(error.line, error.message) for error in object_errors(GRASS)] == [
        (1, "la primera línea debe ser 'object Nombre'"),
        (4, "clave desconocida 'regen'"),
    ]


def test_first_content_line_reports_its_own_line() -> None:
    assert [
        (error.line, error.message)
        for error in terrain_errors("# grass.te\n\nobject Rock\n")
    ] == [
        (3, "la primera línea debe ser 'terrain Nombre'"),
        (3, "falta la clave 'char'"),
        (3, "falta la clave 'resource_max'"),
        (3, "falta la clave 'regen'"),
    ]


def test_empty_source_reports_first_line_and_missing_keys() -> None:
    assert [(error.line, error.message) for error in terrain_errors("")] == [
        (1, "la primera línea debe ser 'terrain Nombre'"),
        (1, "falta la clave 'char'"),
        (1, "falta la clave 'resource_max'"),
        (1, "falta la clave 'regen'"),
    ]


def test_missing_keys_are_all_reported() -> None:
    assert [
        (error.line, error.message)
        for error in terrain_errors("terrain Grass\nchar .\n")
    ] == [
        (1, "falta la clave 'resource_max'"),
        (1, "falta la clave 'regen'"),
    ]


def test_duplicate_key_reports_second_occurrence() -> None:
    assert [
        (error.line, error.message)
        for error in terrain_errors(GRASS + "regen 9\n")
    ] == [(5, "clave duplicada 'regen'")]


def test_unknown_key_is_rejected() -> None:
    source = "terrain Grass\nchar .\nresource_max 100\nregen 2\nspeed 5\n"
    assert [(error.line, error.message) for error in terrain_errors(source)] == [
        (5, "clave desconocida 'speed'")
    ]


def test_regen_is_unknown_in_object_files() -> None:
    source = "object Rock\nchar #\nresource_max 100\nregen 2\n"
    assert [(error.line, error.message) for error in object_errors(source)] == [
        (4, "clave desconocida 'regen'")
    ]


def test_short_and_long_lines_are_invalid() -> None:
    assert [
        (error.line, error.message)
        for error in terrain_errors("terrain Grass\nchar\nresource_max 100\nregen 2\n")
    ] == [(2, "línea inválida"), (1, "falta la clave 'char'")]
    assert [
        (error.line, error.message)
        for error in terrain_errors(
            "terrain Grass\nchar . extra\nresource_max 100\nregen 2\n"
        )
    ] == [(2, "línea inválida"), (1, "falta la clave 'char'")]


def test_char_must_be_single_character() -> None:
    source = "terrain Grass\nchar ab\nresource_max 100\nregen 2\n"
    assert [(error.line, error.message) for error in terrain_errors(source)] == [
        (2, "char debe ser un solo carácter")
    ]


def test_resource_max_must_be_an_integer() -> None:
    source = "terrain Grass\nchar .\nresource_max lots\nregen 2\n"
    assert [(error.line, error.message) for error in terrain_errors(source)] == [
        (3, "el valor de 'resource_max' debe ser un entero")
    ]


def test_negative_resource_max_is_rejected() -> None:
    source = "terrain Grass\nchar .\nresource_max -5\nregen 2\n"
    assert [(error.line, error.message) for error in terrain_errors(source)] == [
        (3, "resource_max debe ser mayor o igual que 0")
    ]


def test_negative_regen_is_rejected() -> None:
    source = "terrain Grass\nchar .\nresource_max 100\nregen -1\n"
    assert [(error.line, error.message) for error in terrain_errors(source)] == [
        (4, "regen debe ser mayor o igual que 0")
    ]


def test_zero_values_are_allowed() -> None:
    result = load_terrain("terrain Ash\nchar ~\nresource_max 0\nregen 0\n")
    assert result.errors == []
    assert result.terrain is not None
    assert result.terrain.reserve == 0
    assert result.terrain.regen == 0


def test_result_is_none_on_error() -> None:
    result: TerrainResult = load_terrain("terrain Grass\n")
    assert result.terrain is None
    assert result.errors != []


def test_registry_finds_by_char_and_base() -> None:
    registry = Registry()
    grass = load_terrain(GRASS)
    rock = load_object(ROCK)
    assert grass.terrain is not None and rock.object is not None
    assert registry.add_terrain(grass.terrain, grass.char_line) is None
    assert registry.add_object(rock.object, rock.char_line) is None
    assert registry.base_terrain is grass.terrain
    assert registry.terrain_for(".") is grass.terrain
    assert registry.object_for("#") is rock.object
    assert registry.terrain_for("#") is None
    assert registry.object_for(".") is None


def test_registry_rejects_duplicate_char() -> None:
    registry = Registry()
    first = load_terrain(GRASS)
    second = load_terrain("terrain Dirt\nchar .\nresource_max 50\nregen 1\n")
    assert first.terrain is not None and second.terrain is not None
    assert registry.add_terrain(first.terrain, first.char_line) is None
    conflict = registry.add_terrain(second.terrain, second.char_line)
    assert conflict is not None
    assert (conflict.line, conflict.message) == (
        2,
        "el char '.' ya está declarado por 'Grass'",
    )
    assert len(registry.terrains) == 1


def test_registry_char_clash_spans_kinds() -> None:
    registry = Registry()
    grass = load_terrain(GRASS)
    puddle = load_object("object Puddle\nchar .\nresource_max 30\n")
    assert grass.terrain is not None and puddle.object is not None
    assert registry.add_terrain(grass.terrain, grass.char_line) is None
    conflict = registry.add_object(puddle.object, puddle.char_line)
    assert conflict is not None
    assert (conflict.line, conflict.message) == (
        2,
        "el char '.' ya está declarado por 'Grass'",
    )
    assert registry.objects == []


def test_load_definitions_tolerates_broken_files(tmp_path) -> None:
    terrains = tmp_path / "terrains"
    objects = tmp_path / "objects"
    terrains.mkdir()
    objects.mkdir()
    (terrains / "grass.te").write_text(GRASS, encoding="utf-8")
    (terrains / "broken.te").write_text("terrain Broken\n", encoding="utf-8")
    (objects / "rock.ob").write_text(ROCK, encoding="utf-8")
    registry, errors = load_definitions(terrains, objects)
    assert [terrain.name for terrain in registry.terrains] == ["Grass"]
    assert [obj.name for obj in registry.objects] == ["Rock"]
    assert len(errors) == 3
    assert all(error.path == str(terrains / "broken.te") for error in errors)
    assert (errors[0].line, errors[0].message) == (
        1,
        "falta la clave 'char'",
    )


def test_load_definitions_reports_char_clash_between_files(tmp_path) -> None:
    terrains = tmp_path / "terrains"
    objects = tmp_path / "objects"
    terrains.mkdir()
    objects.mkdir()
    (terrains / "a_grass.te").write_text(GRASS, encoding="utf-8")
    (terrains / "b_dirt.te").write_text(
        "terrain Dirt\nchar .\nresource_max 50\nregen 1\n", encoding="utf-8"
    )
    registry, errors = load_definitions(terrains, objects)
    assert [terrain.name for terrain in registry.terrains] == ["Grass"]
    assert [(error.line, error.message, error.path) for error in errors] == [
        (2, "el char '.' ya está declarado por 'Grass'", str(terrains / "b_dirt.te"))
    ]
