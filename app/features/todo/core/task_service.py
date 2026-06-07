"""
Сервисный слой для работы с задачами заметок.

Изолирует SQL-запросы и сериализацию тегов от UI-компонентов.
"""
import json
from datetime import datetime
from typing import List, Dict, Optional


class TaskService:
    """Сервис для работы с задачами."""

    def __init__(self, db):
        """
        Args:
            db: экземпляр Database с методом get_connection()
        """
        self.db = db

    def get_tasks(self, note_id: int, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Получить задачи для заметки.

        Args:
            note_id: ID заметки
            filters: фильтры (completed, priority, deadline, tags)

        Returns:
            список задач
        """
        query = "SELECT * FROM tasks WHERE note_id = ?"
        params = [note_id]

        # Применяем фильтры
        if filters:
            if 'completed' in filters:
                query += " AND completed = ?"
                params.append(filters['completed'])

            if 'priority' in filters and filters['priority']:
                placeholders = ','.join('?' * len(filters['priority']))
                query += f" AND priority IN ({placeholders})"
                params.extend(filters['priority'])

            if 'deadline_today' in filters and filters['deadline_today']:
                today = datetime.now().date().isoformat()
                query += " AND DATE(deadline) = ?"
                params.append(today)

            if 'deadline_overdue' in filters and filters['deadline_overdue']:
                now = datetime.now().isoformat()
                query += " AND deadline < ? AND completed = 0"
                params.append(now)

        # Сортировка
        query += " ORDER BY sort_order ASC, created_at ASC"

        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            tasks = []

            for row in cursor.fetchall():
                task = dict(zip(columns, row))
                # Парсим теги из JSON
                if task.get('tags'):
                    try:
                        task['tags'] = json.loads(task['tags'])
                    except:
                        task['tags'] = []
                else:
                    task['tags'] = []
                tasks.append(task)

        return tasks

    def create_task(self, note_id: int, text: str, **kwargs) -> int:
        """
        Создать задачу.

        Args:
            note_id: ID заметки
            text: название задачи
            **kwargs: description, priority, deadline, reminder_at, tags

        Returns:
            ID созданной задачи
        """
        description = kwargs.get('description', '')
        priority = kwargs.get('priority', 'medium')
        deadline = kwargs.get('deadline')
        reminder_at = kwargs.get('reminder_at')
        tags = kwargs.get('tags', [])
        sort_order = kwargs.get('sort_order', 0)

        # Сериализуем теги в JSON
        tags_json = json.dumps(tags) if tags else None

        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO tasks (note_id, text, description, priority, deadline,
                                 reminder_at, tags, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (note_id, text, description, priority, deadline, reminder_at,
                  tags_json, sort_order, datetime.now().isoformat()))

            return cursor.lastrowid

    def update_task(self, task_id: int, **kwargs):
        """
        Обновить задачу.

        Args:
            task_id: ID задачи
            **kwargs: поля для обновления
        """
        fields = []
        values = []

        for key, value in kwargs.items():
            if key == 'tags':
                # Сериализуем теги
                value = json.dumps(value) if value else None
            fields.append(f"{key} = ?")
            values.append(value)

        if not fields:
            return

        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"

        with self.db.get_connection() as conn:
            conn.execute(query, values)

    def delete_task(self, task_id: int):
        """Удалить задачу."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def reorder_tasks(self, note_id: int, task_ids: List[int]):
        """
        Изменить порядок задач.

        Args:
            note_id: ID заметки
            task_ids: список ID задач в новом порядке
        """
        with self.db.get_connection() as conn:
            for order, task_id in enumerate(task_ids):
                conn.execute(
                    "UPDATE tasks SET sort_order = ? WHERE id = ? AND note_id = ?",
                    (order, task_id, note_id)
                )

    def toggle_completed(self, task_id: int) -> bool:
        """
        Переключить статус выполнения.

        Returns:
            новый статус (True = выполнено)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT completed FROM tasks WHERE id = ?", (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            new_status = 0 if row[0] else 1
            conn.execute(
                "UPDATE tasks SET completed = ? WHERE id = ?",
                (new_status, task_id)
            )
            return bool(new_status)

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Получить задачу по ID."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            task = dict(zip(columns, row))

            # Парсим теги
            if task.get('tags'):
                try:
                    task['tags'] = json.loads(task['tags'])
                except:
                    task['tags'] = []
            else:
                task['tags'] = []

            return task

    def get_all_tags(self, note_id: int) -> List[str]:
        """Получить все уникальные теги для заметки."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT tags FROM tasks WHERE note_id = ? AND tags IS NOT NULL",
                (note_id,)
            )

            all_tags = set()
            for row in cursor.fetchall():
                try:
                    tags = json.loads(row[0])
                    all_tags.update(tags)
                except:
                    pass

            return sorted(list(all_tags))

    def get_progress(self, note_id: int) -> Dict:
        """
        Получить прогресс выполнения задач.

        Returns:
            {'total': 5, 'completed': 2, 'percent': 40}
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as total, SUM(completed) as completed FROM tasks WHERE note_id = ?",
                (note_id,)
            )
            row = cursor.fetchone()

            total = row[0] or 0
            completed = row[1] or 0
            percent = int((completed / total * 100)) if total > 0 else 0

            return {
                'total': total,
                'completed': completed,
                'percent': percent
            }
