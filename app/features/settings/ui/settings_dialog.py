from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QGraphicsDropShadowEffect, QSlider,
    QComboBox, QStackedWidget, QWidget, QLineEdit, QFileDialog, QGridLayout,
    QRadioButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from app.core import config
from app.core.autostart import set_autostart, is_enabled


class SettingsDialog(QDialog):
    settings_changed = Signal(dict)

    TABS = [("⚙", "general"), ("▶", "player"), ("📁", "sorter"), ("📝", "notes"), ("🖼", "enhancer")]

    _STYLE_CARD        = "QFrame#card{background:#141414;border-radius:18px;border:1px solid #2a2a2a;}"
    _STYLE_ROW_FRAME   = "QFrame{background:#1e1e1e;border-radius:12px;border:1px solid #2a2a2a;}"
    _STYLE_LABEL_TITLE = "color:#e0e0e0; border:none; background:transparent;"
    _STYLE_LABEL_SUB   = "color:#555; border:none; background:transparent;"
    _STYLE_LABEL_BLUE  = "color:#0078d7; border:none; background:transparent;"

    def __init__(self, parent=None, initial_tab: str = "general"):
        super().__init__(parent)
        self.cfg = config.load()
        # Без WindowStaysOnTopHint — не блокирует взаимодействие с другими окнами
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._drag_pos = None
        self._build_ui(initial_tab)
        self._apply_shadow()

    # ── Построение UI ─────────────────────────────────────────────────────

    def _build_ui(self, initial_tab: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        self._card = self._make_card(initial_tab)
        root.addWidget(self._card)

    def _make_card(self, initial_tab: str) -> QFrame:
        card = QFrame(); card.setObjectName("card")
        card.setStyleSheet(self._STYLE_CARD)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 20); lay.setSpacing(0)
        lay.addWidget(self._make_header())
        lay.addLayout(self._make_tabs_row())
        lay.addWidget(self._make_separator())
        lay.addLayout(self._make_stack_layout())
        lay.addSpacing(16)
        lay.addWidget(self._make_save_btn())
        self._switch_tab(initial_tab)
        return card

    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background:#0f0f0f; border-radius:18px 18px 0 0;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(20, 16, 16, 12)
        title = QLabel("Настройки")
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet("color:#f0f0f0;")
        lay.addWidget(title); lay.addStretch()
        lay.addWidget(self._make_close_btn())
        return frame

    def _make_close_btn(self) -> QPushButton:
        btn = QPushButton("✕"); btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#888; border:none;
                          border-radius:8px; font-size:13px; }
            QPushButton:hover { background:#c0392b; color:white; }
        """)
        btn.clicked.connect(self.reject)
        return btn

    def _make_tabs_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(16, 12, 16, 0); row.setSpacing(6)
        self._tab_btns = {}
        for label, key in self.TABS:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton { background:transparent; color:#666; border:none;
                              border-radius:8px; padding:0 12px; }
                QPushButton:hover   { color:#aaa; background:rgba(255,255,255,5); }
                QPushButton:checked { background:#0078d7; color:white; }
            """)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            row.addWidget(btn)
            self._tab_btns[key] = btn
        row.addStretch()
        return row

    def _make_separator(self) -> QFrame:
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:#222; margin:8px 0 0 0;")
        return sep

    def _make_stack_layout(self) -> QVBoxLayout:
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_general())
        self._stack.addWidget(self._page_player())
        self._stack.addWidget(self._page_sorter())
        self._stack.addWidget(self._page_notes())
        self._stack.addWidget(self._page_enhancer())
        lay = QVBoxLayout()
        lay.setContentsMargins(16, 12, 16, 0)
        lay.addWidget(self._stack)
        return lay

    def _make_save_btn(self) -> QPushButton:
        btn = QPushButton("Сохранить")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton { background:#0078d7; color:white; border:none;
                          border-radius:10px; font-size:13px; font-weight:600;
                          margin:0 16px; }
            QPushButton:hover   { background:#1a8fe3; }
            QPushButton:pressed { background:#006cbf; }
        """)
        btn.clicked.connect(self._save)
        return btn

    def _apply_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40); sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self._card.setGraphicsEffect(sh)

    # ── Страницы ──────────────────────────────────────────────────────────

    def _page_general(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        lay.addWidget(self._section("СИСТЕМА"))
        row, self._cb_autostart = self._toggle_row(
            "Запуск вместе с Windows",
            "Приложение стартует при входе в систему",
            is_enabled(),
        )
        lay.addWidget(row)
        lay.addStretch()
        return page

    def _page_player(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        lay.addWidget(self._section("ВОСПРОИЗВЕДЕНИЕ"))
        lay.addWidget(self._make_quality_row())
        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))
        lay.addWidget(self._opacity_row("player_opacity", "_lbl_player_opacity", "_slider_player_opacity"))
        lay.addStretch()
        return page

    def _page_sorter(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        lay.addWidget(self._section("ПАПКА-ИСТОЧНИК"))
        lay.addWidget(self._make_source_row())
        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))
        lay.addWidget(self._opacity_row("sorter_opacity", "_lbl_sorter_opacity", "_slider_sorter_opacity"))
        lay.addStretch()
        return page

    # ── Строки страниц ────────────────────────────────────────────────────

    def _make_quality_row(self) -> QFrame:
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QHBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12)
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title("Качество по умолчанию"))
        col.addWidget(self._row_subtitle("Применяется при загрузке нового видео"))
        self._combo_quality = QComboBox()
        self._combo_quality.addItems(["Авто", "1080p", "720p", "480p", "360p"])
        idx = self._combo_quality.findText(self.cfg.get("player_quality", "Авто"))
        if idx >= 0: self._combo_quality.setCurrentIndex(idx)
        self._combo_quality.setFixedWidth(80)
        self._combo_quality.setStyleSheet("""
            QComboBox { background:#2a2a2a; color:white; border:none;
                        border-radius:8px; padding:4px 8px; font-size:11px; }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#1a1a1a; color:white;
                selection-background-color:#0078d7; border:1px solid #333; }
        """)
        lay.addLayout(col, stretch=1); lay.addWidget(self._combo_quality)
        return frame

    def _make_source_row(self) -> QFrame:
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10); lay.setSpacing(8)
        self._sorter_src_edit = QLineEdit()
        self._sorter_src_edit.setText(self.cfg.get("sorter_source", ""))
        self._sorter_src_edit.setPlaceholderText("Например: C:/Users/User/Downloads")
        self._sorter_src_edit.setStyleSheet(
            "QLineEdit{background:transparent;color:white;border:none;font-size:11px;}"
        )
        btn = QPushButton("Обзор")
        btn.setFixedHeight(28); btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#ccc; border:none;
                          border-radius:6px; padding:0 10px; font-size:11px; }
            QPushButton:hover { background:#333; color:white; }
        """)
        btn.clicked.connect(self._choose_sorter_src)
        lay.addWidget(self._sorter_src_edit, stretch=1)
        lay.addWidget(btn)
        return frame

    def _opacity_row(self, cfg_key: str, lbl_attr: str, slider_attr: str) -> QFrame:
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(6)
        val = self.cfg.get(cfg_key, 100)
        hdr = QHBoxLayout()
        hdr.addWidget(self._row_title("Прозрачность окна"))
        hdr.addStretch()
        lbl = QLabel(f"{val}%"); lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(self._STYLE_LABEL_BLUE)
        setattr(self, lbl_attr, lbl)
        hdr.addWidget(lbl)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(20, 100); slider.setValue(val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal { height:4px; background:rgba(255,255,255,20);
                                         border-radius:2px; }
            QSlider::sub-page:horizontal { background:#0078d7; border-radius:2px; }
            QSlider::handle:horizontal   { width:14px; height:14px; margin:-5px 0;
                                           background:#0078d7; border-radius:7px; }
        """)
        slider.valueChanged.connect(lambda v, l=lbl: l.setText(f"{v}%"))
        setattr(self, slider_attr, slider)
        lay.addLayout(hdr); lay.addWidget(slider)
        return frame

    # ── Вспомогательные виджеты ───────────────────────────────────────────

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#555; letter-spacing:1.5px;")
        return lbl

    def _row_title(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(self._STYLE_LABEL_TITLE)
        return lbl

    def _row_subtitle(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(self._STYLE_LABEL_SUB)
        return lbl

    def _toggle_row(self, title: str, subtitle: str, checked: bool):
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QHBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12)
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title(title))
        col.addWidget(self._row_subtitle(subtitle))
        cb = QCheckBox(); cb.setChecked(checked)
        cb.setStyleSheet("""
            QCheckBox::indicator { width:44px; height:24px; border-radius:12px;
                                   background:#333; border:none; }
            QCheckBox::indicator:checked { background:#0078d7; }
        """)
        lay.addLayout(col, stretch=1); lay.addWidget(cb)
        return frame, cb

    # ── Позиционирование ──────────────────────────────────────────────────

    def smart_position(self, parent_geo):
        """Позиционирует диалог рядом с родительским окном в свободном месте."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        w, h = self.width(), self.height()
        cy = parent_geo.top() + (parent_geo.height() - h) // 2
        cx = parent_geo.left() + (parent_geo.width() - w) // 2

        candidates = [
            (parent_geo.left() - w - 12, cy),       # слева
            (parent_geo.right() + 12,    cy),        # справа
            (cx, parent_geo.top() - h - 12),         # сверху
            (cx, parent_geo.bottom() + 12),          # снизу
        ]
        for x, y in candidates:
            if (x >= screen.left() and x + w <= screen.right() and
                    y >= screen.top() and y + h <= screen.bottom()):
                self.move(x, y)
                return
        self.move(screen.center().x() - w // 2, screen.center().y() - h // 2)

    # ── Логика ────────────────────────────────────────────────────────────

    def _switch_tab(self, key: str):
        keys = [k for _, k in self.TABS]
        if key not in keys: key = keys[0]
        self._stack.setCurrentIndex(keys.index(key))
        for k, btn in self._tab_btns.items():
            btn.setChecked(k == key)

    def _choose_sorter_src(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку-источник")
        if folder: self._sorter_src_edit.setText(folder)

    def _save(self):
        self.cfg["autostart"]      = self._cb_autostart.isChecked()
        self.cfg["player_quality"] = self._combo_quality.currentText()
        self.cfg["player_opacity"] = self._slider_player_opacity.value()
        self.cfg["sorter_source"]  = self._sorter_src_edit.text().strip()
        self.cfg["sorter_opacity"] = self._slider_sorter_opacity.value()

        # Enhancer settings
        self.cfg["enhancer_autosave"] = self._cb_enhancer_autosave.isChecked()
        self.cfg["enhancer_format"] = self._combo_enhancer_format.currentText()
        self.cfg["enhancer_jpeg_quality"] = self._slider_enhancer_quality.value()

        # Notes settings
        from app.core.database import db
        selected_position = None
        for pos, btn in self._notes_position_btns.items():
            if btn.isChecked():
                selected_position = pos
                break
        if selected_position:
            db.set_setting('edge_position', selected_position, 'notes')
            self.cfg['notes_edge_position'] = selected_position  # Добавляем в cfg для emit

        note_width = self._notes_width_slider.value()
        note_height = self._notes_height_slider.value()
        notes_opacity = self._slider_notes_opacity.value()

        db.set_setting('note_width', str(note_width), 'notes')
        db.set_setting('note_height', str(note_height), 'notes')
        db.set_setting('notes_opacity', str(notes_opacity), 'notes')

        # Добавляем в cfg для emit
        self.cfg['notes_width'] = note_width
        self.cfg['notes_height'] = note_height
        self.cfg['notes_opacity'] = notes_opacity

        config.save(self.cfg)
        set_autostart(self.cfg["autostart"])
        self.settings_changed.emit(self.cfg)
        self.accept()

    # ── Перетаскивание ────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ── Страница Notes ────────────────────────────────────────────────────

    def _page_notes(self) -> QWidget:
        """Настройки Smart Notes."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(self._section("РЕЖИМ РАБОТЫ"))
        lay.addWidget(self._make_notes_mode_row())

        lay.addWidget(self._section("ПОЛОЖЕНИЕ"))
        lay.addWidget(self._make_notes_position_row())

        lay.addWidget(self._section("РАЗМЕР СТИКЕРОВ"))
        lay.addWidget(self._make_notes_size_row())

        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))
        lay.addWidget(self._opacity_row("notes_opacity", "_lbl_notes_opacity", "_slider_notes_opacity"))

        lay.addStretch()
        return page

    def _make_notes_mode_row(self) -> QFrame:
        """Переключение режима работы заметок."""
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)

        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title("Режим работы"))
        col.addWidget(self._row_subtitle("Обычные заметки или список задач"))
        lay.addLayout(col)

        # Читаем текущий режим из БД (пока заглушка — будет per-sticker)
        from app.core.database import db
        current_mode = db.get_setting('notes_mode', 'notes', 'normal')

        # Два радио-баттона
        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(12)

        self._mode_normal_radio = QRadioButton("📝 Обычный режим (заметки)")
        self._mode_normal_radio.setChecked(current_mode == 'normal')
        self._mode_normal_radio.setCursor(Qt.PointingHandCursor)
        self._mode_normal_radio.toggled.connect(lambda checked: self._on_mode_changed('normal') if checked else None)
        radio_layout.addWidget(self._mode_normal_radio)

        self._mode_work_radio = QRadioButton("✅ Рабочий режим (задачи)")
        self._mode_work_radio.setChecked(current_mode == 'work')
        self._mode_work_radio.setCursor(Qt.PointingHandCursor)
        self._mode_work_radio.toggled.connect(lambda checked: self._on_mode_changed('work') if checked else None)
        radio_layout.addWidget(self._mode_work_radio)

        radio_layout.addStretch()
        lay.addLayout(radio_layout)

        return frame

    def _make_notes_position_row(self) -> QFrame:
        """Выбор положения Edge-панели для заметок."""
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
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
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
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
        self._notes_width_lbl.setStyleSheet(self._STYLE_LABEL_BLUE)
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
        self._notes_height_lbl.setStyleSheet(self._STYLE_LABEL_BLUE)
        self._notes_height_slider.valueChanged.connect(lambda v: self._notes_height_lbl.setText(f"{v}px"))
        height_row.addWidget(self._notes_height_slider, 1)
        height_row.addWidget(self._notes_height_lbl)
        lay.addLayout(height_row)

        return frame

    def _on_mode_changed(self, mode: str):
        """Обработчик смены режима работы заметок."""
        from app.core.database import db
        db.set_setting('notes_mode', mode, 'notes')
        self.settings_changed.emit({'notes_mode': mode})
        print(f"[settings] Notes mode changed to: {mode}")

    def _select_notes_position(self, position: str):
        """Выбрать положение Edge-панели."""
        for pos, btn in self._notes_position_btns.items():
            btn.setChecked(pos == position)

    # ── Страница Enhancer ─────────────────────────────────────────────────

    def _page_enhancer(self) -> QWidget:
        """Настройки Image Enhancer."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(self._section("IMAGE ENHANCER"))

        # Автосохранение
        row, self._cb_enhancer_autosave = self._toggle_row(
            "Автосохранение результата",
            "Сохранять улучшенное изображение автоматически",
            self.cfg.get("enhancer_autosave", True),
        )
        lay.addWidget(row)

        # Формат сохранения
        format_frame = QFrame()
        format_frame.setStyleSheet(self._STYLE_ROW_FRAME)
        format_lay = QHBoxLayout(format_frame)
        format_lay.setContentsMargins(14, 12, 14, 12)

        format_col = QVBoxLayout()
        format_col.setSpacing(2)
        format_col.addWidget(self._row_title("Формат сохранения"))
        format_col.addWidget(self._row_subtitle("Формат выходного файла"))

        self._combo_enhancer_format = QComboBox()
        self._combo_enhancer_format.addItems(["PNG", "JPEG", "WEBP"])
        self._combo_enhancer_format.setCurrentText(self.cfg.get("enhancer_format", "PNG"))
        self._combo_enhancer_format.setFixedWidth(100)
        self._combo_enhancer_format.setStyleSheet("""
            QComboBox {
                background:#2a2a2a; color:white; border:none;
                border-radius:6px; padding:6px 10px; font-size:11px;
            }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView {
                background:#1e1e1e; color:white;
                selection-background-color:#0078d7; border:1px solid #333;
            }
        """)

        format_lay.addLayout(format_col, stretch=1)
        format_lay.addWidget(self._combo_enhancer_format)
        lay.addWidget(format_frame)

        # Качество JPEG
        quality_frame = QFrame()
        quality_frame.setStyleSheet(self._STYLE_ROW_FRAME)
        quality_lay = QVBoxLayout(quality_frame)
        quality_lay.setContentsMargins(14, 12, 14, 12)
        quality_lay.setSpacing(6)

        quality_val = self.cfg.get("enhancer_jpeg_quality", 95)
        quality_hdr = QHBoxLayout()
        quality_hdr.addWidget(self._row_title("Качество JPEG"))
        quality_hdr.addStretch()

        self._lbl_enhancer_quality = QLabel(f"{quality_val}%")
        self._lbl_enhancer_quality.setFont(QFont("Segoe UI", 11))
        self._lbl_enhancer_quality.setStyleSheet(self._STYLE_LABEL_BLUE)
        quality_hdr.addWidget(self._lbl_enhancer_quality)

        self._slider_enhancer_quality = QSlider(Qt.Horizontal)
        self._slider_enhancer_quality.setRange(70, 100)
        self._slider_enhancer_quality.setValue(quality_val)
        self._slider_enhancer_quality.setStyleSheet("""
            QSlider::groove:horizontal { height:4px; background:rgba(255,255,255,20);
                                         border-radius:2px; }
            QSlider::sub-page:horizontal { background:#0078d7; border-radius:2px; }
            QSlider::handle:horizontal   { width:14px; height:14px; margin:-5px 0;
                                           background:#0078d7; border-radius:7px; }
        """)
        self._slider_enhancer_quality.valueChanged.connect(
            lambda v: self._lbl_enhancer_quality.setText(f"{v}%")
        )

        quality_lay.addLayout(quality_hdr)
        quality_lay.addWidget(self._slider_enhancer_quality)
        lay.addWidget(quality_frame)

        lay.addStretch()
        return page