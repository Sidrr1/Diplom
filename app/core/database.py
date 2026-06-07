"""
Единая SQLite-база EdgeTools (edgetools.db).

Хранит заметки, настройки, правила сортировщика, историю плеера/OCR/улучшателя
и привязанные аккаунты WebView2. Singleton Database доступен как db.
"""
import json
import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime, timedelta


class Database:
    """Singleton: подключение к edgetools.db, миграции схемы и CRUD по всем модулям."""

    _instance = None
    _db_path = None

    def __new__(cls):
        """Создать единственный экземпляр Database."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализировать путь к app/data/edgetools.db и схему при первом обращении."""
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

        # Сначала миграция старых таблиц (до индексов из schema.sql)
        self._migrate_schema()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    cursor.executescript(f.read())
            else:
                print(f"[database] WARNING: schema.sql not found at {schema_path}")

        from app.core.migrate_legacy import migrate_legacy_json
        migrate_legacy_json(self)
        self._migrate_schema()
        self.purge_expired_histories()
        print(f"[database] Initialized at {self._db_path}")

    def _migrate_schema(self):
        """Добавление колонок в существующие БД."""
        alters = [
            "ALTER TABLE player_history ADD COLUMN source TEXT NOT NULL DEFAULT 'mpv'",
            "ALTER TABLE player_history ADD COLUMN thumbnail_url TEXT",
            "ALTER TABLE sorter_history ADD COLUMN trigger TEXT NOT NULL DEFAULT 'manual'",
        ]
        with self.get_connection() as conn:
            cur = conn.cursor()
            for sql in alters:
                try:
                    cur.execute(sql)
                except sqlite3.OperationalError:
                    pass
            for idx_sql in (
                "CREATE INDEX IF NOT EXISTS idx_player_history_played ON player_history(played_at)",
                "CREATE INDEX IF NOT EXISTS idx_player_history_source ON player_history(source)",
                "CREATE INDEX IF NOT EXISTS idx_sorter_history_moved ON sorter_history(moved_at)",
            ):
                try:
                    cur.execute(idx_sql)
                except sqlite3.OperationalError:
                    pass

    def _history_cutoff(self, days: int) -> str:
        """
        ISO-метка времени: записи старше days дней считаются просроченными.

        Args:
            days: глубина хранения истории (минимум 1).

        Returns:
            Строка datetime для сравнения в SQL.
        """
        days = max(1, int(days))
        return (datetime.now() - timedelta(days=days)).isoformat()

    def purge_expired_histories(self):
        """Удалить устаревшие записи player_history и sorter_history по настройкам retention."""
        player_days = int(self.get_setting("player_history_days", "player", 7) or 7)
        sorter_days = int(self.get_setting("sorter_history_days", "sorter", 7) or 7)
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM player_history WHERE played_at < ?",
                (self._history_cutoff(player_days),),
            )
            p = cur.rowcount
            cur.execute(
                "DELETE FROM sorter_history WHERE moved_at < ?",
                (self._history_cutoff(sorter_days),),
            )
            s = cur.rowcount
        if p or s:
            print(f"[database] history purge: player={p}, sorter={s}")

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
        """
        Записать несколько настроек одного модуля за один проход.

        Args:
            items: словарь key -> value.
            module: имя модуля в таблице settings.
        """
        for key, value in items.items():
            self.set_setting(key, value, module)

    # ========================================
    # LINKED ACCOUNTS
    # ========================================

    def upsert_linked_account(
        self,
        service_id: str,
        profile_path: str,
        status: str = "connected",
        display_name: str = "",
    ):
        """
        Создать или обновить привязанный аккаунт WebView2.

        Args:
            service_id: идентификатор сервиса.
            profile_path: каталог профиля в AppData.
            status: connected / disconnected и т.д.
            display_name: отображаемое имя пользователя.
        """
        now = datetime.now().isoformat()
        connected_at = now if status == "connected" else None
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO linked_accounts
                    (service_id, display_name, status, profile_path, connected_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(service_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    status = excluded.status,
                    profile_path = excluded.profile_path,
                    connected_at = COALESCE(excluded.connected_at, linked_accounts.connected_at),
                    updated_at = excluded.updated_at
                """,
                (
                    service_id,
                    display_name or None,
                    status,
                    profile_path,
                    connected_at,
                    now,
                ),
            )

    def get_linked_account(self, service_id: str) -> Optional[Dict]:
        """
        Получить запись linked_accounts по service_id.

        Returns:
            Словарь полей или None.
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM linked_accounts WHERE service_id = ?",
                (service_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_linked_accounts(self) -> List[Dict]:
        """Список всех привязанных аккаунтов, отсортированный по service_id."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM linked_accounts ORDER BY service_id"
            )
            return [dict(r) for r in cur.fetchall()]

    def set_linked_account_status(
        self,
        service_id: str,
        status: str,
        display_name: str = "",
    ):
        """
        Обновить статус аккаунта; при отсутствии записи создать с auth_profile_dir.

        Args:
            service_id: идентификатор сервиса.
            status: новый статус подключения.
            display_name: имя для UI (опционально).
        """
        acc = self.get_linked_account(service_id)
        if not acc:
            from app.core.paths import auth_profile_dir
            self.upsert_linked_account(
                service_id,
                auth_profile_dir(service_id),
                status=status,
                display_name=display_name,
            )
            return
        self.upsert_linked_account(
            service_id,
            acc["profile_path"],
            status=status,
            display_name=display_name or (acc.get("display_name") or ""),
        )

    # ========================================
    # FILE SORTER
    # ========================================

    def count_sorter_rules(self) -> int:
        """Число правил в sorter_rules (включая отключённые)."""
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
        from app.core.paths import normalize_path

        folder = normalize_path(folder)
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
        """
        Удалить правило сортировки по первичному ключу.

        Args:
            rule_id: id в таблице sorter_rules.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sorter_rules WHERE id = ?", (rule_id,))

    def delete_sorter_rule_by_index(self, index: int) -> bool:
        """
        Удалить правило по индексу в списке активных правил UI.

        Args:
            index: позиция в get_sorter_rules().

        Returns:
            True, если правило найдено и удалено.
        """
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
        trigger: str = "manual",
    ):
        """
        Записать факт перемещения файла сортировщиком.

        Args:
            source_path: исходный путь файла.
            destination_path: куда перемещён.
            rule_id: id правила или None.
            trigger: 'manual' или 'auto'.
        """
        trigger = "auto" if trigger == "auto" else "manual"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sorter_history
                (source_path, destination_path, rule_id, moved_at, trigger)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    source_path,
                    destination_path,
                    rule_id,
                    datetime.now().isoformat(),
                    trigger,
                ),
            )

    # ========================================
    # PLAYER / ENHANCER / OCR HISTORY
    # ========================================

    def _upsert_player_history(
        self,
        url: str,
        source: str,
        title: str = "",
        thumbnail_url: str = "",
        duration: float = 0.0,
        last_position: float = 0.0,
    ):
        """
        Обновить или вставить запись истории плеера по паре url+source.

        Args:
            url: адрес медиа или страницы.
            source: 'mpv' или 'web'.
        """
        if not url or not url.strip():
            return
        url = url.strip()
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id FROM player_history
                WHERE url = ? AND source = ?
                ORDER BY played_at DESC LIMIT 1
                """,
                (url, source),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE player_history
                    SET title = ?, thumbnail_url = ?, duration = ?,
                        last_position = ?, played_at = ?
                    WHERE id = ?
                    """,
                    (
                        title or None,
                        thumbnail_url or None,
                        duration,
                        last_position,
                        now,
                        row["id"],
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO player_history
                    (url, title, thumbnail_url, source, duration, last_position, played_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        title or None,
                        thumbnail_url or None,
                        source,
                        duration,
                        last_position,
                        now,
                    ),
                )

    def add_player_history(
        self,
        url: str,
        title: str = "",
        duration: float = 0.0,
        last_position: float = 0.0,
        thumbnail_url: str = "",
    ):
        """
        Добавить/обновить историю локального плеера (source=mpv).

        Args:
            url: URL или путь к файлу.
            last_position: позиция воспроизведения в секундах.
        """
        from app.features.player.core.history_meta import thumbnail_for_url

        thumb = thumbnail_url or thumbnail_for_url(url)
        self._upsert_player_history(
            url, "mpv", title=title, thumbnail_url=thumb,
            duration=duration, last_position=last_position,
        )

    def add_web_history(self, url: str, title: str = ""):
        """
        Добавить историю встроенного WebView (source=web).

        Служебные URL браузера пропускаются.
        """
        from app.features.player.core.history_meta import display_title, thumbnail_for_url

        if not url or url.startswith(("about:", "chrome:", "edge:", "devtools:")):
            return
        self._upsert_player_history(
            url,
            "web",
            title=display_title(url, title),
            thumbnail_url=thumbnail_for_url(url),
        )

    def get_player_history(self, source: str, limit: int = 200) -> List[Dict]:
        """
        История плеера за период player_history_days.

        Args:
            source: 'mpv' или 'web'.
            limit: максимум записей.

        Returns:
            Список словарей, новые первыми.
        """
        days = int(self.get_setting("player_history_days", "player", 7) or 7)
        cutoff = self._history_cutoff(days)
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM player_history
                WHERE source = ? AND played_at >= ?
                ORDER BY played_at DESC
                LIMIT ?
                """,
                (source, cutoff, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def get_sorter_history(
        self, limit: int = 300, search: str | None = None
    ) -> List[Dict]:
        """
        История перемещений сортировщика с опциональным поиском.

        Args:
            limit: максимум строк.
            search: подстрока в путях или имени правила.

        Returns:
            Записи с полем rule_name из JOIN.
        """
        days = int(self.get_setting("sorter_history_days", "sorter", 7) or 7)
        cutoff = self._history_cutoff(days)
        query = (search or "").strip().lower()
        with self.get_connection() as conn:
            cur = conn.cursor()
            if query:
                like = f"%{query}%"
                cur.execute(
                    """
                    SELECT h.*, r.name AS rule_name
                    FROM sorter_history h
                    LEFT JOIN sorter_rules r ON r.id = h.rule_id
                    WHERE h.moved_at >= ?
                      AND (
                        LOWER(h.source_path) LIKE ?
                        OR LOWER(h.destination_path) LIKE ?
                        OR LOWER(COALESCE(r.name, '')) LIKE ?
                      )
                    ORDER BY h.moved_at DESC
                    LIMIT ?
                    """,
                    (cutoff, like, like, like, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT h.*, r.name AS rule_name
                    FROM sorter_history h
                    LEFT JOIN sorter_rules r ON r.id = h.rule_id
                    WHERE h.moved_at >= ?
                    ORDER BY h.moved_at DESC
                    LIMIT ?
                    """,
                    (cutoff, limit),
                )
            return [dict(r) for r in cur.fetchall()]

    def clear_player_history(self, source: str | None = None):
        """
        Очистить историю плеера.

        Args:
            source: фильтр mpv/web; None — удалить всё.
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            if source:
                cur.execute("DELETE FROM player_history WHERE source = ?", (source,))
            else:
                cur.execute("DELETE FROM player_history")

    def clear_sorter_history(self):
        """Удалить все записи sorter_history."""
        with self.get_connection() as conn:
            conn.cursor().execute("DELETE FROM sorter_history")

    def add_enhancer_history(
        self,
        original_path: str,
        enhanced_path: str,
        settings_used: dict | None = None,
        processing_time: float = 0.0,
    ):
        """
        Записать результат улучшения изображения.

        Args:
            original_path: исходный файл.
            enhanced_path: сохранённый результат.
            settings_used: JSON-совместимый словарь параметров.
            processing_time: длительность в секундах.
        """
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
        """
        Сохранить результат OCR в историю.

        Args:
            text: распознанный текст.
            screenshot_path: путь к скриншоту (опционально).
            language: код языков Tesseract.
        """
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


db = Database()
