"""
Диалог добавления/редактирования задачи.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QFrame
)
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtGui import QFont, QColor
from datetime import datetime


class TaskEditorDialog(QDialog):
    """Диалог для создания/редактирования задачи."""

    task_saved = Signal(dict)  # данные задачи

    def __init__(self, task_data: dict = None, parent=None):
        """
        Args:
            task_data: данные задачи для редактирования (None = новая задача)
        """
        super().__init__(parent)
        self.task_data = task_data or {}
        self.is_edit_mode = task_data is not None

        self.setWindowTitle("Редактировать задачу" if self.is_edit_mode else "Новая задача")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(400)

        self._build_ui()

    def _build_ui(self):
        """Построить UI."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Главная карточка
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card {
                background: #1e1e1e;
                border-radius: 12px;
                border: 1px solid #333;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # Заголовок
        title = QLabel("Редактировать задачу" if self.is_edit_mode else "Новая задача")
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet("color: white;")
        card_layout.addWidget(title)

        # Название задачи
        card_layout.addWidget(self._label("Название задачи"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Что нужно сделать?")
        self.text_input.setText(self.task_data.get('text', ''))
        self.text_input.setStyleSheet(self._input_style())
        self.text_input.setFont(QFont("Segoe UI", 10))
        card_layout.addWidget(self.text_input)

        # Описание (опционально)
        card_layout.addWidget(self._label("Описание (опционально)"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Дополнительные детали...")
        self.description_input.setPlainText(self.task_data.get('description', ''))
        self.description_input.setStyleSheet(self._input_style())
        self.description_input.setFont(QFont("Segoe UI", 10))
        self.description_input.setFixedHeight(80)
        card_layout.addWidget(self.description_input)

        # Приоритет
        card_layout.addWidget(self._label("Приоритет"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["🟢 Низкий", "🟡 Средний", "🔴 Высокий"])
        priority_map = {'low': 0, 'medium': 1, 'high': 2}
        current_priority = self.task_data.get('priority', 'medium')
        self.priority_combo.setCurrentIndex(priority_map.get(current_priority, 1))
        self.priority_combo.setStyleSheet(self._combo_style())
        self.priority_combo.setFont(QFont("Segoe UI", 10))
        card_layout.addWidget(self.priority_combo)

        # Дедлайн (опционально)
        deadline_row = QHBoxLayout()
        deadline_row.setSpacing(10)

        self.deadline_checkbox = QPushButton("📅 Добавить дедлайн")
        self.deadline_checkbox.setCheckable(True)
        self.deadline_checkbox.setChecked(bool(self.task_data.get('deadline')))
        self.deadline_checkbox.setStyleSheet(self._checkbox_style())
        self.deadline_checkbox.toggled.connect(self._toggle_deadline)
        deadline_row.addWidget(self.deadline_checkbox)

        self.deadline_input = QDateTimeEdit()
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDisplayFormat("dd.MM.yyyy HH:mm")

        if self.task_data.get('deadline'):
            dt = datetime.fromisoformat(self.task_data['deadline'])
            self.deadline_input.setDateTime(QDateTime(dt))
        else:
            self.deadline_input.setDateTime(QDateTime.currentDateTime().addDays(1))

        self.deadline_input.setStyleSheet(self._input_style())
        self.deadline_input.setFont(QFont("Segoe UI", 10))
        self.deadline_input.setVisible(bool(self.task_data.get('deadline')))
        deadline_row.addWidget(self.deadline_input)

        card_layout.addLayout(deadline_row)

        # Кнопки
        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(self._button_style("#444", "#555"))
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить" if self.is_edit_mode else "Создать")
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet(self._button_style("#0078d7", "#1084e0"))
        save_btn.clicked.connect(self._save_task)
        buttons.addWidget(save_btn)

        card_layout.addLayout(buttons)

        root.addWidget(card)

    def _label(self, text: str) -> QLabel:
        """Создать label."""
        label = QLabel(text)
        label.setFont(QFont("Segoe UI Semibold", 9))
        label.setStyleSheet("color: #aaa;")
        return label

    def _toggle_deadline(self, checked: bool):
        """Показать/скрыть поле дедлайна."""
        self.deadline_input.setVisible(checked)

    def _save_task(self):
        """Сохранить задачу."""
        text = self.text_input.text().strip()
        if not text:
            # TODO: показать ошибку
            return

        # Собираем данные
        priority_map = {0: 'low', 1: 'medium', 2: 'high'}
        priority = priority_map[self.priority_combo.currentIndex()]

        deadline = None
        if self.deadline_checkbox.isChecked():
            dt = self.deadline_input.dateTime().toPython()
            deadline = dt.isoformat()

        task_data = {
            'text': text,
            'description': self.description_input.toPlainText().strip(),
            'priority': priority,
            'deadline': deadline,
        }

        # Если редактирование — добавляем ID
        if self.is_edit_mode:
            task_data['id'] = self.task_data['id']

        self.task_saved.emit(task_data)
        self.accept()

    def _input_style(self) -> str:
        """Стиль для input полей."""
        return """
            QLineEdit, QTextEdit, QDateTimeEdit {
                background: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QDateTimeEdit:focus {
                border: 1px solid #0078d7;
            }
        """

    def _combo_style(self) -> str:
        """Стиль для combobox."""
        return """
            QComboBox {
                background: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                color: white;
            }
            QComboBox:focus {
                border: 1px solid #0078d7;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #2a2a2a;
                border: 1px solid #444;
                selection-background-color: #0078d7;
                color: white;
            }
        """

    def _checkbox_style(self) -> str:
        """Стиль для checkbox-кнопки."""
        return """
            QPushButton {
                background: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                color: #aaa;
                text-align: left;
            }
            QPushButton:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
                color: white;
            }
            QPushButton:hover {
                background: #333;
            }
        """

    def _button_style(self, bg: str, hover: str) -> str:
        """Стиль для кнопок."""
        return f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {hover};
            }}
        """
