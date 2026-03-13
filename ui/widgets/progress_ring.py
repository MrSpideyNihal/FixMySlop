"""
Progress ring widget — circular animated progress indicator.
"""
import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont


class ProgressRing(QWidget):
    """
    Circular progress indicator with percentage text in the center.
    Supports both determinate (0-100) and indeterminate (spinning) modes.
    """

    def __init__(self, parent=None, size: int = 80, line_width: int = 6):
        """Initialize the progress ring."""
        super().__init__(parent)
        self._size = size
        self._line_width = line_width
        self._value = 0
        self._max_value = 100
        self._indeterminate = False
        self._angle = 0
        self._color = QColor("#7c6af7")
        self._bg_color = QColor("#1e2433")
        self._text_color = QColor("#e2e8f0")

        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._spin)

    def set_value(self, value: int):
        """Set the progress value (0-100)."""
        self._value = max(0, min(value, self._max_value))
        self._indeterminate = False
        if self._timer.isActive():
            self._timer.stop()
        self.update()

    def set_indeterminate(self, spinning: bool = True):
        """Toggle indeterminate (spinning) mode."""
        self._indeterminate = spinning
        if spinning and not self._timer.isActive():
            self._timer.start(30)
        elif not spinning and self._timer.isActive():
            self._timer.stop()
        self.update()

    def _spin(self):
        """Advance the spin angle for indeterminate mode."""
        self._angle = (self._angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        """Paint the progress ring."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = self._line_width / 2 + 2
        rect = QRectF(margin, margin, self._size - 2 * margin, self._size - 2 * margin)

        # Background circle
        bg_pen = QPen(self._bg_color, self._line_width)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Progress arc
        fg_pen = QPen(self._color, self._line_width)
        fg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(fg_pen)

        if self._indeterminate:
            start = self._angle * 16
            span = 90 * 16
            painter.drawArc(rect, start, span)
        else:
            span = int(-self._value / self._max_value * 360 * 16)
            painter.drawArc(rect, 90 * 16, span)

            # Center text
            if not self._indeterminate:
                painter.setPen(self._text_color)
                font = QFont("Segoe UI", self._size // 6, QFont.Bold)
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, f"{self._value}%")

        painter.end()

    def set_color(self, color: str):
        """Set the progress ring color from a hex string."""
        self._color = QColor(color)
        self.update()
