"""Вкладка заметок."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QSlider, QGridLayout, QTimeEdit, QAbstractSpinBox,
)
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QFont

from app.features.settings.ui import settings_styles as ss


class NotesMixin:
    def _notes_chip_btn(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(30)
        return btn

    def _style_notes_chip(self, btn: QPushButton, on: bool) -> None:
        btn.setStyleSheet(ss.NOTES_CHIP_ON if on else ss.NOTES_CHIP_OFF)

    def _page_notes(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(self._section("РЕЖИМ"))
        lay.addWidget(self._make_notes_mode_row())
        lay.addWidget(self._section("НАПОМИНАНИЯ"))
        lay.addWidget(self._make_notes_reminders_card())
        lay.addWidget(self._section("ОФОРМЛЕНИЕ"))
        lay.addWidget(self._make_notes_position_row())
        lay.addWidget(self._make_notes_size_row())
        lay.addWidget(self._opacity_row("notes_opacity", "_lbl_notes_opacity", "_slider_notes_opacity"))
        lay.addStretch()
        return page

    def _make_notes_reminders_card(self) -> QFrame:
        from app.features.todo.core.reminder_settings import (
            OFFSET_CHOICES,
            get_daily_time,
            get_mode,
            get_offsets,
            is_enabled,
        )
        from PySide6.QtWidgets import QTimeEdit

        frame = QFrame()
        frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(self._row_title("Напоминания"))
        hdr.addStretch()
        self._cb_reminder_enabled = QCheckBox()
        self._cb_reminder_enabled.setChecked(is_enabled())
        self._cb_reminder_enabled.setStyleSheet(ss.STYLE_TOGGLE)
        self._cb_reminder_enabled.toggled.connect(self._sync_reminder_ui)
        hdr.addWidget(self._cb_reminder_enabled)
        lay.addLayout(hdr)

        self._reminder_body = QWidget()
        self._reminder_body.setStyleSheet("background:transparent;")
        body = QVBoxLayout(self._reminder_body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self._reminder_mode_btns: dict[str, QPushButton] = {}
        current_mode = get_mode()
        self._reminder_mode = current_mode
        for key, label in (("daily", "Ежедневно"), ("before", "Дедлайн"), ("both", "Оба")):
            btn = self._notes_chip_btn(label)
            btn.clicked.connect(lambda _=False, k=key: self._set_reminder_mode(k))
            self._reminder_mode_btns[key] = btn
            mode_row.addWidget(btn, 1)
        body.addLayout(mode_row)
        self._set_reminder_mode(current_mode)

        self._reminder_daily_box = QFrame()
        self._reminder_daily_box.setStyleSheet(
            "QFrame{background:#141414;border-radius:8px;border:1px solid #2a2a2a;}"
        )
        daily_lay = QHBoxLayout(self._reminder_daily_box)
        daily_lay.setContentsMargins(10, 8, 10, 8)
        daily_lay.addWidget(self._row_subtitle("Время"))
        daily_lay.addStretch()
        self._time_reminder_daily = QTimeEdit()
        h, m = get_daily_time()
        self._time_reminder_daily.setTime(QTime(h, m))
        self._time_reminder_daily.setDisplayFormat("HH:mm")
        self._time_reminder_daily.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self._time_reminder_daily.setAlignment(Qt.AlignCenter)
        self._time_reminder_daily.setFixedSize(76, 28)
        self._time_reminder_daily.setStyleSheet("""
            QTimeEdit {
                background:#252525; border:1px solid #333; border-radius:6px;
                padding:2px 8px; color:#ccc; font-size:12px;
            }
            QTimeEdit:focus { border-color:#0078d7; color:#9ecbff; }
        """)
        daily_lay.addWidget(self._time_reminder_daily)
        body.addWidget(self._reminder_daily_box)

        self._reminder_before_box = QFrame()
        self._reminder_before_box.setStyleSheet(
            "QFrame{background:#141414;border-radius:8px;border:1px solid #2a2a2a;}"
        )
        before_lay = QVBoxLayout(self._reminder_before_box)
        before_lay.setContentsMargins(10, 8, 10, 8)
        before_lay.setSpacing(6)
        before_lay.addWidget(self._row_subtitle("Заранее"))
        off_row = QHBoxLayout()
        off_row.setSpacing(4)
        self._reminder_offset_btns: dict[str, QPushButton] = {}
        selected_offsets = set(get_offsets())
        for key, _, label in OFFSET_CHOICES:
            btn = self._notes_chip_btn(label)
            btn.setChecked(key in selected_offsets)
            btn.toggled.connect(lambda _on, k=key: self._style_reminder_offset_chip(k))
            self._reminder_offset_btns[key] = btn
            off_row.addWidget(btn, 1)
            self._style_reminder_offset_chip(key)
        before_lay.addLayout(off_row)
        body.addWidget(self._reminder_before_box)

        lay.addWidget(self._reminder_body)
        self._sync_reminder_ui(self._cb_reminder_enabled.isChecked())
        return frame

    def _set_reminder_mode(self, mode: str) -> None:
        self._reminder_mode = mode
        for key, btn in self._reminder_mode_btns.items():
            self._style_notes_chip(btn, key == mode)
            btn.setChecked(key == mode)
        self._sync_reminder_ui(self._cb_reminder_enabled.isChecked())
        self._mark_tab_dirty("notes")

    def _style_reminder_offset_chip(self, key: str) -> None:
        btn = self._reminder_offset_btns.get(key)
        if btn:
            self._style_notes_chip(btn, btn.isChecked())
        self._mark_tab_dirty("notes")

    def _collect_reminder_offsets(self) -> list[str]:
        if not getattr(self, "_reminder_offset_btns", None):
            return ["1h", "1d"]
        return [k for k, btn in self._reminder_offset_btns.items() if btn.isChecked()]

    def _sync_reminder_ui(self, enabled: bool) -> None:
        mode = getattr(self, "_reminder_mode", "both")
        if hasattr(self, "_reminder_body"):
            self._reminder_body.setVisible(enabled)
        if hasattr(self, "_reminder_daily_box"):
            self._reminder_daily_box.setVisible(mode in ("daily", "both"))
        if hasattr(self, "_reminder_before_box"):
            self._reminder_before_box.setVisible(mode in ("before", "both"))

    def _make_notes_mode_row(self) -> QFrame:
        from app.core.database import db

        frame = QFrame()
        frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(self._row_title("Режим"))
        col.addWidget(self._row_subtitle("Заметки или задачи"))
        lay.addLayout(col, 1)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        current_mode = db.get_setting("notes_mode", "notes", "normal")

        self._mode_normal_radio = self._notes_chip_btn("Заметки")
        self._mode_work_radio = self._notes_chip_btn("Задачи")
        self._mode_normal_radio.clicked.connect(
            lambda: self._select_notes_mode("normal", notify=True)
        )
        self._mode_work_radio.clicked.connect(
            lambda: self._select_notes_mode("work", notify=True)
        )
        chips.addWidget(self._mode_normal_radio)
        chips.addWidget(self._mode_work_radio)
        lay.addLayout(chips)

        self._select_notes_mode(current_mode, notify=False)
        return frame

    def _select_notes_mode(self, mode: str, *, notify: bool = False) -> None:
        is_normal = mode == "normal"
        self._style_notes_chip(self._mode_normal_radio, is_normal)
        self._style_notes_chip(self._mode_work_radio, not is_normal)
        self._mode_normal_radio.setChecked(is_normal)
        self._mode_work_radio.setChecked(not is_normal)
        if notify:
            self._on_mode_changed(mode)

    def _make_notes_position_row(self) -> QFrame:
        """Выбор положения Edge-панели для заметок."""
        frame = QFrame(); frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)

        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title("Положение Edge-панели"))
        col.addWidget(self._row_subtitle("Где показывать кнопку заметок"))
        lay.addLayout(col)

        # Визуальный экранчик с 4 квадратиками
        from app.core.database import db
        current_pos = db.get_setting('edge_position', 'notes', 'right')

        screen_widget = QWidget()
        screen_widget.setFixedSize(120, 90)
        screen_layout = QGridLayout(screen_widget)
        screen_layout.setContentsMargins(0, 0, 0, 0)
        screen_layout.setSpacing(0)

        # Центральный экран (серый прямоугольник)
        center = QLabel()
        center.setFixedSize(60, 50)
        center.setStyleSheet("background:#2a2a2a; border-radius:4px;")
        screen_layout.addWidget(center, 1, 1, Qt.AlignCenter)

        # 4 кнопки по углам (соответствие UI ↔ позиция стикеров)
        self._notes_position_btns = {}
        positions = [
            ('left', 0, 0),    # левый верхний угол UI → стикеры СЛЕВА
            ('right', 0, 2),   # правый верхний угол UI → стикеры СПРАВА
            ('bottom', 2, 0),  # левый нижний угол UI → стикеры СНИЗУ
            ('top', 2, 2)      # правый нижний угол UI → стикеры СВЕРХУ
        ]

        for pos, row, col in positions:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setChecked(pos == current_pos)
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, p=pos: self._select_notes_position(p))
            btn.setStyleSheet("""
                QPushButton {
                    background:#444;
                    border:2px solid #555;
                    border-radius:4px;
                }
                QPushButton:hover {
                    background:#555;
                    border:2px solid #0078d7;
                }
                QPushButton:checked {
                    background:#0078d7;
                    border:2px solid #1a8fe3;
                }
            """)
            self._notes_position_btns[pos] = btn
            screen_layout.addWidget(btn, row, col, Qt.AlignCenter)

        lay.addWidget(screen_widget, 0, Qt.AlignCenter)

        return frame

    def _make_notes_size_row(self) -> QFrame:
        """Размер стикеров."""
        frame = QFrame(); frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)

        from app.core.database import db
        width = int(db.get_setting('note_width', 'notes', '250'))
        height = int(db.get_setting('note_height', 'notes', '200'))

        # Ширина
        width_row = QHBoxLayout()
        width_row.addWidget(self._row_subtitle("Ширина:"))
        self._notes_width_slider = QSlider(Qt.Horizontal)
        self._notes_width_slider.setRange(200, 400)
        self._notes_width_slider.setValue(width)
        self._notes_width_lbl = QLabel(f"{width}px")
        self._notes_width_lbl.setStyleSheet(ss.STYLE_LABEL_BLUE)
        self._notes_width_slider.valueChanged.connect(lambda v: self._notes_width_lbl.setText(f"{v}px"))
        width_row.addWidget(self._notes_width_slider, 1)
        width_row.addWidget(self._notes_width_lbl)
        lay.addLayout(width_row)

        # Высота
        height_row = QHBoxLayout()
        height_row.addWidget(self._row_subtitle("Высота:"))
        self._notes_height_slider = QSlider(Qt.Horizontal)
        self._notes_height_slider.setRange(150, 400)
        self._notes_height_slider.setValue(height)
        self._notes_height_lbl = QLabel(f"{height}px")
        self._notes_height_lbl.setStyleSheet(ss.STYLE_LABEL_BLUE)
        self._notes_height_slider.valueChanged.connect(lambda v: self._notes_height_lbl.setText(f"{v}px"))
        height_row.addWidget(self._notes_height_slider, 1)
        height_row.addWidget(self._notes_height_lbl)
        lay.addLayout(height_row)

        return frame

    def _on_mode_changed(self, mode: str):
        self._mark_tab_dirty("notes")

    def _select_notes_position(self, position: str):
        for pos, btn in self._notes_position_btns.items():
            btn.setChecked(pos == position)
        self._mark_tab_dirty("notes")

    