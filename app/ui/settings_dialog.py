from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QGraphicsDropShadowEffect, QSlider,
    QComboBox, QStackedWidget, QWidget, QLineEdit, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from app.core import config
from app.core.autostart import set_autostart, is_enabled


class SettingsDialog(QDialog):
    settings_changed = Signal(dict)

    TABS = [("⚙  Общие", "general"), ("▶  Плеер", "player"), ("📁  Сортировщик", "sorter")]

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