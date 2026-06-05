"""Вкладка Image Enhancer."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QComboBox, QSlider, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.features.settings.ui import settings_styles as ss


class EnhancerMixin:
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
        format_frame.setStyleSheet(ss.STYLE_ROW_FRAME)
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
        quality_frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        quality_lay = QVBoxLayout(quality_frame)
        quality_lay.setContentsMargins(14, 12, 14, 12)
        quality_lay.setSpacing(6)

        quality_val = self.cfg.get("enhancer_jpeg_quality", 95)
        quality_hdr = QHBoxLayout()
        quality_hdr.addWidget(self._row_title("Качество JPEG"))
        quality_hdr.addStretch()

        self._lbl_enhancer_quality = QLabel(f"{quality_val}%")
        self._lbl_enhancer_quality.setFont(QFont("Segoe UI", 11))
        self._lbl_enhancer_quality.setStyleSheet(ss.STYLE_LABEL_BLUE)
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
