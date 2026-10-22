"""Motor de simulación por ticks con orden aleatorio y envejecimiento."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from instinct.world.entities import Creature
from instinct.world.rng import Rng
from instinct.world.world import World


@dataclass(frozen=True)
class TickReport:
    """Representa el resumen de un tick: número, muertes, nacimientos y orden de turno.

    Invariante: order trae posiciones al inicio en orden de actuación, sin
    recién nacidos; deaths suma ictus, combate y fin de tick.
    """

    tick: int
    deaths: int
    births: int
    order: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class Roar:
    """Rugido publicado al cerrar un tick: texto y oyentes por identidad.

    Invariante: listeners trae id() de criaturas vivas a distancia Chebyshev
    menor o igual que su propia visión desde la posición de emisión.
    """

    text: str
    listeners: frozenset[int]


@dataclass(frozen=True)
class WorldSnapshot:
    """Representa una foto inmutable del mundo: tick, tamaño y criaturas como tuplas.

    Invariante: creatures guarda (nombre, facción, x, y, salud, edad) sin referencias vivas.
    """

    tick: int
    width: int
    height: int
    creatures: tuple[tuple[str, str, int, int, int, int], ...]


class Engine:
    """Representa el motor que avanza el mundo tick a tick con semilla fija.

    Invariante: cada tick corre turnos, cobra vida y edad, retira muertes (las
    de fin de tick y las que llegan por kill() a mitad de tick), regenera y suma nacidos.
    """

    def __init__(self, world: World, seed: int = 0) -> None:
        """Crea el motor sobre un mundo existente con la semilla dada.

        Args:
            world: Mundo a simular; se guarda por referencia, no se clona.
            seed: Semilla del orden aleatorio de turnos.
        """
        self._world = world
        self._rng = Rng(seed)
        self._tick = 0
        self._pending: list[Creature] = []
        self._turn_runner: Callable[[Creature], bool] | None = None
        self._emitted: list[tuple[int, int, str]] = []
        self._heard: list[Roar] = []
        self._deaths = 0

    @property
    def tick(self) -> int:
        """Devuelve el número de ticks ya ejecutados."""
        return self._tick

    def set_turn_runner(self, runner: Callable[[Creature], bool] | None) -> None:
        """Asigna la función que ejecuta el turno de cada criatura, o None para desactivarla.

        Args:
            runner: Recibe cada criatura por referencia; su valor devuelto se ignora.
        """
        self._turn_runner = runner

    def perception_random(self) -> int:
        """Devuelve un entero en [0, 99] del único RNG para la percepción `random`.

        Returns:
            Tirada del generador compartido con el sorteo de turnos.
        """
        return self._rng.perception_random()

    def emit_roar(self, x: int, y: int, text: str) -> None:
        """Encola un rugido emitido en este tick para oírlo en el siguiente.

        Args:
            x: Columna de emisión.
            y: Fila de emisión.
            text: Texto rugido ya convertido a cadena.
        """
        self._emitted.append((x, y, text))

    def heard_roars(self, creature: Creature) -> tuple[int, str]:
        """Devuelve lo que la criatura oyó del tick anterior.

        Args:
            creature: Criatura que pregunta, por identidad.

        Returns:
            Tupla (cantidad, último texto) o (0, "") si no oyó nada.
        """
        heard = [roar.text for roar in self._heard if id(creature) in roar.listeners]
        if not heard:
            return (0, "")
        return (len(heard), heard[-1])

    def queue_newborn(self, creature: Creature) -> None:
        """Encola una criatura nacida en este tick para que actúe desde el siguiente.

        Args:
            creature: Se guarda por referencia y cuenta como nacimiento al cerrar el tick.
        """
        self._pending.append(creature)

    def kill(self, creature: Creature) -> bool:
        """Retira a la criatura del mundo y cuenta su muerte en el tick actual.

        Args:
            creature: Criatura viva; se localiza por identidad aunque su
                posición registrada esté desfasada.

        Returns:
            True si estaba en el mundo y se retiró; False si ya no estaba.
        """
        if not self._bury(creature):
            return False
        self._deaths += 1
        return True

    def _bury(self, creature: Creature) -> bool:
        """Localiza y retira a la criatura por identidad.

        Returns:
            True si se encontró y retiró; False si ya no está en el mundo.
        """
        if self._world.creature_at(creature.x, creature.y) is creature:
            self._world.remove_creature(creature.x, creature.y)
            return True
        found = self._find_creature(creature)
        if found is None:
            return False
        self._world.remove_creature(found[0], found[1])
        return True

    def state(self) -> WorldSnapshot:
        """Devuelve una foto inmutable del mundo que no expone sus estructuras internas.

        Returns:
            WorldSnapshot con tuplas copiadas; modificarla no altera al mundo.
        """
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
        """Avanza un tick completo y devuelve su resumen.

        Orden de fin de tick: coste de vida y edad, muertes, regeneración, limpieza y nacidos.

        Returns:
            TickReport con el nuevo tick, muertes, nacimientos y orden de actuación.
        """
        self._deaths = 0
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
        for creature in after_turns:
            if creature.health <= 0 or creature.age >= creature.lifespan:
                self.kill(creature)
        self._publish_roars()
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
            tick=self._tick, deaths=self._deaths, births=births, order=order
        )

    def _publish_roars(self) -> None:
        """Publica los rugidos del tick para oírlos en el siguiente y vacía la cola.

        Los oyentes se calculan con las criaturas vivas: cada una oye lo emitido
        a distancia Chebyshev menor o igual que su propia visión.
        """
        published: list[Roar] = []
        for x, y, text in self._emitted:
            listeners = frozenset(
                id(creature)
                for creature in self._world.creatures()
                if max(abs(creature.x - x), abs(creature.y - y)) <= creature.vision
            )
            published.append(Roar(text=text, listeners=listeners))
        self._heard = published
        self._emitted = []

    def _find_creature(self, target: Creature) -> tuple[int, int] | None:
        """Busca la posición actual de una criatura desplazada o devuelve None.

        Returns:
            Tupla (x, y) donde está target, o None si ya no está en el mundo.
        """
        for y in range(self._world.height):
            for x in range(self._world.width):
                if self._world.creature_at(x, y) is target:
                    return (x, y)
        return None
