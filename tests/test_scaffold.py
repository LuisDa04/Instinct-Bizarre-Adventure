from pathlib import Path

from instinct.world.rng import Rng

ROOT = Path(__file__).resolve().parent.parent

CONTENT_DIRS = ("terrains", "objects", "maps", "creatures")


def test_runtime_content_dirs_exist() -> None:
    for directory in CONTENT_DIRS:
        assert (ROOT / directory).is_dir()


def test_rng_is_reproducible() -> None:
    first_rng = Rng(42)
    first = [first_rng.perception_random() for _ in range(20)]

    other = Rng(42)
    second = [other.perception_random() for _ in range(20)]

    assert first == second


def test_rng_values_stay_in_range() -> None:
    rng = Rng(7)
    values = [rng.perception_random() for _ in range(500)]
    assert all(0 <= value <= 99 for value in values)
    assert len(set(values)) > 1


def test_different_seeds_differ() -> None:
    a = Rng(1)
    b = Rng(2)
    assert [a.perception_random() for _ in range(10)] != [
        b.perception_random() for _ in range(10)
    ]
