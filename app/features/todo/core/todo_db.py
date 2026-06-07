"""
SQLite-база данных для задач todo (legacy-слой).

Хранит задачи с приоритетом, категорией, дедлайном и напоминаниями.
Используется отдельным файлом app/data/todo.db.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict


class TodoDB:
    """Управление задачами через SQLite."""

    def __init__(self, db_path: str = None):
        """
        Инициализировать подключение к БД задач.

        Args:
            db_path: путь к файлу SQLite; по умолчанию app/data/todo.db
        """
        if db_path is None:
            # app/data/todo.db
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "todo.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Создать таблицу tasks, если она ещё не существует."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 3,
                category TEXT,
                deadline TEXT,
                created_at TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                reminder_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        print(f"[todo_db] Database initialized at {self.db_path}")

    def add(self, title: str, priority: int = 3, deadline: str = None,
            category: str = None, description: str = None,
            reminder_at: str = None) -> int:
        """
        Добавить задачу.

        Args:
            title: название задачи
            priority: 1 (красный), 2 (жёлтый), 3 (зелёный)
            deadline: ISO формат "YYYY-MM-DD HH:MM:SS"
            category: категория (работа, личное, срочно)
            description: описание
            reminder_at: время напоминания ISO формат

        Returns:
            id созданной задачи
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO tasks (title, description, priority, category, deadline, created_at, reminder_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, description, priority, category, deadline, created_at, reminder_at))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"[todo_db] Added task #{task_id}: {title}")
        return task_id

    def get_all(self) -> List[Dict]:
        """Получить все задачи."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY priority ASC, created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_active(self) -> List[Dict]:
        """Получить только активные (не завершённые) задачи."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks
            WHERE completed = 0
            ORDER BY priority ASC, created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_by_id(self, task_id: int) -> Optional[Dict]:
        """Получить задачу по ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def complete(self, task_id: int):
        """Отметить задачу как завершённую."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        print(f"[todo_db] Completed task #{task_id}")

    def uncomplete(self, task_id: int):
        """Снять отметку завершения."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET completed = 0 WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        print(f"[todo_db] Uncompleted task #{task_id}")

    def delete(self, task_id: int):
        """Удалить задачу."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        print(f"[todo_db] Deleted task #{task_id}")

    def update(self, task_id: int, **kwargs):
        """
        Обновить задачу.

        Args:
            task_id: ID задачи
            **kwargs: поля для обновления (title, description, priority, category, deadline, reminder_at)
        """
        allowed_fields = ['title', 'description', 'priority', 'category', 'deadline', 'reminder_at']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [task_id]

        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
        print(f"[todo_db] Updated task #{task_id}: {updates}")

    def get_reminders_due(self) -> List[Dict]:
        """Получить задачи у которых пора напомнить."""
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks
            WHERE completed = 0
            AND reminder_at IS NOT NULL
            AND reminder_at <= ?
        """, (now,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_reminder(self, task_id: int):
        """Очистить напоминание после срабатывания."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET reminder_at = NULL WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
