"""Cadena de carga completa: terrenos, objetos, mapas y criaturas en orden."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..compiler.semantic import ResolvedProgram
from .creature_loader import load_creatures
from .errors import LoadError
from .map_loader import GameMap, load_maps
from .registry import Registry, load_definitions


@dataclass(frozen=True)
class LoadedWorld:
    """Todo lo cargado al arrancar: registro, mapas, criaturas y errores.

    Invariante: los dicts solo traen lo válido; los errores de todos los
    pasos quedan acumulados en load_errors para el registro de la aplicación.

    Attributes:
        registry: Catálogo de terrenos y objetos con chars resueltos.
        maps: Mapas validados indexados por su nombre.
        creatures: Programas resueltos indexados por su nombre.
        load_errors: Errores de carga de todas las etapas, con su ruta.
    """

    registry: Registry
    maps: dict[str, GameMap] = field(default_factory=dict)
    creatures: dict[str, ResolvedProgram] = field(default_factory=dict)
    load_errors: list[LoadError] = field(default_factory=list)


def load_all(
    terrains_dir: Path,
    objects_dir: Path,
    maps_dir: Path,
    creatures_dir: Path,
) -> LoadedWorld:
    """Carga todo el contenido del juego en orden: .te → .ob → .map → .ins.

    Cada paso tolera fallos parciales: lo que carga bien queda disponible
    y lo que falla se acumula en load_errors sin romper los demás pasos.

    Args:
        terrains_dir: Carpeta con ficheros *.te.
        objects_dir: Carpeta con ficheros *.ob.
        maps_dir: Carpeta con ficheros *.map.
        creatures_dir: Carpeta con ficheros *.ins.

    Returns:
        LoadedWorld con los diccionarios listos para la interfaz.
    """
    registry, definition_errors = load_definitions(terrains_dir, objects_dir)
    map_list, map_errors = load_maps(maps_dir, registry)
    creatures, creature_errors = load_creatures(creatures_dir)
    return LoadedWorld(
        registry=registry,
        maps={game_map.name: game_map for game_map in map_list},
        creatures=creatures,
        load_errors=definition_errors + map_errors + creature_errors,
    )
