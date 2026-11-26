"""Editor de código Instinct integrado."""
from .compiler_bridge import compile_source, get_catalogs, Diagnostic
from .hot_reload import HotReloadManager

# Imports perezosos (PEP 562) para módulos que dependen de PyQt6
# y aún no están instalados en el entorno. Se importan solo cuando
# se accede a ellos por primera vez.
__all__ = [
    "compile_source",
    "get_catalogs",
    "Diagnostic",
    "HotReloadManager",
    "InstinctHighlighter",
    "InstinctCompleter",
    "InstinctLinter",
    "FileManager",
    "EditorTab",
    "EditorWidget",
    "EditorWindow",
]


def __getattr__(name: str):
    """Imports perezosos para módulos con dependencia de PyQt6."""
    if name == "InstinctHighlighter":
        from .highlighter import InstinctHighlighter
        return InstinctHighlighter
    if name == "InstinctCompleter":
        from .completer import InstinctCompleter
        return InstinctCompleter
    if name == "InstinctLinter":
        from .linter import InstinctLinter
        return InstinctLinter
    if name == "FileManager":
        from .file_manager import FileManager
        return FileManager
    if name == "EditorTab":
        from .file_manager import EditorTab
        return EditorTab
    if name == "EditorWidget":
        from .editor_widget import EditorWidget
        return EditorWidget
    if name == "EditorWindow":
        from .window import EditorWindow
        return EditorWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
