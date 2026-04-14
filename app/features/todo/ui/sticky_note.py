"""
Один стикер (sticky note) в стиле post-it.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
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

    def __init__(self, note: dict, parent=None):
        super().__init__(parent)
        self.note = note
        self.note_id = note['id']
        self._collapsed = note.get('collapsed', 0) == 1
        self._content_dirty = False  # Флаг для отслеживания изменений
        self._expanded_height = note.get('height', 200)  # Сохраняем высоту до сворачивания

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
        header = QHBoxLayout()
        header.setSpacing(6)

        # Иконка приложения + название
        app_context = self.note.get('app_context', 'global')
        display_name = self._get_display_name(app_context)

        self.title_label = QLabel(f"📌 {display_name}")
        self.title_label.setFont(QFont("Segoe UI Semibold", 9))
        self.title_label.setStyleSheet("color: rgba(0, 0, 0, 140);")
        header.addWidget(self.title_label)

        header.addStretch()

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
            header.addWidget(delete_btn)

        card_layout.addLayout(header)

        # Текстовое поле
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Заметка...")
        self.text_edit.setFont(QFont("Segoe UI", 10))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: rgba(0, 0, 0, 220);
                text-shadow: 0px 1px 2px rgba(255, 255, 255, 0.8);
            }
        """)
        self.text_edit.setPlainText(self.note.get('content', ''))
        self.text_edit.textChanged.connect(self._on_text_changed)

        # QTextEdit может получать фокус независимо от WS_EX_NOACTIVATE окна
        self.text_edit.setFocusPolicy(Qt.StrongFocus)

        card_layout.addWidget(self.text_edit, 1)

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
        """Анимация сворачивания."""
        # Сохраняем текущую высоту перед сворачиванием
        self._expanded_height = self.height()

        # Удаляем старую анимацию если есть
        if hasattr(self, 'animation') and self.animation:
            self.animation.stop()
            self.animation.deleteLater()
        if hasattr(self, 'opacity_animation') and self.opacity_animation:
            self.opacity_animation.stop()
            self.opacity_animation.deleteLater()

        # Анимация прозрачности окна
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(500)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.85)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Анимация уменьшения высоты (сохраняем текущую позицию)
        current_geom = self.geometry()
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(500)  # 500ms для плавности
        self.animation.setStartValue(current_geom)
        end_rect = QRect(current_geom.x(), current_geom.y(), current_geom.width(), 40)
        self.animation.setEndValue(end_rect)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)  # Более плавная кривая
        self.animation.finished.connect(self._set_collapsed_view)

        # Запускаем обе анимации одновременно
        self.opacity_animation.start()
        self.animation.start()

        # Скрываем элементы в середине анимации (250ms)
        QTimer.singleShot(250, self.text_edit.hide)
        QTimer.singleShot(250, self.collapse_btn.hide)

    def _set_collapsed_view(self):
        """Установить свёрнутый вид."""
        # Не используем setFixedHeight — это блокирует анимацию
        # Показываем только название приложения
        display_name = self._get_display_name(self.note.get('app_context', 'global'))
        self.title_label.setText(f"📌 {display_name}")
        self.card.setCursor(QCursor(Qt.PointingHandCursor))

        # Скрываем текстовое поле и кнопку сворачивания
        self.text_edit.hide()
        self.collapse_btn.hide()

    def _animate_expand(self):
        """Анимация разворачивания."""
        # Сначала показываем элементы
        self.text_edit.show()
        self.collapse_btn.show()

        # Удаляем старую анимацию если есть
        if hasattr(self, 'animation') and self.animation:
            self.animation.stop()
            self.animation.deleteLater()
        if hasattr(self, 'opacity_animation') and self.opacity_animation:
            self.opacity_animation.stop()
            self.opacity_animation.deleteLater()

        # Анимация прозрачности
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(500)
        self.opacity_animation.setStartValue(0.85)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Анимация увеличения высоты (используем сохранённую высоту)
        current_geom = self.geometry()
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(500)  # 500ms для плавности
        self.animation.setStartValue(current_geom)
        end_rect = QRect(current_geom.x(), current_geom.y(), current_geom.width(), self._expanded_height)
        self.animation.setEndValue(end_rect)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)  # Более плавная кривая
        self.animation.finished.connect(self._set_expanded_view)

        # Запускаем обе анимации одновременно
        self.opacity_animation.start()
        self.animation.start()

    def _set_expanded_view(self):
        """Установить развёрнутый вид."""
        self.text_edit.show()
        self.collapse_btn.show()
        self.collapse_btn.setText("▼ свернуть")
        self.title_label.setText(f"📌 {self._get_display_name(self.note.get('app_context', 'global'))}")
        self.card.setCursor(QCursor(Qt.ArrowCursor))

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
        print(f"[sticky_note] Closing, saved note {self.note_id}")
        event.accept()
