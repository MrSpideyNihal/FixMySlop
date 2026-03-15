"""
MainWindow — the outer shell.
Contains: sidebar navigation + stacked panel area.
All heavy logic runs in background QThreads — UI never freezes.
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QStackedWidget, QPushButton, QVBoxLayout, QLabel,
)
from PyQt5.QtCore import Qt
from ui.panels.home_panel import HomePanel
from ui.panels.scan_panel import ScanPanel
from ui.panels.report_panel import ReportPanel
from ui.panels.fix_panel import FixPanel
from ui.panels.settings_panel import SettingsPanel
from ui.panels.about_panel import AboutPanel
from ui.widgets.toast import ToastManager
from ui.theme import apply_theme
from utils.config import Config
from macros import APP_NAME, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, SIDEBAR_WIDTH


class MainWindow(QMainWindow):
    """
    Main application window.
    Sidebar on left, panel stack on right.
    Panels communicate through signals — never direct calls.
    """

    def __init__(self, config: Config):
        """Initialize the main window with config."""
        super().__init__()
        self.config = config
        self.toast = ToastManager(self)
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._navigate(0)  # Start on Home

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1280, 800)

    def _build_ui(self):
        """Build the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        # Panel stack
        self.stack = QStackedWidget()
        self.home_panel = HomePanel(self.config)
        self.scan_panel = ScanPanel(self.config)
        self.report_panel = ReportPanel(self.config)
        self.fix_panel = FixPanel(self.config)
        self.settings_panel = SettingsPanel(self.config)
        self.about_panel = AboutPanel()

        for panel in [
            self.home_panel, self.scan_panel, self.report_panel,
            self.fix_panel, self.settings_panel, self.about_panel,
        ]:
            self.stack.addWidget(panel)

        layout.addWidget(self.stack, 1)

    def _build_sidebar(self) -> QWidget:
        """Build the navigation sidebar."""
        sidebar = QWidget()
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 24, 12, 24)
        layout.setSpacing(4)

        # Logo
        logo = QLabel(APP_NAME)
        logo.setObjectName("SidebarLogo")
        layout.addWidget(logo)
        layout.addSpacing(16)

        # Navigation buttons
        self._nav_buttons = {}
        nav_items = [
            ("Home", "🏠"),
            ("Scan", "🔍"),
            ("Report", "📊"),
            ("Fix", "🔧"),
            ("Settings", "⚙️"),
            ("About", "ℹ️"),
        ]

        for idx, (label, icon) in enumerate(nav_items):
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, i=idx: self._navigate(i))
            self._nav_buttons[idx] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Version at bottom
        from macros import APP_VERSION
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet("color: #546e7a; font-size: 11px;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        return sidebar

    def _navigate(self, index: int):
        """Switch to the panel at the given index."""
        self.stack.setCurrentIndex(index)
        for idx, btn in self._nav_buttons.items():
            btn.setChecked(idx == index)

    def _connect_signals(self):
        """Wire up inter-panel signals."""
        # Home quick actions
        self.home_panel.navigate_scan.connect(lambda: self._navigate(1))
        self.home_panel.navigate_settings.connect(lambda: self._navigate(4))

        # Scan complete → load report + fix panels
        self.scan_panel.scan_complete.connect(self._on_scan_complete)
        self.scan_panel.scan_failed.connect(
            lambda msg: self.toast.error(msg)
        )

        # Report → fix
        self.report_panel.fix_requested.connect(self._on_fix_requested)

        # Settings → theme change
        self.settings_panel.theme_changed.connect(self._on_theme_changed)
        self.settings_panel.font_size_changed.connect(self._on_font_size_changed)

    def _on_scan_complete(self, report):
        """Handle scan completion — load results and switch panels."""
        self.report_panel.load_report(report)
        self.fix_panel.load_report(report)
        self._navigate(2)  # Switch to Report panel
        self.toast.success(
            f"Scan complete — {len(report.issues)} issues found"
        )

    def _on_fix_requested(self, issue):
        """Switch to fix panel with the selected issue."""
        self._navigate(3)

    def _on_theme_changed(self, theme: str):
        """Apply a new theme to the application."""
        from PyQt5.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp:
            apply_theme(qapp, theme, self.config.font_size)
        self.toast.info(f"Theme changed to {theme}")

    def _on_font_size_changed(self, font_size: int):
        """Apply updated font size immediately across the application."""
        from PyQt5.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp:
            apply_theme(qapp, self.config.theme, font_size)
        self.toast.info(f"Font size set to {font_size}px")
