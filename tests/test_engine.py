from __future__ import annotations

from instinct.compiler.semantic import ResolvedProgram
from instinct.sim.engine import Engine
from instinct.world.entities import Creature, Terrain, WorldObject
from instinct.world.world import World


def grass() -> Terrain:
    return Terrain("Grass", ".", 100, 2)


def rock() -> WorldObject:
    return WorldObject("Rock", "#", 100)


def hobbit(name: str = "Hobbit", health: int = 60) -> Creature:
    program = ResolvedProgram(
        name=name,
        faction="shire",
        health=health,
        vision=5,
        lifespan=300,
        body=[],
        labels={"start": 0},
        line=1,
    )
    return Creature(program)


def make_program(name: str, health: int, lifespan: int) -> ResolvedProgram:
    return ResolvedProgram(
        name=name,
        faction="shire",
        health=health,
        vision=5,
        lifespan=lifespan,
        body=[],
        labels={"start": 0},
        line=1,
    )


def build_twin_world() -> World:
    world = World(3, 2, grass())
    first = Creature(make_program("A", 60, 300))
    second = Creature(make_program("B", 60, 300))
    third = Creature(make_program("C", 60, 300))
    assert world.place_creature(0, 0, first)
    assert world.place_creature(1, 0, second)
    assert world.place_creature(2, 0, third)
    return world


def test_tick_costs_one_health_and_one_age() -> None:
    world = World(2, 2, grass())
    creature = hobbit()
    assert world.place_creature(0, 0, creature)
    engine = Engine(world, seed=0)
    report = engine.step()
    assert report.tick == 1
    assert engine.tick == 1
    assert report.deaths == 0
    assert report.births == 0
    assert creature.health == 59
    assert creature.age == 1
    assert world.creature_at(0, 0) is creature


def test_age_never_goes_below_zero() -> None:
    world = World(2, 2, grass())
    creature = hobbit()
    assert world.place_creature(0, 0, creature)
    creature.age = -5
    engine = Engine(world, seed=0)
    engine.step()
    assert creature.age == 0


def test_death_by_zero_health_clears_cell() -> None:
    world = World(2, 2, grass())
    creature = hobbit(health=1)
    assert world.place_creature(0, 0, creature)
    engine = Engine(world, seed=0)
    report = engine.step()
    assert report.deaths == 1
    assert world.creature_at(0, 0) is None


def test_death_by_lifespan_clears_cell() -> None:
    world = World(2, 2, grass())
    creature = Creature(make_program("Hobbit", 60, 1))
    assert world.place_creature(0, 0, creature)
    engine = Engine(world, seed=0)
    report = engine.step()
    assert report.deaths == 1
    assert world.creature_at(0, 0) is None


def test_terrain_regenerates_capped() -> None:
    world = World(2, 2, grass())
    engine = Engine(world, seed=0)
    damaged = world.terrain_at(0, 0)
    intact = world.terrain_at(1, 0)
    assert damaged is not None and intact is not None
    damaged.hit(10)
    assert damaged.reserve == 90
    engine.step()
    assert world.terrain_at(0, 0) is not None
    assert world.terrain_at(0, 0).reserve == 92
    assert world.terrain_at(1, 0) is not None
    assert world.terrain_at(1, 0).reserve == 100


def test_depleted_object_disappears() -> None:
    world = World(2, 2, grass())
    assert world.place_object(0, 0, rock())
    target = world.object_at(0, 0)
    assert target is not None
    target.hit(100)
    assert target.reserve == 0
    engine = Engine(world, seed=0)
    engine.step()
    assert world.object_at(0, 0) is None


def test_sleeping_creature_skips_turn_but_ages() -> None:
    world = World(2, 2, grass())
    creature = hobbit()
    assert world.place_creature(0, 0, creature)
    creature.wait_remaining = 2
    engine = Engine(world, seed=0)
    calls: list[Creature] = []
    engine.set_turn_runner(lambda c: calls.append(c) or False)
    engine.step()
    assert calls == []
    assert creature.wait_remaining == 1
    assert creature.health == 59
    assert creature.age == 1
    assert world.creature_at(0, 0) is creature


def test_newborn_waits_next_tick() -> None:
    world = World(2, 2, grass())
    mother = Creature(make_program("Mother", 60, 300))
    child = Creature(make_program("Child", 60, 300))
    assert world.place_creature(0, 0, mother)
    assert world.place_creature(1, 0, child)
    engine = Engine(world, seed=0)
    engine.queue_newborn(child)
    calls: list[Creature] = []
    engine.set_turn_runner(lambda c: calls.append(c) or False)
    report = engine.step()
    assert report.births == 1
    assert calls == [mother]
    assert child.health == 59
    calls.clear()
    report_next = engine.step()
    assert report_next.births == 0
    assert mother in calls
    assert child in calls
    assert len(calls) == 2


def test_same_seed_same_order_and_trace() -> None:
    first_world = build_twin_world()
    second_world = build_twin_world()
    first_engine = Engine(first_world, seed=7)
    second_engine = Engine(second_world, seed=7)
    for _ in range(5):
        first_report = first_engine.step()
        second_report = second_engine.step()
        assert first_report.order == second_report.order
        assert first_report.tick == second_report.tick
    first_stats = sorted((c.health, c.age) for c in first_world.creatures())
    second_stats = sorted((c.health, c.age) for c in second_world.creatures())
    assert first_stats == second_stats
    assert first_stats == [(55, 5), (55, 5), (55, 5)]


def test_different_seeds_can_diverge() -> None:
    orders_a: list[tuple[tuple[int, int], ...]] = []
    orders_b: list[tuple[tuple[int, int], ...]] = []
    world_a = World(3, 1, grass())
    assert world_a.place_creature(0, 0, Creature(make_program("A", 60, 300)))
    assert world_a.place_creature(1, 0, Creature(make_program("B", 60, 300)))
    assert world_a.place_creature(2, 0, Creature(make_program("C", 60, 300)))
    world_b = World(3, 1, grass())
    assert world_b.place_creature(0, 0, Creature(make_program("A", 60, 300)))
    assert world_b.place_creature(1, 0, Creature(make_program("B", 60, 300)))
    assert world_b.place_creature(2, 0, Creature(make_program("C", 60, 300)))
    engine_a = Engine(world_a, seed=0)
    engine_b = Engine(world_b, seed=999)
    for _ in range(5):
        orders_a.append(engine_a.step().order)
        orders_b.append(engine_b.step().order)
    assert any(a != b for a, b in zip(orders_a, orders_b))


def test_state_does_not_expose_mutable_world() -> None:
    world = World(2, 2, grass())
    creature = hobbit()
    assert world.place_creature(0, 0, creature)
    engine = Engine(world, seed=0)
    snapshot = engine.state()
    assert snapshot.tick == 0
    assert snapshot.width == 2
    assert snapshot.height == 2
    assert not hasattr(snapshot, "_cells")
    assert not hasattr(snapshot, "rng")
    assert not hasattr(snapshot, "_random")
    before = list(world.creatures())
    assert len(before) == 1
    mutable = list(snapshot.creatures)
    mutable.clear()
    mutable.append(("Fake", "shire", 9, 9, 1, 1))
    assert len(list(world.creatures())) == 1
    assert world.creature_at(0, 0) is creature
    first = snapshot.creatures[0]
    assert first == ("Hobbit", "shire", 0, 0, 60, 0)
    engine.step()
    assert snapshot.tick == 0
    assert snapshot.creatures[0] == ("Hobbit", "shire", 0, 0, 60, 0)


def test_wait_remaining_starts_at_zero() -> None:
    creature = hobbit()
    assert creature.wait_remaining == 0


def test_newborn_queued_mid_tick_counts_and_waits() -> None:
    world = World(3, 1, grass())
    mother = Creature(make_program("Mother", 60, 300))
    assert world.place_creature(0, 0, mother)
    engine = Engine(world, seed=0)
    child = Creature(make_program("Child", 60, 300))
    calls: list[Creature] = []

    def runner(creature: Creature) -> bool:
        calls.append(creature)
        if creature is mother and world.creature_at(2, 0) is None:
            assert world.place_creature(2, 0, child)
            engine.queue_newborn(child)
        return True

    engine.set_turn_runner(runner)
    report = engine.step()
    assert report.births == 1
    assert calls == [mother]
    assert child.health == 59
    calls.clear()
    engine.step()
    assert mother in calls
    assert child in calls
