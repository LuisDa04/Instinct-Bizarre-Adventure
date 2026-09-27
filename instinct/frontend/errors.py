from __future__ import annotations


class CompileError(Exception):
    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


class LexError(CompileError):
    pass


class ParseError(CompileError):
    pass


class SemanticError(CompileError):
    pass
