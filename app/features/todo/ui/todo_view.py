"""
Главное окно Todo модуля.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QScrollArea, QFrame, QCheckBox, QDateTimeEdit,
    QTextEdit
)
from PySide6.QtCore import Qt, Signal, QDateTime, QTimer
from PySide6.QtGui import QFont, QCursor
from datetime import datetime


class TodoItemWidget(QWidget):
    """Виджет одной задачи в списке."""

    completed = Signal(int)  # task_id
    deleted = Signal(int)    # task_id

    def __init__(self, task: dict, parent=None):
        super().__init__(parent)
        self.task = task
        self._build_ui()

    def _build_ui(self):
        """Построить UI элемента."""
        self.setFixedHeight(70)
        self.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 30, 180);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 8);
            }
            QWidget:hover {
                background: rgba(40, 40, 40, 200);
                border: 1px solid rgba(255, 255, 255, 15);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Чекбокс
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.task['completed'] == 1)
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 30);
                background: rgba(255, 255, 255, 5);
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 2px solid #0078d7;
            }
        """)
        self.checkbox.stateChanged.connect(lambda: self.completed.emit(self.task['id']))
        layout.addWidget(self.checkbox)

        # Приоритет индикатор
        priority_colors = {1: "#e74c3c", 2: "#f39c12", 3: "#27ae60"}
        priority_dot = QLabel("●")
        priority_dot.setFont(QFont("Segoe UI", 16))
        priority_dot.setStyleSheet(f"color: {priority_colors.get(self.task['priority'], '#27ae60')};")
        layout.addWidget(priority_dot)

        # Текст задачи
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(self.task['title'])
        title_label.setFont(QFont("Segoe UI", 10))
        title_label.setStyleSheet("color: white;")
        if self.task['completed'] == 1:
            title_label.setStyleSheet("color: rgba(255, 255, 255, 100); text-decoration: line-through;")
        text_layout.addWidget(title_label)

        # Категория и дедлайн
        info_parts = []
        if self.task.get('category'):
            info_parts.append(f"📁 {self.task['category']}")
        if self.task.get('deadline'):
            try:
                deadline = datetime.fromisoformat(self.task['deadline'])
                info_parts.append(f"📅 {deadline.strftime('%d.%m %H:%M')}")
            except:
                pass

        if info_parts:
            info_label = QLabel(" • ".join(info_parts))
            info_label.setFont(QFont("Segoe UI", 8))
            info_label.setStyleSheet("color: rgba(200, 200, 200, 120);")
            text_layout.addWidget(info_label)

        layout.addLayout(text_layout, 1)

        # Кнопка удалить
        delete_btn = QPushButton("✕")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        delete_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231, 76, 60, 100);
                border-radius: 14px;
                border: none;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(231, 76, 60, 180);
            }
        """)
        delete_btn.clicked.connect(lambda: self.deleted.emit(self.task['id']))
        layout.addWidget(delete_btn)


class TodoView(QWidget):
    """Главное окно Todo."""

    add_task = Signal(str, int, str, str, str)  # title, priority, deadline, category, description
    complete_task = Signal(int)  # task_id
    delete_task = Signal(int)    # task_id

    def __init__(self):
        super().__init__()
        self._compact = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()
        self._init_geometry()

    def _init_geometry(self):
        """Начальная позиция — правый верхний угол."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = 80
        self.move(x, y)

    def _build_ui(self):
        """Построить UI."""
        self.setFixedSize(420, 650)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Главная карточка
        self.card = QFrame()
        self.card.setObjectName("main_card")
        self.card.setStyleSheet("""
            QFrame#main_card {
                background: rgba(18, 18, 18, 240);
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 10);
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        # Заголовок + кнопки
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("📝 Задачи")
        title.setFont(QFont("Segoe UI Semibold", 13))
        title.setStyleSheet("color: white;")
        header.addWidget(title)

        header.addStretch()

        # Кнопка компактный режим
        self.compact_btn = QPushButton("⇅")
        self.compact_btn.setFixedSize(32, 32)
        self.compact_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.compact_btn.setToolTip("Компактный режим")
        self.compact_btn.setStyleSheet(self._button_style())
        self.compact_btn.clicked.connect(self._toggle_compact)
        header.addWidget(self.compact_btn)

        # Кнопка закрыть
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(self._button_style())
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)

        card_layout.addLayout(header)

        # Форма добавления задачи
        self.add_form = QFrame()
        add_form_layout = QVBoxLayout(self.add_form)
        add_form_layout.setContentsMargins(0, 0, 0, 0)
        add_form_layout.setSpacing(8)

        # Поле ввода
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Новая задача...")
        self.title_input.setFont(QFont("Segoe UI", 10))
        self.title_input.setStyleSheet("""
            QLineEdit {
                background: rgba(40, 40, 40, 180);
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 8px;
                padding: 10px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        add_form_layout.addWidget(self.title_input)

        # Приоритет кнопки
        priority_layout = QHBoxLayout()
        priority_layout.setSpacing(6)

        priority_label = QLabel("Приоритет:")
        priority_label.setFont(QFont("Segoe UI", 9))
        priority_label.setStyleSheet("color: rgba(200, 200, 200, 160);")
        priority_layout.addWidget(priority_label)

        self.priority_btns = []
        priorities = [
            (1, "Высокий", "#e74c3c"),
            (2, "Средний", "#f39c12"),
            (3, "Низкий", "#27ae60")
        ]

        for priority, name, color in priorities:
            btn = QPushButton(name)
            btn.setFixedHeight(28)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setCheckable(True)
            btn.setProperty("priority", priority)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 8);
                    border: 1px solid rgba(255, 255, 255, 10);
                    border-radius: 6px;
                    color: {color};
                    font-size: 9px;
                    padding: 4px 12px;
                }}
                QPushButton:checked {{
                    background: {color};
                    color: white;
                    border: 1px solid {color};
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 15);
                }}
            """)
            btn.clicked.connect(lambda checked, b=btn: self._select_priority(b))
            self.priority_btns.append(btn)
            priority_layout.addWidget(btn)

        # По умолчанию средний приоритет
        self.priority_btns[2].setChecked(True)

        priority_layout.addStretch()
        add_form_layout.addLayout(priority_layout)

        # Дедлайн
        deadline_layout = QHBoxLayout()
        deadline_layout.setSpacing(6)

        deadline_label = QLabel("Дедлайн:")
        deadline_label.setFont(QFont("Segoe UI", 9))
        deadline_label.setStyleSheet("color: rgba(200, 200, 200, 160);")
        deadline_layout.addWidget(deadline_label)

        self.deadline_input = QDateTimeEdit()
        self.deadline_input.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.deadline_input.setFont(QFont("Segoe UI", 9))
        self.deadline_input.setStyleSheet("""
            QDateTimeEdit {
                background: rgba(40, 40, 40, 180);
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 6px;
                padding: 4px 8px;
                color: white;
            }
        """)
        deadline_layout.addWidget(self.deadline_input)

        self.deadline_checkbox = QCheckBox("Включить")
        self.deadline_checkbox.setFont(QFont("Segoe UI", 9))
        self.deadline_checkbox.setStyleSheet("color: rgba(200, 200, 200, 160);")
        deadline_layout.addWidget(self.deadline_checkbox)

        deadline_layout.addStretch()
        add_form_layout.addLayout(deadline_layout)

        # Кнопка добавить
        add_btn = QPushButton("+ Добавить задачу")
        add_btn.setFixedHeight(36)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.setFont(QFont("Segoe UI Semibold", 10))
        add_btn.setStyleSheet("""
            QPushButton {
                background: #0078d7;
                border: none;
                border-radius: 8px;
                color: white;
            }
            QPushButton:hover {
                background: #1084e0;
            }
            QPushButton:pressed {
                background: #006cc1;
            }
        """)
        add_btn.clicked.connect(self._on_add_task)
        add_form_layout.addWidget(add_btn)

        card_layout.addWidget(self.add_form)

        # Список задач
        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setFrameShape(QFrame.NoFrame)
        self.tasks_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 5);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 30);
                border-radius: 4px;
            }
        """)

        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.addStretch()

        self.tasks_scroll.setWidget(self.tasks_container)
        card_layout.addWidget(self.tasks_scroll, 1)

        root.addWidget(self.card)

    def _button_style(self) -> str:
        """Стиль для кнопок заголовка."""
        return """
            QPushButton {
                background: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 6px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(0, 120, 215, 100);
                border: 1px solid #0078d7;
            }
        """

    def _select_priority(self, btn: QPushButton):
        """Выбрать приоритет."""
        for b in self.priority_btns:
            if b != btn:
                b.setChecked(False)

    def _on_add_task(self):
        """Создать задачу из полей формы и испустить сигнал add_task."""
        """Добавить задачу."""
        title = self.title_input.text().strip()
        if not title:
            return

        # Получаем выбранный приоритет
        priority = 3
        for btn in self.priority_btns:
            if btn.isChecked():
                priority = btn.property("priority")
                break

        # Дедлайн
        deadline = ""
        if self.deadline_checkbox.isChecked():
            deadline = self.deadline_input.dateTime().toString(Qt.ISODate)

        # Автоопределение категории
        from app.features.todo.core.smart_tagger import SmartTagger
        category = SmartTagger.detect_category(title)

        self.add_task.emit(title, priority, deadline, category, "")

        # Очистить форму
        self.title_input.clear()
        self.priority_btns[2].setChecked(True)
        self.deadline_checkbox.setChecked(False)

    def update_tasks(self, tasks: list):
        """Обновить список задач в UI после изменений в БД."""
        """Обновить список задач."""
        # Очистить текущий список
        while self.tasks_layout.count() > 1:
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Добавить задачи
        for task in tasks:
            item = TodoItemWidget(task)
            item.completed.connect(self.complete_task)
            item.deleted.connect(self.delete_task)
            self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, item)

    def _toggle_compact(self):
        """Переключить компактный режим."""
        self._compact = not self._compact
        if self._compact:
            self.setFixedSize(280, 400)
            self.add_form.hide()
        else:
            self.setFixedSize(420, 650)
            self.add_form.show()

    def mousePressEvent(self, event):
        """Начало перетаскивания."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        """Перетаскивание окна."""
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
