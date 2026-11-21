"""Hot-reload: recompila .ins y recarga en la sesión sin reiniciar el mundo.

Reutiliza ``Session.reload_creature`` (API pública) y
``instinct.loaders.creature_loader.load_creature`` (compilación).
"""
from __future__ import annotations

from typing import Optional

from instinct.ui.session import Session
from instinct.loaders.creature_loader import load_creature


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
            name: Nombre de la criatura (especie) a recargar.
            source: Texto completo del .ins a compilar.

        Returns:
            Tupla (ok, errores). Si ``ok`` es False, ``errores`` contiene
            los mensajes de compilación en español.
        """
        return self._session.reload_creature(name, source)
