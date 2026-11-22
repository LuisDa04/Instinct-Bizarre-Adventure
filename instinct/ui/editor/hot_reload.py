"""Hot-reload: recompila .ins y recarga en la sesión sin reiniciar el mundo.

Reutiliza la API pública de ``Session``.
"""
from __future__ import annotations

from instinct.ui.session import ReloadResult, Session


class HotReloadManager:
    """Gestiona la recarga en caliente de criaturas mediante Session.

    Cuando el usuario guarda un .ins, este manager recompila el código y
    actualiza la criatura en el mundo sin reiniciar la simulación.
    """

    def __init__(self, session: Session) -> None:
        """Crea el gestor de hot-reload sobre una sesión existente."""
        self._session = session

    def reload_from_source(self, source: str) -> ReloadResult:
        """Recompila y recarga una criatura usando el nombre de su cabecera."""
        return self._session.reload_from_source(source)

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
