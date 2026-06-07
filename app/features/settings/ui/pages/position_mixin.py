"""Позиционирование диалога настроек."""
from PySide6.QtWidgets import QApplication


class PositionMixin:
    """Умное позиционирование диалога настроек относительно родительского окна."""

    def smart_position(self, parent_geo):
        """Позиционирует диалог рядом с родительским окном в свободном месте."""
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        w, h = self.width(), self.height()
        cy = parent_geo.top() + (parent_geo.height() - h) // 2
        cx = parent_geo.left() + (parent_geo.width() - w) // 2

        candidates = [
            (parent_geo.left() - w - 12, cy),
            (parent_geo.right() + 12, cy),
            (cx, parent_geo.top() - h - 12),
            (cx, parent_geo.bottom() + 12),
        ]
        for x, y in candidates:
            if (x >= screen.left() and x + w <= screen.right() and
                    y >= screen.top() and y + h <= screen.bottom()):
                self.move(x, y)
                return
        self.move(screen.center().x() - w // 2, screen.center().y() - h // 2)
