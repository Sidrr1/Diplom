"""Вспомогательные плавающие кнопки плеера."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ClickThroughToggle(QWidget):
    def __init__(self, player):
        super().__init__()
        self._player = player
        self._active = False
        self._drag_pos = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(32, 72)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self._make_toggle_btn(), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_dot(), 0, Qt.AlignHCenter)

    def _make_toggle_btn(self) -> QPushButton:
        self._btn = QPushButton("🖱")
        self._btn.setFixedSize(28, 28)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setCheckable(True)
        self._btn.setToolTip("Click-through режим")
        self._btn.clicked.connect(self._toggle)
        self._btn.setStyleSheet("""
            QPushButton { background:rgba(30,30,30,200); color:#aaa;
                          border:1px solid rgba(255,255,255,20); border-radius:8px; font-size:14px; }
            QPushButton:hover   { background:rgba(50,50,50,220); color:white; }
            QPushButton:checked { background:rgba(0,120,215,200); color:white; border-color:#0078d7; }
        """)
        return self._btn

    def _make_dot(self) -> QLabel:
        self._dot = QLabel("●")
        self._dot.setAlignment(Qt.AlignCenter)
        self._dot.setFont(QFont("Segoe UI", 7))
        self._dot.setStyleSheet("color:#555; background:transparent; border:none;")
        return self._dot

    def _toggle(self):
        self._active = self._btn.isChecked()
        try:
            from app.core.window_manager import set_click_through
            set_click_through(int(self._player.winId()), self._active)
        except Exception as e:
            print(f"[click-through] {e}")
        color = "#0078d7" if self._active else "#555"
        self._dot.setStyleSheet(f"color:{color}; background:transparent; border:none;")

    def reposition(self, player_geo):
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        py = player_geo.top() + (player_geo.height() - h) // 2
        for x, y in [
            (player_geo.left() - w - 4, py),
            (player_geo.right() + 4, py),
            (player_geo.left() + (player_geo.width() - w) // 2, player_geo.bottom() + 4),
            (player_geo.left() + (player_geo.width() - w) // 2, player_geo.top() - h - 4),
        ]:
            if screen.left() <= x and x + w <= screen.right() and screen.top() <= y and y + h <= screen.bottom():
                self.move(x, y)
                return
        self.move(screen.left() + 4, py)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


class SettingsToggle(QWidget):
    """Плавающая кнопка настроек рядом с окном плеера."""

    def __init__(self, parent_window, tab: str = "general"):
        super().__init__()
        self._parent_win = parent_window
        self._tab = tab
        self._drag_pos = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(32, 32)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("⚙")
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Настройки")
        btn.clicked.connect(self._open)
        btn.setStyleSheet("""
            QPushButton { background:rgba(30,30,30,200); color:#aaa;
                          border:1px solid rgba(255,255,255,20); border-radius:8px;
                          font-size:14px; }
            QPushButton:hover   { background:rgba(50,50,50,220); color:white; }
            QPushButton:pressed { background:rgba(0,120,215,200); color:white; }
        """)
        lay.addWidget(btn, 0, Qt.AlignCenter)

    def _open(self):
        from app.features.settings.ui.settings_dialog import SettingsDialog
        pw = self._parent_win
        d = SettingsDialog(parent=pw, initial_tab=self._tab)
        if hasattr(pw, "_apply_settings"):
            d.settings_changed.connect(pw._apply_settings)
        if hasattr(pw, "_open_auth_browser"):
            d.open_auth_browser.connect(pw._open_auth_browser)
        d.show_near(pw.geometry())

    def reposition(self, parent_geo):
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        ct_h = 72
        gap = 6
        cy = parent_geo.top() + (parent_geo.height() - ct_h) // 2 + ct_h + gap
        candidates = [
            (parent_geo.left() - w - 4, cy),
            (parent_geo.right() + 4, cy),
            (parent_geo.left() + (parent_geo.width() - w) // 2, parent_geo.bottom() + ct_h + gap + 4),
            (parent_geo.left() + (parent_geo.width() - w) // 2, parent_geo.top() - h - 4),
        ]
        for x, y in candidates:
            if (screen.left() <= x and x + w <= screen.right() and
                    screen.top() <= y and y + h <= screen.bottom()):
                self.move(x, y)
                return
        self.move(screen.left() + 4, parent_geo.top() + 80)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
