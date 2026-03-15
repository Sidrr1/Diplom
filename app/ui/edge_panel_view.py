import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
    QLabel, QFrame, QApplication)
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, Signal, QSize
from PySide6.QtGui import QColor, QPainter, QIcon, QFont, QPainterPath

class ToolButton(QWidget):
    clicked = Signal()

    def __init__(self, icon_path: str, label: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(62, 70)
        self.setCursor(Qt.PointingHandCursor)
        self._build_ui(icon_path, label)

    def _build_ui(self, icon_path: str, label: str):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 4); lay.setSpacing(3)
        lay.setAlignment(Qt.AlignHCenter)
        lay.addWidget(self._make_icon_btn(icon_path), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_label(label),        0, Qt.AlignHCenter)

    def _make_icon_btn(self, icon_path: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(44, 44); btn.setIconSize(QSize(26, 26))
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.clicked)
        btn.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,8); border-radius:13px;
                          border:1px solid rgba(255,255,255,12); }
            QPushButton:hover { background:rgba(0,120,215,60); border:1px solid #0078d7; }
            QPushButton:pressed { background:rgba(0,120,215,90); }
        """)
        return btn

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color:rgba(200,200,200,160); border:none; background:transparent;")
        return lbl


class EdgePanelView(QWidget):
    on_player_click = Signal()
    on_sorter_click = Signal()

    HANDLE_W = 6
    PANEL_W  = 90
    H_RATIO  = 0.42

    def __init__(self):
        super().__init__()
        self._expanded   = False
        self._anim       = None
        self._settings_d = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()
        self._init_geometry()

    # ── Построение UI ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self._card = self._make_card()
        root.addWidget(self._card)

    def _make_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card { background:rgba(18,18,18,235); border-radius:18px;
                          border:1px solid rgba(255,255,255,10); }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(13, 18, 13, 14); lay.setSpacing(6)
        lay.setAlignment(Qt.AlignHCenter)

        lay.addWidget(self._make_header())
        lay.addSpacing(8)
        lay.addWidget(self._make_tool_btn("player.jpeg",       "Плеер",        self.on_player_click))
        lay.addWidget(self._make_tool_btn("auto_sorter.jpeg",  "Сортировщик",  self.on_sorter_click))
        lay.addStretch()
        lay.addWidget(self._make_separator())
        lay.addSpacing(4)
        lay.addWidget(self._make_settings_btn(), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_quit_btn(),     0, Qt.AlignHCenter)
        return card

    def _make_header(self) -> QLabel:
        hdr = QLabel("TOOLS"); hdr.setAlignment(Qt.AlignCenter)
        hdr.setFont(QFont("Segoe UI Semibold", 8))
        hdr.setStyleSheet(
            "color:rgba(255,255,255,35); letter-spacing:2px;"
            " border:none; background:transparent;"
        )
        return hdr

    def _make_tool_btn(self, icon_file: str, label: str, signal: Signal) -> ToolButton:
        assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets")
        btn = ToolButton(os.path.join(assets, icon_file), label)
        btn.clicked.connect(signal)
        return btn

    def _make_separator(self) -> QFrame:
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(255,255,255,15);")
        return sep

    def _make_settings_btn(self) -> QPushButton:
        btn = QPushButton("⚙")
        btn.setFixedSize(44, 34); btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 14))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:rgba(200,200,200,150);
                          border:none; border-radius:8px; }
            QPushButton:hover { background:rgba(255,255,255,10); color:white; }
        """)
        btn.clicked.connect(self._open_settings)
        return btn

    def _make_quit_btn(self) -> QPushButton:
        btn = QPushButton("✕")
        btn.setFixedSize(44, 30); btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 13))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:rgba(255,85,85,140);
                          border:none; border-radius:8px; }
            QPushButton:hover { background:rgba(192,57,43,40); color:#ff5555; }
        """)
        btn.clicked.connect(QApplication.instance().quit)
        return btn

    # ── Геометрия ────────────────────────────────────────────────────────

    def _init_geometry(self):
        s = QApplication.primaryScreen().geometry()
        h = int(s.height() * self.H_RATIO)
        y = (s.height() - h) // 2
        self._geo_closed = QRect(s.width() - self.HANDLE_W, y, self.PANEL_W, h)
        self._geo_open   = QRect(s.width() - self.PANEL_W,  y, self.PANEL_W, h)
        self.setGeometry(self._geo_closed)

    # ── Анимация ─────────────────────────────────────────────────────────

    def _toggle(self):
        if self._anim and self._anim.state() == QPropertyAnimation.Running:
            return
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.OutExpo)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(self._geo_closed if self._expanded else self._geo_open)
        self._expanded = not self._expanded
        self._anim.start()

    # ── Настройки ────────────────────────────────────────────────────────

    def _open_settings(self):
        from app.ui.settings_dialog import SettingsDialog
        if self._settings_d and self._settings_d.isVisible():
            return
        self._settings_d = SettingsDialog()
        g = self.geometry()
        self._settings_d.move(g.left() - self._settings_d.width() - 12, g.top())
        self._settings_d.exec()

    # ── Отрисовка ────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        if not self._expanded:
            self._draw_handle(p)

    def _draw_handle(self, p: QPainter):
        """Рисует маленькую полоску-индикатор когда панель свёрнута."""
        bw, bh = 4, 40
        bx = self.width() - bw
        by = (self.height() - bh) // 2
        path = QPainterPath()
        path.addRoundedRect(bx, by, bw, bh, 2, 2)
        p.fillPath(path, QColor(255, 255, 255, 70))

    # ── Мышь ─────────────────────────────────────────────────────────────

    def enterEvent(self, e):
        if not self._expanded:
            self._toggle()

    def leaveEvent(self, e):
        if self._expanded:
            if self._settings_d and self._settings_d.isVisible():
                return
            self._toggle()