"""Pruebas de las siete acciones a través del intérprete."""

from __future__ import annotations

from instinct.compiler.lexer import scan
from instinct.compiler.parser import parse
from instinct.compiler.semantic import ResolvedProgram, resolve
from instinct.lang.interpreter import Interpreter
from instinct.sim.engine import Engine
from instinct.world.entities import Creature, Terrain, WorldObject
from instinct.world.world import World

HEADER = "creature Uruk\nfaction isengard\nhealth 80\nvision 6\nlifespan 400\n"

ANNEX_URUK = """\
creature Uruk
faction isengard
health 80
vision 6
lifespan 400

start:
    if health < 20 goto flee
    if enemy_dist == 1 goto bite
    if enemy_dist > 0 goto hunt
    if health > 70 and allies_near < 2 goto breed
    if allies_near > 3 goto celebrate
wander:
    move(random % 3 - 1, random % 3 - 1, 1)
    goto start

bite:
    consume(enemy_dx, enemy_dy, 15, 15)
    goto start

hunt:
    move(enemy_dx, enemy_dy, 2)
    goto start

flee:
    move(-enemy_dx, -enemy_dy, 3)
    goto start

breed:
    # bred in the pits of Isengard
    if see(x, y + 1) != GROUND goto wander
    reproduce(0, 1, 30)
    goto start

celebrate:
    say("meat is back on the menu")
    roar("we are the fighting Uruk-hai")
    goto start
"""

ANNEX_HOBBIT = """\
creature Hobbit
faction shire
health 60
vision 5
lifespan 300

start:
    if enemy_dist >= 0 goto flee
    if health > 45 and total_allies < 20 goto breed
    if reserve_here > 0 and health < 80 goto second_breakfast
    if ally_dist > 1 goto go_ally
    wait(1)
    goto start
flee:
    say("they are taking us to Isengard")
    move(-enemy_dx, -enemy_dy, 2)
    goto start
second_breakfast:
    consume(0, 0, 10, 10)
    goto start
go_ally:
    move(ally_dx, ally_dy, 1)
    goto start
breed:
    if see(x + 1, y) == GROUND goto breed_right
    if see(x - 1, y) == GROUND goto breed_left
    wait(1)
    goto start
breed_right:
    reproduce(1, 0, 20)
    goto start
breed_left:
    reproduce(-1, 0, 20)
    goto start
"""

ANNEX_ENT = """\
creature Ent
faction fangorn
health 150
vision 4
lifespan 1000

start:
    home_x = x
    home_y = y
watch:
    if enemy_dist == 1 goto hit
    if enemies_near > 0 and roars_near == 0 goto warn
    if x != home_x or y != home_y goto go_home
    if health < 150 goto roots
    wait(1)
    goto watch
hit:
    attack(enemy_dx, enemy_dy, 12)
    goto watch
warn:
    roar("hoom, hom, do not be hasty")
    goto watch
roots:
    consume(0, 0, 3, 3)
    goto watch
go_home:
    dx = (home_x > x) - (home_x < x)
    dy = (home_y > y) - (home_y < y)
    move(dx, dy, 1)
    goto watch
"""

ANNEX_DWARF = """\
creature Dwarf
faction erebor
health 100
vision 3
lifespan 600

start:
    if last_roar == "khazad ai-menu" goto rescue
    if object_dist == 1 and health < 100 goto mine
    dx = random % 3 - 1
    dy = random % 3 - 1
    steps = 0
walk:
    if steps >= 5 goto start
    if enemy_dist == 1 goto shout
    move(dx, dy, 1)
    steps = steps + 1
    goto walk
mine:
    # never too greedily and too deep
    if name(x + object_dx, y + object_dy) != "Rock" goto start
    consume(object_dx, object_dy, 20, 20)
    goto start
shout:
    roar("khazad ai-menu")
    goto start
rescue:
    say("and my axe")
    move(ally_dx, ally_dy, 2)
    goto start
"""


def compile_body(body: str) -> ResolvedProgram:
    parsed = parse(scan(HEADER + "start:\n" + body).tokens)
    assert parsed.errors == []
    assert parsed.program is not None
    result = resolve(parsed.program)
    assert result.errors == []
    assert result.resolved is not None
    return result.resolved


def compile_file(source: str) -> ResolvedProgram:
    parsed = parse(scan(source).tokens)
    assert parsed.errors == []
    assert parsed.program is not None
    result = resolve(parsed.program)
    assert result.errors == []
    assert result.resolved is not None
    return result.resolved


def grass() -> Terrain:
    return Terrain("Grass", ".", 100, 2)


def rock() -> WorldObject:
    return WorldObject("Rock", "#", 100)


def make_world(program: ResolvedProgram, x: int = 2, y: int = 2) -> tuple[World, Creature]:
    world = World(5, 5, grass())
    creature = Creature(program)
    assert world.place_creature(x, y, creature)
    return world, creature


def turn(
    world: World, creature: Creature, seed: int = 1, log: list[str] | None = None
) -> Engine:
    engine = Engine(world, seed=seed)
    Interpreter(world, engine, log=log.append if log is not None else None).run_turn(
        creature
    )
    return engine


def wire(world: World, seed: int = 1) -> Engine:
    engine = Engine(world, seed=seed)
    engine.set_turn_runner(Interpreter(world, engine).run_turn)
    return engine


def test_move_advances_up_to_speed() -> None:
    world, creature = make_world(compile_body("    move(1, 0, 2)\n"))
    turn(world, creature)
    assert (creature.x, creature.y) == (4, 2)
    assert creature.pc == 2


def test_move_stops_before_object() -> None:
    world, creature = make_world(compile_body("    move(1, 0, 3)\n"))
    assert world.place_object(4, 2, rock())
    turn(world, creature)
    assert (creature.x, creature.y) == (3, 2)


def test_move_stops_before_creature() -> None:
    world, creature = make_world(compile_body("    move(1, 0, 3)\n"))
    blocker = Creature(compile_body("    wait(1)\n"))
    assert world.place_creature(4, 2, blocker)
    turn(world, creature)
    assert (creature.x, creature.y) == (3, 2)


def test_move_stops_at_map_border() -> None:
    world, creature = make_world(compile_body("    move(1, 0, 9)\n"))
    turn(world, creature)
    assert (creature.x, creature.y) == (4, 2)


def test_move_without_steps_stays_in_place() -> None:
    for body in ("    move(0, 0, 5)\n", "    move(1, 0, 0)\n", "    move(1, 0, -3)\n"):
        world, creature = make_world(compile_body(body))
        turn(world, creature)
        assert (creature.x, creature.y) == (2, 2), body
        assert creature.pc == 2, body


def test_attack_damages_creature() -> None:
    world, creature = make_world(compile_body("    attack(1, 0, 10)\n"))
    victim = Creature(compile_body("    wait(1)\n"))
    assert world.place_creature(3, 2, victim)
    turn(world, creature)
    assert victim.health == 70


def test_attack_damages_object() -> None:
    world, creature = make_world(compile_body("    attack(1, 0, 10)\n"))
    assert world.place_object(3, 2, rock())
    obj = world.object_at(3, 2)
    assert obj is not None
    turn(world, creature)
    assert obj.reserve == 90


def test_attack_damages_terrain() -> None:
    world, creature = make_world(compile_body("    attack(1, 0, 5)\n"))
    terrain = world.terrain_at(3, 2)
    assert terrain is not None
    turn(world, creature)
    assert terrain.reserve == 95


def test_attack_zero_direction_hits_own_terrain() -> None:
    world, creature = make_world(compile_body("    attack(0, 0, 7)\n"))
    terrain = world.terrain_at(2, 2)
    assert terrain is not None
    turn(world, creature)
    assert terrain.reserve == 93
    assert creature.health == 80


def test_attack_outside_map_does_nothing() -> None:
    world, creature = make_world(compile_body("    attack(1, 0, 5)\n"), x=4, y=4)
    turn(world, creature)
    assert creature.pc == 2
    assert creature.health == 80


def test_attack_kills_in_place_and_counts_death() -> None:
    world, attacker = make_world(compile_body("    attack(1, 0, 15)\n"))
    victim = Creature(compile_body("    wait(1)\n"))
    assert world.place_creature(3, 2, victim)
    victim.health = 10
    engine = wire(world)
    report = engine.step()
    assert world.creature_at(3, 2) is None
    assert report.deaths == 1


def test_attack_negative_damage_heals_creature() -> None:
    world, creature = make_world(compile_body("    attack(1, 0, -10)\n"))
    victim = Creature(compile_body("    wait(1)\n"))
    assert world.place_creature(3, 2, victim)
    turn(world, creature)
    assert victim.health == 90


def test_attack_negative_damage_is_capped_on_terrain() -> None:
    world, creature = make_world(compile_body("    attack(1, 0, -50)\n"))
    terrain = world.terrain_at(3, 2)
    assert terrain is not None
    terrain.hit(30)
    turn(world, creature)
    assert terrain.reserve == 100


def test_consume_damages_creature_and_heals() -> None:
    world, creature = make_world(compile_body("    consume(1, 0, 10, 15)\n"))
    victim = Creature(compile_body("    wait(1)\n"))
    assert world.place_creature(3, 2, victim)
    turn(world, creature)
    assert victim.health == 70
    assert creature.health == 95


def test_consume_grass_heals_without_cap() -> None:
    world, creature = make_world(compile_body("    consume(0, 0, 5, 100)\n"))
    terrain = world.terrain_at(2, 2)
    assert terrain is not None
    turn(world, creature)
    assert terrain.reserve == 95
    assert creature.health == 180


def test_consume_outside_map_does_nothing() -> None:
    world, creature = make_world(compile_body("    consume(1, 0, 10, 15)\n"), x=4, y=4)
    turn(world, creature)
    assert creature.health == 80
    assert creature.pc == 2


def test_consume_negative_heal_kills_in_place() -> None:
    world, creature = make_world(compile_body("    consume(1, 0, 1, -15)\n"))
    creature.health = 10
    engine = wire(world)
    report = engine.step()
    assert world.creature_at(2, 2) is None
    assert report.deaths == 1


def test_reproduce_places_child_that_acts_next_tick() -> None:
    world, mother = make_world(compile_body("    reproduce(1, 0, 20)\n"))
    engine = wire(world)
    first = engine.step()
    child = world.creature_at(3, 2)
    assert child is not None and child is not mother
    assert child.program is mother.program
    assert child.name == "Uruk"
    assert child.health == 19  # nace con 20 y el fin de tick cobra 1
    assert child.age == 1
    assert child.variables == {}
    assert child.pc == child.program.labels["start"]
    assert mother.health == 59  # 80 menos 20 por la cría, menos 1 del tick
    assert (first.births, first.deaths) == (1, 0)
    second = engine.step()
    assert second.births == 0  # la cría tiene 19, no más de 20: no puede parir
    assert world.creature_at(4, 2) is None
    assert child.health == 18
    assert child.age == 2


def test_reproduce_aborts_when_mother_cannot_pay() -> None:
    world, mother = make_world(compile_body("    reproduce(1, 0, 80)\n"))
    engine = wire(world)
    report = engine.step()
    assert world.creature_at(3, 2) is None
    assert mother.health == 79  # aborto natural: solo el coste del tick
    assert report.births == 0


def test_reproduce_aborts_without_viable_birth() -> None:
    world, mother = make_world(compile_body("    reproduce(1, 0, 20)\n"))
    assert world.place_object(3, 2, rock())
    turn(world, mother)
    assert world.creature_at(3, 2) is None
    assert mother.health == 80

    blocked_world, blocker = make_world(compile_body("    reproduce(1, 0, 20)\n"))
    squatter = Creature(compile_body("    wait(1)\n"))
    assert blocked_world.place_creature(3, 2, squatter)
    turn(blocked_world, blocker)
    assert list(blocked_world.creatures()) == [blocker, squatter]

    center_world, center = make_world(compile_body("    reproduce(0, 0, 20)\n"))
    turn(center_world, center)
    assert list(center_world.creatures()) == [center]

    poor_world, poor = make_world(compile_body("    reproduce(1, 0, 0)\n"))
    turn(poor_world, poor)
    assert list(poor_world.creatures()) == [poor]
    assert poor.health == 80

    edge_world, edge = make_world(compile_body("    reproduce(1, 0, 20)\n"), x=4, y=4)
    turn(edge_world, edge)
    assert list(edge_world.creatures()) == [edge]


def test_roar_is_heard_next_tick() -> None:
    world, creature = make_world(compile_body("    roar(\"AWOO\")\n"))
    listener = Creature(
        compile_body("    r = roars_near\n    m = last_roar\n    wait(1)\n    goto start\n")
    )
    assert world.place_creature(0, 0, listener)
    engine = wire(world)
    engine.step()
    assert listener.variables["r"] == 0
    engine.step()
    assert listener.variables["r"] == 1
    assert listener.variables["m"] == "AWOO"


def test_roar_logs_text_and_numbers() -> None:
    world, creature = make_world(compile_body("    roar(42)\n"))
    log: list[str] = []
    turn(world, creature, log=log)
    assert log == ["Uruk ruge: 42"]
    other_world, other = make_world(compile_body("    roar(\"menacing\")\n"))
    other_log: list[str] = []
    turn(other_world, other, log=other_log)
    assert other_log == ["Uruk ruge: menacing"]
    assert other.pc == 2


def test_say_is_free_and_logs() -> None:
    world, creature = make_world(
        compile_body("    say(\"hola\")\n    say(\"chao\")\n    wait(1)\n")
    )
    log: list[str] = []
    turn(world, creature, log=log)
    assert log == ["Uruk dice: hola", "Uruk dice: chao"]
    assert creature.pc == 4  # llegó al wait dentro del mismo turno


def test_say_accepts_numbers() -> None:
    world, creature = make_world(compile_body("    say(7)\n    wait(1)\n"))
    log: list[str] = []
    turn(world, creature, log=log)
    assert log == ["Uruk dice: 7"]


def test_say_without_log_discards_text() -> None:
    world, creature = make_world(
        compile_body("    say(\"nadie me oye\")\n    wait(1)\n")
    )
    turn(world, creature)
    assert creature.pc == 3


def test_action_validation_is_ictus() -> None:
    cases = [
        ("    move(2, 0, 1)\n", "la acción 'move' espera dx y dy en {-1, 0, 1}"),
        ("    move(\"a\", 0, 1)\n", "la acción 'move' espera un número"),
        ("    move(1, 0, \"a\")\n", "la acción 'move' espera un número"),
        ("    attack(2, 0, 5)\n", "la acción 'attack' espera dx y dy en {-1, 0, 1}"),
        ("    attack(1, 0, \"a\")\n", "la acción 'attack' espera un número"),
        ("    consume(1, 2, 5, 5)\n", "la acción 'consume' espera dx y dy en {-1, 0, 1}"),
        ("    consume(1, 0, 5, \"a\")\n", "la acción 'consume' espera un número"),
        ("    reproduce(0, 5, 20)\n", "la acción 'reproduce' espera dx y dy en {-1, 0, 1}"),
        ("    reproduce(1, 0, \"a\")\n", "la acción 'reproduce' espera un número"),
    ]
    for body, message in cases:
        world, creature = make_world(compile_body(body))
        log: list[str] = []
        turn(world, creature, log=log)
        assert world.creature_at(2, 2) is None, body
        assert log == ["Uruk: línea 7: " + message], body


def test_annex_examples_run_together() -> None:
    world = World(10, 10, grass())
    species = [
        compile_file(source)
        for source in (ANNEX_URUK, ANNEX_HOBBIT, ANNEX_ENT, ANNEX_DWARF)
    ]
    spots = [(4, 4), (6, 6), (0, 0), (9, 0)]
    for program, (x, y) in zip(species, spots):
        assert world.place_creature(x, y, Creature(program))
    for x, y in ((2, 2), (7, 3), (3, 8)):
        assert world.place_object(x, y, rock())
    engine = wire(world, seed=5)
    for _ in range(50):
        engine.step()
    assert engine.tick == 50
    assert sum(1 for _ in world.creatures()) >= 1
