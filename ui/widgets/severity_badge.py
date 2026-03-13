"""
Severity badge widget — colored label showing CRITICAL/HIGH/MEDIUM/LOW/INFO.
"""
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from macros import SEVERITY_COLORS


class SeverityBadge(QLabel):
    """A colored badge label for issue severity levels."""

    def __init__(self, severity: str, parent=None):
        """Initialize badge with severity level text and color."""
        super().__init__(severity, parent)
        self.setAlignment(Qt.AlignCenter)
        color = SEVERITY_COLORS.get(severity, "#90A4AE")
        self.setStyleSheet(
            f"background-color: {color}20; "
            f"color: {color}; "
            f"border: 1px solid {color}40; "
            f"border-radius: 4px; "
            f"padding: 2px 8px; "
            f"font-size: 11px; "
            f"font-weight: bold; "
        )
        self.setFixedHeight(22)

    def set_severity(self, severity: str):
        """Update the badge to a new severity level."""
        self.setText(severity)
        color = SEVERITY_COLORS.get(severity, "#90A4AE")
        self.setStyleSheet(
            f"background-color: {color}20; "
            f"color: {color}; "
            f"border: 1px solid {color}40; "
            f"border-radius: 4px; "
            f"padding: 2px 8px; "
            f"font-size: 11px; "
            f"font-weight: bold; "
        )
