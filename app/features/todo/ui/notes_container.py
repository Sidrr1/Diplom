"""
Контейнер для управления всеми стикерами.
"""
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QKeyEvent
from typing import List, Dict


class NotesContainer(QWidget):
    """Контейнер для всех стикеров текущего контекста."""

    add_note_requested = Signal(str)  # app_context
    settings_requested = Signal()

    def __init__(self):
        super().__init__()
        self._notes = []  # список StickyNote виджетов
        self._current_context = 'global'
        self._visible = False
        self._edge_position = 'right'  # положение edge-кнопки
        self._last_collapsed_state = 0  # Последнее состояние сворачивания (0=развёрнут, 1=свёрнут)

        # Для обработки ALT + клик
        self._alt_pressed = False

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_context(self, app_context: str):
        """
        Переключить контекст и загрузить соответствующие заметки.

        Args:
            app_context: имя процесса ('chrome.exe', 'global')
        """
        if app_context == self._current_context:
            return

        print(f"[notes_container] Switching context: {self._current_context} → {app_context}")
        self._current_context = app_context

        # Скрываем все текущие заметки
        self._hide_all_notes()

        # Загружаем заметки для нового контекста
        self._load_notes_for_context(app_context)

    def _load_notes_for_context(self, app_context: str):
        """Загрузить заметки для контекста из БД."""
        from app.core.database import db
        from app.features.todo.ui.sticky_note import StickyNote

        notes_data = db.get_notes_by_context(app_context)

        # Читаем настройки
        default_width = int(db.get_setting('note_width', 'notes', 250))
        default_height = int(db.get_setting('note_height', 'notes', 200))
        default_opacity = int(db.get_setting('notes_opacity', 'notes', 100))

        # Если нет заметок, создаём базовую (БЕЗ width/height — они всегда из настроек)
        if not notes_data:
            note_id = db.add_note(
                app_context=app_context,
                content="",
                is_base=1,
                collapsed=self._last_collapsed_state,  # Применяем последнее состояние
                color=self._get_color_for_context(app_context)
            )
            notes_data = [db.get_note_by_id(note_id)]

        # Создаём виджеты стикеров
        for note_data in notes_data:
            # ВСЕГДА применяем размеры из настроек (только цвет индивидуальный)
            note_data['width'] = default_width
            note_data['height'] = default_height

            note_widget = StickyNote(note_data)
            note_widget.setWindowOpacity(default_opacity / 100.0)
            note_widget.content_changed.connect(self._on_note_content_changed)
            note_widget.delete_requested.connect(self._on_note_delete_requested)
            note_widget.collapsed_changed.connect(self._on_note_collapsed_changed)
            note_widget.settings_requested.connect(self._on_settings_requested)
            self._notes.append(note_widget)

        # Позиционируем стикеры
        self._arrange_notes()

        # Показываем если контейнер видим
        if self._visible:
            self._show_all_notes()

    def _hide_all_notes(self):
        """Скрыть все текущие заметки."""
        for note in self._notes:
            note.hide()
            note.deleteLater()
        self._notes.clear()

    def cleanup(self):
        """Принудительно закрыть и удалить все окна стикеров."""
        print(f"[notes_container] Cleanup: force closing {len(self._notes)} notes")
        for note in self._notes:
            # Принудительное сохранение перед закрытием
            if note._save_timer.isActive():
                note._save_timer.stop()
                note._save_content()
            # Немедленное закрытие окна
            note.close()
            note.deleteLater()
        self._notes.clear()
        print("[notes_container] Cleanup complete")

    def _show_all_notes(self):
        """Показать все заметки с анимацией."""
        for i, note in enumerate(self._notes):
            note.setWindowOpacity(0.0)
            note.show()
            note.raise_()
            note.activateWindow()
            note.update()

            QTimer.singleShot(i * 50, lambda n=note: self._animate_show(n))

        QApplication.processEvents()

    def _arrange_notes(self):
        """Расположить стикеры вдоль края экрана."""
        if not self._notes:
            return

        print(f"[notes_container] Arranging {len(self._notes)} notes, position: {self._edge_position}")
        screen = QApplication.primaryScreen().availableGeometry()
        spacing = 10

        if self._edge_position == 'right':
            # Право верх (вертикальное расположение справа сверху)
            x = screen.width() - self._notes[0].width() - 60
            y = 20

            for note in self._notes:
                note.move(x, y)
                y += note.height() + spacing

        elif self._edge_position == 'left':
            # Лево верх (вертикальное расположение слева сверху)
            x = 60
            y = 20

            for note in self._notes:
                note.move(x, y)
                y += note.height() + spacing

        elif self._edge_position == 'top':
            # Право низ (вертикальное расположение справа снизу)
            x = screen.width() - self._notes[0].width() - 60
            y_start = screen.height() - 60  # Начинаем снизу

            # Считаем общую высоту всех заметок
            total_height = sum(note.height() for note in self._notes) + spacing * (len(self._notes) - 1)
            y = y_start - total_height

            for note in self._notes:
                note.move(x, y)
                y += note.height() + spacing

        else:  # bottom
            # Лево низ (вертикальное расположение слева снизу)
            print(f"[notes_container] Positioning notes at BOTTOM (left-bottom corner)")
            x = 60
            y_start = screen.height() - 60

            # Считаем общую высоту всех заметок
            total_height = sum(note.height() for note in self._notes) + spacing * (len(self._notes) - 1)
            y = y_start - total_height

            for note in self._notes:
                print(f"[notes_container] Note at x={x}, y={y}, screen.height={screen.height()}, note.height={note.height()}")
                note.move(x, y)
                y += note.height() + spacing

    def toggle_visibility(self):
        """Переключить видимость заметок."""
        self._visible = not self._visible

        if self._visible:
            if not self._notes:
                self._load_notes_for_context(self._current_context)
            self._show_all_notes()
        else:
            for i, note in enumerate(self._notes):
                QTimer.singleShot(i * 30, lambda n=note: self._animate_hide(n))

    def add_note(self):
        """Добавить новую заметку в текущий контекст."""
        from app.core.database import db
        from app.features.todo.ui.sticky_note import StickyNote

        # Читаем настройки
        default_width = int(db.get_setting('note_width', 'notes', 250))
        default_height = int(db.get_setting('note_height', 'notes', 200))
        default_opacity = int(db.get_setting('notes_opacity', 'notes', 100))

        # Создаём новую заметку в БД (БЕЗ width/height — они всегда из настроек)
        note_id = db.add_note(
            app_context=self._current_context,
            content="",
            color=self._get_color_for_context(self._current_context),
            sort_order=len(self._notes)
        )

        # Создаём виджет
        note_data = db.get_note_by_id(note_id)
        note_data['width'] = default_width
        note_data['height'] = default_height

        note_widget = StickyNote(note_data)
        note_widget.setWindowOpacity(default_opacity / 100.0)
        note_widget.content_changed.connect(self._on_note_content_changed)
        note_widget.delete_requested.connect(self._on_note_delete_requested)
        note_widget.collapsed_changed.connect(self._on_note_collapsed_changed)
        self._notes.append(note_widget)

        # Позиционируем
        self._arrange_notes()

        # Показываем
        if self._visible:
            note_widget.show()

        print(f"[notes_container] Added note #{note_id} for context '{self._current_context}'")

    def _get_color_for_context(self, app_context: str) -> str:
        """Получить цвет стикера для контекста."""
        colors = {
            'global': '#fef3c7',      # жёлтый
            'chrome.exe': '#dbeafe',  # голубой
            'firefox.exe': '#fce7f3', # розовый
            'code.exe': '#e0e7ff',    # индиго
            'pycharm64.exe': '#dcfce7',  # зелёный
            'notepad.exe': '#fef3c7', # жёлтый
        }
        return colors.get(app_context, '#fef3c7')

    def _on_note_content_changed(self, note_id: int, content: str):
        """Сохранить изменения содержимого заметки."""
        from app.core.database import db
        db.update_note(note_id, content=content)

    def _on_note_delete_requested(self, note_id: int):
        """Удалить заметку."""
        from app.core.database import db

        # Находим виджет
        note_widget = None
        for note in self._notes:
            if note.note_id == note_id:
                note_widget = note
                break

        if note_widget:
            # Удаляем из БД
            db.delete_note(note_id)

            # Удаляем виджет
            self._notes.remove(note_widget)
            note_widget.hide()
            note_widget.deleteLater()

            # Перепозиционируем оставшиеся
            self._arrange_notes()

            print(f"[notes_container] Deleted note #{note_id}")

    def _on_note_collapsed_changed(self, note_id: int, collapsed: bool):
        """Сохранить состояние сворачивания."""
        from app.core.database import db
        db.update_note(note_id, collapsed=1 if collapsed else 0)

        # Сохраняем последнее состояние для новых контекстов
        self._last_collapsed_state = 1 if collapsed else 0
        print(f"[notes_container] Collapsed state changed: {self._last_collapsed_state}")

        # Перепозиционируем заметки (т.к. размер изменился)
        QTimer.singleShot(250, self._arrange_notes)

    def _on_settings_requested(self):
        """Двойной клик ПКМ по стикеру → настройки."""
        print("[notes_container] Settings requested from sticky note")
        self.settings_requested.emit()

    def set_edge_position(self, position: str):
        """
        Установить положение edge-кнопки.

        Args:
            position: 'left', 'right', 'top', 'bottom'
        """
        print(f"[notes_container] Setting edge position: {position}")
        self._edge_position = position
        self._arrange_notes()
        print(f"[notes_container] Edge position set to: {self._edge_position}")

    def apply_size_to_notes(self, width: int = None, height: int = None):
        """
        Применить новый размер к существующим заметкам.

        Args:
            width: новая ширина (если None — не меняем)
            height: новая высота (если None — не меняем)
        """
        # НЕ сохраняем размеры в БД — они всегда берутся из настроек
        for note in self._notes:
            if width:
                note.setFixedWidth(width)
            if height:
                # Если стикер свёрнут — обновляем только _expanded_height, не трогая текущий размер
                if note._collapsed:
                    note._expanded_height = height
                    print(f"[notes_container] Note {note.note_id} is collapsed, updated _expanded_height to {height}")
                else:
                    # Если развёрнут — применяем размер сразу
                    note.resize(note.width(), height)
                    note._expanded_height = height
                    print(f"[notes_container] Note {note.note_id} is expanded, resized to {height}")

        # Перепозиционируем заметки
        self._arrange_notes()
        print(f"[notes_container] Applied size {width}x{height} to {len(self._notes)} notes")

    def apply_opacity_to_notes(self, opacity: int):
        """
        Применить прозрачность к существующим заметкам.

        Args:
            opacity: прозрачность 0-100
        """
        opacity_value = opacity / 100.0

        for note in self._notes:
            note.setWindowOpacity(opacity_value)

        print(f"[notes_container] Applied opacity {opacity}% to {len(self._notes)} notes")

    def keyPressEvent(self, event: QKeyEvent):
        """Обработка нажатия клавиш."""
        if event.key() == Qt.Key_Alt:
            self._alt_pressed = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        """Обработка отпускания клавиш."""
        if event.key() == Qt.Key_Alt:
            self._alt_pressed = False
        super().keyReleaseEvent(event)

    def is_alt_pressed(self) -> bool:
        """Проверить нажат ли ALT."""
        return self._alt_pressed

    def _animate_show(self, note):
        """Анимация появления заметки."""
        if not note.isVisible():
            return

        # Читаем целевую прозрачность из настроек
        from app.core.database import db
        target_opacity = int(db.get_setting('notes_opacity', 'notes', 100)) / 100.0

        animation = QPropertyAnimation(note, b"windowOpacity")
        animation.setDuration(300)
        animation.setStartValue(0.0)
        animation.setEndValue(target_opacity)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()

        # Сохраняем ссылку чтобы не удалилась
        if not hasattr(self, '_animations'):
            self._animations = []
        self._animations.append(animation)

    def _animate_hide(self, note):
        """Анимация скрытия заметки."""
        animation = QPropertyAnimation(note, b"windowOpacity")
        animation.setDuration(200)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InCubic)
        animation.finished.connect(note.hide)
        animation.start()

        if not hasattr(self, '_animations'):
            self._animations = []
        self._animations.append(animation)
