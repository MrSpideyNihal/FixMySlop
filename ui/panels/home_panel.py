"""
Home panel — welcome screen with quick-start actions and recent scans.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea,
)
from PyQt5.QtCore import Qt, pyqtSignal
from utils.config import Config
from macros import APP_NAME, APP_DESCRIPTION, APP_VERSION


class _QuickActionCard(QFrame):
    """A clickable quick-action card for the home screen."""

    clicked = pyqtSignal()

    def __init__(self, title: str, description: str, icon_text: str, parent=None):
        """Initialize the quick action card."""
        super().__init__(parent)
        self.setObjectName("CardWidget")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        icon = QLabel(icon_text)
        icon.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 11px; color: #8892a4;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

    def mousePressEvent(self, event):
        """Emit clicked signal on mouse press."""
        self.clicked.emit()
        super().mousePressEvent(event)


class HomePanel(QWidget):
    """Welcome screen with branding, quick actions, and recent scans."""

    navigate_scan = pyqtSignal()
    navigate_settings = pyqtSignal()

    def __init__(self, config: Config, parent=None):
        """Initialize the home panel."""
        super().__init__(parent)
        self.config = config
        self._build_ui()

    def _build_ui(self):
        """Build the home screen layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(24)

        # Hero section
        hero_label = QLabel(APP_NAME)
        hero_label.setObjectName("SectionTitle")
        hero_label.setStyleSheet(
            "font-size: 32px; font-weight: bold; color: #7c6af7;"
        )
        layout.addWidget(hero_label)

        tagline = QLabel(APP_DESCRIPTION)
        tagline.setObjectName("SectionSubtitle")
        tagline.setStyleSheet("font-size: 16px; color: #8892a4;")
        layout.addWidget(tagline)

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet("font-size: 12px; color: #546e7a;")
        layout.addWidget(version_label)

        layout.addSpacing(16)

        # Quick actions
        actions_label = QLabel("Quick Actions")
        actions_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(actions_label)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        scan_card = _QuickActionCard(
            "Scan Repository",
            "Select a folder and run a full audit scan",
            "🔍",
        )
        scan_card.clicked.connect(self.navigate_scan.emit)
        cards_layout.addWidget(scan_card)

        settings_card = _QuickActionCard(
            "Configure Model",
            "Set up your local LLM backend and preferences",
            "⚙️",
        )
        settings_card.clicked.connect(self.navigate_settings.emit)
        cards_layout.addWidget(settings_card)

        docs_card = _QuickActionCard(
            "Documentation",
            "Learn about FixMySlop features and workflows",
            "📖",
        )
        cards_layout.addWidget(docs_card)

        layout.addLayout(cards_layout)

        # Recent scans
        layout.addSpacing(24)
        recent_label = QLabel("Recent Scans")
        recent_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(recent_label)

        recent_paths = self.config.get("recent_paths", [])
        if recent_paths:
            for path in recent_paths[-5:]:
                path_label = QLabel(f"  →  {path}")
                path_label.setStyleSheet("color: #8892a4; font-size: 12px; padding: 4px 0;")
                layout.addWidget(path_label)
        else:
            no_recent = QLabel("No recent scans. Start your first scan above!")
            no_recent.setStyleSheet("color: #546e7a; font-style: italic;")
            layout.addWidget(no_recent)

        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
