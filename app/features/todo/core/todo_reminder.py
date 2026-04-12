"""
Менеджер напоминаний для todo задач.
"""
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from typing import Dict


class ToastNotification(QWidget):
    """Всплывающее уведомление в правом нижнем углу."""

    def __init__(self, task: Dict, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(320, 100)
        self._build_ui(task)
        self._position_bottom_right()
        self._animate_in()

    def _build_ui(self, task: Dict):
        """Построить UI уведомления."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Карточка
        card = QWidget()
        card.setObjectName("toast_card")
        card.setStyleSheet("""
            QWidget#toast_card {
                background: rgba(18, 18, 18, 240);
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 10);
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(6)

        # Заголовок
        title_label = QLabel("⏰ Напоминание")
        title_label.setFont(QFont("Segoe UI Semibold", 10))
        title_label.setStyleSheet("color: #0078d7;")
        card_layout.addWidget(title_label)

        # Текст задачи
        task_label = QLabel(task['title'])
        task_label.setFont(QFont("Segoe UI", 10))
        task_label.setStyleSheet("color: white;")
        task_label.setWordWrap(True)
        card_layout.addWidget(task_label)

        # Приоритет
        priority_colors = {1: "#e74c3c", 2: "#f39c12", 3: "#27ae60"}
        priority_names = {1: "Высокий", 2: "Средний", 3: "Низкий"}
        priority = task.get('priority', 3)

        priority_label = QLabel(f"Приоритет: {priority_names[priority]}")
        priority_label.setFont(QFont("Segoe UI", 9))
        priority_label.setStyleSheet(f"color: {priority_colors[priority]};")
        card_layout.addWidget(priority_label)

        layout.addWidget(card)

    def _position_bottom_right(self):
        """Позиционировать в правом нижнем углу."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 60
        self.move(x, y)

    def _animate_in(self):
        """Анимация появления."""
        self.setWindowOpacity(0.0)
        self.show()

        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

        # Автоматически закрыть через 5 секунд
        QTimer.singleShot(5000, self._animate_out)

    def _animate_out(self):
        """Анимация исчезновения."""
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.InCubic)
        self.anim.finished.connect(self.close)
        self.anim.start()


class ReminderManager(QObject):
    """Менеджер напоминаний для задач."""

    reminder_triggered = Signal(dict)  # task_dict

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_reminders)
        self._active_toasts = []

    def start(self):
        """Запустить проверку напоминаний каждые 60 секунд."""
        self._timer.start(60000)  # 60 секунд
        print("[reminder] Started checking reminders every 60 seconds")

    def stop(self):
        """Остановить проверку."""
        self._timer.stop()
        print("[reminder] Stopped")

    def _check_reminders(self):
        """Проверить задачи с истёкшим временем напоминания."""
        tasks = self.db.get_reminders_due()

        for task in tasks:
            print(f"[reminder] Triggering reminder for task #{task['id']}: {task['title']}")
            self.reminder_triggered.emit(task)

            # Показать toast уведомление
            self._show_toast(task)

            # Очистить напоминание чтобы не срабатывало повторно
            self.db.clear_reminder(task['id'])

    def _show_toast(self, task: Dict):
        """Показать toast уведомление."""
        toast = ToastNotification(task)
        self._active_toasts.append(toast)

        # Удалить из списка после закрытия
        toast.destroyed.connect(lambda: self._active_toasts.remove(toast) if toast in self._active_toasts else None)
