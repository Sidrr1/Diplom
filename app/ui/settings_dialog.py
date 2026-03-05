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

    def __init__(self, parent=None, initial_tab: str = "general"):
        super().__init__(parent)
        self.cfg = config.load()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._drag_pos = None
        self._build_ui(initial_tab)
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40); sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self._card.setGraphicsEffect(sh)

    # ── Основной UI ───────────────────────────────────────────────────────
    def _build_ui(self, initial_tab: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        self._card = QFrame(); self._card.setObjectName("card")
        self._card.setStyleSheet("""
            QFrame#card { background:#141414; border-radius:18px;
                          border:1px solid #2a2a2a; }
        """)
        lay = QVBoxLayout(self._card)
        lay.setContentsMargins(0, 0, 0, 20); lay.setSpacing(0)

        # ── Заголовок ──
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("background:#0f0f0f; border-radius:18px 18px 0 0;")
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(20, 16, 16, 12)
        title = QLabel("Настройки")
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet("color:#f0f0f0;")
        btn_x = QPushButton("✕"); btn_x.setFixedSize(28, 28)
        btn_x.setCursor(Qt.PointingHandCursor)
        btn_x.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#888; border:none;
                          border-radius:8px; font-size:13px; }
            QPushButton:hover { background:#c0392b; color:white; }
        """)
        btn_x.clicked.connect(self.reject)
        hdr_lay.addWidget(title); hdr_lay.addStretch(); hdr_lay.addWidget(btn_x)
        lay.addWidget(hdr_frame)

        # ── Вкладки ──
        tabs_row = QHBoxLayout()
        tabs_row.setContentsMargins(16, 12, 16, 0); tabs_row.setSpacing(6)
        self._tab_btns = {}
        self._stack = QStackedWidget()

        for label, key in self.TABS:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton { background:transparent; color:#666; border:none;
                              border-radius:8px; padding:0 12px; }
                QPushButton:hover { color:#aaa; background:rgba(255,255,255,5); }
                QPushButton:checked { background:#0078d7; color:white; }
            """)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            tabs_row.addWidget(btn)
            self._tab_btns[key] = btn

        tabs_row.addStretch()
        lay.addLayout(tabs_row)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:#222; margin:8px 0 0 0;")
        lay.addWidget(sep)

        # ── Страницы ──
        self._stack.addWidget(self._page_general())   # 0
        self._stack.addWidget(self._page_player())    # 1
        self._stack.addWidget(self._page_sorter())    # 2

        p_lay = QVBoxLayout()
        p_lay.setContentsMargins(16, 12, 16, 0)
        p_lay.addWidget(self._stack)
        lay.addLayout(p_lay)
        lay.addSpacing(16)

        # ── Кнопка сохранить ──
        btn_save = QPushButton("Сохранить")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(42)
        btn_save.setStyleSheet("""
            QPushButton { background:#0078d7; color:white; border:none;
                          border-radius:10px; font-size:13px; font-weight:600;
                          margin: 0 16px; }
            QPushButton:hover  { background:#1a8fe3; }
            QPushButton:pressed{ background:#006cbf; }
        """)
        btn_save.clicked.connect(self._save)
        lay.addWidget(btn_save)

        root.addWidget(self._card)
        self._switch_tab(initial_tab)

    # ── Страница: Общие ───────────────────────────────────────────────────
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

    # ── Страница: Плеер ───────────────────────────────────────────────────
    def _page_player(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(self._section("ВОСПРОИЗВЕДЕНИЕ"))

        # Качество
        qrow = QFrame()
        qrow.setStyleSheet(
            "QFrame{background:#1e1e1e;border-radius:12px;border:1px solid #2a2a2a;}"
        )
        qrl = QHBoxLayout(qrow); qrl.setContentsMargins(14, 12, 14, 12)
        ql = QVBoxLayout(); ql.setSpacing(2)
        qt = QLabel("Качество по умолчанию")
        qt.setFont(QFont("Segoe UI", 11))
        qt.setStyleSheet("color:#e0e0e0; border:none; background:transparent;")
        qs = QLabel("Применяется при загрузке нового видео")
        qs.setFont(QFont("Segoe UI", 9))
        qs.setStyleSheet("color:#555; border:none; background:transparent;")
        ql.addWidget(qt); ql.addWidget(qs)

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
        qrl.addLayout(ql, stretch=1); qrl.addWidget(self._combo_quality)
        lay.addWidget(qrow)

        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))

        # Прозрачность плеера
        lay.addWidget(self._opacity_row(
            "player_opacity", "_lbl_player_opacity", "_slider_player_opacity"
        ))
        lay.addStretch()
        return page

    # ── Страница: Сортировщик ─────────────────────────────────────────────
    def _page_sorter(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(self._section("ПАПКА-ИСТОЧНИК"))

        src_frame = QFrame()
        src_frame.setStyleSheet(
            "QFrame{background:#1e1e1e;border-radius:12px;border:1px solid #2a2a2a;}"
        )
        src_lay = QHBoxLayout(src_frame)
        src_lay.setContentsMargins(14, 10, 14, 10); src_lay.setSpacing(8)

        self._sorter_src_edit = QLineEdit()
        self._sorter_src_edit.setText(self.cfg.get("sorter_source", ""))
        self._sorter_src_edit.setPlaceholderText("Например: C:/Users/User/Downloads")
        self._sorter_src_edit.setStyleSheet("""
            QLineEdit { background:transparent; color:white; border:none; font-size:11px; }
        """)

        btn_src = QPushButton("Обзор")
        btn_src.setFixedHeight(28); btn_src.setCursor(Qt.PointingHandCursor)
        btn_src.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#ccc; border:none;
                          border-radius:6px; padding:0 10px; font-size:11px; }
            QPushButton:hover { background:#333; color:white; }
        """)
        btn_src.clicked.connect(self._choose_sorter_src)
        src_lay.addWidget(self._sorter_src_edit, stretch=1)
        src_lay.addWidget(btn_src)
        lay.addWidget(src_frame)

        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))

        # Прозрачность сортировщика
        lay.addWidget(self._opacity_row(
            "sorter_opacity", "_lbl_sorter_opacity", "_slider_sorter_opacity"
        ))
        lay.addStretch()
        return page

    # ── Переключение вкладок ──────────────────────────────────────────────
    def _switch_tab(self, key: str):
        keys = [k for _, k in self.TABS]
        if key not in keys: key = keys[0]
        self._stack.setCurrentIndex(keys.index(key))
        for k, btn in self._tab_btns.items():
            btn.setChecked(k == key)

    # ── Вспомогательные виджеты ───────────────────────────────────────────
    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#555; letter-spacing:1.5px;")
        return lbl

    def _toggle_row(self, title: str, subtitle: str, checked: bool):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{background:#1e1e1e;border-radius:12px;border:1px solid #2a2a2a;}"
        )
        rl = QHBoxLayout(frame); rl.setContentsMargins(14, 12, 14, 12)
        col = QVBoxLayout(); col.setSpacing(2)
        t = QLabel(title); t.setFont(QFont("Segoe UI", 11))
        t.setStyleSheet("color:#e0e0e0; border:none; background:transparent;")
        s = QLabel(subtitle); s.setFont(QFont("Segoe UI", 9))
        s.setStyleSheet("color:#555; border:none; background:transparent;")
        col.addWidget(t); col.addWidget(s)
        cb = QCheckBox(); cb.setChecked(checked)
        cb.setStyleSheet("""
            QCheckBox::indicator { width:44px; height:24px; border-radius:12px;
                                   background:#333; border:none; }
            QCheckBox::indicator:checked { background:#0078d7; }
        """)
        rl.addLayout(col, stretch=1); rl.addWidget(cb)
        return frame, cb

    def _opacity_row(self, cfg_key: str, lbl_attr: str, slider_attr: str) -> QFrame:
        """Универсальная строка с ползунком прозрачности."""
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{background:#1e1e1e;border-radius:12px;border:1px solid #2a2a2a;}"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Прозрачность окна"); t.setFont(QFont("Segoe UI", 11))
        t.setStyleSheet("color:#e0e0e0; border:none; background:transparent;")

        val = self.cfg.get(cfg_key, 100)
        lbl = QLabel(f"{val}%"); lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet("color:#0078d7; border:none; background:transparent;")
        setattr(self, lbl_attr, lbl)

        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(lbl)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(20, 100); slider.setValue(val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal { height:4px; background:rgba(255,255,255,20);
                                         border-radius:2px; }
            QSlider::sub-page:horizontal { background:#0078d7; border-radius:2px; }
            QSlider::handle:horizontal { width:14px; height:14px; margin:-5px 0;
                                         background:#0078d7; border-radius:7px; }
        """)
        slider.valueChanged.connect(lambda v, l=lbl: l.setText(f"{v}%"))
        setattr(self, slider_attr, slider)

        lay.addLayout(hdr); lay.addWidget(slider)
        return frame

    # ── Выбор папки-источника ─────────────────────────────────────────────
    def _choose_sorter_src(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку-источник")
        if folder:
            self._sorter_src_edit.setText(folder)

    # ── Сохранение ────────────────────────────────────────────────────────
    def _save(self):
        self.cfg["autostart"]       = self._cb_autostart.isChecked()
        self.cfg["player_quality"]  = self._combo_quality.currentText()
        self.cfg["player_opacity"]  = self._slider_player_opacity.value()
        self.cfg["sorter_source"]   = self._sorter_src_edit.text().strip()
        self.cfg["sorter_opacity"]  = self._slider_sorter_opacity.value()

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