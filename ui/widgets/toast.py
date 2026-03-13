"""
Toast widget — non-blocking notification toasts (success/error/info).
Appears at the top-right corner and auto-dismisses.
"""
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor


class Toast(QLabel):
    """A single toast notification that auto-dismisses."""

    STYLES = {
        "success": ("background: #1f3c1f; color: #69db7c; border: 1px solid #2d5a2d;", "✓"),
        "error": ("background: #3c1f1f; color: #ff6b6b; border: 1px solid #5a2d2d;", "✗"),
        "info": ("background: #1f2a3c; color: #4FC3F7; border: 1px solid #2d3a5a;", "ℹ"),
        "warning": ("background: #3c3a1f; color: #FFD700; border: 1px solid #5a572d;", "⚠"),
    }

    def __init__(self, message: str, toast_type: str = "info", parent=None, duration_ms: int = 3000):
        """Initialize toast with message, type, and auto-dismiss duration."""
        super().__init__(parent)
        style, icon = self.STYLES.get(toast_type, self.STYLES["info"])
        self.setText(f"  {icon}  {message}")
        self.setStyleSheet(
            f"{style} border-radius: 8px; padding: 12px 20px; "
            f"font-size: 13px; font-weight: 500;"
        )
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setFixedHeight(44)
        self.setMinimumWidth(250)
        self.adjustSize()

        # Opacity effect for fade animation
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)

        # Fade in
        self._fade_in = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.start()

        # Auto dismiss
        QTimer.singleShot(duration_ms, self._dismiss)

    def _dismiss(self):
        """Fade out and remove the toast."""
        self._fade_out = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self.deleteLater)
        self._fade_out.start()


class ToastManager:
    """
    Manages toast notifications for a parent window.
    Stacks toasts vertically at the top-right corner.
    """

    def __init__(self, parent: QWidget):
        """Initialize toast manager with a parent window."""
        self._parent = parent
        self._toasts: list[Toast] = []
        self._offset_y = 16

    def _show_toast(self, message: str, toast_type: str):
        """Create and position a toast."""
        toast = Toast(message, toast_type, self._parent)
        toast.show()

        # Position at top-right
        x = self._parent.width() - toast.width() - 20
        y = self._offset_y + len(self._toasts) * 56
        toast.move(x, y)

        self._toasts.append(toast)
        toast.destroyed.connect(lambda: self._remove_toast(toast))

    def _remove_toast(self, toast):
        """Remove a toast from the stack."""
        if toast in self._toasts:
            self._toasts.remove(toast)

    def success(self, message: str):
        """Show a success toast."""
        self._show_toast(message, "success")

    def error(self, message: str):
        """Show an error toast."""
        self._show_toast(message, "error")

    def info(self, message: str):
        """Show an info toast."""
        self._show_toast(message, "info")

    def warning(self, message: str):
        """Show a warning toast."""
        self._show_toast(message, "warning")
