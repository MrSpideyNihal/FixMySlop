"""
GUI application entry point.
Sets up QApplication, loads theme, shows MainWindow.
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui.main_window import MainWindow
from ui.theme import apply_theme
from utils.config import Config
from macros import APP_NAME, APP_VERSION


def launch():
    """Create and launch the FixMySlop PyQt5 application."""
    # High-DPI attributes must be set BEFORE QApplication is created
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    config = Config()
    apply_theme(app, config.theme)

    window = MainWindow(config)
    window.show()
    sys.exit(app.exec_())
