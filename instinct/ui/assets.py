"""Fuentes y colores de la interfaz, con caché de superficies por tamaño de celda."""
from __future__ import annotations

import pygame

from .constants import (
    BASE_TILE_SIZE,
    COBBLESTONE_TERRAINS,
    FACTION_COLORS,
    FACTION_DEFAULT,
    GRASS_TERRAINS,
    OBJECT_ART,
    OBJECT_COLORS,
    OBJECT_DEFAULT,
    TERRAIN_ART,
    TERRAIN_COLORS,
    TERRAIN_DEFAULT,
)


def _lighten(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    """Devuelve el color con cada canal subido por la cantidad dada."""
    return tuple(min(255, channel + amount) for channel in color)


def _darken(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    """Devuelve el color con cada canal bajado por la cantidad dada."""
    return tuple(max(0, channel - amount) for channel in color)


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
        self._terrain_tiles: dict[tuple[str, int], pygame.Surface] = {}
        self._object_tiles: dict[str, pygame.Surface] = {}
        self._creature_tokens: dict[str, pygame.Surface] = {}
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
        """Adapta las fuentes y vacía las cachés si cambia el tamaño de celda."""
        if size == self.tile_size:
            return
        self.tile_size = size
        self._tiles.clear()
        self._terrain_tiles.clear()
        self._object_tiles.clear()
        self._creature_tokens.clear()
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

    # ------------------------------------------------------------------
    # Tiles procedurales de la rejilla
    # ------------------------------------------------------------------

    def has_terrain_art(self, name: str) -> bool:
        """Indica si el terreno tiene un patrón procedural propio."""
        return name.lower() in TERRAIN_ART

    def has_object_art(self, name: str) -> bool:
        """Indica si el objeto tiene un icono procedural propio."""
        return name.lower() in OBJECT_ART

    def terrain_tile(self, name: str, variant: int = 0) -> pygame.Surface:
        """Devuelve la casilla del terreno con relieve y patrón, cacheada.

        Args:
            name: Nombre del terreno; el desconocido queda en color plano
                con el mismo relieve.
            variant: 0-3; desplaza el patrón para que celdas vecinas no
                repitan exactamente las mismas motas.
        """
        key = (name.lower(), variant)
        surface = self._terrain_tiles.get(key)
        if surface is None:
            surface = self._build_terrain_tile(name, variant)
            self._terrain_tiles[key] = surface
        return surface

    def _build_terrain_tile(self, name: str, variant: int) -> pygame.Surface:
        """Construye la casilla: color base, patrón según el nombre y relieve."""
        size = self.tile_size
        base = self.terrain_color(name)
        surface = pygame.Surface((size, size))
        surface.fill(base)
        lowered = name.lower()
        if lowered in GRASS_TERRAINS:
            self._draw_grass(surface, base, variant)
        elif lowered in COBBLESTONE_TERRAINS:
            self._draw_cobblestone(surface, base)
        self._draw_bevel(surface, base)
        return surface

    def _draw_grass(
        self, surface: pygame.Surface, base: tuple[int, int, int], variant: int
    ) -> None:
        """Siembra briznas oscuras y un punto de luz, desplazadas por variante."""
        size = self.tile_size
        dark = _darken(base, 45)
        light = _lighten(base, 45)
        spots = (
            (0.2, 0.3),
            (0.55, 0.15),
            (0.8, 0.45),
            (0.35, 0.7),
            (0.7, 0.8),
            (0.15, 0.85),
        )
        shift = ((0, 0), (2, 1), (-1, 2), (1, -2))[variant % 4]
        for fx, fy in spots:
            x = int(fx * size) + shift[0]
            y = int(fy * size) + shift[1]
            if 0 <= x < size and 0 <= y < size - 2:
                pygame.draw.line(
                    surface, dark, (x, y), (x, y + max(2, size // 7)), max(1, size // 18)
                )
        shine = spots[variant % len(spots)]
        shine_x = int(shine[0] * size) + shift[0] + 2
        shine_y = int(shine[1] * size) + shift[1]
        if 0 < shine_x < size and 0 < shine_y < size:
            pygame.draw.circle(surface, light, (shine_x, shine_y), max(1, size // 20))

    def _draw_cobblestone(
        self, surface: pygame.Surface, base: tuple[int, int, int]
    ) -> None:
        """Dibuja cuatro piedras redondeadas con junta oscura entre ellas."""
        size = self.tile_size
        grout = _darken(base, 45)
        stone = _lighten(base, 25)
        edge = max(1, size // 16)
        half = size // 2
        radius = max(2, size // 10)
        for row in range(2):
            for col in range(2):
                outer = pygame.Rect(col * half, row * half, half, half)
                inner = outer.inflate(-edge * 2, -edge * 2)
                pygame.draw.rect(surface, grout, outer, border_radius=radius)
                pygame.draw.rect(surface, stone, inner, border_radius=radius)

    def _draw_bevel(self, surface: pygame.Surface, base: tuple[int, int, int]) -> None:
        """Añade luz arriba-izquierda y sombra abajo-derecha para dar relieve."""
        size = self.tile_size
        light = _lighten(base, 28)
        dark = _darken(base, 35)
        edge = max(1, size // 16)
        pygame.draw.rect(surface, light, (0, 0, size, edge))
        pygame.draw.rect(surface, light, (0, 0, edge, size))
        pygame.draw.rect(surface, dark, (0, size - edge, size, edge))
        pygame.draw.rect(surface, dark, (size - edge, 0, edge, size))

    def object_tile(self, name: str) -> pygame.Surface:
        """Devuelve el icono del objeto sobre fondo transparente, cacheado.

        El icono se dibuja encima de la casilla del terreno; los nombres
        desconocidos quedan como un rombo del color base con contorno.
        """
        key = name.lower()
        surface = self._object_tiles.get(key)
        if surface is None:
            surface = self._build_object_tile(name)
            self._object_tiles[key] = surface
        return surface

    def _build_object_tile(self, name: str) -> pygame.Surface:
        """Construye el icono del objeto con el tamaño de celda actual."""
        size = self.tile_size
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        lowered = name.lower()
        if lowered == "steamroller":
            self._draw_steamroller(surface)
        elif lowered == "knives":
            self._draw_knives(surface)
        else:
            color = self.object_color(name)
            points = [
                (size // 2, 1),
                (size - 1, size // 2),
                (size // 2, size - 1),
                (1, size // 2),
            ]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, _darken(color, 50), points, 2)
        return surface

    def _draw_steamroller(self, surface: pygame.Surface) -> None:
        """Silueta de la apisonadora: tambor metálico, cuerpo y ventanita."""
        size = self.tile_size
        color = self.object_color("Steamroller")
        dark = _darken(color, 70)
        metal = (150, 150, 160)
        drum_radius = max(3, size // 4)
        drum = (size - drum_radius - 2, size - drum_radius - 2)
        pygame.draw.circle(surface, metal, drum, drum_radius)
        pygame.draw.circle(
            surface, _darken(metal, 60), drum, drum_radius, max(1, size // 20)
        )
        body = pygame.Rect(2, size // 4, size - 4, size // 3)
        pygame.draw.rect(surface, color, body, border_radius=max(2, size // 9))
        window = pygame.Rect(size // 5, body.y + size // 10, size // 4, size // 6)
        pygame.draw.rect(surface, dark, window, border_radius=2)
        pygame.draw.line(
            surface, dark, (size // 2, body.bottom), (drum[0], drum[1]), max(1, size // 16)
        )

    def _draw_knives(self, surface: pygame.Surface) -> None:
        """Dibuja dos cuchillas plateadas cruzadas con empuñadura central."""
        size = self.tile_size
        blade = self.object_color("Knives")
        handle = (90, 70, 50)
        width = max(2, size // 8)
        pygame.draw.line(surface, blade, (3, 3), (size - 4, size - 4), width)
        pygame.draw.line(surface, blade, (size - 4, 3), (3, size - 4), width)
        pygame.draw.circle(surface, handle, (size // 2, size // 2), max(2, size // 7))

    def creature_token(self, faction: str) -> pygame.Surface:
        """Ficha circular de la facción con borde y brillo, sobre fondo transparente."""
        key = faction.lower()
        surface = self._creature_tokens.get(key)
        if surface is None:
            size = self.tile_size
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            color = self.faction_color(faction)
            radius = int(size * 0.42)
            center = (size // 2, size // 2)
            pygame.draw.circle(surface, color, center, radius)
            pygame.draw.circle(
                surface, _darken(color, 80), center, radius, max(2, size // 16)
            )
            shine = (center[0] - radius // 3, center[1] - radius // 3)
            pygame.draw.circle(surface, _lighten(color, 50), shine, max(1, radius // 4))
            self._creature_tokens[key] = surface
        return surface
