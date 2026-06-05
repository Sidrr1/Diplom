"""
Контроллер для Todo.
"""
from PySide6.QtCore import QObject


class TodoController(QObject):
    """Контроллер связывает все компоненты Smart Notes."""

    def __init__(self, window_tracker=None):
        super().__init__()

        print("[todo_controller] Initializing Smart Notes...")

        # Инициализация компонентов
        from app.features.todo.ui.notes_container import NotesContainer
        from app.features.todo.ui.edge_button import EdgeButton
        from app.features.todo.core.window_tracker import WindowTracker
        from app.features.todo.core.todo_reminder import ReminderManager
        from app.core.database import db

        print("[todo_controller] Checking for migration...")
        # Миграция старых данных (если есть)
        from app.core.migrate_todo import migrate_todo_to_edgetools
        migrate_todo_to_edgetools()
        print("[todo_controller] Migration check complete")

        print("[todo_controller] Creating notes container...")
        # Контейнер заметок
        self.notes_container = NotesContainer()
        self.notes_container.settings_requested.connect(self._on_settings_requested)


        # Используем глобальный трекер или создаём новый
        if window_tracker:
            print("[todo_controller] Using global WindowTracker")
            self.window_tracker = window_tracker
        else:
            print("[todo_controller] Creating new WindowTracker")
            self.window_tracker = WindowTracker(interval_ms=1000)
            self.window_tracker.start()

        # Получаем текущий контекст
        initial_context = self.window_tracker.get_current_context()
        print(f"[todo_controller] Initial context detected: {initial_context}")

        print("[todo_controller] Loading initial context...")
        # Загружаем стикеры для РЕАЛЬНОГО текущего контекста (не 'global')
        self.notes_container.set_context(initial_context)

        # Устанавливаем _visible=True
        self.notes_container._visible = True

        print("[todo_controller] Connecting to window tracker...")
        # Подписываемся на изменения контекста
        self.window_tracker.context_changed.connect(self._on_context_changed)

        print("[todo_controller] Starting reminder manager...")
        # Менеджер напоминаний
        self.reminder_manager = ReminderManager(db)
        self.reminder_manager.reminder_triggered.connect(self._on_reminder)
        self.reminder_manager.start()

        # Применяем настройки при инициализации
        self._apply_initial_settings()

        # Показываем стикеры ПОСЛЕ инициализации всего остального
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._show_notes_delayed())

        # НЕ показываем edge-кнопку сразу — она появится при первом клике на модуль
        # self.edge_button.show()

        print("[todo_controller] Smart Notes initialized successfully!")

    def show(self):
        print("[todo_controller] Showing notes")
        if not self.notes_container._notes:
            current_context = self.window_tracker.get_current_context()
            self.notes_container._load_notes_for_context(current_context)
        self.notes_container._visible = True
        self.notes_container._show_all_notes()
        if not self.window_tracker._timer.isActive():
            self.window_tracker.start()

    def _show_notes_delayed(self):
        """Показать стикеры с задержкой."""
        print("[todo_controller] Delayed show notes")
        if not self.notes_container._notes:
            current_context = self.window_tracker.get_current_context()
            self.notes_container._load_notes_for_context(current_context)
        self.notes_container._show_all_notes()
        # Форсируем показ через доп задержку
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._force_show_notes)

    def _force_show_notes(self):
        """Форсировать показ всех стикеров."""
        for note in self.notes_container._notes:
            note.show()
            note.raise_()
            note.activateWindow()
            note.update()

    def hide(self):
        """Скрыть стикеры."""
        print("[todo_controller] Hiding notes")
        # Принудительно закрываем все окна стикеров
        self.notes_container.cleanup()
        self.notes_container._visible = False
        # Останавливаем трекер для экономии ресурсов
        self.window_tracker.stop()

    def _on_edge_button_clicked(self):
        """Клик по Edge-кнопке — показать/скрыть заметки."""
        # Edge-кнопка удалена, этот метод больше не используется
        pass

    def _on_settings_requested(self):
        """Двойной клик по стикеру — открыть настройки (без modal exec)."""
        from app.features.settings.ui.settings_dialog import SettingsDialog

        panel = SettingsDialog._edge_panel_ref
        dialog = getattr(panel, "_settings_d", None) if panel else None

        if dialog is None:
            dialog = SettingsDialog(parent=panel, initial_tab="notes")
            dialog.settings_changed.connect(self._apply_settings)
            if panel is not None:
                dialog.settings_changed.connect(panel._apply_settings_to_modules)
                panel._settings_d = dialog
        else:
            dialog._switch_tab("notes")

        if dialog.isVisible():
            dialog.raise_()
            dialog.activateWindow()
        elif panel is not None:
            dialog.show_near(panel.geometry())
        else:
            dialog.show_centered()

    def _on_add_note_requested(self):
        """ALT + клик по Edge-кнопке — добавить новую заметку."""
        self.notes_container.add_note()
        print("[todo_controller] Added new note via ALT+click")

    def _on_context_changed(self, process_name: str, window_title: str):
        """Контекст приложения изменился."""
        from app.core.database import db

        # Обновляем активность контекста
        db.update_context_activity(process_name)

        # Переключаем заметки на новый контекст
        self.notes_container.set_context(process_name)

        print(f"[todo_controller] Context: {process_name}")

    def _on_reminder(self, note: dict):
        """Обработка срабатывания напоминания."""
        print(f"[todo_controller] Reminder: {note.get('title') or note.get('content', '')[:50]}")
        # Toast уведомление уже показывается в ReminderManager

    def _apply_initial_settings(self):
        """Применить настройки при инициализации."""
        from app.core.database import db

        # Читаем настройки из БД
        edge_position = db.get_setting('edge_position', 'notes', 'right')
        self.notes_container.set_edge_position(edge_position)

        notes_mode = db.get_setting('notes_mode', 'notes', 'normal')
        self.notes_container.apply_notes_mode(notes_mode)

        print(
            f"[todo_controller] Initial settings applied: "
            f"edge_position={edge_position}, notes_mode={notes_mode}"
        )

    def _apply_settings(self, settings: dict):
        """Применить настройки."""
        from app.core.database import db

        print(f"[todo_controller] Applying settings: {settings}")

        if any(
            k.startswith("reminder_") for k in settings
        ) and hasattr(self, "reminder_manager"):
            self.reminder_manager.reload_settings()

        # Применяем изменения
        if 'notes_edge_position' in settings:
            position = settings['notes_edge_position']
            print(f"[todo_controller] Changing edge position to: {position}")
            self.notes_container.set_edge_position(position)

        if 'notes_width' in settings or 'notes_height' in settings:
            width = settings.get('notes_width')
            height = settings.get('notes_height')
            print(f"[todo_controller] Note size changed: {width}x{height}")
            self.notes_container.apply_size_to_notes(width, height)

        if 'notes_opacity' in settings:
            opacity = settings['notes_opacity']
            print(f"[todo_controller] Opacity changed to: {opacity}")
            self.notes_container.apply_opacity_to_notes(opacity)

        if 'notes_mode' in settings:
            mode = settings['notes_mode']
            print(f"[todo_controller] Mode changed to: {mode}")
            self.notes_container.apply_notes_mode(mode)

        print(f"[todo_controller] Settings applied successfully")
