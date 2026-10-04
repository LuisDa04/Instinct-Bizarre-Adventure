from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .entities import Creature, Terrain, WorldObject


@dataclass
class Cell:
    terrain: Terrain
    object: WorldObject | None = None
    creature: Creature | None = None


class World:
    def __init__(self, width: int, height: int, terrain: Terrain) -> None:
        self.width = width
        self.height = height
        self._cells: list[list[Cell]] = [
            [Cell(terrain=terrain.clone()) for _ in range(width)]
            for _ in range(height)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def terrain_at(self, x: int, y: int) -> Terrain | None:
        if not self.in_bounds(x, y):
            return None
        return self._cells[y][x].terrain

    def object_at(self, x: int, y: int) -> WorldObject | None:
        if not self.in_bounds(x, y):
            return None
        return self._cells[y][x].object

    def creature_at(self, x: int, y: int) -> Creature | None:
        if not self.in_bounds(x, y):
            return None
        return self._cells[y][x].creature

    def walkable(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        cell = self._cells[y][x]
        return cell.object is None and cell.creature is None

    def place_terrain(self, x: int, y: int, terrain: Terrain) -> bool:
        if not self.in_bounds(x, y):
            return False
        self._cells[y][x].terrain = terrain.clone()
        return True

    def place_object(self, x: int, y: int, obj: WorldObject) -> bool:
        if not self.in_bounds(x, y):
            return False
        cell = self._cells[y][x]
        if cell.creature is not None:
            return False
        cell.object = obj.clone()
        return True

    def remove_object(self, x: int, y: int) -> WorldObject | None:
        if not self.in_bounds(x, y):
            return None
        cell = self._cells[y][x]
        obj = cell.object
        cell.object = None
        return obj

    def place_creature(self, x: int, y: int, creature: Creature) -> bool:
        if not self.in_bounds(x, y):
            return False
        cell = self._cells[y][x]
        if cell.object is not None or cell.creature is not None:
            return False
        cell.creature = creature
        creature.x = x
        creature.y = y
        return True

    def remove_creature(self, x: int, y: int) -> Creature | None:
        if not self.in_bounds(x, y):
            return None
        cell = self._cells[y][x]
        creature = cell.creature
        cell.creature = None
        return creature

    def creatures(self) -> Iterator[Creature]:
        for row in self._cells:
            for cell in row:
                if cell.creature is not None:
                    yield cell.creature
