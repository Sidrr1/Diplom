"""Диалог добавления/редактирования задачи."""
from __future__ import annotations

import calendar
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDateTime, QDate
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QApplication,
)

_MONTHS = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)


class CompactDateTimePicker(QWidget):
    """Компактный выбор даты: день / месяц / год / время — отдельные поля."""

    def __init__(self, dt: QDateTime | None = None, parent=None):
        super().__init__(parent)
        self._dt = dt or QDateTime.currentDateTime().addDays(1)
        self._build()

    def _build(self):
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._day = QSpinBox()
        self._day.setRange(1, 31)
        self._day.setValue(self._dt.date().day())
        self._day.setPrefix("д ")
        self._day.setFixedWidth(62)
        self._day.setStyleSheet(self._spin_style())
        self._day.valueChanged.connect(self._clamp_day)
        row.addWidget(self._day)

        self._month = QComboBox()
        self._month.addItems(_MONTHS)
        self._month.setCurrentIndex(self._dt.date().month() - 1)
        self._month.setStyleSheet(self._combo_style())
        row.addWidget(self._month, 1)

        self._year = QSpinBox()
        self._year.setRange(2020, 2036)
        self._year.setValue(self._dt.date().year())
        self._year.setPrefix("г ")
        self._year.setFixedWidth(76)
        self._year.setStyleSheet(self._spin_style())
        row.addWidget(self._year)

        self._time = QTimeEdit()
        self._time.setDisplayFormat("HH:mm")
        self._time.setTime(self._dt.time())
        self._time.setFixedWidth(72)
        self._time.setStyleSheet(self._time_style())
        row.addWidget(self._time)

        self._month.currentIndexChanged.connect(self._clamp_day)
        self._year.valueChanged.connect(self._clamp_day)
        self._clamp_day()

    def _clamp_day(self):
        y = self._year.value()
        m = self._month.currentIndex() + 1
        last = calendar.monthrange(y, m)[1]
        self._day.setMaximum(last)
        if self._day.value() > last:
            self._day.setValue(last)

    def date_time(self) -> QDateTime:
        d = QDate(
            self._year.value(),
            self._month.currentIndex() + 1,
            self._day.value(),
        )
        return QDateTime(d, self._time.time())

    def set_date_time(self, dt: QDateTime) -> None:
        self._year.setValue(dt.date().year())
        self._month.setCurrentIndex(dt.date().month() - 1)
        self._clamp_day()
        self._day.setValue(dt.date().day())
        self._time.setTime(dt.time())

    @staticmethod
    def _spin_style() -> str:
        return """
            QSpinBox {
                background:#252525; border:1px solid #333; border-radius:8px;
                padding:6px 8px; color:#f0f0f0; font-size:10px;
            }
            QSpinBox:focus { border-color:#0078d7; }
            QSpinBox::up-button, QSpinBox::down-button {
                width:14px; border:none; background:#333;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background:#0078d7;
            }
        """

    @staticmethod
    def _combo_style() -> str:
        return """
            QComboBox {
                background:#252525; border:1px solid #333; border-radius:8px;
                padding:6px 10px; color:#f0f0f0; font-size:10px;
            }
            QComboBox:focus { border-color:#0078d7; }
            QComboBox::drop-down { border:none; width:22px; }
            QComboBox QAbstractItemView {
                background:#1e1e1e; border:1px solid #333;
                selection-background-color:#0078d7; color:#f0f0f0;
                outline:none;
            }
        """

    @staticmethod
    def _time_style() -> str:
        return """
            QTimeEdit {
                background:#252525; border:1px solid #333; border-radius:8px;
                padding:6px 8px; color:#f0f0f0; font-size:10px;
            }
            QTimeEdit:focus { border-color:#0078d7; }
            QTimeEdit::up-button, QTimeEdit::down-button {
                width:14px; border:none; background:#333;
            }
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {
                background:#0078d7;
            }
        """


class TaskEditorDialog(QDialog):
    """Диалог для создания/редактирования задачи."""

    task_saved = Signal(dict)

    _PRIORITY = (
        ("low", "Низкий", "#2ecc71"),
        ("medium", "Средний", "#f1c40f"),
        ("high", "Высокий", "#e74c3c"),
    )

    def __init__(self, task_data: dict = None, parent=None):
        super().__init__(parent)
        self.task_data = task_data or {}
        self.is_edit_mode = bool(task_data)
        self._priority_key = self.task_data.get("priority", "medium")
        self._priority_btns: dict[str, QPushButton] = {}
        self._drag_pos = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(380)
        self._build_ui()
        self._apply_shadow()
        self.adjustSize()

    def open_centered(self) -> int:
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        x = screen.center().x() - self.width() // 2
        y = screen.center().y() - self.height() // 2
        self.move(x, y)
        return self.exec()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() <= 56:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            delta = e.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card {
                background: #141414;
                border-radius: 16px;
                border: 1px solid #2a2a2a;
            }
        """)
        self._card = card

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 18)
        lay.setSpacing(14)

        hdr = QHBoxLayout()
        title = QLabel("Редактировать" if self.is_edit_mode else "Новая задача")
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet("color:#f0f0f0;border:none;background:transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        hint = QLabel("перетащить")
        hint.setStyleSheet("color:#444;font-size:9px;border:none;background:transparent;")
        hdr.addWidget(hint)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton{background:#252525;color:#888;border:none;border-radius:8px;}
            QPushButton:hover{background:#c0392b;color:white;}
        """)
        close_btn.clicked.connect(self.reject)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        lay.addWidget(self._field_label("Название"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Что нужно сделать?")
        self.text_input.setText(self.task_data.get("text", ""))
        self.text_input.setStyleSheet(self._input_style())
        self.text_input.setFont(QFont("Segoe UI", 10))
        lay.addWidget(self.text_input)

        lay.addWidget(self._field_label("Описание"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Дополнительные детали…")
        self.description_input.setPlainText(self.task_data.get("description", ""))
        self.description_input.setStyleSheet(self._input_style())
        self.description_input.setFont(QFont("Segoe UI", 10))
        self.description_input.setFixedHeight(72)
        lay.addWidget(self.description_input)

        lay.addWidget(self._field_label("Приоритет"))
        pri_row = QHBoxLayout()
        pri_row.setSpacing(6)
        for key, label, color in self._PRIORITY:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setProperty("pri_color", color)
            btn.clicked.connect(lambda _=False, k=key: self._set_priority(k))
            self._priority_btns[key] = btn
            pri_row.addWidget(btn)
        lay.addLayout(pri_row)
        self._set_priority(self._priority_key)

        lay.addWidget(self._field_label("Дедлайн"))
        deadline_wrap = QFrame()
        deadline_wrap.setStyleSheet(
            "QFrame{background:#1e1e1e;border-radius:10px;border:1px solid #2a2a2a;}"
        )
        dl_lay = QVBoxLayout(deadline_wrap)
        dl_lay.setContentsMargins(10, 8, 10, 8)
        dl_lay.setSpacing(8)

        self.deadline_toggle = QPushButton("Добавить дедлайн")
        self.deadline_toggle.setCheckable(True)
        self.deadline_toggle.setChecked(bool(self.task_data.get("deadline")))
        self.deadline_toggle.setCursor(Qt.PointingHandCursor)
        self.deadline_toggle.setFixedHeight(28)
        self.deadline_toggle.toggled.connect(self._toggle_deadline)
        dl_lay.addWidget(self.deadline_toggle)

        init_dt = QDateTime.currentDateTime().addDays(1)
        if self.task_data.get("deadline"):
            init_dt = QDateTime(datetime.fromisoformat(self.task_data["deadline"]))
        self._date_picker = CompactDateTimePicker(init_dt)
        self._date_picker.setVisible(self.deadline_toggle.isChecked())
        dl_lay.addWidget(self._date_picker)
        lay.addWidget(deadline_wrap)
        self._sync_deadline_toggle_text()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(self._ghost_btn())
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить" if self.is_edit_mode else "Создать")
        save_btn.setFixedHeight(36)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(self._primary_btn())
        save_btn.clicked.connect(self._save_task)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        root.addWidget(card)

    def _apply_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(32)
        sh.setOffset(0, 6)
        sh.setColor(QColor(0, 0, 0, 160))
        self._card.setGraphicsEffect(sh)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#666;border:none;background:transparent;")
        return lbl

    def _set_priority(self, key: str) -> None:
        self._priority_key = key
        for k, btn in self._priority_btns.items():
            on = k == key
            btn.setChecked(on)
            color = btn.property("pri_color")
            if on:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background:rgba(0,120,215,0.2); color:{color};
                        border:1px solid #0078d7; border-radius:8px;
                        font-size:10px; font-weight:600;
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background:#252525; color:#888;
                        border:1px solid #333; border-radius:8px;
                        font-size:10px;
                    }
                    QPushButton:hover { background:#2e2e2e; color:#ccc; }
                """)

    def _toggle_deadline(self, on: bool) -> None:
        self._date_picker.setVisible(on)
        self._sync_deadline_toggle_text()
        self.adjustSize()

    def _sync_deadline_toggle_text(self) -> None:
        if self.deadline_toggle.isChecked():
            self.deadline_toggle.setText("📅  Дедлайн")
            self.deadline_toggle.setStyleSheet("""
                QPushButton {
                    background:rgba(0,120,215,0.15); color:#9ecbff;
                    border:1px solid #0078d7; border-radius:8px;
                    text-align:left; padding-left:10px; font-size:10px;
                }
            """)
        else:
            self.deadline_toggle.setText("Добавить дедлайн")
            self.deadline_toggle.setStyleSheet("""
                QPushButton {
                    background:transparent; color:#777;
                    border:none; text-align:left; padding-left:4px; font-size:10px;
                }
                QPushButton:hover { color:#aaa; }
            """)

    def _save_task(self):
        text = self.text_input.text().strip()
        if not text:
            self.text_input.setStyleSheet(self._input_style(error=True))
            return

        deadline = None
        if self.deadline_toggle.isChecked():
            deadline = self._date_picker.date_time().toPython().isoformat()

        task_data = {
            "text": text,
            "description": self.description_input.toPlainText().strip(),
            "priority": self._priority_key,
            "deadline": deadline,
        }
        if self.is_edit_mode:
            task_data["id"] = self.task_data["id"]

        self.task_saved.emit(task_data)
        self.accept()

    def _input_style(self, error: bool = False) -> str:
        border = "#c0392b" if error else "#333"
        focus = "#c0392b" if error else "#0078d7"
        return f"""
            QLineEdit, QTextEdit {{
                background:#1e1e1e; border:1px solid {border};
                border-radius:10px; padding:10px 12px; color:#f0f0f0;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border:1px solid {focus};
            }}
        """

    def _ghost_btn(self) -> str:
        return """
            QPushButton {
                background:#252525; color:#ccc; border:1px solid #333;
                border-radius:10px; font-size:11px; font-weight:600;
            }
            QPushButton:hover { background:#333; color:white; }
        """

    def _primary_btn(self) -> str:
        return """
            QPushButton {
                background:#0078d7; color:white; border:none;
                border-radius:10px; font-size:11px; font-weight:600;
            }
            QPushButton:hover { background:#1a8fe3; }
            QPushButton:pressed { background:#006cbf; }
        """
