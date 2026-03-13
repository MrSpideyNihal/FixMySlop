"""
Issue card widget — expandable card showing a single issue's details.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.widgets.severity_badge import SeverityBadge
from core.issue import Issue


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

        # Header row: severity badge + title + expand button
        header = QHBoxLayout()
        header.setSpacing(8)

        self._badge = SeverityBadge(self.issue.severity)
        header.addWidget(self._badge)

        title = QLabel(self.issue.title)
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header.addWidget(title)

        self._expand_btn = QPushButton("▼")
        self._expand_btn.setFixedSize(28, 28)
        self._expand_btn.setStyleSheet(
            "border: none; color: #8892a4; font-size: 12px;"
        )
        self._expand_btn.clicked.connect(self._toggle_expand)
        header.addWidget(self._expand_btn)
        layout.addLayout(header)

        # File info
        file_label = QLabel(
            f"{self.issue.file_path}  •  Lines {self.issue.line_start}-{self.issue.line_end}"
            f"  •  {self.issue.category}  •  {self.issue.source_tool}"
        )
        file_label.setStyleSheet("color: #8892a4; font-size: 11px;")
        layout.addWidget(file_label)

        # Description
        desc = QLabel(self.issue.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #c0c8d8; font-size: 12px;")
        layout.addWidget(desc)

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

            evidence_code = QLabel(self.issue.evidence)
            evidence_code.setStyleSheet(
                "background: #141820; padding: 8px; border-radius: 4px; "
                "font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #e2e8f0;"
            )
            evidence_code.setWordWrap(True)
            evidence_code.setTextInteractionFlags(Qt.TextSelectableByMouse)
            detail_layout.addWidget(evidence_code)

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
