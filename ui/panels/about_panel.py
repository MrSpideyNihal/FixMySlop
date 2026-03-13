"""
About panel — version info, license, links, and action buttons.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QSizePolicy,
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from macros import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_URL,
    APP_LICENSE, APP_AUTHOR, USER_GUIDE_PATH,
)


class AboutPanel(QWidget):
    """About panel showing app info, license, and action buttons."""

    def __init__(self, parent=None):
        """Initialize the about panel."""
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        """Build the about panel layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop)

        # ─── Logo / App Name ────────────────────────────────────────────
        name_label = QLabel(APP_NAME)
        name_label.setStyleSheet(
            "font-size: 42px; font-weight: bold; color: #7c6af7; "
            "letter-spacing: 2px;"
        )
        layout.addWidget(name_label)

        # Tagline
        tagline = QLabel(APP_DESCRIPTION)
        tagline.setStyleSheet(
            "font-size: 16px; color: #8892a4; font-style: italic; "
            "padding-bottom: 4px;"
        )
        layout.addWidget(tagline)

        layout.addSpacing(24)

        # ─── Info Card ───────────────────────────────────────────────────
        info_frame = QFrame()
        info_frame.setObjectName("CardWidget")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(24, 20, 24, 20)

        info_items = [
            ("Version", f"v{APP_VERSION}"),
            ("Made by", APP_AUTHOR),
            ("License", f"{APP_LICENSE} — Open Source"),
            ("GitHub", f'<a href="{APP_URL}" style="color: #7c6af7;">{APP_URL}</a>'),
        ]

        for label_text, value in info_items:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            key = QLabel(label_text)
            key.setFixedWidth(80)
            key.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #8892a4;"
            )
            row_layout.addWidget(key)

            val = QLabel(value)
            val.setStyleSheet("font-size: 13px; color: #e2e8f0;")
            val.setTextFormat(Qt.RichText)
            val.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
            )
            val.setOpenExternalLinks(True)
            row_layout.addWidget(val, 1)

            info_layout.addWidget(row)

        layout.addWidget(info_frame)

        layout.addSpacing(24)

        # ─── Description ─────────────────────────────────────────────────
        about_text = QLabel(
            f"{APP_NAME} is a fully open-source, cross-platform desktop "
            "application that scans codebases — especially AI-generated code "
            "— for bugs, security vulnerabilities, technical debt, and bad "
            "patterns.\n\n"
            "It generates a detailed audit report, suggests LLM-powered fixes "
            "with code diffs, and can optionally apply them. Runs 100% "
            "locally with no cloud dependencies."
        )
        about_text.setWordWrap(True)
        about_text.setStyleSheet(
            "font-size: 13px; color: #c0c8d8; line-height: 1.6;"
        )
        layout.addWidget(about_text)

        layout.addSpacing(24)

        # ─── Tech Stack ──────────────────────────────────────────────────
        tech_label = QLabel("Built With")
        tech_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(tech_label)

        techs = [
            "Python 3.10+",
            "PyQt5 (GUI)  •  Typer + Rich (CLI)",
            "OpenAI-compatible LLMs (Ollama / llama.cpp / vLLM)",
            "Ruff, Bandit, Semgrep (static analysis)",
        ]
        for tech in techs:
            tech_item = QLabel(f"  •  {tech}")
            tech_item.setStyleSheet("font-size: 12px; color: #8892a4;")
            layout.addWidget(tech_item)

        layout.addStretch()

        # ─── Action Buttons ──────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        guide_btn = QPushButton("📖  Open User Guide")
        guide_btn.setObjectName("PrimaryButton")
        guide_btn.setFixedHeight(44)
        guide_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        guide_btn.clicked.connect(self._open_user_guide)
        btn_row.addWidget(guide_btn)

        github_btn = QPushButton("🌐  View on GitHub")
        github_btn.setObjectName("SecondaryButton")
        github_btn.setFixedHeight(44)
        github_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        github_btn.clicked.connect(self._open_github)
        btn_row.addWidget(github_btn)

        layout.addLayout(btn_row)

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _open_user_guide(self):
        """Open USER_GUIDE.md in the system default application."""
        url = QUrl.fromLocalFile(str(USER_GUIDE_PATH))
        QDesktopServices.openUrl(url)

    def _open_github(self):
        """Open the GitHub repository URL in the default browser."""
        QDesktopServices.openUrl(QUrl(APP_URL))
