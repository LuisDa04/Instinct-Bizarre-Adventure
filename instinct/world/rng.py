from __future__ import annotations

import random


class Rng:
    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        return self._random.randint(a, b)

    def random(self) -> float:
        return self._random.random()

    def shuffle(self, items: list) -> None:
        self._random.shuffle(items)

    def perception_random(self) -> int:
        return self._random.randint(0, 99)
