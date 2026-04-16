"""
TaskItem — виджет одной задачи в списке.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor
from datetime import datetime


class TaskItem(QWidget):
    """Один элемент задачи (чекбокс + текст + приоритет)."""

    toggled = Signal(int, bool)  # (task_id, completed)
    double_clicked = Signal(int)  # task_id
    clicked = Signal(int)  # task_id (одиночный клик)

    def __init__(self, task: dict, parent=None):
        super().__init__(parent)
        self.task = task
        self.task_id = task['id']

        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self._build_ui()

    def _build_ui(self):
        """Построить UI задачи."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Чекбокс
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.task.get('completed', 0) == 1)
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox)

        # Текст задачи
        self.text_label = QLabel(self.task.get('text', ''))
        self.text_label.setFont(QFont("Segoe UI", 10))
        self.text_label.setWordWrap(True)

        # Зачёркивание если выполнено
        if self.task.get('completed', 0) == 1:
            font = self.text_label.font()
            font.setStrikeOut(True)
            self.text_label.setFont(font)
            self.text_label.setStyleSheet("color: rgba(0, 0, 0, 100);")
        else:
            self.text_label.setStyleSheet("color: rgba(0, 0, 0, 220);")

        layout.addWidget(self.text_label, 1)

        # Приоритет
        priority = self.task.get('priority', 'medium')
        priority_colors = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴'
        }
        priority_labels = {
            'low': 'LOW',
            'medium': 'MED',
            'high': 'HIGH'
        }

        self.priority_label = QLabel(f"{priority_colors.get(priority, '⚪')} {priority_labels.get(priority, 'MED')}")
        self.priority_label.setFont(QFont("Segoe UI", 8))
        self.priority_label.setStyleSheet("color: rgba(0, 0, 0, 140);")
        layout.addWidget(self.priority_label)

        # Дедлайн (если есть)
        if self.task.get('deadline'):
            deadline_text = self._format_deadline(self.task['deadline'])
            self.deadline_label = QLabel(f"⏰ {deadline_text}")
            self.deadline_label.setFont(QFont("Segoe UI", 8))

            # Проверяем просрочен ли
            if self._is_overdue():
                self.deadline_label.setStyleSheet("color: #ef4444; font-weight: bold;")
            else:
                self.deadline_label.setStyleSheet("color: rgba(0, 0, 0, 140);")

            layout.addWidget(self.deadline_label)

    def _on_toggled(self, checked: bool):
        """Чекбокс переключён."""
        self.toggled.emit(self.task_id, checked)

        # Обновляем стиль текста
        font = self.text_label.font()
        font.setStrikeOut(checked)
        self.text_label.setFont(font)

        if checked:
            self.text_label.setStyleSheet("color: rgba(0, 0, 0, 100);")
        else:
            self.text_label.setStyleSheet("color: rgba(0, 0, 0, 220);")

    def mouseDoubleClickEvent(self, event):
        """Двойной клик → открыть редактор."""
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.task_id)
            event.accept()

    def mousePressEvent(self, event):
        """Одиночный клик → показать детали."""
        if event.button() == Qt.LeftButton:
            # Проверяем, что клик не по чекбоксу
            if not self.checkbox.geometry().contains(event.pos()):
                self.clicked.emit(self.task_id)
                event.accept()
        super().mousePressEvent(event)

    def _format_deadline(self, deadline_str: str) -> str:
        """Форматировать дедлайн в читаемый вид."""
        try:
            deadline = datetime.fromisoformat(deadline_str)
            now = datetime.now()
            delta = deadline - now

            if delta.days < 0:
                return "просрочено"
            elif delta.days == 0:
                hours = delta.seconds // 3600
                if hours == 0:
                    minutes = delta.seconds // 60
                    return f"через {minutes} мин"
                return f"через {hours} ч"
            elif delta.days == 1:
                return f"завтра {deadline.strftime('%H:%M')}"
            elif delta.days < 7:
                return f"через {delta.days} дн"
            else:
                return deadline.strftime('%d.%m %H:%M')
        except:
            return deadline_str

    def _is_overdue(self) -> bool:
        """Проверить просрочен ли дедлайн."""
        if not self.task.get('deadline'):
            return False

        try:
            deadline = datetime.fromisoformat(self.task['deadline'])
            return deadline < datetime.now() and self.task.get('completed', 0) == 0
        except:
            return False
