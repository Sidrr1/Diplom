"""
Контроллер для Todo модуля.
"""
from PySide6.QtCore import QObject


class TodoController(QObject):
    """Контроллер связывает TodoView с TodoDB и ReminderManager."""

    def __init__(self, view):
        super().__init__()
        self._view = view

        # Инициализация БД и напоминаний
        from app.features.todo.core.todo_db import TodoDB
        from app.features.todo.core.todo_reminder import ReminderManager

        self.db = TodoDB()
        self.reminder_manager = ReminderManager(self.db)

        # Подключаем сигналы view
        view.add_task.connect(self._on_add_task)
        view.complete_task.connect(self._on_complete_task)
        view.delete_task.connect(self._on_delete_task)

        # Подключаем напоминания
        self.reminder_manager.reminder_triggered.connect(self._on_reminder)

        # Запускаем менеджер напоминаний
        self.reminder_manager.start()

        # Загружаем задачи
        self._refresh_tasks()

    def _on_add_task(self, title: str, priority: int, deadline: str, category: str, description: str):
        """Добавить задачу."""
        # Если есть дедлайн, создаём напоминание за 1 час до дедлайна
        reminder_at = None
        if deadline:
            try:
                from datetime import datetime, timedelta
                deadline_dt = datetime.fromisoformat(deadline)
                reminder_dt = deadline_dt - timedelta(hours=1)
                reminder_at = reminder_dt.isoformat()
            except:
                pass

        self.db.add(
            title=title,
            priority=priority,
            deadline=deadline if deadline else None,
            category=category,
            description=description,
            reminder_at=reminder_at
        )
        self._refresh_tasks()

    def _on_complete_task(self, task_id: int):
        """Переключить статус завершения задачи."""
        task = self.db.get_by_id(task_id)
        if task:
            if task['completed'] == 0:
                self.db.complete(task_id)
            else:
                self.db.uncomplete(task_id)
            self._refresh_tasks()

    def _on_delete_task(self, task_id: int):
        """Удалить задачу."""
        self.db.delete(task_id)
        self._refresh_tasks()

    def _refresh_tasks(self):
        """Обновить список задач в view."""
        tasks = self.db.get_active()
        self._view.update_tasks(tasks)

    def _on_reminder(self, task: dict):
        """Обработка срабатывания напоминания."""
        print(f"[todo_controller] Reminder triggered for task: {task['title']}")
        # Toast уведомление уже показывается в ReminderManager
