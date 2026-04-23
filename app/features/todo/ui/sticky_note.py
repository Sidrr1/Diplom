"""
Один стикер (sticky note) в стиле post-it.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QStackedWidget,
    QPushButton, QLabel, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QFont, QCursor, QColor
from datetime import datetime


class StickyNote(QWidget):
    """Один стикер с текстом заметки."""

    content_changed = Signal(int, str)  # (note_id, content)
    delete_requested = Signal(int)      # note_id
    collapsed_changed = Signal(int, bool)  # (note_id, collapsed)
    settings_requested = Signal()  # Двойной клик ПКМ → настройки
    mode_changed = Signal(int, str)  # (note_id, mode) — режим изменён

    def __init__(self, note: dict, task_service=None, edge_position: str = 'right', parent=None):
        super().__init__(parent)
        self.note = note
        self.note_id = note['id']
        self._collapsed = note.get('collapsed', 0) == 1
        self._content_dirty = False  # Флаг для отслеживания изменений
        self._expanded_height = note.get('height', 200)  # Сохраняем высоту до сворачивания
        self._mode = note.get('mode', 'normal')  # Режим: 'normal' или 'work'
        self.task_service = task_service  # Сервис для работы с задачами
        self._edge_position = edge_position  # Позиция edge-кнопки ('left', 'right', 'top', 'bottom')

        # Автосохранение
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)  # 500ms после последнего изменения (было 1000ms)
        self._save_timer.timeout.connect(self._save_content)

        # Двойной клик ПКМ
        self._rmb_click_timer = QTimer()
        self._rmb_click_timer.setSingleShot(True)
        self._rmb_click_timer.setInterval(300)
        self._rmb_click_timer.timeout.connect(self._handle_rmb_single_click)
        self._rmb_click_count = 0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Размер и позиция
        width = note.get('width', 250)
        height = note.get('height', 200)
        self.setFixedWidth(width)  # Ширина фиксирована
        self.setMinimumHeight(40)  # Минимум для свёрнутого
        self.setMaximumHeight(500)  # Максимум
        self.resize(width, height)  # Начальный размер

        if note.get('position_x') and note.get('position_y'):
            self.move(note['position_x'], note['position_y'])

        self._build_ui()
        self._apply_shadow()
        # Убираем WS_EX_NOACTIVATE — теперь window_tracker игнорирует python.exe

        # Кнопка "+" для добавления задач (только в work режиме)
        from app.features.todo.ui.add_task_button import AddTaskButton
        self._add_task_btn = AddTaskButton(parent=None)
        self._add_task_btn.add_task_requested.connect(self._on_add_task_requested)
        self._add_task_btn.hide()  # Скрываем по умолчанию

        # Если свёрнут, сразу показываем в свёрнутом виде
        if self._collapsed:
            self.resize(width, 40)  # Устанавливаем высоту 40px для свёрнутого
            self._set_collapsed_view()

    def _build_ui(self):
        """Построить UI стикера."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Главная карточка
        self.card = QWidget()
        self.card.setObjectName("sticky_card")

        # Цвет стикера
        color = self.note.get('color', '#fef3c7')
        self.card.setStyleSheet(f"""
            QWidget#sticky_card {{
                background: {color};
                border-radius: 12px;
                border: 1px solid rgba(0, 0, 0, 10);
            }}
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        # Заголовок
        self.header = QHBoxLayout()
        self.header.setSpacing(6)

        # Иконка приложения + название
        app_context = self.note.get('app_context', 'global')
        display_name = self._get_display_name(app_context)

        self.title_label = QLabel(f"📌 {display_name}")
        self.title_label.setFont(QFont("Segoe UI Semibold", 9))
        self.title_label.setStyleSheet("color: rgba(0, 0, 0, 140);")
        self.header.addWidget(self.title_label)

        # Прогресс-бар (создаём сразу, но скрываем) - ПЕРЕД addStretch
        self.progress_label = QLabel()
        self.progress_label.setFont(QFont("Segoe UI", 8))
        self.progress_label.hide()
        self.header.addWidget(self.progress_label)

        self.header.addStretch()

        # Кнопка удалить (только если не базовая заметка)
        if not self.note.get('is_base', 0):
            delete_btn = QPushButton("✕")
            delete_btn.setFixedSize(20, 20)
            delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(231, 76, 60, 120);
                    border-radius: 10px;
                    border: none;
                    color: white;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(231, 76, 60, 200);
                }
            """)
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.note_id))
            self.header.addWidget(delete_btn)

        card_layout.addLayout(self.header)

        # QStackedWidget для переключения между режимами
        self.content_stack = QStackedWidget()

        # Режим 0: Обычная заметка (QTextEdit)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Заметка...")
        self.text_edit.setFont(QFont("Segoe UI", 10))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: rgba(0, 0, 0, 220);
            }
        """)
        self.text_edit.setPlainText(self.note.get('content', ''))
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.setFocusPolicy(Qt.StrongFocus)
        self.content_stack.addWidget(self.text_edit)

        # Режим 1: Рабочий режим (TaskListWidget)
        self.task_list = None  # Создаётся лениво при переключении в work режим
        if self._mode == 'work' and self.task_service:
            self._init_task_list()
            self.content_stack.setCurrentIndex(1)
        else:
            # Placeholder для рабочего режима
            placeholder = QWidget()
            self.content_stack.addWidget(placeholder)
            self.content_stack.setCurrentIndex(0)

        card_layout.addWidget(self.content_stack, 1)

        # Кнопка сворачивания
        self.collapse_btn = QPushButton("▼ свернуть")
        self.collapse_btn.setFixedHeight(24)
        self.collapse_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.collapse_btn.setFont(QFont("Segoe UI", 8))
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 8);
                border: none;
                border-radius: 6px;
                color: rgba(0, 0, 0, 100);
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 15);
                color: rgba(0, 0, 0, 160);
            }
        """)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        card_layout.addWidget(self.collapse_btn)

        root.addWidget(self.card)

    def _apply_shadow(self):
        """Применить тень к стикеру."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.card.setGraphicsEffect(shadow)

    def _get_display_name(self, app_context: str) -> str:
        """Получить отображаемое имя контекста."""
        names = {
            'global': 'Общие',
            'chrome.exe': 'Chrome',
            'firefox.exe': 'Firefox',
            'msedge.exe': 'Edge',
            'code.exe': 'VS Code',
            'pycharm64.exe': 'PyCharm',
            'notepad.exe': 'Блокнот',
            'explorer.exe': 'Проводник'
        }
        return names.get(app_context, app_context.replace('.exe', ''))

    def _on_text_changed(self):
        """Текст изменился — запускаем таймер автосохранения."""
        self._content_dirty = True
        self._save_timer.start()

    def _save_content(self):
        """Сохранить содержимое заметки."""
        if not self._content_dirty:
            return

        content = self.text_edit.toPlainText()
        self.content_changed.emit(self.note_id, content)
        self._content_dirty = False
        print(f"[sticky_note] Saved note {self.note_id}")

    def focusOutEvent(self, event):
        """Окно потеряло фокус — сохраняем немедленно."""
        super().focusOutEvent(event)

        # Останавливаем таймер и сохраняем сразу
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_content()
            print(f"[sticky_note] Focus lost, saved immediately")

    def _toggle_collapse(self):
        """Переключить сворачивание."""
        self._collapsed = not self._collapsed
        self.collapsed_changed.emit(self.note_id, self._collapsed)

        if self._collapsed:
            self._animate_collapse()
        else:
            self._animate_expand()

    def _animate_collapse(self):
        self._expanded_height = self.height()

        if hasattr(self, 'animation') and self.animation:
            self.animation.stop()
            self.animation.deleteLater()
        if hasattr(self, 'opacity_animation') and self.opacity_animation:
            self.opacity_animation.stop()
            self.opacity_animation.deleteLater()

        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(500)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.85)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)

        current_geom = self.geometry()
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(500)
        self.animation.setStartValue(current_geom)

        if self._edge_position in ['top', 'bottom']:
            end_rect = QRect(current_geom.x(), current_geom.bottom() - 40, current_geom.width(), 40)
        else:
            end_rect = QRect(current_geom.x(), current_geom.y(), current_geom.width(), 40)

        self.animation.setEndValue(end_rect)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self._set_collapsed_view)

        self.opacity_animation.start()
        self.animation.start()

        QTimer.singleShot(250, self.content_stack.hide)
        QTimer.singleShot(250, self.collapse_btn.hide)

    def _set_collapsed_view(self):
        display_name = self._get_display_name(self.note.get('app_context', 'global'))
        self.title_label.setText(f"📌 {display_name}")
        self.card.setCursor(QCursor(Qt.PointingHandCursor))
        self.content_stack.hide()
        self.collapse_btn.hide()
        self._add_task_btn.hide()

    def _animate_expand(self):
        self.content_stack.show()
        self.collapse_btn.show()

        if hasattr(self, 'animation') and self.animation:
            self.animation.stop()
            self.animation.deleteLater()
        if hasattr(self, 'opacity_animation') and self.opacity_animation:
            self.opacity_animation.stop()
            self.opacity_animation.deleteLater()

        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(500)
        self.opacity_animation.setStartValue(0.85)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)

        current_geom = self.geometry()
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(500)
        self.animation.setStartValue(current_geom)

        if self._edge_position in ['top', 'bottom']:
            end_rect = QRect(
                current_geom.x(),
                current_geom.bottom() - self._expanded_height,
                current_geom.width(),
                self._expanded_height
            )
        else:
            end_rect = QRect(current_geom.x(), current_geom.y(), current_geom.width(), self._expanded_height)

        self.animation.setEndValue(end_rect)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self._set_expanded_view)

        self.opacity_animation.start()
        self.animation.start()

    def _set_expanded_view(self):
        print(f"[debug] _set_expanded_view mode={self._mode} stack_index={self.content_stack.currentIndex()}")
        self.content_stack.show()
        self.collapse_btn.show()
        self.collapse_btn.setText("▼ свернуть")
        self.title_label.setText(f"📌 {self._get_display_name(self.note.get('app_context', 'global'))}")
        self.card.setCursor(QCursor(Qt.ArrowCursor))

        if self._mode == 'work':
            print(f"[debug] setting stack to 1 (task_list)")
            self.content_stack.setCurrentIndex(1)
            self._add_task_btn.show()
            self._sync_add_button()
            self._update_progress()
        else:
            print(f"[debug] setting stack to 0 (text_edit)")
            self.content_stack.setCurrentIndex(0)


    def mousePressEvent(self, event):
        """Обработка кликов."""
        if event.button() == Qt.LeftButton:
            # ALT + клик → удалить (если не базовая)
            if event.modifiers() & Qt.AltModifier:
                if not self.note.get('is_base', 0):
                    self.delete_requested.emit(self.note_id)
                return

            # Если свёрнут — всегда развернуть при клике
            if self._collapsed:
                self._toggle_collapse()
                return

            # Если клик по QTextEdit — передать фокус
            widget_under_mouse = self.childAt(event.pos())
            if widget_under_mouse == self.text_edit or self.text_edit.isAncestorOf(widget_under_mouse):
                self.text_edit.setFocus()
                return

        elif event.button() == Qt.RightButton:
            # ПКМ — отслеживаем двойной клик
            self._rmb_click_count += 1

            if self._rmb_click_count == 1:
                # Первый клик — запускаем таймер
                self._rmb_click_timer.start()
            elif self._rmb_click_count == 2:
                # Второй клик — двойной клик ПКМ → настройки
                self._rmb_click_timer.stop()
                self._rmb_click_count = 0
                print(f"[sticky_note] RMB double click → settings")
                self.settings_requested.emit()
                event.accept()
                return

    def _handle_rmb_single_click(self):
        """Обработка одиночного клика ПКМ."""
        self._rmb_click_count = 0

    def closeEvent(self, event):
        """Сохранить перед закрытием."""
        self._save_timer.stop()
        self._save_content()
        # Закрываем кнопку "+"
        if self._add_task_btn:
            self._add_task_btn.close()
            self._add_task_btn.deleteLater()
        print(f"[sticky_note] Closing, saved note {self.note_id}")
        event.accept()

    def _init_task_list(self):
        """Инициализировать TaskListWidget (ленивая загрузка)."""
        if self.task_list or not self.task_service:
            return

        from app.features.todo.ui.task_list_widget import TaskListWidget
        from app.features.todo.ui.task_detail_view import TaskDetailView

        self.task_list = TaskListWidget(self.note_id, self.task_service)
        self.task_list.task_toggled.connect(self._on_task_toggled)
        self.task_list.task_double_clicked.connect(self._on_task_double_clicked)
        self.task_list.task_clicked.connect(self._on_task_clicked)  # Одиночный клик

        # Заменяем placeholder на task_list
        placeholder = self.content_stack.widget(1)
        if placeholder is not None:
            self.content_stack.removeWidget(placeholder)
            placeholder.deleteLater()
        self.content_stack.insertWidget(1, self.task_list)

        # Добавляем TaskDetailView
        self.task_detail = TaskDetailView()
        self.task_detail.back_requested.connect(self._on_detail_back)
        self.task_detail.edit_requested.connect(self._on_task_double_clicked)
        self.task_detail.delete_requested.connect(self._on_task_deleted)
        self.content_stack.addWidget(self.task_detail)  # Индекс 2

        print(f"[sticky_note] TaskListWidget and TaskDetailView initialized for note {self.note_id}")

    def switch_mode(self, mode: str):
        """
        Переключить режим стикера.

        Args:
            mode: 'normal' или 'work'
        """
        if mode == self._mode:
            return

        print(f"[sticky_note] Switching mode: {self._mode} → {mode}")

        if mode == 'work':
            # Переключаемся в рабочий режим
            if not self.task_list:
                self._init_task_list()

            self.content_stack.setCurrentIndex(1)  # TaskListWidget
            self._mode = 'work'

            # Обновляем прогресс
            self._update_progress()

            # Показываем кнопку "+"
            if self.isVisible():
                self._add_task_btn.show()
                self._sync_add_button()

        else:
            # Переключаемся в обычный режим
            self.content_stack.setCurrentIndex(0)
            self._mode = 'normal'

            # Убираем прогресс
            self._update_progress()  # Это удалит прогресс-бар

            # Скрываем кнопку "+"
            self._add_task_btn.hide()

            # Восстанавливаем заголовок
            app_context = self.note.get('app_context', 'global')
            display_name = self._get_display_name(app_context)
            self.title_label.setText(f"📌 {display_name}")

        # НЕ сохраняем режим в БД — режим теперь глобальный (в settings)
        # Пробрасываем сигнал
        self.mode_changed.emit(self.note_id, mode)

    def _on_task_toggled(self, task_id: int, completed: bool):
        """Задача переключена — обновляем прогресс в заголовке."""
        self._update_progress()
        print(f"[sticky_note] Task {task_id} toggled: {completed}")

    def _on_task_clicked(self, task_id: int):
        """Одиночный клик по задаче — показать детали."""
        task = self.task_service.get_task_by_id(task_id)
        if not task:
            return

        # Показываем детали
        self.task_detail.show_task(task)
        self.content_stack.setCurrentIndex(2)  # TaskDetailView

        # Меняем заголовок: (Окружение) / (Название задачи) / 🔴
        app_context = self.note.get('app_context', 'global')
        display_name = self._get_display_name(app_context)

        priority = task.get('priority', 'medium')
        priority_icons = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴'
        }
        priority_icon = priority_icons.get(priority, '⚪')

        task_name = task.get('text', '')[:30]  # Обрезаем если длинное
        if len(task.get('text', '')) > 30:
            task_name += '...'

        self.title_label.setText(f"({display_name}) / {task_name} / {priority_icon}")

        print(f"[sticky_note] Showing details for task {task_id}")

    def _on_detail_back(self):
        """Вернуться к списку задач."""
        # Возвращаем список задач
        self.content_stack.setCurrentIndex(1)  # TaskListWidget

        # Восстанавливаем заголовок
        app_context = self.note.get('app_context', 'global')
        display_name = self._get_display_name(app_context)
        self.title_label.setText(f"📌 {display_name}")

        print(f"[sticky_note] Back to task list")

    def _on_task_deleted(self, task_id: int):
        """Задача удалена из деталей."""
        self.task_service.delete_task(task_id)

        # Возвращаемся к списку
        self._on_detail_back()

        # Обновляем список задач
        if self.task_list:
            self.task_list.load_tasks()
        self._update_progress()

        print(f"[sticky_note] Task {task_id} deleted")

    def _update_progress(self):
        """Обновить прогресс-бар в заголовке."""
        if self._mode != 'work' or not self.task_service:
            # Скрываем прогресс-бар
            self.progress_label.hide()
            return

        progress = self.task_service.get_progress(self.note_id)
        total = progress['total']
        completed = progress['completed']

        if total == 0:
            # Скрываем прогресс-бар если нет задач
            self.progress_label.hide()
            return

        # Показываем и обновляем прогресс-бар
        self.progress_label.show()

        # Определяем цвет по проценту выполнения
        percent = progress['percent']
        if percent == 100:
            color = '#10b981'  # зелёный
            icon = '🟢'
        elif percent >= 50:
            color = '#f59e0b'  # оранжевый
            icon = '🟡'
        else:
            color = '#ef4444'  # красный
            icon = '🔴'

        self.progress_label.setText(f"{icon} {completed}/{total}")
        self.progress_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _on_task_double_clicked(self, task_id: int):
        """Двойной клик по задаче — открыть редактор."""
        from app.features.todo.ui.task_editor_dialog import TaskEditorDialog

        # Получаем данные задачи
        task = self.task_service.get_task_by_id(task_id)
        if not task:
            return

        # Открываем диалог редактирования
        dialog = TaskEditorDialog(task_data=task, parent=self)
        dialog.task_saved.connect(lambda data: self._on_task_edited(task_id, data))
        dialog.exec()

    def _on_task_edited(self, task_id: int, data: dict):
        """Задача отредактирована."""
        self.task_service.update_task(task_id, **data)
        # Обновляем список задач
        if self.task_list:
            self.task_list.load_tasks()
        self._update_progress()
        print(f"[sticky_note] Task {task_id} edited")

    def _on_add_task_requested(self):
        """Кнопка "+" нажата — открыть диалог добавления задачи."""
        from app.features.todo.ui.task_editor_dialog import TaskEditorDialog

        dialog = TaskEditorDialog(parent=self)
        dialog.task_saved.connect(self._on_task_created)
        dialog.exec()

    def _on_task_created(self, data: dict):
        """Новая задача создана."""
        self.task_service.create_task(self.note_id, **data)
        # Обновляем список задач
        if self.task_list:
            self.task_list.load_tasks()
        self._update_progress()
        print(f"[sticky_note] New task created for note {self.note_id}")

    def _sync_add_button(self):
        """Синхронизировать позицию кнопки "+" с окном стикера."""
        if not self._add_task_btn:
            return

        # Автоматическое позиционирование (ищет свободное место)
        self._add_task_btn.reposition(self.geometry())

    def showEvent(self, event):
        """Окно показано — показываем кнопку если work режим и не свёрнут."""
        super().showEvent(event)
        if self._mode == 'work' and not self._collapsed:
            self._add_task_btn.show()
            self._sync_add_button()

    def hideEvent(self, event):
        """Окно скрыто — скрываем кнопку."""
        super().hideEvent(event)
        self._add_task_btn.hide()

    def moveEvent(self, event):
        """Окно перемещено — синхронизируем кнопку."""
        super().moveEvent(event)
        self._sync_add_button()

    def resizeEvent(self, event):
        """Окно изменило размер — синхронизируем кнопку."""
        super().resizeEvent(event)
        self._sync_add_button()

    def get_mode(self) -> str:
        """Получить текущий режим."""
        return self._mode
