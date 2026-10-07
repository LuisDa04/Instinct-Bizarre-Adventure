"""Rejilla rectangular de casillas con terreno, objeto y criatura."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .entities import Creature, Terrain, WorldObject


@dataclass
class Cell:
    """Representa una casilla con terreno siempre presente y objeto o criatura excluyentes."""

    terrain: Terrain
    object: WorldObject | None = None
    creature: Creature | None = None


class World:
    """Representa el mapa rectangular cuyas casillas nacen como clones del terreno base.

    Invariante: cada casilla guarda su propio Terrain y nunca mezcla objeto y criatura.
    """

    def __init__(self, width: int, height: int, terrain: Terrain) -> None:
        """Crea un mundo de width x height clonando el terreno base en cada casilla.

        Args:
            width: Ancho en casillas; se espera > 0.
            height: Alto en casillas; se espera > 0.
            terrain: Prototipo a clonar; no se guarda por referencia y su reserva se ignora.
        """
        self.width = width
        self.height = height
        self._cells: list[list[Cell]] = [
            [Cell(terrain=terrain.clone()) for _ in range(width)]
            for _ in range(height)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        """Indica si (x, y) cae dentro del mapa."""
        return 0 <= x < self.width and 0 <= y < self.height

    def terrain_at(self, x: int, y: int) -> Terrain | None:
        """Devuelve el terreno de (x, y) o None si está fuera del mapa.

        Returns:
            La instancia guardada por referencia, o None fuera del mapa.
        """
        if not self.in_bounds(x, y):
            return None
        return self._cells[y][x].terrain

    def object_at(self, x: int, y: int) -> WorldObject | None:
        """Devuelve el objeto de (x, y) o None si no hay o está fuera del mapa.

        Returns:
            La instancia guardada por referencia, o None si no hay objeto.
        """
        if not self.in_bounds(x, y):
            return None
        return self._cells[y][x].object

    def creature_at(self, x: int, y: int) -> Creature | None:
        """Devuelve la criatura de (x, y) o None si no hay o está fuera del mapa.

        Returns:
            La instancia guardada por referencia, o None si no hay criatura.
        """
        if not self.in_bounds(x, y):
            return None
        return self._cells[y][x].creature

    def walkable(self, x: int, y: int) -> bool:
        """Indica si (x, y) admite entrar: dentro del mapa y sin objeto ni criatura.

        Returns:
            False fuera del mapa o si la casilla está ocupada.
        """
        if not self.in_bounds(x, y):
            return False
        cell = self._cells[y][x]
        return cell.object is None and cell.creature is None

    def place_terrain(self, x: int, y: int, terrain: Terrain) -> bool:
        """Coloca un clon del terreno dado en (x, y) con la reserva llena.

        Args:
            terrain: Prototipo a clonar; su reserva actual se ignora.

        Returns:
            True si se colocó, False si (x, y) está fuera del mapa.
        """
        if not self.in_bounds(x, y):
            return False
        self._cells[y][x].terrain = terrain.clone()
        return True

    def place_object(self, x: int, y: int, obj: WorldObject) -> bool:
        """Coloca un clon del objeto dado en (x, y) si no hay criatura.

        Sobrescribe cualquier objeto previo con un clon de reserva llena.

        Returns:
            False si (x, y) está fuera del mapa o la casilla tiene criatura.
        """
        if not self.in_bounds(x, y):
            return False
        cell = self._cells[y][x]
        if cell.creature is not None:
            return False
        cell.object = obj.clone()
        return True

    def remove_object(self, x: int, y: int) -> WorldObject | None:
        """Retira y devuelve el objeto de (x, y), o None si no hay o está fuera.

        Returns:
            La instancia que estaba guardada, o None si no había nada que retirar.
        """
        if not self.in_bounds(x, y):
            return None
        cell = self._cells[y][x]
        obj = cell.object
        cell.object = None
        return obj

    def place_creature(self, x: int, y: int, creature: Creature) -> bool:
        """Coloca la criatura dada en (x, y) y sincroniza su posición.

        Args:
            creature: Se guarda por referencia, no se clona.

        Returns:
            False si (x, y) está fuera o la casilla tiene objeto o criatura.
        """
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
        """Retira y devuelve la criatura de (x, y), o None si no hay o está fuera.

        Returns:
            La instancia que estaba guardada, o None si no había nada que retirar.
        """
        if not self.in_bounds(x, y):
            return None
        cell = self._cells[y][x]
        creature = cell.creature
        cell.creature = None
        return creature

    def creatures(self) -> Iterator[Creature]:
        """Recorre en orden de filas todas las criaturas colocadas.

        Yields:
            Las instancias guardadas por referencia, no copias.
        """
        for row in self._cells:
            for cell in row:
                if cell.creature is not None:
                    yield cell.creature
