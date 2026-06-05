"""Привязка аккаунтов — отдельное окно из настроек (как история)."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.database import db
from app.core.paths import app_data_dir
from app.features.accounts.auth_services import (
    list_account_services,
    profile_id_for_service,
)


class AccountsBindingDialog(QDialog):
    _STYLE_CARD = (
        "QFrame#card { background:#141414; border-radius:18px; border:1px solid #2a2a2a; }"
    )
    _STYLE_ROW = (
        "QFrame { background:#1e1e1e; border-radius:12px; border:1px solid #2a2a2a; }"
    )
    _STYLE_HINT = "color:#555; border:none; background:transparent;"
    _BTN_LOGIN = (
        "QPushButton{background:#0078d7;color:white;border:none;border-radius:10px;"
        "font-size:12px;font-weight:600;min-height:34px;}"
        "QPushButton:hover{background:#1a8fe3;}"
    )
    _BTN_OUT = (
        "QPushButton{background:rgba(192,57,43,0.22);color:#e88;border:none;"
        "border-radius:10px;font-size:12px;min-height:34px;}"
        "QPushButton:hover{background:#c0392b;color:white;}"
    )

    def __init__(self, settings_parent, parent=None):
        super().__init__(parent)
        self._settings = settings_parent
        self._drag_pos = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)
        self.setMinimumHeight(420)
        self._body_host: QWidget | None = None
        self._scroll: QScrollArea | None = None
        self._build_shell()
        self._apply_shadow()

    def _build_shell(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(self._STYLE_CARD)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 16)
        lay.setSpacing(0)

        lay.addWidget(self._make_header())
        lay.addWidget(self._make_sep())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { background:transparent; border:none; }"
            "QScrollBar:vertical { background:#1a1a1a; width:8px; border:none; }"
            "QScrollBar::handle:vertical { background:#444; border-radius:4px; min-height:24px; }"
        )
        self._body_host = QWidget()
        self._body_host.setStyleSheet("background:transparent;")
        self._scroll.setWidget(self._body_host)
        lay.addWidget(self._scroll, stretch=1)

        root.addWidget(card)
        self._card = card
        self._rebuild_body()

    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background:#0f0f0f; border-radius:18px 18px 0 0;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 14, 14, 12)
        lay.setSpacing(8)

        back = QPushButton("←")
        back.setFixedSize(36, 32)
        back.setCursor(Qt.PointingHandCursor)
        back.setToolTip("Назад к настройкам")
        back.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#ccc;border:none;border-radius:8px;"
            "font-size:16px;font-weight:600;}"
            "QPushButton:hover{background:#0078d7;color:white;}"
        )
        back.clicked.connect(self.accept)
        lay.addWidget(back)

        title = QLabel("Привязка")
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet("color:#f0f0f0; border:none; background:transparent;")
        lay.addWidget(title)
        lay.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#888;border:none;border-radius:8px;}"
            "QPushButton:hover{background:#c0392b;color:white;}"
        )
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return frame

    def _make_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#222;")
        return sep

    def _rebuild_body(self):
        if not self._body_host:
            return
        lay = self._body_host.layout()
        if lay is None:
            lay = QVBoxLayout(self._body_host)
        else:
            while lay.count():
                item = lay.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

        lay.setContentsMargins(20, 14, 20, 12)
        lay.setSpacing(12)

        sec = QLabel("АККАУНТЫ")
        sec.setFont(QFont("Segoe UI", 9))
        sec.setStyleSheet("color:#555; letter-spacing:1.5px;")
        lay.addWidget(sec)

        hint = QLabel(
            "Вход в отдельном окне браузера. Сессия хранится в профиле WebView2 "
            "(не в базе данных). Сброс — «Отвязать»."
        )
        hint.setWordWrap(True)
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(self._STYLE_HINT)
        lay.addWidget(hint)

        path_lbl = QLabel(app_data_dir() + os.sep + "profiles")
        path_lbl.setWordWrap(True)
        path_lbl.setFont(QFont("Segoe UI", 8))
        path_lbl.setStyleSheet("color:#444; border:none; background:transparent;")
        lay.addWidget(path_lbl)

        for svc in list_account_services():
            lay.addWidget(self._make_service_row(svc))

        lay.addStretch()

    def _make_service_row(self, svc: dict) -> QFrame:
        sid = svc["service_id"]
        pid = profile_id_for_service(sid)
        acc = db.get_linked_account(pid)
        connected = acc and acc.get("status") == "connected"

        frame = QFrame()
        frame.setStyleSheet(self._STYLE_ROW)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QVBoxLayout(frame)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)
        t = QLabel(svc["title"])
        t.setFont(QFont("Segoe UI Semibold", 12))
        t.setStyleSheet("color:#e8e8e8; border:none; background:transparent;")
        top.addWidget(t)
        top.addStretch()
        st = QLabel("Подключён" if connected else "Не подключён")
        st.setFont(QFont("Segoe UI", 9))
        st.setStyleSheet(
            "color:#5a9fd4; border:none; background:transparent;"
            if connected
            else "color:#555; border:none; background:transparent;"
        )
        top.addWidget(st)
        outer.addLayout(top)

        if not connected:
            sub = QLabel(svc.get("subtitle", ""))
            sub.setWordWrap(True)
            sub.setFont(QFont("Segoe UI", 9))
            sub.setStyleSheet("color:#666; border:none; background:transparent;")
            outer.addWidget(sub)

        btns = QHBoxLayout()
        btns.setSpacing(10)

        login = QPushButton("Войти" if not connected else "Снова войти")
        login.setCursor(Qt.PointingHandCursor)
        login.setStyleSheet(self._BTN_LOGIN)
        login.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        login.clicked.connect(lambda _c=False, s=sid: self._launch_login(s))

        out = QPushButton("Отвязать")
        out.setCursor(Qt.PointingHandCursor)
        out.setStyleSheet(self._BTN_OUT)
        out.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        out.clicked.connect(lambda _c=False, s=sid: self._logout(s))

        btns.addWidget(login, 1)
        btns.addWidget(out, 1)
        outer.addLayout(btns)

        return frame

    def _resolve_player_view(self):
        if self._settings and hasattr(self._settings, "_resolve_player_view"):
            return self._settings._resolve_player_view()
        return None

    def _launch_login(self, service_id: str):
        from app.features.accounts.account_login_window import AccountLoginWindow

        win = AccountLoginWindow(self)
        win.finished.connect(self._on_login_finished)
        if not win.start(
            service_id,
            player_view=self._resolve_player_view(),
            parent_widget=self,
        ):
            return

    def _on_login_finished(self, _service_id: str, _ok: bool):
        from app.features.accounts.account_login_window import AccountLoginWindow

        AccountLoginWindow.force_reset_stale()
        pv = self._resolve_player_view()
        if pv and hasattr(pv, "on_login_window_closed"):
            pv.on_login_window_closed()
        self._rebuild_body()

    def _logout(self, service_id: str):
        from app.features.accounts.account_login_window import (
            AccountLoginWindow,
            logout_service,
        )

        AccountLoginWindow.force_reset_stale()
        logout_service(
            service_id,
            player_view=self._resolve_player_view(),
            parent_widget=self,
        )
        pv = self._resolve_player_view()
        if pv and hasattr(pv, "on_login_window_closed"):
            pv.on_login_window_closed(False)
        self._rebuild_body()

    def _apply_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40)
        sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self._card.setGraphicsEffect(sh)

    def smart_position(self, parent_geo):
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        w, h = self.width(), self.height()
        cy = parent_geo.top() + (parent_geo.height() - h) // 2
        cx = parent_geo.left() + (parent_geo.width() - w) // 2
        for x, y in (
            (parent_geo.left() - w - 12, cy),
            (parent_geo.right() + 12, cy),
            (cx, parent_geo.top() - h - 12),
            (cx, parent_geo.bottom() + 12),
        ):
            if (
                x >= screen.left()
                and x + w <= screen.right()
                and y >= screen.top()
                and y + h <= screen.bottom()
            ):
                self.move(x, y)
                return
        self.move(screen.center().x() - w // 2, screen.center().y() - h // 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
