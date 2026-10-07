"""Entidades con reserva del mundo: terreno, objeto y criatura."""
from __future__ import annotations

from ..compiler.semantic import ResolvedProgram


class Entity:
    """Representa una entidad con reserva agotable que nunca baja de 0 por golpe."""

    name: str
    walkable: bool
    reserve: int

    def hit(self, damage: int) -> bool:
        """Resta daño a la reserva sin bajar de 0 e indica si quedó agotada.

        Args:
            damage: Cantidad a restar; se esperan valores >= 0.

        Returns:
            True si la reserva quedó en 0, False en caso contrario.
        """
        self.reserve = max(0, self.reserve - damage)
        return self.reserve == 0


class Terrain(Entity):
    """Representa un terreno transitable con regeneración por tick.

    Invariante: la reserva empieza llena y nunca supera resource_max.
    """

    walkable = True

    def __init__(self, name: str, char: str, resource_max: int, regen: int) -> None:
        """Crea un terreno con la reserva inicial llena.

        Args:
            name: Nombre del terreno.
            char: Carácter que lo identifica en el mapa.
            resource_max: Reserva máxima; se espera >= 0.
            regen: Puntos que recupera por tick; se espera >= 0.
        """
        self.name = name
        self.char = char
        self.resource_max = resource_max
        self.regen = regen
        self.reserve = resource_max

    def regenerate(self) -> None:
        """Suma regen a la reserva sin superar resource_max."""
        self.reserve = min(self.resource_max, self.reserve + self.regen)

    def clone(self) -> Terrain:
        """Crea una copia independiente del terreno con la reserva llena.

        Returns:
            Nuevo Terrain con los mismos datos y reserve igual a resource_max.
        """
        return Terrain(self.name, self.char, self.resource_max, self.regen)


class WorldObject(Entity):
    """Representa un objeto sólido no transitable con reserva agotable sin regeneración.

    Invariante: la reserva empieza llena y solo baja por daño.
    """

    walkable = False

    def __init__(self, name: str, char: str, resource_max: int) -> None:
        """Crea un objeto con la reserva inicial llena.

        Args:
            name: Nombre del objeto.
            char: Carácter que lo identifica en el mapa.
            resource_max: Reserva máxima; se espera >= 0.
        """
        self.name = name
        self.char = char
        self.resource_max = resource_max
        self.reserve = resource_max

    def clone(self) -> WorldObject:
        """Crea una copia independiente del objeto con la reserva llena.

        Returns:
            Nuevo WorldObject con los mismos datos y reserve igual a resource_max.
        """
        return WorldObject(self.name, self.char, self.resource_max)


class Creature(Entity):
    """Representa una criatura que ejecuta un programa y envejece un año por tick.

    Invariante: health es un alias directo de reserve y walkable siempre es False.
    """

    walkable = False

    def __init__(self, program: ResolvedProgram, x: int = 0, y: int = 0) -> None:
        """Crea una criatura en (x, y) con salud, edad y estado de turno iniciales.

        Args:
            program: Programa resuelto; se guarda por referencia, no se clona.
            x: Columna inicial.
            y: Fila inicial.
        """
        self.name = program.name
        self.faction = program.faction
        self.vision = program.vision
        self.lifespan = program.lifespan
        self.reserve = program.health
        self.age = 0
        self.x = x
        self.y = y
        self.program = program
        self.variables: dict[str, int | str] = {}
        self.pc = 0
        self.wait_remaining: int = 0

    @property
    def health(self) -> int:
        """Devuelve la salud actual, que es la reserva de la entidad."""
        return self.reserve

    @health.setter
    def health(self, value: int) -> None:
        """Asigna la salud actual como alias directo de la reserva.

        Args:
            value: Nuevo valor; se guarda tal cual, sin limitar a 0 como hace hit.
        """
        self.reserve = value
