"""Carga de mapas .map: nombre, filas de chars validados contra el registro."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..world.entities import Terrain, WorldObject
from ..world.world import World
from .errors import LoadError, read_source, tag_errors
from .registry import Registry


@dataclass(frozen=True)
class MapCell:
    """Representa una casilla de mapa con su terreno y su objeto opcional.

    Invariante: terrain siempre presente; object es opcional y aún no hay
    criaturas en el mapa.
    """

    terrain: Terrain
    object: WorldObject | None = None


@dataclass(frozen=True)
class GameMap:
    """Representa un mapa validado con prototipos del registro ya resueltos.

    Invariante: todas las filas miden lo mismo y cada casilla referencia al
    prototipo del registro (se clona al colocar, nunca aquí).
    """

    name: str
    base: Terrain
    cells: tuple[tuple[MapCell, ...], ...]

    @property
    def width(self) -> int:
        """Devuelve el número de columnas de la rejilla."""
        return len(self.cells[0])

    @property
    def height(self) -> int:
        """Devuelve el número de filas de la rejilla."""
        return len(self.cells)


@dataclass(frozen=True)
class MapResult:
    """Representa el resultado de cargar un mapa: instancia o None más errores.

    Invariante: map es None si y solo si errors no está vacío.
    """

    map: GameMap | None
    errors: list[LoadError]


def load_map(source: str, registry: Registry) -> MapResult:
    """Carga un mapa desde su texto validando cada char contra el registro.

    La primera línea con contenido es el nombre y cada línea siguiente con
    contenido es una fila de casillas del mismo largo. Cualquier
    error (filas disconformes, chars sin dueño) rechaza el archivo entero
    con todos sus errores recogidos de una vez, como el compilador.

    Args:
        source: Texto con el nombre en la primera línea y las filas después.
        registry: Registro de terrenos y objetos ya cargados.

    Returns:
        MapResult con map válido y errores vacíos, o map None y errores no vacíos.
    """
    errors: list[LoadError] = []
    significant = [
        (number, text)
        for number, text in enumerate(source.splitlines(), start=1)
        if text.strip()
    ]
    if not significant:
        errors.append(LoadError(1, "la primera línea debe ser el nombre del mapa"))
        return MapResult(map=None, errors=errors)
    name_number, name_text = significant[0]
    name = name_text.strip()
    rows = [(number, text.strip()) for number, text in significant[1:]]
    if not rows:
        errors.append(LoadError(name_number, "el mapa debe tener al menos una fila"))
        return MapResult(map=None, errors=errors)
    if not registry.terrains:
        errors.append(
            LoadError(name_number, "el mapa necesita al menos un terreno cargado")
        )
        return MapResult(map=None, errors=errors)
    base = registry.base_terrain
    width = len(rows[0][1])
    cells: list[tuple[MapCell, ...]] = []
    for number, row in rows:
        if len(row) != width:
            errors.append(
                LoadError(number, f"las filas deben medir {width} caracteres, no {len(row)}")
            )
        cells.append(tuple(_resolve(row, number, registry, base, errors)))
    if errors:
        return MapResult(map=None, errors=errors)
    return MapResult(
        map=GameMap(name=name, base=base, cells=tuple(cells)),
        errors=[],
    )


def _resolve(
    row: str,
    number: int,
    registry: Registry,
    base: Terrain,
    errors: list[LoadError],
) -> list[MapCell]:
    """Traduce los chars de una fila a casillas o registra los desconocidos.

    Los chars de objeto resuelven al terreno base debajo; los
    desconocidos dejan una casilla provisional que se descarta al rechazar.

    Returns:
        Lista de casillas de la fila en orden de columnas.
    """
    resolved: list[MapCell] = []
    for char in row:
        terrain = registry.terrain_for(char)
        if terrain is not None:
            resolved.append(MapCell(terrain=terrain))
            continue
        obj = registry.object_for(char)
        if obj is not None:
            resolved.append(MapCell(terrain=base, object=obj))
            continue
        errors.append(LoadError(number, f"char desconocido {char!r}"))
        resolved.append(MapCell(terrain=base))
    return resolved


def build_world(game_map: GameMap) -> World:
    """Construye el mundo del mapa colocando terrenos y objetos casilla a casilla.

    La rejilla nace cubierta de clones del terreno base y solo se
    rellenan las casillas que difieren: el terreno propio con place_terrain y
    el objeto encima con place_object. Ambos colocan clones con la reserva
    llena, así el mapa y el mundo no comparten instancias.

    Args:
        game_map: Mapa ya validado por load_map.

    Returns:
        Mundo nuevo de game_map.width x game_map.height, sin criaturas.
    """
    world = World(game_map.width, game_map.height, game_map.base)
    for y, row in enumerate(game_map.cells):
        for x, cell in enumerate(row):
            if cell.terrain is not game_map.base:
                world.place_terrain(x, y, cell.terrain)
            if cell.object is not None:
                world.place_object(x, y, cell.object)
    return world


def load_maps(
    maps_dir: Path, registry: Registry
) -> tuple[list[GameMap], list[LoadError]]:
    """Carga todos los .map de una carpeta y devuelve los válidos y los errores.

    Recorre la carpeta en orden alfabético, conserva lo válido y acumula los
    errores etiquetados con su ruta, igual que load_definitions. La carga es
    tolerante por archivo: un mapa roto o ilegible no impide cargar el resto.
    Si dos archivos declaran el mismo nombre, se conserva el que llega primero
    en orden alfabético y cada archivo posterior aporta un solo error.

    Args:
        maps_dir: Carpeta con ficheros *.map.
        registry: Registro de terrenos y objetos ya cargados.

    Returns:
        Tupla (mapas, errores): entran los mapas sin errores cuyo nombre no
        estuviera ya presente, y los errores llevan la ruta de su archivo.
    """
    maps: list[GameMap] = []
    errors: list[LoadError] = []
    names: set[str] = set()
    for path in sorted(maps_dir.glob("*.map")):
        source, read_error = read_source(path)
        if read_error is not None:
            errors.append(read_error)
            continue
        assert source is not None
        result = load_map(source, registry)
        errors.extend(tag_errors(result.errors, path))
        if result.map is None:
            continue
        if result.map.name in names:
            errors.append(
                LoadError(
                    1, f"nombre de mapa duplicado {result.map.name!r}", str(path)
                )
            )
            continue
        names.add(result.map.name)
        maps.append(result.map)
    return maps, errors
