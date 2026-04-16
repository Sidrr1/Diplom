"""
TaskDetailView — виджет просмотра деталей задачи.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from datetime import datetime


class TaskDetailView(QWidget):
    """Виджет просмотра деталей задачи."""

    back_requested = Signal()  # Вернуться к списку
    edit_requested = Signal(int)  # Редактировать задачу
    delete_requested = Signal(int)  # Удалить задачу

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_task = None
        self._build_ui()

    def _build_ui(self):
        """Построить UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Кнопка "Назад"
        back_btn = QPushButton("← Назад к списку")
        back_btn.setFont(QFont("Segoe UI", 9))
        back_btn.setFixedHeight(28)
        back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 8);
                border: none;
                border-radius: 6px;
                color: rgba(0, 0, 0, 140);
                text-align: left;
                padding-left: 8px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 15);
                color: rgba(0, 0, 0, 200);
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(back_btn)

        # Название задачи
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI Semibold", 11))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("color: rgba(0, 0, 0, 220);")
        layout.addWidget(self.title_label)

        # Метаданные (приоритет, дедлайн)
        self.meta_label = QLabel()
        self.meta_label.setFont(QFont("Segoe UI", 9))
        self.meta_label.setStyleSheet("color: rgba(0, 0, 0, 140);")
        layout.addWidget(self.meta_label)

        # Описание
        desc_header = QLabel("Описание:")
        desc_header.setFont(QFont("Segoe UI", 9))
        desc_header.setStyleSheet("color: rgba(0, 0, 0, 100);")
        layout.addWidget(desc_header)

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setFont(QFont("Segoe UI", 10))
        self.description_text.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 5);
                border: 1px solid rgba(0, 0, 0, 10);
                border-radius: 6px;
                color: rgba(0, 0, 0, 200);
                padding: 6px;
            }
        """)
        layout.addWidget(self.description_text, 1)

        # Кнопки действий
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        edit_btn = QPushButton("✏ Редактировать")
        edit_btn.setFont(QFont("Segoe UI", 9))
        edit_btn.setFixedHeight(28)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 120, 215, 20);
                border: 1px solid rgba(0, 120, 215, 60);
                border-radius: 6px;
                color: rgba(0, 120, 215, 200);
            }
            QPushButton:hover {
                background: rgba(0, 120, 215, 40);
            }
        """)
        edit_btn.clicked.connect(self._on_edit_clicked)
        actions_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑 Удалить")
        delete_btn.setFont(QFont("Segoe UI", 9))
        delete_btn.setFixedHeight(28)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231, 76, 60, 20);
                border: 1px solid rgba(231, 76, 60, 60);
                border-radius: 6px;
                color: rgba(231, 76, 60, 200);
            }
            QPushButton:hover {
                background: rgba(231, 76, 60, 40);
            }
        """)
        delete_btn.clicked.connect(self._on_delete_clicked)
        actions_layout.addWidget(delete_btn)

        layout.addLayout(actions_layout)

    def show_task(self, task: dict):
        """Показать детали задачи."""
        self._current_task = task

        # Название
        self.title_label.setText(task.get('text', ''))

        # Метаданные
        priority = task.get('priority', 'medium')
        priority_colors = {
            'low': '🟢 Низкий',
            'medium': '🟡 Средний',
            'high': '🔴 Высокий'
        }
        priority_text = priority_colors.get(priority, '⚪ Средний')

        meta_parts = [f"Приоритет: {priority_text}"]

        # Дедлайн
        if task.get('deadline'):
            deadline_text = self._format_deadline(task['deadline'])
            is_overdue = self._is_overdue(task)
            if is_overdue:
                meta_parts.append(f"⏰ <span style='color: #ef4444; font-weight: bold;'>Просрочено: {deadline_text}</span>")
            else:
                meta_parts.append(f"⏰ Дедлайн: {deadline_text}")

        # Статус
        if task.get('completed', 0) == 1:
            meta_parts.append("✓ <span style='color: #10b981;'>Выполнено</span>")

        self.meta_label.setText(" • ".join(meta_parts))

        # Описание
        description = task.get('description', '')
        if description:
            self.description_text.setPlainText(description)
        else:
            self.description_text.setPlainText("(нет описания)")

    def _on_edit_clicked(self):
        """Редактировать задачу."""
        if self._current_task:
            self.edit_requested.emit(self._current_task['id'])

    def _on_delete_clicked(self):
        """Удалить задачу."""
        if self._current_task:
            self.delete_requested.emit(self._current_task['id'])

    def _format_deadline(self, deadline_str: str) -> str:
        """Форматировать дедлайн."""
        try:
            deadline = datetime.fromisoformat(deadline_str)
            return deadline.strftime('%d.%m.%Y %H:%M')
        except:
            return deadline_str

    def _is_overdue(self, task: dict) -> bool:
        """Проверить просрочен ли дедлайн."""
        if not task.get('deadline'):
            return False

        try:
            deadline = datetime.fromisoformat(task['deadline'])
            return deadline < datetime.now() and task.get('completed', 0) == 0
        except:
            return False
