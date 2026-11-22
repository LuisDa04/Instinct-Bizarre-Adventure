"""El compilador no debe depender en runtime de `instinct.lang`."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


COMPILER_DIR = Path(__file__).resolve().parents[1] / "instinct" / "compiler"


def test_compiler_has_no_lang_imports() -> None:
    for path in COMPILER_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("instinct.lang"), (
                        f"{path.name} importa {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level > 0:
                    # resolver relativo desde instinct.compiler
                    # from ..lang.x import ... => level 2 desde compiler
                    if node.level >= 2 and mod.startswith("lang"):
                        raise AssertionError(f"{path.name} importa relativo {mod}")
                assert not mod.startswith("instinct.lang"), (
                    f"{path.name} importa {mod}"
                )


def test_compiler_ast_nodes_import_does_not_load_lang() -> None:
    code = (
        "import sys, instinct.compiler.ast_nodes; "
        "bad=[m for m in sys.modules if m=='instinct.lang' or m.startswith('instinct.lang.')]; "
        "raise SystemExit(1 if bad else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert result.returncode == 0, result.stdout + result.stderr
