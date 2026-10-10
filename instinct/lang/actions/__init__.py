"""Acciones del lenguaje: una clase por acción sobre una base común (§5)."""

from __future__ import annotations

from .base import Action, ActionContext
from .wait import Wait

#: Registro de nombre a acción: añadir una acción es registrar una clase más.
ACTIONS: dict[str, Action] = {}


def register(action: Action) -> None:
    """Apunta la acción en el registro bajo su nombre.

    Args:
        action: Instancia de la subclase a registrar.
    """
    ACTIONS[action.name] = action


register(Wait())

__all__ = ["ACTIONS", "Action", "ActionContext", "register"]
