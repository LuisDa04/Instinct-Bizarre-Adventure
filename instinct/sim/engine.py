from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from instinct.world.entities import Creature
from instinct.world.rng import Rng
from instinct.world.world import World


@dataclass(frozen=True)
class TickReport:
    tick: int
    deaths: int
    births: int
    order: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class WorldSnapshot:
    tick: int
    width: int
    height: int
    creatures: tuple[tuple[str, str, int, int, int, int], ...]


class Engine:
    def __init__(self, world: World, seed: int = 0) -> None:
        self._world = world
        self._rng = Rng(seed)
        self._tick = 0
        self._pending: list[Creature] = []
        self._turn_runner: Callable[[Creature], bool] | None = None

    @property
    def tick(self) -> int:
        return self._tick

    def set_turn_runner(self, runner: Callable[[Creature], bool] | None) -> None:
        self._turn_runner = runner

    def queue_newborn(self, creature: Creature) -> None:
        self._pending.append(creature)

    def state(self) -> WorldSnapshot:
        entries: list[tuple[str, str, int, int, int, int]] = []
        for creature in self._world.creatures():
            entries.append(
                (
                    creature.name,
                    creature.faction,
                    creature.x,
                    creature.y,
                    creature.health,
                    creature.age,
                )
            )
        return WorldSnapshot(
            tick=self._tick,
            width=self._world.width,
            height=self._world.height,
            creatures=tuple(entries),
        )

    def step(self) -> TickReport:
        pending_ids = {id(creature) for creature in self._pending}
        snapshot = [
            creature
            for creature in self._world.creatures()
            if id(creature) not in pending_ids
        ]
        self._rng.shuffle(snapshot)
        order = tuple((creature.x, creature.y) for creature in snapshot)
        for creature in snapshot:
            if self._world.creature_at(creature.x, creature.y) is not creature:
                continue
            if creature.wait_remaining > 0:
                creature.wait_remaining -= 1
                continue
            if self._turn_runner is not None:
                self._turn_runner(creature)
        after_turns = list(self._world.creatures())
        for creature in after_turns:
            creature.health -= 1
            creature.age = max(0, creature.age + 1)
        deaths = 0
        for creature in after_turns:
            if creature.health <= 0 or creature.age >= creature.lifespan:
                if self._world.creature_at(creature.x, creature.y) is creature:
                    self._world.remove_creature(creature.x, creature.y)
                    deaths += 1
                else:
                    missing = self._find_creature(creature)
                    if missing is not None:
                        self._world.remove_creature(missing[0], missing[1])
                        deaths += 1
        for y in range(self._world.height):
            for x in range(self._world.width):
                terrain = self._world.terrain_at(x, y)
                if terrain is not None:
                    terrain.regenerate()
        for y in range(self._world.height):
            for x in range(self._world.width):
                obj = self._world.object_at(x, y)
                if obj is not None and obj.reserve <= 0:
                    self._world.remove_object(x, y)
        births = len(self._pending)
        self._pending.clear()
        self._tick += 1
        return TickReport(
            tick=self._tick, deaths=deaths, births=births, order=order
        )

    def _find_creature(self, target: Creature) -> tuple[int, int] | None:
        for y in range(self._world.height):
            for x in range(self._world.width):
                if self._world.creature_at(x, y) is target:
                    return (x, y)
        return None
