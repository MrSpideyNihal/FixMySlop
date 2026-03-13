"""
Code block widget — syntax-highlighted read-only code display.
"""
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter
from PyQt5.QtCore import QRegularExpression


class PythonHighlighter(QSyntaxHighlighter):
    """Basic syntax highlighter for Python code."""

    def __init__(self, parent=None):
        """Initialize highlighter with Python rules."""
        super().__init__(parent)
        self._rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#c792ea"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "\\bdef\\b", "\\bclass\\b", "\\breturn\\b", "\\bif\\b",
            "\\belse\\b", "\\belif\\b", "\\bfor\\b", "\\bwhile\\b",
            "\\bimport\\b", "\\bfrom\\b", "\\bas\\b", "\\btry\\b",
            "\\bexcept\\b", "\\bfinally\\b", "\\bwith\\b", "\\braise\\b",
            "\\bpass\\b", "\\bbreak\\b", "\\bcontinue\\b", "\\blambda\\b",
            "\\byield\\b", "\\bassert\\b", "\\bin\\b", "\\bnot\\b",
            "\\band\\b", "\\bor\\b", "\\bTrue\\b", "\\bFalse\\b",
            "\\bNone\\b", "\\bself\\b", "\\basync\\b", "\\bawait\\b",
        ]
        for kw in keywords:
            self._rules.append((QRegularExpression(kw), keyword_format))

        # Strings (single and double quoted)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#c3e88d"))
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self._rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#546e7a"))
        comment_format.setFontItalic(True)
        self._rules.append((QRegularExpression(r"#[^\n]*"), comment_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#f78c6c"))
        self._rules.append((QRegularExpression(r"\b\d+\.?\d*\b"), number_format))

        # Decorators
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#82aaff"))
        self._rules.append((QRegularExpression(r"@\w+"), decorator_format))

        # Function calls
        func_format = QTextCharFormat()
        func_format.setForeground(QColor("#82aaff"))
        self._rules.append((QRegularExpression(r"\b\w+(?=\()"), func_format))

    def highlightBlock(self, text: str):
        """Apply highlighting rules to a block of text."""
        for pattern, fmt in self._rules:
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class CodeBlock(QPlainTextEdit):
    """
    Syntax-highlighted, read-only code display widget.
    Uses a monospace font and optional line numbers.
    """

    def __init__(self, code: str = "", language: str = "python", parent=None):
        """Initialize the code block with optional initial code."""
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("JetBrains Mono", 11))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        if language == "python":
            self._highlighter = PythonHighlighter(self.document())
        else:
            self._highlighter = None

        if code:
            self.setPlainText(code)

    def set_code(self, code: str, language: str = "python"):
        """Set the displayed code content."""
        self.setPlainText(code)
