# app/ui/ocr_overlay.py
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QPixmap, QScreen


class OcrOverlay(QWidget):
    """Полноэкранный полупрозрачный оверлей для выделения области скриншота."""
    area_selected = Signal(QPixmap)   # скриншот выделенной области
    cancelled     = Signal()

    def __init__(self):
        super().__init__()
        self._start  = QPoint()
        self._end    = QPoint()
        self._active = False

        # Захватываем весь экран как фон
        screen = QApplication.primaryScreen()
        self._bg = screen.grabWindow(0)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setGeometry(screen.geometry())
        self.showFullScreen()

    # ── Отрисовка ────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)

        # Фон — скриншот экрана затемнённый
        p.drawPixmap(0, 0, self._bg)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))

        if self._active and not self._start.isNull() and not self._end.isNull():
            rect = self._selection_rect()

            # Вырезаем выделенную область — светлее
            p.drawPixmap(rect, self._bg, rect)

            # Рамка
            pen = QPen(QColor("#0078d7"), 2)
            p.setPen(pen)
            p.drawRect(rect)

            # Размер выделения
            p.setPen(QColor("white"))
            p.drawText(
                rect.x() + 4,
                rect.y() - 6 if rect.y() > 20 else rect.y() + rect.height() + 16,
                f"{rect.width()} × {rect.height()}"
            )

    # ── Мышь ─────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._start  = e.position().toPoint()
            self._end    = e.position().toPoint()
            self._active = True

    def mouseMoveEvent(self, e):
        if self._active:
            self._end = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._active:
            self._end    = e.position().toPoint()
            self._active = False
            rect = self._selection_rect()
            if rect.width() > 10 and rect.height() > 10:
                cropped = self._bg.copy(rect)
                self.close()
                self.area_selected.emit(cropped)
            else:
                self.close()
                self.cancelled.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
            self.cancelled.emit()

    # ── Утилита ──────────────────────────────────────────────────────────

    def _selection_rect(self) -> QRect:
        return QRect(self._start, self._end).normalized()