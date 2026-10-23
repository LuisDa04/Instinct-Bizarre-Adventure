"""Fuentes y colores de la interfaz, con caché de superficies por tamaño de celda."""
from __future__ import annotations

import pygame

from .constants import (
    BASE_TILE_SIZE,
    FACTION_COLORS,
    FACTION_DEFAULT,
    OBJECT_COLORS,
    OBJECT_DEFAULT,
    TERRAIN_COLORS,
    TERRAIN_DEFAULT,
)


class Assets:
    """Provee las fuentes y superficies de color para dibujar la rejilla.

    Las fuentes se recrean al cambiar el tamaño de celda para que el char
    de cada casilla crezca con el zoom; las superficies se cachean para no
    reconstruir un rectángulo por celda en cada frame.
    """

    def __init__(self, tile_size: int = BASE_TILE_SIZE) -> None:
        """Crea los recursos con el tamaño de celda inicial.

        Args:
            tile_size: Lado de la celda en píxeles.
        """
        self.tile_size = tile_size
        self._tiles: dict[tuple[int, int, int], pygame.Surface] = {}
        self._build_fonts()

    def _build_fonts(self) -> None:
        """Crea la fuente de rejilla acorde al tamaño de celda y la fija de paneles."""
        self.font_mono = pygame.font.SysFont(
            "consolas,dejavusansmono,couriernew,monospace",
            max(10, self.tile_size - 8),
            bold=True,
        )
        self.font_ui = pygame.font.SysFont("arial,helvetica,sans", 14)

    def ensure_tile_size(self, size: int) -> None:
        """Adapta las fuentes y vacía la caché si cambia el tamaño de celda."""
        if size == self.tile_size:
            return
        self.tile_size = size
        self._tiles.clear()
        self._build_fonts()

    def tile(self, color: tuple[int, int, int]) -> pygame.Surface:
        """Devuelve una superficie del color pedido, creada solo la primera vez."""
        surface = self._tiles.get(color)
        if surface is None:
            surface = pygame.Surface((self.tile_size, self.tile_size))
            surface.fill(color)
            self._tiles[color] = surface
        return surface

    def terrain_color(self, name: str) -> tuple[int, int, int]:
        """Devuelve el color del terreno por nombre; los desconocidos en gris."""
        return TERRAIN_COLORS.get(name.lower(), TERRAIN_DEFAULT)

    def object_color(self, name: str) -> tuple[int, int, int]:
        """Devuelve el color del objeto por nombre; los desconocidos en ámbar."""
        return OBJECT_COLORS.get(name.lower(), OBJECT_DEFAULT)

    def faction_color(self, faction: str) -> tuple[int, int, int]:
        """Devuelve el color de la facción por nombre; las desconocidas en gris claro."""
        return FACTION_COLORS.get(faction.lower(), FACTION_DEFAULT)
