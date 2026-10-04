from __future__ import annotations

from ..compiler.semantic import ResolvedProgram


class Entity:
    name: str
    walkable: bool
    reserve: int

    def hit(self, damage: int) -> bool:
        self.reserve = max(0, self.reserve - damage)
        return self.reserve == 0


class Terrain(Entity):
    walkable = True

    def __init__(self, name: str, char: str, resource_max: int, regen: int) -> None:
        self.name = name
        self.char = char
        self.resource_max = resource_max
        self.regen = regen
        self.reserve = resource_max

    def regenerate(self) -> None:
        self.reserve = min(self.resource_max, self.reserve + self.regen)

    def clone(self) -> Terrain:
        return Terrain(self.name, self.char, self.resource_max, self.regen)


class WorldObject(Entity):
    walkable = False

    def __init__(self, name: str, char: str, resource_max: int) -> None:
        self.name = name
        self.char = char
        self.resource_max = resource_max
        self.reserve = resource_max

    def clone(self) -> WorldObject:
        return WorldObject(self.name, self.char, self.resource_max)


class Creature(Entity):
    walkable = False

    def __init__(self, program: ResolvedProgram, x: int = 0, y: int = 0) -> None:
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

    @property
    def health(self) -> int:
        return self.reserve

    @health.setter
    def health(self, value: int) -> None:
        self.reserve = value
