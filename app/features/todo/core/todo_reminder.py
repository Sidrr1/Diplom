"""Напоминания о задачах: ежедневный дайджест и оповещения перед дедлайном.

Содержит всплывающие toast-уведомления и менеджер периодической проверки
открытых задач по настройкам модуля notes.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

from PySide6.QtCore import QObject, QPropertyAnimation, QEasingCurve, QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from app.features.todo.core.reminder_settings import (
    get_daily_time,
    get_mode,
    get_offsets,
    is_enabled,
    offset_minutes,
)


class ToastNotification(QWidget):
    """Всплывающее уведомление в правом нижнем углу."""

    def __init__(self, title: str, body: str, accent: str = "#0078d7", parent=None):
        """
        Args:
            title: заголовок уведомления
            body: основной текст (поддерживает перенос строк)
            accent: цвет заголовка в hex
            parent: родительский виджет Qt
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(340)
        self._build_ui(title, body, accent)
        self._position_bottom_right()
        self._animate_in()

    def _build_ui(self, title: str, body: str, accent: str):
        """Собрать карточку toast с заголовком и телом."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("toast_card")
        card.setStyleSheet(f"""
            QWidget#toast_card {{
                background: rgba(18, 18, 18, 245);
                border-radius: 14px;
                border: 1px solid rgba(0, 120, 215, 0.35);
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI Semibold", 10))
        title_label.setStyleSheet(f"color: {accent}; border:none; background:transparent;")
        card_layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setFont(QFont("Segoe UI", 10))
        body_label.setWordWrap(True)
        body_label.setStyleSheet("color: #f0f0f0; border:none; background:transparent;")
        card_layout.addWidget(body_label)

        layout.addWidget(card)
        self.adjustSize()

    def _position_bottom_right(self):
        """Разместить окно в правом нижнем углу доступной области экрана."""
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 20, screen.bottom() - self.height() - 50)

    def _animate_in(self):
        """Плавно показать toast и запланировать автозакрытие через 6 с."""
        self.setWindowOpacity(0.0)
        self.show()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(280)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim
        QTimer.singleShot(6000, self._animate_out)

    def _animate_out(self):
        """Плавно скрыть toast и закрыть окно."""
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(280)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.close)
        anim.start()
        self._anim = anim


class ReminderManager(QObject):
    """Проверяет задачи и показывает напоминания по настройкам."""

    reminder_triggered = Signal(dict)

    def __init__(self, db):
        """
        Args:
            db: экземпляр Database для чтения задач
        """
        super().__init__()
        self.db = db
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_reminders)
        self._active_toasts: list = []
        self._fired_before: set[tuple[int, str]] = set()
        self._last_daily_date: str | None = None

    def start(self):
        """Запустить таймер проверки напоминаний (каждые 30 с)."""
        self._timer.start(30_000)
        print("[reminder] Started (every 30s)")

    def stop(self):
        """Остановить периодическую проверку напоминаний."""
        self._timer.stop()

    def reload_settings(self):
        """Сбросить кэш сработавших напоминаний после изменения настроек."""
        self._fired_before.clear()
        self._last_daily_date = None
        print("[reminder] Settings reloaded")

    def _check_reminders(self):
        """Один цикл проверки: ежедневный дайджест и/или напоминания до дедлайна."""
        if not is_enabled():
            return

        now = datetime.now()
        mode = get_mode()

        if mode in ("daily", "both"):
            self._check_daily(now)

        if mode in ("before", "both"):
            self._check_before_deadline(now)

        self._cleanup_fired(now)

    def _check_daily(self, now: datetime):
        """Показать дайджест открытых задач на сегодня в заданное время."""
        today = now.date().isoformat()
        if self._last_daily_date == today:
            return

        hour, minute = get_daily_time()
        if now.hour < hour or (now.hour == hour and now.minute < minute):
            return

        tasks = self._tasks_for_daily_digest(now)
        if not tasks:
            self._last_daily_date = today
            return

        lines = []
        for t in tasks[:5]:
            lines.append(f"• {t.get('text', 'Задача')[:40]}")
        if len(tasks) > 5:
            lines.append(f"…и ещё {len(tasks) - 5}")

        h, m = hour, minute
        self._show_toast(
            f"⏰ Задачи на сегодня ({h:02d}:{m:02d})",
            "\n".join(lines),
        )
        self._last_daily_date = today

    def _check_before_deadline(self, now: datetime):
        """Показать toast за заданное время до наступления дедлайна задачи."""
        offsets = get_offsets()
        if not offsets:
            return

        for task in self._open_tasks_with_deadline():
            deadline = self._parse_dt(task.get("deadline"))
            if not deadline or deadline <= now:
                continue

            for key in offsets:
                fired_key = (task["id"], key)
                if fired_key in self._fired_before:
                    continue

                remind_at = deadline - timedelta(minutes=offset_minutes(key))
                if now >= remind_at:
                    label = self._offset_label(key)
                    self._show_toast(
                        f"⏳ Скоро дедлайн ({label})",
                        task.get("text", "Задача"),
                        accent="#f1c40f",
                    )
                    self.reminder_triggered.emit(task)
                    self._fired_before.add(fired_key)

    def _tasks_for_daily_digest(self, now: datetime) -> list[Dict]:
        """Открытые задачи с дедлайном сегодня или раньше."""
        today = now.date().isoformat()
        tasks = self._open_tasks_with_deadline()
        result = []
        for t in tasks:
            dl = self._parse_dt(t.get("deadline"))
            if not dl:
                continue
            if dl.date().isoformat() <= today:
                result.append(t)
        return result

    def _open_tasks_with_deadline(self) -> list[Dict]:
        """Все незавершённые задачи с указанным дедлайном."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM tasks
                WHERE completed = 0 AND deadline IS NOT NULL AND deadline != ''
                ORDER BY deadline ASC
                """
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _cleanup_fired(self, now: datetime):
        """Удалить из кэша сработавших напоминаний устаревшие записи."""
        stale = set()
        for task_id, offset_key in self._fired_before:
            task = self._get_task(task_id)
            if not task:
                stale.add((task_id, offset_key))
                continue
            dl = self._parse_dt(task.get("deadline"))
            if not dl or dl <= now or task.get("completed"):
                stale.add((task_id, offset_key))
        self._fired_before -= stale

    def _get_task(self, task_id: int) -> Dict | None:
        """Загрузить задачу по ID или вернуть None."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    @staticmethod
    def _parse_dt(value) -> datetime | None:
        """Безопасно распарсить ISO-дату/время из строки БД."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _offset_label(key: str) -> str:
        """Человекочитаемая подпись смещения (5 мин, 1 час…) по ключу."""
        from app.features.todo.core.reminder_settings import OFFSET_CHOICES

        for k, _, label in OFFSET_CHOICES:
            if k == key:
                return label
        return key

    def _show_toast(self, title: str, body: str, accent: str = "#0078d7"):
        """Создать и показать toast, отслеживая его в списке активных."""
        toast = ToastNotification(title, body, accent)
        self._active_toasts.append(toast)
        toast.destroyed.connect(
            lambda: self._active_toasts.remove(toast)
            if toast in self._active_toasts
            else None
        )
