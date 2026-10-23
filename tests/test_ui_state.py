"""Pruebas del estado de la interfaz: fases, velocidad y listas de contenido."""
from __future__ import annotations

from instinct.ui.constants import (
    PHASE_LOADING,
    PHASE_PLACEMENT,
    SPEEDS,
)
from instinct.ui.state import UIState


def test_defaults() -> None:
    state = UIState()
    assert state.phase == PHASE_LOADING
    assert state.tile_size == 32
    assert state.seed == 42
    assert state.speed_tps == SPEEDS[0]
    assert state.messages == []


def test_speed_tps_follows_index() -> None:
    state = UIState()
    assert state.speed_tps == 0.5
    state.speed_index = 4
    assert state.speed_tps == 30


def test_map_and_species_names_empty_without_load() -> None:
    state = UIState()
    assert state.map_names == []
    assert state.species_names == []


def test_in_simulation_only_in_that_phase() -> None:
    state = UIState()
    state.phase = PHASE_PLACEMENT
    assert not state.in_simulation()
    state.phase = "simulation"
    assert state.in_simulation()
