"""Generador aleatorio con semilla para partidas reproducibles."""
from __future__ import annotations

import random


class Rng:
    """Representa una fuente aleatoria con semilla que repite la secuencia con igual seed."""

    def __init__(self, seed: int = 0) -> None:
        """Crea el generador con la semilla dada.

        Args:
            seed: Semilla inicial; igual valor produce igual secuencia.
        """
        self.seed = seed
        self._random = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        """Devuelve un entero aleatorio en [a, b], ambos incluidos."""
        return self._random.randint(a, b)

    def random(self) -> float:
        """Devuelve un flotante aleatorio en [0.0, 1.0)."""
        return self._random.random()

    def shuffle(self, items: list) -> None:
        """Mezcla la lista dada en su lugar.

        Args:
            items: Lista que se reordena directamente; no se devuelve copia.
        """
        self._random.shuffle(items)

    def perception_random(self) -> int:
        """Devuelve un entero aleatorio en [0, 99] para tiradas de percepción."""
        return self._random.randint(0, 99)
