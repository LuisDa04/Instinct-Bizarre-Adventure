from instinct.compiler.semantic import ResolvedProgram
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


def test_world_starts_with_full_base_terrain() -> None:
    world = World(3, 2, grass())
    for y in range(2):
        for x in range(3):
            terrain = world.terrain_at(x, y)
            assert terrain is not None
            assert terrain.name == "Grass"
            assert terrain.reserve == 100


def test_cells_have_independent_reserves() -> None:
    world = World(2, 1, grass())
    first = world.terrain_at(0, 0)
    second = world.terrain_at(1, 0)
    assert first is not None and second is not None
    first.hit(40)
    assert first.reserve == 60
    assert second.reserve == 100


def test_in_bounds_corners() -> None:
    world = World(3, 2, grass())
    assert world.in_bounds(0, 0)
    assert world.in_bounds(2, 1)
    assert not world.in_bounds(3, 0)
    assert not world.in_bounds(0, 2)
    assert not world.in_bounds(-1, 0)
    assert not world.in_bounds(0, -1)


def test_out_of_bounds_queries_return_none() -> None:
    world = World(2, 2, grass())
    assert world.terrain_at(5, 5) is None
    assert world.object_at(5, 5) is None
    assert world.creature_at(5, 5) is None


def test_empty_cell_is_walkable() -> None:
    world = World(2, 2, grass())
    assert world.walkable(0, 0)


def test_cell_with_object_is_not_walkable() -> None:
    world = World(2, 2, grass())
    assert world.place_object(0, 0, rock())
    assert not world.walkable(0, 0)


def test_cell_with_creature_is_not_walkable() -> None:
    world = World(2, 2, grass())
    assert world.place_creature(0, 0, hobbit())
    assert not world.walkable(0, 0)


def test_out_of_bounds_is_not_walkable() -> None:
    world = World(2, 2, grass())
    assert not world.walkable(9, 9)


def test_place_terrain_replaces_terrain() -> None:
    world = World(2, 2, grass())
    lava = Terrain("Lava", "~", 50, 0)
    assert world.place_terrain(1, 1, lava)
    assert world.terrain_at(1, 1) is not None
    assert world.terrain_at(1, 1).name == "Lava"
    assert world.terrain_at(1, 1).reserve == 50
    assert not world.place_terrain(9, 9, lava)


def test_place_object_clones_prototype() -> None:
    world = World(2, 1, grass())
    prototype = rock()
    assert world.place_object(0, 0, prototype)
    assert world.place_object(1, 0, prototype)
    first = world.object_at(0, 0)
    second = world.object_at(1, 0)
    assert first is not None and second is not None
    assert first is not prototype
    first.hit(30)
    assert first.reserve == 70
    assert second.reserve == 100


def test_place_object_over_creature_fails() -> None:
    world = World(2, 2, grass())
    assert world.place_creature(0, 0, hobbit())
    assert not world.place_object(0, 0, rock())
    assert world.object_at(0, 0) is None
    assert not world.place_object(9, 9, rock())


def test_remove_object_returns_and_clears() -> None:
    world = World(2, 2, grass())
    assert world.place_object(0, 0, rock())
    removed = world.remove_object(0, 0)
    assert removed is not None
    assert removed.name == "Rock"
    assert world.object_at(0, 0) is None
    assert world.walkable(0, 0)
    assert world.remove_object(1, 1) is None
    assert world.remove_object(9, 9) is None


def test_place_creature_sets_position() -> None:
    world = World(3, 3, grass())
    creature = hobbit()
    assert world.place_creature(2, 1, creature)
    assert (creature.x, creature.y) == (2, 1)
    assert world.creature_at(2, 1) is creature


def test_place_creature_over_object_fails() -> None:
    world = World(2, 2, grass())
    assert world.place_object(0, 0, rock())
    assert not world.place_creature(0, 0, hobbit())
    assert world.creature_at(0, 0) is None


def test_place_creature_over_creature_fails() -> None:
    world = World(2, 2, grass())
    assert world.place_creature(0, 0, hobbit())
    assert not world.place_creature(0, 0, hobbit("Other"))
    assert world.creature_at(0, 0) is not None
    assert world.creature_at(0, 0).name == "Hobbit"


def test_place_creature_out_of_bounds_fails() -> None:
    world = World(2, 2, grass())
    assert not world.place_creature(9, 9, hobbit())


def test_remove_creature_returns_and_clears() -> None:
    world = World(2, 2, grass())
    placed = hobbit()
    assert world.place_creature(1, 0, placed)
    removed = world.remove_creature(1, 0)
    assert removed is placed
    assert world.creature_at(1, 0) is None
    assert world.walkable(1, 0)
    assert world.remove_creature(0, 0) is None
    assert world.remove_creature(9, 9) is None


def test_creatures_lists_all_placed() -> None:
    world = World(3, 1, grass())
    assert world.place_creature(0, 0, hobbit("A"))
    assert world.place_creature(2, 0, hobbit("B"))
    names = sorted(creature.name for creature in world.creatures())
    assert names == ["A", "B"]


def test_hit_clamps_reserve_at_zero() -> None:
    terrain = grass()
    assert terrain.hit(1000)
    assert terrain.reserve == 0
    assert terrain.hit(1)
    assert terrain.reserve == 0


def test_terrain_hit_never_reports_depleted_below_zero() -> None:
    obj = rock()
    assert not obj.hit(99)
    assert obj.reserve == 1
    assert obj.hit(1)
    assert obj.reserve == 0


def test_terrain_regenerate_caps_at_max() -> None:
    terrain = grass()
    terrain.hit(1)
    terrain.regenerate()
    assert terrain.reserve == 100
    terrain.hit(10)
    terrain.regenerate()
    assert terrain.reserve == 92


def test_creature_health_tracks_reserve() -> None:
    creature = hobbit(health=60)
    assert creature.health == 60
    assert not creature.hit(20)
    assert creature.health == 40
    creature.health += 30
    assert creature.reserve == 70
    assert creature.hit(70)
    assert creature.health == 0


def test_creature_starts_with_age_zero_and_header() -> None:
    creature = hobbit()
    assert creature.age == 0
    assert creature.name == "Hobbit"
    assert creature.faction == "shire"
    assert creature.vision == 5
    assert creature.lifespan == 300
    assert creature.variables == {}
    assert creature.pc == 0


def test_prototypes_start_full() -> None:
    assert grass().reserve == 100
    assert rock().reserve == 100
