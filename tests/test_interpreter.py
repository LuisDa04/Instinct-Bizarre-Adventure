from __future__ import annotations

from instinct.compiler.lexer import scan
from instinct.compiler.parser import parse
from instinct.compiler.semantic import ResolvedProgram, resolve
from instinct.lang.interpreter import MAX_LINES, Interpreter
from instinct.sim.engine import Engine
from instinct.world.entities import Creature, Terrain
from instinct.world.world import World

HEADER = "creature Uruk\nfaction isengard\nhealth 80\nvision 6\nlifespan 400\n"


def compile_body(body: str) -> ResolvedProgram:
    parsed = parse(scan(HEADER + "start:\n" + body).tokens)
    assert parsed.errors == []
    assert parsed.program is not None
    result = resolve(parsed.program)
    assert result.errors == []
    assert result.resolved is not None
    return result.resolved


def grass() -> Terrain:
    return Terrain("Grass", ".", 100, 2)


def make_world(program: ResolvedProgram, x: int = 2, y: int = 2) -> tuple[World, Creature]:
    world = World(5, 5, grass())
    creature = Creature(program)
    assert world.place_creature(x, y, creature)
    return world, creature


def turn(
    world: World, creature: Creature, seed: int = 1, log: list[str] | None = None
) -> Interpreter:
    interp = Interpreter(
        world, Engine(world, seed=seed), log=log.append if log is not None else None
    )
    interp.run_turn(creature)
    return interp


def test_creature_starts_at_start_label() -> None:
    parsed = parse(scan(HEADER + "wander:\n    wait(1)\nstart:\n    wait(1)\n").tokens)
    assert parsed.errors == []
    assert parsed.program is not None
    result = resolve(parsed.program)
    assert result.errors == []
    assert result.resolved is not None
    program = result.resolved
    _, creature = make_world(program)
    assert creature.pc == program.labels["start"] == 2


def test_wait_sets_remaining_and_advances_pc() -> None:
    world, creature = make_world(compile_body("    wait(2)\n"))
    turn(world, creature)
    assert creature.wait_remaining == 1
    assert creature.pc == 2


def test_wait_below_one_counts_as_one() -> None:
    world, creature = make_world(compile_body("    wait(0)\n"))
    turn(world, creature)
    assert creature.wait_remaining == 0
    assert creature.pc == 2


def test_eof_wraps_to_start_next_turn() -> None:
    world, creature = make_world(compile_body("    n = 1\n    wait(1)\n"))
    interp = Interpreter(world, Engine(world, seed=1))
    interp.run_turn(creature)
    assert creature.variables["n"] == 1
    assert creature.pc == 3
    interp.run_turn(creature)
    assert creature.pc == 0
    assert creature.variables["n"] == 1
    interp.run_turn(creature)
    assert creature.pc == 3


def test_goto_loop_is_capped() -> None:
    assert MAX_LINES == 100
    world, creature = make_world(compile_body("    goto start\n"))
    turn(world, creature)
    assert creature.pc == 0


def test_hundred_line_accounting() -> None:
    world, creature = make_world(compile_body("    n = 1\nmore:\n    n = n + 1\n    goto more\n"))
    turn(world, creature)
    assert creature.variables["n"] == 34
    assert creature.pc == 4


def test_variables_persist_between_turns() -> None:
    world, creature = make_world(compile_body("    n = 1\n    wait(1)\n    n = n + 1\n    wait(1)\n"))
    interp = Interpreter(world, Engine(world, seed=1))
    interp.run_turn(creature)
    assert creature.variables["n"] == 1
    interp.run_turn(creature)
    assert creature.variables["n"] == 2
    assert creature.pc == 5
    interp.run_turn(creature)
    assert creature.variables["n"] == 2
    assert creature.pc == 0


def test_if_goto_takes_both_branches() -> None:
    body = (
        "    if health < 20 goto flee\n"
        "    n = 1\n"
        "    goto done\n"
        "flee:\n"
        "    n = 2\n"
        "done:\n"
        "    wait(1)\n"
    )
    world, creature = make_world(compile_body(body))
    turn(world, creature)
    assert creature.variables["n"] == 1
    weak_world, weak = make_world(compile_body(body))
    weak.health = 10
    turn(weak_world, weak)
    assert weak.variables["n"] == 2


def test_arithmetic_and_integer_division() -> None:
    world, creature = make_world(
        compile_body("    a = 2 + 3 * 4\n    b = (2 + 3) * 4\n    c = 7 / 2\n    d = -7 / 2\n    e = 7 % 3\n    wait(1)\n")
    )
    turn(world, creature)
    assert creature.variables["a"] == 14
    assert creature.variables["b"] == 20
    assert creature.variables["c"] == 3
    assert creature.variables["d"] == -4
    assert creature.variables["e"] == 1


def test_comparisons_return_one_or_zero() -> None:
    world, creature = make_world(
        compile_body("    a = 2 < 3\n    b = 2 >= 3\n    c = 2 == 2\n    d = 2 != 2\n    wait(1)\n")
    )
    turn(world, creature)
    assert (creature.variables["a"], creature.variables["b"]) == (1, 0)
    assert (creature.variables["c"], creature.variables["d"]) == (1, 0)


def test_text_only_admits_equality() -> None:
    world, creature = make_world(compile_body('    a = "x" == "x"\n    b = "x" != "y"\n    wait(1)\n'))
    turn(world, creature)
    assert (creature.variables["a"], creature.variables["b"]) == (1, 1)


def test_logical_results_and_short_circuit() -> None:
    world, creature = make_world(
        compile_body(
            "    a = 0 and nunca\n"
            "    b = 1 or nunca\n"
            "    c = 1 and \"x\"\n"
            "    d = 0 or \"\"\n"
            "    e = not \"\"\n"
            "    f = not \"x\"\n"
            "    g = not 0\n"
            "    wait(1)\n"
        )
    )
    turn(world, creature)
    assert creature.variables["a"] == 0
    assert creature.variables["b"] == 1
    assert creature.variables["c"] == 1
    assert creature.variables["d"] == 0
    assert creature.variables["e"] == 1
    assert creature.variables["f"] == 0
    assert creature.variables["g"] == 1


def test_unary_minus() -> None:
    world, creature = make_world(compile_body("    a = -3 * 2\n    b = -health\n    wait(1)\n"))
    turn(world, creature)
    assert creature.variables["a"] == -6
    assert creature.variables["b"] == -80


def test_annex_sign_idiom() -> None:
    world, creature = make_world(
        compile_body("    home_x = x + 2\n    dx = (home_x > x) - (home_x < x)\n    wait(1)\n")
    )
    turn(world, creature)
    assert creature.variables["dx"] == 1


def test_random_stays_in_range() -> None:
    world, creature = make_world(compile_body("    n = random\n    wait(1)\n"))
    interp = Interpreter(world, Engine(world, seed=9))
    for _ in range(3):
        interp.run_turn(creature)
        assert 0 <= creature.variables["n"] <= 99


def test_self_perceptions() -> None:
    world, creature = make_world(
        compile_body(
            "    a = health\n"
            "    b = age\n"
            "    c = x\n"
            "    d = y\n"
            "    e = species\n"
            "    f = faction\n"
            "    g = vision\n"
            "    h = lifespan\n"
            "    i = tick\n"
            "    j = width\n"
            "    k = height\n"
            "    l = terrain_here\n"
            "    m = reserve_here\n"
            "    wait(1)\n"
        )
    )
    creature.age = 4
    turn(world, creature)
    assert creature.variables["a"] == 80
    assert creature.variables["b"] == 4
    assert (creature.variables["c"], creature.variables["d"]) == (2, 2)
    assert (creature.variables["e"], creature.variables["f"]) == ("Uruk", "isengard")
    assert creature.variables["g"] == 6
    assert creature.variables["h"] == 400
    assert creature.variables["i"] == 0
    assert (creature.variables["j"], creature.variables["k"]) == (5, 5)
    assert creature.variables["l"] == "Grass"
    assert creature.variables["m"] == 100


def test_enemy_triple_drives_branch() -> None:
    body = (
        "    if enemy_dist == 1 goto found\n"
        "    n = 0\n"
        "    goto done\n"
        "found:\n"
        "    n = enemy_dx * 10 + enemy_dy\n"
        "done:\n"
        "    wait(1)\n"
    )
    world, creature = make_world(compile_body(body))
    foe = Creature(compile_body("    wait(1)\n"))
    foe.faction = "mordor"
    assert world.place_creature(3, 3, foe)
    turn(world, creature)
    assert creature.variables["n"] == 11
    lone_world, lone = make_world(compile_body(body))
    turn(lone_world, lone)
    assert lone.variables["n"] == 0


def test_see_and_name_in_expressions() -> None:
    world, creature = make_world(compile_body("    a = see(x + 1, y)\n    b = name(x, y)\n    wait(1)\n"))
    ally = Creature(compile_body("    wait(1)\n"))
    assert world.place_creature(3, 2, ally)
    turn(world, creature)
    assert creature.variables["a"] == 2
    assert creature.variables["b"] == "Uruk"


def test_totals_exclude_self() -> None:
    world, creature = make_world(compile_body("    a = total_creatures\n    wait(1)\n"))
    turn(world, creature)
    assert creature.variables["a"] == 0
    other = Creature(compile_body("    wait(1)\n"))
    assert world.place_creature(0, 0, other)
    interp = Interpreter(world, Engine(world, seed=1))
    interp.run_turn(creature)
    interp.run_turn(creature)
    assert creature.variables["a"] == 1


def test_roars_are_heard_next_tick() -> None:
    world, creature = make_world(compile_body("    r = roars_near\n    m = last_roar\n    wait(1)\n"))
    engine = Engine(world, seed=7)
    interp = Interpreter(world, engine)
    interp.run_turn(creature)
    assert (creature.variables["r"], creature.variables["m"]) == (0, "")
    engine.emit_roar(2, 2, "hola")
    engine.step()
    interp.run_turn(creature)
    interp.run_turn(creature)
    assert (creature.variables["r"], creature.variables["m"]) == (1, "hola")
    engine.step()
    interp.run_turn(creature)
    interp.run_turn(creature)
    assert (creature.variables["r"], creature.variables["m"]) == (0, "")


def test_engine_runs_turns_through_interpreter() -> None:
    world, creature = make_world(compile_body("    wait(2)\n"))
    engine = Engine(world, seed=3)
    engine.set_turn_runner(Interpreter(world, engine).run_turn)
    engine.step()
    assert (creature.wait_remaining, creature.pc) == (1, 2)
    engine.step()
    assert (creature.wait_remaining, creature.pc) == (0, 2)
    engine.step()
    assert (creature.wait_remaining, creature.pc) == (0, 0)
    engine.step()
    assert (creature.wait_remaining, creature.pc) == (1, 2)


def test_newborn_starts_at_start_next_tick() -> None:
    world, mother = make_world(compile_body("    wait(1)\n"))
    engine = Engine(world, seed=3)
    interp = Interpreter(world, engine)
    calls: list[str] = []

    def runner(creature: Creature) -> None:
        calls.append(creature.name)
        interp.run_turn(creature)

    engine.set_turn_runner(runner)
    child = Creature(compile_body("    n = 99\n    wait(1)\n"))
    child.name = "Child"
    assert world.place_creature(0, 0, child)
    engine.queue_newborn(child)
    engine.step()
    assert calls == ["Uruk"]
    assert "n" not in child.variables
    engine.step()
    assert calls == ["Uruk", "Uruk", "Child"]
    assert child.variables["n"] == 99


def test_same_seed_same_trace() -> None:
    def run(seed: int) -> tuple[list[tuple[int, ...]], list[int]]:
        world = World(5, 5, grass())
        first = Creature(compile_body("    n = random % 10\n    wait(1)\n"))
        second = Creature(compile_body("    n = random % 10\n    wait(1)\n"))
        assert world.place_creature(0, 0, first)
        assert world.place_creature(4, 4, second)
        engine = Engine(world, seed=seed)
        engine.set_turn_runner(Interpreter(world, engine).run_turn)
        traces: list[tuple[int, ...]] = []
        orders: list[int] = []
        for _ in range(5):
            report = engine.step()
            traces.append((first.variables["n"], second.variables["n"]))
            orders.append(len(report.order))
        return traces, orders

    assert run(11) == run(11)
    assert run(11) != run(12)


def test_runtime_errors_kill_and_log_with_line() -> None:
    cases = [
        ("    n = 1 / 0\n    wait(1)\n", 7, "división por cero"),
        ("    n = 1 % 0\n    wait(1)\n", 7, "resto por cero"),
        ("    n = nunca\n    wait(1)\n", 7, "variable no asignada 'nunca'"),
        ("    n = 1 + \"a\"\n    wait(1)\n", 7, "no se pueden mezclar entero y texto"),
        ("    n = 1 == \"a\"\n    wait(1)\n", 7, "no se pueden mezclar entero y texto"),
        ("    n = \"a\" < \"b\"\n    wait(1)\n", 7, "el texto solo admite '==' y '!='"),
        ("    n = \"a\" + \"b\"\n    wait(1)\n", 7, "el texto solo admite '==' y '!='"),
        ("    n = -\"a\"\n    wait(1)\n", 7, "el menos unario solo admite números"),
        ("    wait(\"ya\")\n", 7, "la acción 'wait' espera un número"),
        ("    n = see(\"a\", 0)\n    wait(1)\n", 7, "la función 'see' espera números"),
        ("    n = name(0, \"a\")\n    wait(1)\n", 7, "la función 'name' espera números"),
    ]
    for body, line, message in cases:
        world, creature = make_world(compile_body(body))
        log: list[str] = []
        turn(world, creature, log=log)
        assert world.creature_at(2, 2) is None, body
        assert log == [f"Uruk: línea {line}: {message}"], body
        assert "n" not in creature.variables, body


def test_ictus_during_step_counts_death() -> None:
    world, creature = make_world(compile_body("    n = 1 / 0\n    wait(1)\n"))
    engine = Engine(world, seed=1)
    engine.set_turn_runner(Interpreter(world, engine).run_turn)
    report = engine.step()
    assert world.creature_at(2, 2) is None
    assert report.deaths == 1
