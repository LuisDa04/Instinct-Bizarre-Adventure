from __future__ import annotations

from ..compiler.errors import CompileError


class LoadError(CompileError):
    def __init__(self, line: int, message: str, path: str = "") -> None:
        super().__init__(line, message)
        self.path = path
