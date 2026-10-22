from instinct.loaders.errors import LoadError
from instinct.loaders.map_loader import build_world, load_map, load_maps
from instinct.loaders.object_loader import load_object
from instinct.loaders.registry import Registry
from instinct.loaders.terrain_loader import load_terrain

GRASS = "terrain Grass\nchar .\nresource_max 100\nregen 2\n"
WATER = "terrain Water\nchar w\nresource_max 10\nregen 1\n"
ROCK = "object Rock\nchar #\nresource_max 100\n"

# Mapa de 7 filas y 20 columnas con hierba y roca.
PLAIN_MAP = (
    "Plain with rocks\n"
    "....................\n"
    "...##...............\n"
    "...##.....#.........\n"
    "..........#....###..\n"
    "...............#....\n"
    ".#..................\n"
    ".#........##........\n"
)


def make_registry(
    terrains: tuple[str, ...] = (), objects: tuple[str, ...] = ()
) -> Registry:
    """Carga definiciones inline en un registro limpio.

    Args:
        terrains: Fuentes .te válidas en orden de declaración.
        objects: Fuentes .ob válidas en orden de declaración.
    """
    registry = Registry()
    for source in terrains:
        result = load_terrain(source)
        assert result.terrain is not None
        assert registry.add_terrain(result.terrain, result.char_line) is None
    for source in objects:
        result = load_object(source)
        assert result.object is not None
        assert registry.add_object(result.object, result.char_line) is None
    return registry


def map_errors(source: str, registry: Registry) -> list[LoadError]:
    """Carga un mapa que debe fallar y devuelve sus errores."""
    result = load_map(source, registry)
    assert result.map is None
    return result.errors


def test_valid_plain_map_loads() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    result = load_map(PLAIN_MAP, registry)
    assert result.errors == []
    assert result.map is not None
    game_map = result.map
    assert game_map.name == "Plain with rocks"
    assert game_map.width == 20
    assert game_map.height == 7
    assert game_map.base is registry.base_terrain
    grass_cell = game_map.cells[0][0]
    assert grass_cell.terrain.name == "Grass"
    assert grass_cell.object is None
    rock_cell = game_map.cells[1][3]
    assert rock_cell.terrain.name == "Grass"
    assert rock_cell.object is not None
    assert rock_cell.object.name == "Rock"


def test_non_base_terrain_cells_resolve_their_own_terrain() -> None:
    registry = make_registry((GRASS, WATER), (ROCK,))
    result = load_map("Costa\nww.\n", registry)
    assert result.errors == []
    assert result.map is not None
    cells = result.map.cells[0]
    assert cells[0].terrain.name == "Water"
    assert cells[0].object is None
    assert cells[2].terrain.name == "Grass"
    assert result.map.base is registry.terrain_for(".")


def test_unknown_char_is_rejected_with_char_and_line() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    assert [(error.line, error.message) for error in map_errors("Cueva\n..X.\n", registry)] == [
        (2, "char desconocido 'X'")
    ]


def test_unknown_chars_across_rows_accumulate() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    source = "Cueva\n..X.\n.Y..\n"
    assert [(error.line, error.message) for error in map_errors(source, registry)] == [
        (2, "char desconocido 'X'"),
        (3, "char desconocido 'Y'"),
    ]


def test_uneven_rows_are_rejected() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    source = "Lugar\n....\n...\n"
    assert [(error.line, error.message) for error in map_errors(source, registry)] == [
        (3, "las filas deben medir 4 caracteres, no 3")
    ]


def test_uneven_row_and_unknown_char_accumulate() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    source = "Lugar\n....\n..X\n"
    assert [(error.line, error.message) for error in map_errors(source, registry)] == [
        (3, "las filas deben medir 4 caracteres, no 3"),
        (3, "char desconocido 'X'"),
    ]


def test_empty_source_reports_first_line() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    for source in ("", "\n   \n"):
        assert [
            (error.line, error.message) for error in map_errors(source, registry)
        ] == [(1, "la primera línea debe ser el nombre del mapa")]


def test_name_only_reports_missing_rows() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    assert [(error.line, error.message) for error in map_errors("Soledad\n", registry)] == [
        (1, "el mapa debe tener al menos una fila")
    ]


def test_blank_lines_are_skipped_but_lines_stay_physical() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    valid = load_map("Nombre\n\n...\n\n...\n", registry)
    assert valid.errors == []
    assert valid.map is not None
    assert valid.map.height == 2
    assert [(error.line, error.message) for error in map_errors("Nombre\n\n...\n\n..X\n", registry)] == [
        (5, "char desconocido 'X'")
    ]


def test_row_edges_are_stripped() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    result = load_map("Borde\n  ...  \n...\n", registry)
    assert result.errors == []
    assert result.map is not None
    assert result.map.width == 3


def test_hash_in_first_column_is_a_cell_not_a_comment() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    result = load_map("Minas\n#..\n...\n", registry)
    assert result.errors == []
    assert result.map is not None
    corner = result.map.cells[0][0]
    assert corner.terrain.name == "Grass"
    assert corner.object is not None
    assert corner.object.name == "Rock"


def test_registry_without_terrains_is_rejected() -> None:
    registry = make_registry(objects=(ROCK,))
    source = "Muro\n###\n"
    assert [(error.line, error.message) for error in map_errors(source, registry)] == [
        (1, "el mapa necesita al menos un terreno cargado")
    ]


def test_result_map_is_none_iff_errors() -> None:
    registry = make_registry((GRASS,), (ROCK,))
    for source in ("", "Solo nombre\n", "M\n..X\n", PLAIN_MAP):
        result = load_map(source, registry)
        assert (result.map is None) == bool(result.errors)


def plain_world():
    """Construye el mundo del mapa de ejemplo con hierba y roca."""
    registry = make_registry((GRASS,), (ROCK,))
    result = load_map(PLAIN_MAP, registry)
    assert result.map is not None
    return registry, result.map, build_world(result.map)


def test_build_world_matches_map_dimensions_and_cells() -> None:
    _, _, world = plain_world()
    assert (world.width, world.height) == (20, 7)
    assert world.terrain_at(0, 0).name == "Grass"
    assert world.object_at(3, 1) is not None
    assert world.object_at(3, 1).name == "Rock"
    assert world.object_at(0, 0) is None
    assert world.walkable(0, 0)
    assert not world.walkable(3, 1)


def test_build_world_objects_sit_on_the_base_terrain() -> None:
    _, _, world = plain_world()
    terrain = world.terrain_at(3, 1)
    assert terrain.name == "Grass"
    assert world.object_at(3, 1) is not None
    assert world.creature_at(3, 1) is None


def test_build_world_places_clones_not_prototypes() -> None:
    registry, game_map, world = plain_world()
    first = world.object_at(3, 1)
    second = world.object_at(4, 1)
    assert first is not second
    assert first is not registry.object_for("#")
    first.hit(100)
    assert first.reserve == 0
    assert second.reserve == 100
    cell_terrain = world.terrain_at(0, 0)
    assert cell_terrain is not registry.terrain_for(".")
    assert cell_terrain is not game_map.cells[0][0].terrain
    assert cell_terrain.reserve == 100


def test_build_world_places_non_base_terrains() -> None:
    registry = make_registry((GRASS, WATER), (ROCK,))
    result = load_map("Costa\nww.\n", registry)
    assert result.map is not None
    world = build_world(result.map)
    assert world.terrain_at(0, 0).name == "Water"
    assert world.terrain_at(0, 0).reserve == 10
    assert world.terrain_at(2, 0).name == "Grass"
    assert world.walkable(0, 0)


def test_build_world_starts_without_creatures() -> None:
    _, _, world = plain_world()
    assert list(world.creatures()) == []
    assert world.creature_at(0, 0) is None
    assert world.creature_at(19, 6) is None


def test_load_maps_keeps_valid_and_reports_broken(tmp_path) -> None:
    maps = tmp_path / "maps"
    maps.mkdir()
    (maps / "plain.map").write_text(PLAIN_MAP, encoding="utf-8")
    (maps / "bad_char.map").write_text("Cueva\n..X.\n", encoding="utf-8")
    (maps / "uneven.map").write_text("Lugar\n....\n...\n", encoding="utf-8")
    registry = make_registry((GRASS,), (ROCK,))
    loaded, errors = load_maps(maps, registry)
    assert [game_map.name for game_map in loaded] == ["Plain with rocks"]
    assert [
        (error.line, error.message, error.path) for error in errors
    ] == [
        (2, "char desconocido 'X'", str(maps / "bad_char.map")),
        (3, "las filas deben medir 4 caracteres, no 3", str(maps / "uneven.map")),
    ]


def test_load_maps_returns_alphabetical_by_filename(tmp_path) -> None:
    maps = tmp_path / "maps"
    maps.mkdir()
    (maps / "z_map.map").write_text("Primero\n...\n", encoding="utf-8")
    (maps / "a_map.map").write_text("Segundo\n...\n", encoding="utf-8")
    registry = make_registry((GRASS,), (ROCK,))
    loaded, errors = load_maps(maps, registry)
    assert errors == []
    assert [game_map.name for game_map in loaded] == ["Segundo", "Primero"]
