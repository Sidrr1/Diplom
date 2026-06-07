"""
Миграция Smart Notes из отдельной todo.db в единую edgetools.db.

Одноразовый скрипт: старые задачи становятся заметками в таблице notes.
"""
import sqlite3
import os
from datetime import datetime


def migrate_todo_to_edgetools():
    """
    Перенести задачи из app/data/todo.db в app/data/edgetools.db.

    После успеха todo.db переименовывается в todo.db.backup.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, "data")
    old_db_path = os.path.join(data_dir, "todo.db")
    new_db_path = os.path.join(data_dir, "edgetools.db")

    if not os.path.exists(old_db_path):
        print("[migrate] No old todo.db found, skipping migration")
        return

    backup_path = old_db_path + ".backup"
    if os.path.exists(backup_path):
        print("[migrate] Migration already done (backup exists)")
        return

    print(f"[migrate] Starting migration from {old_db_path} to {new_db_path}")

    try:
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        cursor = old_conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        if not cursor.fetchone():
            print("[migrate] No tasks table in old DB")
            old_conn.close()
            return

        tasks = cursor.execute("SELECT * FROM tasks").fetchall()
        old_conn.close()

        if not tasks:
            print("[migrate] No tasks to migrate")
            os.rename(old_db_path, backup_path)
            return

        from app.core.database import db

        migrated_count = 0
        for task in tasks:
            try:
                note_id = db.add_note(
                    app_context='global',
                    content=task['description'] or task['title'],
                    title=task['title'],
                    priority=task['priority'],
                    category=task['category'],
                    deadline=task['deadline'],
                    reminder_at=task['reminder_at'],
                    completed=task['completed'],
                    is_base=1 if migrated_count == 0 else 0
                )
                migrated_count += 1
                print(f"[migrate] Migrated task #{task['id']} → note #{note_id}")
            except Exception as e:
                print(f"[migrate] Error migrating task #{task['id']}: {e}")

        os.rename(old_db_path, backup_path)
        print(f"[migrate] Migration complete! Migrated {migrated_count} tasks")
        print(f"[migrate] Old database backed up to {backup_path}")

    except Exception as e:
        print(f"[migrate] Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    migrate_todo_to_edgetools()
