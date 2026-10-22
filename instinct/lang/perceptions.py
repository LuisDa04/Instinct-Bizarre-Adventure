"""Percepciones del lenguaje: foto del turno y registro de nombre a valor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from instinct.compiler.catalogs import PERCEPTIONS
from instinct.world.entities import Creature
from instinct.world.perceptions import WorldSense, sense
from instinct.world.world import World

if TYPE_CHECKING:
    from instinct.sim.engine import Engine

#: Valor que puede tomar una percepción: entero o texto.
Value = int | str


@dataclass(frozen=True)
class TurnFrame:
    """Foto congelada de todo lo que una criatura percibe al empezar su turno.

    Attributes:
        creature: Criatura que percibe, por referencia.
        world: Rejilla donde está colocada.
        engine: Motor que da el tick y la aleatoriedad.
        sense: Conteos y más cercanos calculados por los sensores.
        tick: Número de ticks ya cerrados al empezar el turno.
        roars_near: Rugidos del tick anterior oídos dentro del radio.
        last_roar: Texto del último rugido oído o "".
    """

    creature: Creature
    world: World
    engine: Engine
    sense: WorldSense
    tick: int
    roars_near: int
    last_roar: str


def refresh(creature: Creature, world: World, engine: Engine) -> TurnFrame:
    """Toma la foto de percepciones al empezar el turno de la criatura.

    Args:
        creature: Criatura colocada en el mundo que va a actuar.
        world: Rejilla donde está colocada.
        engine: Motor que aporta el tick y los rugidos del tick anterior.

    Returns:
        TurnFrame con todo salvo `random`, que se lee en cada aparición.
    """
    heard = engine.heard_roars(creature)
    return TurnFrame(
        creature=creature,
        world=world,
        engine=engine,
        sense=sense(world, creature),
        tick=engine.tick,
        roars_near=heard[0],
        last_roar=heard[1],
    )


def _ground(frame: TurnFrame):
    """Devuelve el terreno bajo la criatura, que siempre existe."""
    ground = frame.world.terrain_at(frame.creature.x, frame.creature.y)
    assert ground is not None
    return ground


#: Un resolvedor por percepción: la alternativa a un `if nombre == ...` por cada una.
PERCEPTION_RESOLVERS: dict[str, Callable[[TurnFrame], Value]] = {
    "health": lambda frame: frame.creature.health,
    "age": lambda frame: frame.creature.age,
    "lifespan": lambda frame: frame.creature.lifespan,
    "vision": lambda frame: frame.creature.vision,
    "species": lambda frame: frame.creature.name,
    "faction": lambda frame: frame.creature.faction,
    "x": lambda frame: frame.creature.x,
    "y": lambda frame: frame.creature.y,
    "terrain_here": lambda frame: _ground(frame).name,
    "reserve_here": lambda frame: _ground(frame).reserve,
    "width": lambda frame: frame.world.width,
    "height": lambda frame: frame.world.height,
    "tick": lambda frame: frame.tick,
    "total_creatures": lambda frame: frame.sense.total_creatures,
    "total_allies": lambda frame: frame.sense.total_allies,
    "total_enemies": lambda frame: frame.sense.total_enemies,
    "random": lambda frame: frame.engine.perception_random(),
    "allies_near": lambda frame: frame.sense.allies_near,
    "enemies_near": lambda frame: frame.sense.enemies_near,
    "objects_near": lambda frame: frame.sense.objects_near,
    "enemy_dist": lambda frame: frame.sense.enemy[0],
    "enemy_dx": lambda frame: frame.sense.enemy[1],
    "enemy_dy": lambda frame: frame.sense.enemy[2],
    "ally_dist": lambda frame: frame.sense.ally[0],
    "ally_dx": lambda frame: frame.sense.ally[1],
    "ally_dy": lambda frame: frame.sense.ally[2],
    "object_dist": lambda frame: frame.sense.object[0],
    "object_dx": lambda frame: frame.sense.object[1],
    "object_dy": lambda frame: frame.sense.object[2],
    "roars_near": lambda frame: frame.roars_near,
    "last_roar": lambda frame: frame.last_roar,
}

assert set(PERCEPTION_RESOLVERS) == set(PERCEPTIONS)


def perception_value(name: str, frame: TurnFrame) -> Value:
    """Devuelve el valor de la percepción para la foto dada.

    Args:
        name: Nombre de una de las 31 percepciones del lenguaje.
        frame: Foto tomada al empezar el turno.

    Returns:
        Entero o texto de la percepción; `random` se sortea en cada llamada.
    """
    return PERCEPTION_RESOLVERS[name](frame)
