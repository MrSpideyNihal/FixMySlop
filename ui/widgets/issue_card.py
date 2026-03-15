"""
Issue card widget — expandable card showing a single issue's details.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QPlainTextEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.widgets.severity_badge import SeverityBadge
from core.issue import Issue


class _ClickableHeader(QFrame):
    """Header frame that emits clicked when the user presses anywhere on it."""

    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        """Emit click for left-button presses."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class IssueCard(QWidget):
    """
    Expandable card for a single issue.
    Shows severity, title, file, and description.
    Has expand/collapse for evidence and fix buttons.
    """

    fix_requested = pyqtSignal(object)   # Emits the Issue
    apply_requested = pyqtSignal(object) # Emits the Issue

    def __init__(self, issue: Issue, parent=None):
        """Initialize the issue card with an Issue object."""
        super().__init__(parent)
        self.issue = issue
        self._expanded = False
        self.setObjectName("CardWidget")
        self._build_ui()

    def _build_ui(self):
        """Build the card layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Clickable header: collapsed view always visible.
        self._header_frame = _ClickableHeader()
        self._header_frame.setCursor(Qt.PointingHandCursor)
        header_layout = QVBoxLayout(self._header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._badge = SeverityBadge(self.issue.severity)
        self._badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(self._badge)

        file_label = QLabel(
            f"{self.issue.file_path}  •  Line {self.issue.line_start}-{self.issue.line_end}"
        )
        file_label.setStyleSheet("color: #8892a4; font-size: 11px;")
        file_label.setWordWrap(True)
        file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        file_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(file_label, 1)

        self._expand_btn = QPushButton("▼")
        self._expand_btn.setFixedSize(28, 28)
        self._expand_btn.setStyleSheet(
            "border: none; color: #8892a4; font-size: 12px;"
        )
        self._expand_btn.clicked.connect(self._toggle_expand)
        top_row.addWidget(self._expand_btn)

        header_layout.addLayout(top_row)

        title = QLabel(str(self.issue.title))
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        title.setWordWrap(True)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        header_layout.addWidget(title)

        self._header_frame.clicked.connect(self._on_header_clicked)
        layout.addWidget(self._header_frame)

        # Expandable section
        self._detail_frame = QFrame()
        self._detail_frame.setVisible(False)
        detail_layout = QVBoxLayout(self._detail_frame)
        detail_layout.setContentsMargins(0, 8, 0, 0)
        detail_layout.setSpacing(8)

        if self.issue.evidence:
            evidence_label = QLabel("Evidence:")
            evidence_label.setStyleSheet("font-weight: bold; color: #8892a4;")
            detail_layout.addWidget(evidence_label)

            self._evidence_view = QPlainTextEdit()
            self._evidence_view.setPlainText(str(self.issue.evidence))
            self._evidence_view.setReadOnly(True)
            self._evidence_view.setMaximumHeight(120)
            self._evidence_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self._evidence_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self._evidence_view.setStyleSheet(
                "background: #141820; padding: 8px; border-radius: 4px; "
                "font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #e2e8f0;"
            )
            detail_layout.addWidget(self._evidence_view)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        fix_btn = QPushButton("Generate Fix")
        fix_btn.setObjectName("SecondaryButton")
        fix_btn.clicked.connect(lambda: self.fix_requested.emit(self.issue))
        btn_row.addWidget(fix_btn)

        if self.issue.diff:
            apply_btn = QPushButton("Apply Fix")
            apply_btn.setObjectName("PrimaryButton")
            apply_btn.clicked.connect(lambda: self.apply_requested.emit(self.issue))
            btn_row.addWidget(apply_btn)

        btn_row.addStretch()
        detail_layout.addLayout(btn_row)

        layout.addWidget(self._detail_frame)

    def _toggle_expand(self):
        """Toggle the expanded detail section."""
        self._expanded = not self._expanded
        self._detail_frame.setVisible(self._expanded)
        self._expand_btn.setText("▲" if self._expanded else "▼")

    def _on_header_clicked(self):
        """Expand/collapse card when any part of the header is clicked."""
        self._toggle_expand()
