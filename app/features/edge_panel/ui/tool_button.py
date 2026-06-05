import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont

from app.core.ui_scale import scale_font, scale_px


class ToolButton(QWidget):
    clicked = Signal()

    def __init__(self, icon_path: str, label: str, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self._scale = scale
        w, h = scale_px(62, scale), scale_px(70, scale)
        self.setFixedSize(w, h)
        self.setCursor(Qt.PointingHandCursor)
        self._build_ui(icon_path, label)

    def _build_ui(self, icon_path: str, label: str):
        lay = QVBoxLayout(self)
        m = scale_px(6, self._scale)
        lay.setContentsMargins(0, m, 0, scale_px(4, self._scale))
        lay.setSpacing(scale_px(3, self._scale))
        lay.setAlignment(Qt.AlignHCenter)
        lay.addWidget(self._make_icon_btn(icon_path), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_label(label), 0, Qt.AlignHCenter)

    def _make_icon_btn(self, icon_path: str) -> QPushButton:
        s = self._scale
        side = scale_px(44, s)
        btn = QPushButton()
        btn.setFixedSize(side, side)
        icon_sz = scale_px(26, s)
        btn.setIconSize(QSize(icon_sz, icon_sz))
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.clicked)
        r = scale_px(13, s)
        btn.setStyleSheet(f"""
            QPushButton {{ background:rgba(255,255,255,8); border-radius:{r}px;
                          border:1px solid rgba(255,255,255,12); }}
            QPushButton:hover {{ background:rgba(0,120,215,60); border:1px solid #0078d7; }}
            QPushButton:pressed {{ background:rgba(0,120,215,90); }}
        """)
        return btn

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", scale_font(8, self._scale)))
        lbl.setStyleSheet("color:rgba(200,200,200,160); border:none; background:transparent;")
        return lbl
