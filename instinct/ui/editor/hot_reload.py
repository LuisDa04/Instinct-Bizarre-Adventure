"""Hot-reload: recompila .ins y recarga en la sesión sin reiniciar el mundo.

Reutiliza ``Session`` (API limpia sobre CLI) y
``instinct.loaders.creature_loader.load_creature`` (compilación).
"""
from __future__ import annotations

from typing import Optional

from instinct.ui.session import Session
from instinct.loaders.creature_loader import load_creature
from instinct.world.entities import Creature


class HotReloadManager:
    """Gestiona la recarga en caliente de criaturas mediante Session.

    Cuando el usuario guarda un .ins, este manager recompila el código y
    actualiza la criatura en el mundo sin reiniciar la simulación.
    """

    def __init__(self, session: Session) -> None:
        """Crea el gestor de hot-reload sobre una sesión existente."""
        self._session = session

    def reload_creature(self, name: str, source: str) -> tuple[bool, list[str]]:
        """Recompila y recarga una criatura en la sesión activa.

        Args:
            name: Nombre de la criatura (coincide con el nombre del archivo .ins
                sin la extensión).
            source: Texto completo del .ins a compilar.

        Returns:
            Tupla (ok, errores). Si ``ok`` es False, ``errores`` contiene
            los mensajes de compilación en español.
        """
        result = load_creature(source)
        if result.creature is None:
            errors = [f"línea {e.line}: {e.message}" for e in result.errors]
            return False, errors

        # Actualiza el registro de criaturas cargadas en el CLI
        self._session._cli.loaded.creatures[name] = result.creature

        # Si la criatura ya está colocada en el mundo, la recolocamos
        # con su nuevo programa (misma posición, nuevo código)
        self._recolocar_si_existe(name)

        return True, []

    def _recolocar_si_existe(self, name: str) -> None:
        """Si la criatura ya está colocada, la sustituye por la nueva versión.

        Busca la criatura por nombre en el mundo, la elimina y la vuelve a
        colocar en la misma posición con el programa recién compilado.
        """
        world = self._session.state.world
        if world is None:
            return

        for y in range(world.height):
            for x in range(world.width):
                c = world.creature_at(x, y)
                if c is not None and c.name == name:
                    # Quitar la criatura antigua
                    world.remove_creature(x, y)
                    # Colocar la nueva versión con el programa actualizado
                    new_c = Creature(
                        self._session._cli.loaded.creatures[name], x, y
                    )
                    world.place_creature(x, y, new_c)
                    return
