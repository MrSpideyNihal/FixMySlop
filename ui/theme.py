"""
Theme — loads and applies QSS stylesheets to the QApplication.
Supports dark and light themes, loaded from assets/styles/.
"""
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from utils.logger import get_logger
from macros import (
    ROOT_DIR,
    DEFAULT_THEME,
    DEFAULT_FONT_SIZE,
    MIN_FONT_SIZE,
    MAX_FONT_SIZE,
)

logger = get_logger(__name__)

STYLES_DIR = ROOT_DIR / "ui" / "assets" / "styles"


def _clamp_font_size(font_size: int) -> int:
    """Clamp configured font size to a safe, readable range."""
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(font_size)))


def _font_size_overrides(font_size: int) -> str:
    """Build a small override stylesheet to scale UI text consistently."""
    base = _clamp_font_size(font_size)
    code_font = max(base - 1, MIN_FONT_SIZE)
    title_font = base + 7
    subtitle_font = base + 1
    primary_button_font = base + 1
    return (
        "\n"
        "QMainWindow, QWidget {"
        f"font-size: {base}px;"
        "}\n"
        "#NavButton {"
        f"font-size: {base}px;"
        "}\n"
        "QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox {"
        f"font-size: {base}px;"
        "}\n"
        "QTextEdit, QPlainTextEdit {"
        f"font-size: {code_font}px;"
        "}\n"
        "#PrimaryButton {"
        f"font-size: {primary_button_font}px;"
        "}\n"
        "#SecondaryButton, #DangerButton {"
        f"font-size: {base}px;"
        "}\n"
        "#SectionTitle {"
        f"font-size: {title_font}px;"
        "}\n"
        "#SectionSubtitle {"
        f"font-size: {subtitle_font}px;"
        "}\n"
    )


def apply_theme(
    app: QApplication,
    theme: str = DEFAULT_THEME,
    font_size: int = DEFAULT_FONT_SIZE,
):
    """Load and apply a QSS theme stylesheet to the app."""
    qss_file = STYLES_DIR / f"{theme}.qss"
    if not qss_file.exists():
        logger.warning("Theme file not found: %s — falling back to dark", qss_file)
        qss_file = STYLES_DIR / "dark.qss"

    if qss_file.exists():
        stylesheet = qss_file.read_text(encoding="utf-8")
        final_stylesheet = f"{stylesheet}\n{_font_size_overrides(font_size)}"
        app.setStyleSheet(final_stylesheet)
        logger.info(
            "Applied theme: %s (font size: %spx)",
            theme,
            _clamp_font_size(font_size),
        )
    else:
        logger.error("No theme files found in %s", STYLES_DIR)


def get_available_themes() -> list[str]:
    """Return list of available theme names (without extension)."""
    if not STYLES_DIR.exists():
        return []
    return [f.stem for f in STYLES_DIR.glob("*.qss")]
