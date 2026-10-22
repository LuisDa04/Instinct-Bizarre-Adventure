"""Acciones del lenguaje: una clase por acción sobre una base común."""

from __future__ import annotations

from instinct.compiler.catalogs import ACTION_ARITY

from .attack import Attack
from .base import Action, ActionContext
from .consume import Consume
from .move import Move
from .reproduce import Reproduce
from .roar import Roar
from .say import Say
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
register(Move())
register(Attack())
register(Consume())
register(Reproduce())
register(Roar())
register(Say())

#: El registro debe cubrir el catálogo del compilador, ni más ni menos.
assert set(ACTIONS) == set(ACTION_ARITY)

__all__ = ["ACTIONS", "Action", "ActionContext", "register"]
