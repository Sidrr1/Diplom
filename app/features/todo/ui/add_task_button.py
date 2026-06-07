"""
Плавающая кнопка "+" для добавления задач (только в work режиме).
Стиль и позиционирование как у плавающих кнопок плеера (ClickThroughToggle, SettingsToggle).
"""
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor


class AddTaskButton(QWidget):
    """Плавающая кнопка для добавления задач — позиционируется рядом со стикером."""

    add_task_requested = Signal()

    def __init__(self, parent=None):
        """Создать плавающую кнопку «+» для добавления задачи."""
        super().__init__(parent)
        self._drag_pos = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(32, 32)
        self._build_ui()

    def _build_ui(self):
        """Построить UI кнопки."""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        btn = QPushButton("+")
        btn.setFixedSize(28, 28)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setToolTip("Добавить задачу")
        btn.clicked.connect(self._on_clicked)

        btn.setStyleSheet("""
            QPushButton {
                background: rgba(30,30,30,200);
                color: #aaa;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(50,50,50,220);
                color: white;
            }
            QPushButton:pressed {
                background: rgba(0,120,215,200);
                color: white;
            }
        """)

        lay.addWidget(btn, 0, Qt.AlignCenter)

    def _on_clicked(self):
        """Клик по кнопке."""
        self.add_task_requested.emit()

    def reposition(self, note_geo):
        """
        Автоматически позиционировать кнопку рядом со стикером.
        Пробует несколько позиций-кандидатов и выбирает первую свободную.

        Args:
            note_geo: QRect геометрия стикера
        """
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()

        # Кандидаты для позиционирования (в порядке приоритета):
        # 1. Справа снизу (дефолт)
        # 2. Слева снизу
        # 3. Справа сверху
        # 4. Слева сверху
        # 5. Снизу по центру
        # 6. Сверху по центру
        candidates = [
            (note_geo.right() + 2, note_geo.bottom() - h),           # справа снизу
            (note_geo.left() - w - 2, note_geo.bottom() - h),        # слева снизу
            (note_geo.right() + 2, note_geo.top()),                  # справа сверху
            (note_geo.left() - w - 2, note_geo.top()),               # слева сверху
            (note_geo.left() + (note_geo.width() - w) // 2, note_geo.bottom() + 2),  # снизу по центру
            (note_geo.left() + (note_geo.width() - w) // 2, note_geo.top() - h - 2), # сверху по центру
        ]

        for x, y in candidates:
            if (x >= screen.left() and x + w <= screen.right() and
                    y >= screen.top() and y + h <= screen.bottom()):
                self.move(x, y)
                return

        # Если ни одна позиция не подошла — ставим справа снизу (может выйти за экран)
        self.move(note_geo.right() + 2, note_geo.bottom() - h)

    def mousePressEvent(self, event):
        """Начало перетаскивания."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Перетаскивание кнопки."""
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Конец перетаскивания."""
        self._drag_pos = None
