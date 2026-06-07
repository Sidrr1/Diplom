"""
Миграция схемы БД для рабочего режима (Work Mode) EdgeTools.

Добавляет колонку mode в notes и таблицу tasks с индексами.
"""
import sqlite3
from pathlib import Path


def migrate_work_mode():
    """
    Безопасно обновить edgetools.db для Work Mode.

    Идемпотентна: повторный запуск не ломает уже мигрированную БД.
    """
    db_path = Path(__file__).parent.parent / "data" / "edgetools.db"

    if not db_path.exists():
        print("[migrate_work_mode] Database not found, skipping migration")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        print("[migrate_work_mode] Adding 'mode' column to notes...")
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN mode TEXT DEFAULT 'normal'")
            conn.commit()
            print("[migrate_work_mode] OK Column 'mode' added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("[migrate_work_mode] OK Column 'mode' already exists")
            else:
                raise

        print("[migrate_work_mode] Creating 'tasks' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                description TEXT,
                completed INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high')),
                deadline TEXT,
                reminder_at TEXT,
                tags TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("[migrate_work_mode] OK Table 'tasks' created")

        print("[migrate_work_mode] Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_note_id ON tasks(note_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
        conn.commit()
        print("[migrate_work_mode] OK Indexes created")

        print("[migrate_work_mode] Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"[migrate_work_mode] ERROR Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_work_mode()
