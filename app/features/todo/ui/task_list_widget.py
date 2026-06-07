"""
Виджет прокручиваемого списка задач для рабочего режима заметки.

Загружает задачи через TaskService, поддерживает фильтры и очистку выполненных.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor
from app.features.todo.ui.task_item import TaskItem
from app.features.todo.core.task_service import TaskService


class TaskListWidget(QWidget):
    """Список задач для рабочего режима."""

    task_toggled = Signal(int, bool)  # (task_id, completed)
    task_double_clicked = Signal(int)  # task_id
    task_clicked = Signal(int)  # task_id (одиночный клик)
    add_task_requested = Signal()

    def __init__(self, note_id: int, task_service: TaskService, parent=None):
        """
        Args:
            note_id: ID заметки, к которой привязаны задачи
            task_service: сервис доступа к задачам в БД
            parent: родительский виджет
        """
        super().__init__(parent)
        self.note_id = note_id
        self.task_service = task_service
        self._task_widgets = []

        self._build_ui()
        self.load_tasks()

    def _build_ui(self):
        """Построить UI."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # Scroll area для задач
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        # Контейнер для задач
        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(2)
        self.tasks_layout.addStretch()

        scroll.setWidget(self.tasks_container)
        root.addWidget(scroll, 1)

        # Кнопка "Очистить выполненные"
        self.clear_btn = QPushButton("🗑 Очистить выполненные")
        self.clear_btn.setFont(QFont("Segoe UI", 9))
        self.clear_btn.setFixedHeight(28)
        self.clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231, 76, 60, 15);
                border: 1px solid rgba(231, 76, 60, 40);
                border-radius: 6px;
                color: rgba(231, 76, 60, 180);
            }
            QPushButton:hover {
                background: rgba(231, 76, 60, 30);
                color: rgba(231, 76, 60, 220);
            }
            QPushButton:disabled {
                background: rgba(0, 0, 0, 5);
                border: 1px solid rgba(0, 0, 0, 10);
                color: rgba(0, 0, 0, 60);
            }
        """)
        self.clear_btn.clicked.connect(self._clear_completed)
        root.addWidget(self.clear_btn)

    def load_tasks(self, filters: dict = None):
        """
        Перезагрузить список задач из БД.

        Args:
            filters: необязательные фильтры для TaskService.get_tasks
        """
        # Очищаем старые виджеты
        for widget in self._task_widgets:
            widget.deleteLater()
        self._task_widgets.clear()

        # Загружаем задачи
        tasks = self.task_service.get_tasks(self.note_id, filters)

        # Создаём виджеты
        for task in tasks:
            task_widget = TaskItem(task)
            task_widget.toggled.connect(self._on_task_toggled)
            task_widget.double_clicked.connect(self.task_double_clicked.emit)
            task_widget.clicked.connect(self.task_clicked.emit)  # Одиночный клик

            # Вставляем перед stretch
            self.tasks_layout.insertWidget(len(self._task_widgets), task_widget)
            self._task_widgets.append(task_widget)

        # Обновляем состояние кнопки очистки
        self._update_clear_button()

        print(f"[task_list] Loaded {len(tasks)} tasks for note {self.note_id}")

    def _on_task_toggled(self, task_id: int, completed: bool):
        """Задача переключена."""
        # Обновляем в БД
        self.task_service.update_task(task_id, completed=1 if completed else 0)

        # Пробрасываем сигнал наверх (для обновления прогресса)
        self.task_toggled.emit(task_id, completed)

        # Обновляем состояние кнопки очистки
        self._update_clear_button()

        print(f"[task_list] Task {task_id} toggled: {completed}")

    def _clear_completed(self):
        """Удалить все выполненные задачи."""
        # Получаем все задачи
        tasks = self.task_service.get_tasks(self.note_id)
        completed_count = 0

        # Удаляем выполненные
        for task in tasks:
            if task.get('completed', 0) == 1:
                self.task_service.delete_task(task['id'])
                completed_count += 1

        if completed_count > 0:
            print(f"[task_list] Cleared {completed_count} completed tasks")
            # Перезагружаем список
            self.load_tasks()
            # Пробрасываем сигнал для обновления прогресса
            self.task_toggled.emit(0, False)

    def _update_clear_button(self):
        """Обновить состояние кнопки очистки."""
        # Проверяем есть ли выполненные задачи
        tasks = self.task_service.get_tasks(self.note_id)
        has_completed = any(task.get('completed', 0) == 1 for task in tasks)
        self.clear_btn.setEnabled(has_completed)

    def add_task(self, text: str, **kwargs):
        """
        Создать задачу и обновить список.

        Args:
            text: название задачи
            **kwargs: дополнительные поля (description, priority, deadline…)

        Returns:
            ID созданной задачи
        """
        task_id = self.task_service.create_task(self.note_id, text, **kwargs)
        print(f"[task_list] Created task {task_id}: {text}")

        # Перезагружаем список
        self.load_tasks()

        return task_id

    def get_task_count(self) -> int:
        """Получить количество задач."""
        return len(self._task_widgets)
