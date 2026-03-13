"""
Theme — loads and applies QSS stylesheets to the QApplication.
Supports dark and light themes, loaded from assets/styles/.
"""
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from utils.logger import get_logger
from macros import ROOT_DIR, DEFAULT_THEME

logger = get_logger(__name__)

STYLES_DIR = ROOT_DIR / "ui" / "assets" / "styles"


def apply_theme(app: QApplication, theme: str = DEFAULT_THEME):
    """Load and apply a QSS theme stylesheet to the app."""
    qss_file = STYLES_DIR / f"{theme}.qss"
    if not qss_file.exists():
        logger.warning("Theme file not found: %s — falling back to dark", qss_file)
        qss_file = STYLES_DIR / "dark.qss"

    if qss_file.exists():
        stylesheet = qss_file.read_text(encoding="utf-8")
        app.setStyleSheet(stylesheet)
        logger.info("Applied theme: %s", theme)
    else:
        logger.error("No theme files found in %s", STYLES_DIR)


def get_available_themes() -> list[str]:
    """Return list of available theme names (without extension)."""
    if not STYLES_DIR.exists():
        return []
    return [f.stem for f in STYLES_DIR.glob("*.qss")]
