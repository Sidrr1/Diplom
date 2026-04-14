"""
Единая база данных для всего EdgeTools проекта.
"""
import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime


class Database:
    """Singleton для работы с единой БД."""

    _instance = None
    _db_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self._db_path = os.path.join(data_dir, "edgetools.db")
            self._init_db()

    @contextmanager
    def get_connection(self):
        """Context manager для безопасной работы с БД."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """Инициализация всех таблиц."""
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    cursor.executescript(f.read())
            else:
                print(f"[database] WARNING: schema.sql not found at {schema_path}")

        print(f"[database] Initialized at {self._db_path}")

    # ========================================
    # NOTES (Smart Notes)
    # ========================================

    def add_note(self, app_context: str, content: str, **kwargs) -> int:
        """
        Добавить заметку.

        Args:
            app_context: контекст приложения ('chrome.exe', 'global')
            content: текст заметки
            **kwargs: title, priority, category, color, position_x, position_y,
                     width, height, is_base, deadline, reminder_at

        Returns:
            id созданной заметки
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            created_at = datetime.now().isoformat()

            fields = ['app_context', 'content', 'created_at']
            values = [app_context, content, created_at]

            allowed_fields = ['title', 'priority', 'category', 'color', 'position_x',
                            'position_y', 'width', 'height', 'is_base', 'deadline',
                            'reminder_at', 'collapsed', 'sort_order']

            for field in allowed_fields:
                if field in kwargs:
                    fields.append(field)
                    values.append(kwargs[field])

            placeholders = ', '.join(['?'] * len(values))
            fields_str = ', '.join(fields)

            cursor.execute(
                f"INSERT INTO notes ({fields_str}) VALUES ({placeholders})",
                values
            )

            note_id = cursor.lastrowid
            print(f"[database] Added note #{note_id} for context '{app_context}'")
            return note_id

    def get_notes_by_context(self, app_context: str, include_completed: bool = False) -> List[Dict]:
        """Получить заметки для конкретного контекста."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if include_completed:
                query = "SELECT * FROM notes WHERE app_context = ? ORDER BY sort_order, created_at DESC"
            else:
                query = "SELECT * FROM notes WHERE app_context = ? AND completed = 0 ORDER BY sort_order, created_at DESC"

            cursor.execute(query, (app_context,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_note_by_id(self, note_id: int) -> Optional[Dict]:
        """Получить заметку по ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_note(self, note_id: int, **kwargs):
        """
        Обновить заметку.

        Args:
            note_id: ID заметки
            **kwargs: поля для обновления
        """
        allowed_fields = ['title', 'content', 'priority', 'category', 'color',
                         'position_x', 'position_y', 'width', 'height', 'collapsed',
                         'deadline', 'reminder_at', 'completed', 'sort_order']

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [note_id]
            cursor.execute(f"UPDATE notes SET {set_clause} WHERE id = ?", values)

    def delete_note(self, note_id: int):
        """Удалить заметку."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            print(f"[database] Deleted note #{note_id}")

    def get_reminders_due(self) -> List[Dict]:
        """Получить заметки у которых пора напомнить."""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                WHERE completed = 0
                AND reminder_at IS NOT NULL
                AND reminder_at <= ?
            """, (now,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_reminder(self, note_id: int):
        """Очистить напоминание после срабатывания."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notes SET reminder_at = NULL WHERE id = ?", (note_id,))

    # ========================================
    # WINDOW CONTEXTS
    # ========================================

    def get_all_contexts(self) -> List[Dict]:
        """Получить все контексты приложений."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM window_contexts ORDER BY display_name")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_context_by_process(self, process_name: str) -> Optional[Dict]:
        """Получить контекст по имени процесса."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM window_contexts WHERE process_name = ?", (process_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_context_activity(self, process_name: str):
        """Обновить время последней активности контекста."""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE window_contexts SET last_active = ? WHERE process_name = ?",
                (now, process_name)
            )

    def update_context_notes_count(self, process_name: str):
        """Обновить счётчик заметок для контекста."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE window_contexts
                SET notes_count = (
                    SELECT COUNT(*) FROM notes
                    WHERE app_context = ? AND completed = 0
                )
                WHERE process_name = ?
            """, (process_name, process_name))

    # ========================================
    # SETTINGS
    # ========================================

    def get_setting(self, key: str, module: str = 'global', default: Any = None) -> Any:
        """Получить настройку."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM settings WHERE key = ? AND module = ?",
                (key, module)
            )
            row = cursor.fetchone()
            return row['value'] if row else default

    def set_setting(self, key: str, value: Any, module: str = 'global'):
        """Установить настройку."""
        updated_at = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, module, updated_at)
                VALUES (?, ?, ?, ?)
            """, (key, str(value), module, updated_at))

    def get_all_settings(self, module: str = None) -> Dict[str, str]:
        """Получить все настройки модуля."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if module:
                cursor.execute("SELECT key, value FROM settings WHERE module = ?", (module,))
            else:
                cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
            return {row['key']: row['value'] for row in rows}


# Глобальный экземпляр
db = Database()
