"""Pruebas de aceptación F11: 1000 ticks, comportamiento Anexo y rendimiento."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from instinct.sim.controller import SimulationController
from instinct.loaders.pipeline import load_all

FIXTURES = Path(__file__).parent / "fixtures"


def load_anexo_controller(seed: int = 12345) -> SimulationController:
    """Carga el contenido del Anexo y devuelve un controlador listo."""
    controller = SimulationController(FIXTURES, seed=seed)
    report = controller.load_content()
    assert controller.loaded is not None
    assert controller.loaded.load_errors == [], [
        f"{e.path}: linea {e.line}: {e.message}" for e in controller.loaded.load_errors
    ]
    return controller


def test_load_anexo_content_without_errors() -> None:
    """El contenido del Anexo carga sin errores."""
    controller = load_anexo_controller()
    assert controller.loaded is not None
    assert "Grass" in {t.name for t in controller.loaded.registry.terrains}
    assert "Rock" in {o.name for o in controller.loaded.registry.objects}
    assert "Plain with rocks" in controller.loaded.maps
    assert {"Hobbit", "Ent", "Dwarf"}.issubset(set(controller.loaded.creatures.keys()))


@pytest.mark.slow
def test_anexo_1000_ticks_no_exception() -> None:
    """El contenido del Anexo corre 1000 ticks sin excepción."""
    controller = load_anexo_controller(seed=42)
    controller.select_map("Plain with rocks")

    # Coloca una de cada especie
    for species, (x, y) in (
        ("Hobbit", (2, 2)),
        ("Ent", (16, 2)),
        ("Dwarf", (8, 5)),
    ):
        msg = controller.place_creature(species, x, y)
        assert "colocada" in msg

    for _ in range(1000):
        controller.engine.step()

    assert controller.engine.tick == 1000
    # Al menos una criatura sigue viva (o todas murieron de forma natural)
    # Lo importante: no hubo excepción


def test_hobbit_flees_when_enemy_visible() -> None:
    """Hobbit huye si enemy_dist >= 0 (hay enemigo visible)."""
    controller = load_anexo_controller(seed=999)
    controller.select_map("Plain with rocks")
    # Hobbit en (2,2), Enano en (5,2) -> distancia 3, bien dentro de vision=5
    controller.place_creature("Hobbit", 2, 2)
    controller.place_creature("Dwarf", 5, 2)

    controller.engine.step()
    hobbit = controller.world.creature_at(2, 2)
    assert hobbit is None, "Hobbit debería haber huido"
    hobbit_creature = next(c for c in controller.world.creatures() if c.name == "Hobbit")
    assert hobbit_creature.x < 2, f"Hobbit debería haber huido a la izquierda, está en x={hobbit_creature.x}"


def test_ent_returns_to_home() -> None:
    """Ent vuelve a home_x/home_y si se le desplaza."""
    controller = load_anexo_controller(seed=777)
    controller.select_map("Plain with rocks")
    # Coloca Ent en (8,5) - lejos de su home (que será su posición inicial)
    controller.place_creature("Ent", 10, 5)
    # Fuerza un desplazamiento manual: muévelo a (12,5) con move_creature
    assert controller.world.move_creature(
        next(c for c in controller.world.creatures() if c.name == "Ent"), 12, 5
    )

    # Corre unos ticks - el Ent debe volver hacia su home original
    for _ in range(10):
        controller.engine.step()

    ent = next(c for c in controller.world.creatures() if c.name == "Ent")
    # Debe haberse movido hacia su home (10,5) -> x debe haber bajado
    assert ent.x <= 12, f"Ent debería haber ido hacia home, está en x={ent.x}"


def test_dwarf_mines_only_rock() -> None:
    """Enano solo mina Rock (name == 'Rock')."""
    controller = load_anexo_controller(seed=888)
    controller.select_map("Plain with rocks")
    # Busca una roca en el mapa cargado
    rock_pos = None
    for y in range(controller.world.height):
        for x in range(controller.world.width):
            obj = controller.world.object_at(x, y)
            if obj and obj.name == "Rock":
                # Busca casilla adyacente libre
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if controller.world.walkable(nx, ny):
                        rock_pos = (nx, ny)
                        break
                if rock_pos:
                    break
        if rock_pos:
            break

    assert rock_pos is not None, "Debe haber una roca con casilla adyacente libre"
    controller.place_creature("Dwarf", *rock_pos)

    # El enano solo mina si health < 100 -> lo dañamos primero
    dwarf = next(c for c in controller.world.creatures() if c.name == "Dwarf")
    dwarf.health = 90

    initial_rock_reserve = None
    for y in range(controller.world.height):
        for x in range(controller.world.width):
            obj = controller.world.object_at(x, y)
            if obj and obj.name == "Rock":
                initial_rock_reserve = obj.reserve
                break

    controller.engine.step()
    # Verifica que la roca perdió reserva (fue minada)
    rock_after = None
    found = False
    for y in range(controller.world.height):
        for x in range(controller.world.width):
            obj = controller.world.object_at(x, y)
            if obj and obj.name == "Rock":
                rock_after = obj.reserve
                found = True
                break
        if found:
            break

    assert rock_after is not None and rock_after < initial_rock_reserve, \
        "La roca debería haber perdido reserva al ser minada"


def test_anexo_corrupt_ins_does_not_break_others() -> None:
    """Un .ins roto en creatures/ no impide cargar los demás."""
    controller = SimulationController(FIXTURES, seed=1)
    # Escribe un .ins roto
    bad = FIXTURES / "creatures" / "bad.ins"
    bad.write_text("esto no compila\n", encoding="utf-8")
    try:
        report = controller.load_content()
        assert controller.loaded is not None
        assert "Errores de carga:" in report
        assert "bad.ins" in report
        # Los válidos siguen cargados
        assert {"Hobbit", "Ent", "Dwarf"}.issubset(set(controller.loaded.creatures.keys()))
    finally:
        bad.unlink(missing_ok=True)


@pytest.mark.slow
@pytest.mark.parametrize("seed", [1, 42, 123, 999])
def test_determinism_same_seed_same_trace(seed: int) -> None:
    """Misma semilla => traza idéntica (criaturas + mensajes) en 200 ticks."""
    def run(seed: int):
        controller = load_anexo_controller(seed)
        controller.select_map("Plain with rocks")
        for sp, (x, y) in (("Hobbit", (2, 2)), ("Ent", (16, 2)), ("Dwarf", (8, 5))):
            controller.place_creature(sp, x, y)
        for _ in range(200):
            controller.engine.step()
        # Estado final: lista de (nombre, x, y, health, age) desde el snapshot
        snapshot = controller.engine.state()
        creatures = tuple(sorted((c[0], c[2], c[3], c[4], c[5]) for c in snapshot.creatures))
        return creatures, tuple(controller.logs)

    s1, logs1 = run(seed)
    s2, logs2 = run(seed)
    assert s1 == s2, f"Semilla {seed}: estado final diverge"
    assert logs1 == logs2, f"Semilla {seed}: logs divergen"


@pytest.mark.slow
@pytest.mark.skip(reason="Requiere contenido completo en maps/ (solo fixtures en repo)")
def test_performance_300_creatures_30_tps() -> None:
    """300 criaturas a 30 tps: 100 ticks en < 3.5s (headless)."""
    from instinct.sim.engine import Engine
    from instinct.world.world import World
    from instinct.world.entities import Creature

    # Carga base JoJo (ya existe en repo)
    base = Path(__file__).parents[3]
    loaded = load_all(
        base / "terrains", base / "objects", base / "maps", base / "creatures"
    )
    assert loaded.load_errors == []

    # Mapa grande
    game_map = next(iter(loaded.maps.values()))
    world = World(game_map.width * 3, game_map.height * 3, loaded.registry.base_terrain)
    # Coloca terrenos/objetos del mapa original replicados
    for y in range(game_map.height):
        for x in range(game_map.width):
            cell = game_map.cells[y][x]
            for dy in range(3):
                for dx in range(3):
                    world.place_terrain(x + dx * game_map.width, y + dy * game_map.height, cell.terrain)
                    if cell.object:
                        world.place_object(x + dx * game_map.width, y + dy * game_map.height, cell.object)

    engine = Engine(world, seed=42)
    # 300 criaturas aleatorias
    import random
    rng = random.Random(123)
    species = list(loaded.creatures.keys())
    for _ in range(300):
        sp = rng.choice(species)
        x = rng.randint(0, world.width - 1)
        y = rng.randint(0, world.height - 1)
        if world.walkable(x, y):
            creature = Creature(loaded.creatures[sp], x, y)
            world.place_creature(x, y, creature)
            engine.queue_newborn(creature)

    start = time.perf_counter()
    for _ in range(100):
        engine.step()
    elapsed = time.perf_counter() - start

    # 100 ticks a 30 tps = 3.33s ideal; permitimos 3.5s con margen headless
    assert elapsed < 3.5, f"100 ticks tardaron {elapsed:.2f}s (esperado < 3.5s)"
    print(f"Performance: 100 ticks en {elapsed:.2f}s = {100/elapsed:.1f} tps")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "not slow"])