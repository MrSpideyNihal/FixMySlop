"""
Diff viewer widget — side-by-side code diff with syntax highlighting.
"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTextEdit,
    QLabel, QScrollBar,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QTextCharFormat, QFont


class DiffViewer(QWidget):
    """
    Side-by-side diff viewer with color-coded additions and removals.
    Shows original code on left, modified code on right.
    """

    def __init__(self, parent=None):
        """Initialize the diff viewer."""
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        """Build the side-by-side layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Headers
        header_layout = QHBoxLayout()
        self._left_label = QLabel("Original")
        self._left_label.setObjectName("SectionSubtitle")
        self._right_label = QLabel("Modified")
        self._right_label.setObjectName("SectionSubtitle")
        header_layout.addWidget(self._left_label)
        header_layout.addWidget(self._right_label)
        layout.addLayout(header_layout)

        # Code panes
        pane_layout = QHBoxLayout()
        self._left_pane = self._create_text_edit()
        self._right_pane = self._create_text_edit()
        pane_layout.addWidget(self._left_pane)
        pane_layout.addWidget(self._right_pane)
        layout.addLayout(pane_layout)

        # Sync scrolling
        self._left_pane.verticalScrollBar().valueChanged.connect(
            self._right_pane.verticalScrollBar().setValue
        )
        self._right_pane.verticalScrollBar().valueChanged.connect(
            self._left_pane.verticalScrollBar().setValue
        )

    def _create_text_edit(self) -> QTextEdit:
        """Create a styled read-only text editor for code display."""
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setFont(QFont("JetBrains Mono", 11))
        editor.setLineWrapMode(QTextEdit.NoWrap)
        return editor

    def load_diff(self, diff_text: str):
        """Parse and display a unified diff."""
        self._left_pane.clear()
        self._right_pane.clear()

        left_lines = []
        right_lines = []

        for line in diff_text.splitlines():
            if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                continue
            elif line.startswith("-"):
                left_lines.append(("removed", line[1:]))
                right_lines.append(("blank", ""))
            elif line.startswith("+"):
                left_lines.append(("blank", ""))
                right_lines.append(("added", line[1:]))
            else:
                content = line[1:] if line.startswith(" ") else line
                left_lines.append(("context", content))
                right_lines.append(("context", content))

        self._render_lines(self._left_pane, left_lines)
        self._render_lines(self._right_pane, right_lines)

    def load_before_after(self, before: str, after: str):
        """Load raw before/after code into the two panes."""
        self._left_pane.setPlainText(before)
        self._right_pane.setPlainText(after)

    def _render_lines(self, editor: QTextEdit, lines: list[tuple[str, str]]):
        """Render color-coded lines into a QTextEdit."""
        cursor = editor.textCursor()
        for line_type, content in lines:
            fmt = QTextCharFormat()
            if line_type == "removed":
                fmt.setBackground(QColor("#3c1f1f"))
                fmt.setForeground(QColor("#ff6b6b"))
            elif line_type == "added":
                fmt.setBackground(QColor("#1f3c1f"))
                fmt.setForeground(QColor("#69db7c"))
            elif line_type == "blank":
                fmt.setBackground(QColor("#1a1a2e"))
                fmt.setForeground(QColor("#1a1a2e"))
            else:
                fmt.setForeground(QColor("#e2e8f0"))

            cursor.insertText(content + "\n", fmt)
