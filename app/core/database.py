"""
Единая база данных для всего EdgeTools проекта.
"""
import json
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

        from app.core.migrate_legacy import migrate_legacy_json
        migrate_legacy_json(self)
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

    def set_settings_bulk(self, items: Dict[str, Any], module: str = "global"):
        for key, value in items.items():
            self.set_setting(key, value, module)

    # ========================================
    # FILE SORTER
    # ========================================

    def count_sorter_rules(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM sorter_rules")
            return int(cursor.fetchone()["c"])

    def get_sorter_rules(self) -> List[Dict]:
        """Список правил в формате UI: type, patterns, folder, id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sorter_rules WHERE enabled = 1 ORDER BY id"
            )
            out = []
            for row in cursor.fetchall():
                r = dict(row)
                try:
                    patterns = json.loads(r["pattern"])
                    if not isinstance(patterns, list):
                        patterns = [str(patterns)]
                except (json.JSONDecodeError, TypeError):
                    patterns = [r["pattern"]] if r.get("pattern") else []
                out.append({
                    "id": r["id"],
                    "type": r["rule_type"],
                    "patterns": patterns,
                    "folder": r["destination"],
                })
            return out

    def add_sorter_rule(self, folder: str, rule_type: str, patterns: list) -> int:
        name = f"{rule_type}: {', '.join(str(p) for p in patterns[:3])}"
        patterns_json = json.dumps(patterns, ensure_ascii=False)
        created_at = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sorter_rules
                (name, rule_type, pattern, destination, enabled, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (name, rule_type, patterns_json, folder, created_at),
            )
            rule_id = cursor.lastrowid
            print(f"[database] sorter rule #{rule_id}: {rule_type} -> {folder}")
            return rule_id

    def delete_sorter_rule(self, rule_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sorter_rules WHERE id = ?", (rule_id,))

    def delete_sorter_rule_by_index(self, index: int) -> bool:
        rules = self.get_sorter_rules()
        if 0 <= index < len(rules):
            self.delete_sorter_rule(rules[index]["id"])
            return True
        return False

    def add_sorter_history(
        self,
        source_path: str,
        destination_path: str,
        rule_id: int | None = None,
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sorter_history
                (source_path, destination_path, rule_id, moved_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    source_path,
                    destination_path,
                    rule_id,
                    datetime.now().isoformat(),
                ),
            )

    # ========================================
    # PLAYER / ENHANCER / OCR HISTORY
    # ========================================

    def add_player_history(
        self,
        url: str,
        title: str = "",
        duration: float = 0.0,
        last_position: float = 0.0,
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO player_history (url, title, duration, last_position, played_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url, title, duration, last_position, datetime.now().isoformat()),
            )

    def add_enhancer_history(
        self,
        original_path: str,
        enhanced_path: str,
        settings_used: dict | None = None,
        processing_time: float = 0.0,
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO enhancer_history
                (original_path, enhanced_path, settings_used, processing_time, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    original_path,
                    enhanced_path,
                    json.dumps(settings_used or {}, ensure_ascii=False),
                    processing_time,
                    datetime.now().isoformat(),
                ),
            )

    def add_ocr_history(self, text: str, screenshot_path: str = "", language: str = "rus+eng"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ocr_history
                (screenshot_path, recognized_text, language, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (screenshot_path, text, language, datetime.now().isoformat()),
            )


# Глобальный экземпляр
db = Database()
