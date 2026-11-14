"""Resaltado de sintaxis Instinct usando catálogos existentes del compilador."""
from __future__ import annotations

from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt, QRegularExpression

from instinct.ui.editor.compiler_bridge import get_catalogs


class InstinctHighlighter(QSyntaxHighlighter):
    """Resaltador de sintaxis para ficheros .ins.

    Usa los catálogos centrales (keywords, acciones, percepciones, constantes)
    para que cualquier cambio en el lenguaje se refleje automáticamente en el
    editor sin tocar este archivo.
    """

    def __init__(self, document) -> None:
        """Inicializa el resaltador sobre el documento dado."""
        super().__init__(document)
        self._catalogs = get_catalogs()
        self._formats = self._build_formats()
        self._patterns = self._build_patterns()

    def _build_formats(self) -> dict[str, QTextCharFormat]:
        """Crea formatos QTextCharFormat usando los colores del tema editor."""
        from instinct.ui.constants import EDITOR_THEME

        def fmt(color_key: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            color = EDITOR_THEME.get(color_key, (200, 200, 200))
            f.setForeground(QColor(*color[:3]))
            if len(color) == 4:
                f.setBackground(QColor(*color[:3]))
                f.setProperty("alpha", color[3])
            if bold:
                font = QFont()
                font.setBold(True)
                font.setWeight(QFont.Weight.Bold)
                f.setFont(font)
                f.setFontWeight(QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        return {
            "keyword": fmt("keyword", bold=True),
            "action": fmt("action", bold=True),
            "function": fmt("function", bold=True),
            "perception": fmt("perception"),
            "constant": fmt("constant"),
            "string": fmt("string"),
            "number": fmt("number"),
            "comment": fmt("comment", italic=True),
            "label": fmt("label", bold=True),
            "variable": fmt("fg"),
            "error": fmt("error"),
        }

    def _build_patterns(self) -> list[tuple[QRegularExpression, QTextCharFormat]]:
        """Construye patrones regex + formato usando los catálogos."""
        cat = self._catalogs
        patterns: list[tuple[QRegularExpression, QTextCharFormat]] = []

        # Keywords reservadas (if, goto, and, or, not)
        kw_regex = r"\b(" + "|".join(cat["keywords"]) + r")\b"
        patterns.append((QRegularExpression(kw_regex), self._formats["keyword"]))

        # Acciones (wait, move, attack, consume, reproduce, roar, say)
        act_regex = r"\b(" + "|".join(cat["actions"].keys()) + r")\b(?=\s*\()"
        patterns.append((QRegularExpression(act_regex), self._formats["action"]))

        # Funciones reservadas (see, name)
        fn_regex = r"\b(" + "|".join(cat["functions"].keys()) + r")\b(?=\s*\()"
        patterns.append((QRegularExpression(fn_regex), self._formats["function"]))

        # Percepciones (health, age, enemy_dist, etc.)
        perc_regex = r"\b(" + "|".join(sorted(cat["perceptions"])) + r")\b"
        patterns.append((QRegularExpression(perc_regex), self._formats["perception"]))

        # Constantes (NONE, GROUND, OBJECT, ALLY, ENEMY)
        const_regex = r"\b(" + "|".join(sorted(cat["constants"])) + r")\b"
        patterns.append((QRegularExpression(const_regex), self._formats["constant"]))

        # Strings entre comillas dobles
        patterns.append(
            (QRegularExpression(r'"(?:[^"\\]|\\.)*"'), self._formats["string"])
        )

        # Números (enteros, incl. negativos)
        patterns.append((QRegularExpression(r"\b-?\d+\b"), self._formats["number"]))

        # Comentarios (# ...)
        patterns.append((QRegularExpression(r"#.*"), self._formats["comment"]))

        # Etiquetas label: (al inicio de línea)
        patterns.append(
            (QRegularExpression(r"^\s*[A-Za-z_][A-Za-z0-9_]*:"), self._formats["label"])
        )

        return patterns

    def highlightBlock(self, text: str) -> None:
        """Aplica resaltado a un bloque de texto."""
        for regex, fmt in self._patterns:
            it = regex.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
