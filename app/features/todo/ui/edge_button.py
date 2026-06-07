"""
Плавающая кнопка Edge-панели для показа и скрытия заметок.

Поддерживает перетаскивание, сохранение позиции, двойной клик ПКМ (настройки)
и ALT+ЛКМ (новая заметка).
"""
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QFont, QCursor


class EdgeButton(QWidget):
    """Плавающая кнопка для показа/скрытия заметок."""

    clicked = Signal()
    double_clicked = Signal()  # Двойной клик → настройки
    alt_clicked = Signal()     # ALT + клик → новая заметка

    def __init__(self, position: str = 'right'):
        """
        Args:
            position: положение кнопки ('left', 'right', 'top', 'bottom')
        """
        super().__init__()
        self._position = position
        self._drag_pos = None
        self._click_timer = QTimer()
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(300)  # 300ms для определения двойного клика
        self._click_count = 0
        self._last_button = None  # Запоминаем последнюю нажатую кнопку

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(50, 120)

        self._build_ui()
        self._position_button()

    def _build_ui(self):
        """Построить UI кнопки."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QPushButton("📝")
        self.button.setFixedSize(40, 100)
        self.button.setCursor(QCursor(Qt.PointingHandCursor))
        self.button.setFont(QFont("Segoe UI", 20))
        self.button.setToolTip("Заметки\n\nЛКМ: показать/скрыть\nПКМ двойной клик: настройки\nALT+ЛКМ: новая заметка")

        # Стиль зависит от позиции
        if self._position in ['left', 'right']:
            border_radius = "border-radius: 0 12px 12px 0;" if self._position == 'left' else "border-radius: 12px 0 0 12px;"
        else:
            border_radius = "border-radius: 0 0 12px 12px;" if self._position == 'top' else "border-radius: 12px 12px 0 0;"

        self.button.setStyleSheet(f"""
            QPushButton {{
                background: rgba(30, 30, 30, 220);
                color: white;
                border: 1px solid rgba(255, 255, 255, 20);
                {border_radius}
            }}
            QPushButton:hover {{
                background: rgba(0, 120, 215, 200);
                border: 1px solid #0078d7;
            }}
            QPushButton:pressed {{
                background: rgba(0, 100, 180, 220);
            }}
        """)

        self.button.installEventFilter(self)
        layout.addWidget(self.button, 0, Qt.AlignCenter)

    def _position_button(self):
        """Позиционировать кнопку на краю экрана."""
        from app.core.database import db

        # Проверяем сохранённую позицию
        saved_x = db.get_setting('edge_button_x', 'notes')
        saved_y = db.get_setting('edge_button_y', 'notes')

        if saved_x is not None and saved_y is not None:
            # Используем сохранённую позицию
            self.move(int(saved_x), int(saved_y))
            print(f"[edge_button] Restored saved position: ({saved_x}, {saved_y})")
            return

        # Иначе — дефолтная позиция по краю экрана
        screen = QApplication.primaryScreen().availableGeometry()

        if self._position == 'right':
            x = screen.width() - self.width()
            y = screen.height() // 2 - self.height() // 2
        elif self._position == 'left':
            x = 0
            y = screen.height() // 2 - self.height() // 2
        elif self._position == 'top':
            x = screen.width() // 2 - self.width() // 2
            y = 0
        else:  # bottom
            x = screen.width() // 2 - self.width() // 2
            y = screen.height() - self.height()

        self.move(x, y)

    def eventFilter(self, obj, event):
        """Фильтр событий для определения двойного клика и ALT."""
        if obj == self.button:
            if event.type() == QEvent.MouseButtonPress:
                button = event.button()

                # Обрабатываем и ЛКМ и ПКМ
                if button in (Qt.LeftButton, Qt.RightButton):
                    # Проверяем ALT (только для ЛКМ)
                    if button == Qt.LeftButton and event.modifiers() & Qt.AltModifier:
                        # ALT + клик → новая заметка
                        print("[edge_button] ALT + click detected")
                        self.alt_clicked.emit()
                        return True

                    # Проверяем, та же кнопка или другая
                    if self._click_count > 0 and self._last_button != button:
                        # Другая кнопка — сбрасываем счётчик
                        self._click_timer.stop()
                        self._click_count = 0

                    self._last_button = button
                    self._click_count += 1

                    if self._click_count == 1:
                        # Первый клик — запускаем таймер
                        self._click_timer.timeout.connect(self._handle_single_click)
                        self._click_timer.start()
                    elif self._click_count == 2:
                        # Второй клик — это двойной клик
                        self._click_timer.stop()
                        self._click_count = 0

                        if button == Qt.RightButton:
                            # ПКМ двойной клик → настройки
                            print("[edge_button] RMB double click → settings")
                            self.double_clicked.emit()
                        else:
                            # ЛКМ двойной клик → показать/скрыть (как обычный клик)
                            print("[edge_button] LMB double click → toggle")
                            self.clicked.emit()

                        return True

        return super().eventFilter(obj, event)

    def _handle_single_click(self):
        """Обработка одиночного клика."""
        self._click_count = 0
        self.clicked.emit()

    def set_position(self, position: str):
        """
        Изменить положение кнопки.

        Args:
            position: 'left', 'right', 'top', 'bottom'
        """
        self._position = position
        self._build_ui()  # Перестроить UI с новым стилем
        self._position_button()

    def mousePressEvent(self, event):
        """Начало перетаскивания."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        """Перетаскивание кнопки."""
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        """Конец перетаскивания — сохранить позицию."""
        if self._drag_pos:
            self._drag_pos = None
            # Сохраняем позицию в БД
            from app.core.database import db
            db.set_setting('edge_button_x', self.x(), 'notes')
            db.set_setting('edge_button_y', self.y(), 'notes')
            print(f"[edge_button] Saved position: ({self.x()}, {self.y()})")

    def showEvent(self, event):
        """При показе — форсируем topmost."""
        super().showEvent(event)
        QTimer.singleShot(100, self._force_topmost)

    def _force_topmost(self):
        """Форсировать окно поверх всех через WinAPI."""
        try:
            import ctypes
            hwnd = int(self.winId())
            # HWND_TOPMOST = -1, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0040)
        except Exception as e:
            print(f"[edge_button] topmost error: {e}")
