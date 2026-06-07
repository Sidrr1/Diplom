"""Вкладка Image Enhancer."""
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QComboBox,
    QSlider, QLabel, QLineEdit, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.core.paths import normalize_path
from app.features.image_enhancer.core.save_utils import default_save_folder
from app.features.settings.ui import settings_styles as ss


class EnhancerMixin:
    """Вкладка настроек модуля улучшения изображений (путь, формат, качество)."""

    def _page_enhancer(self) -> QWidget:
        """Настройки Image Enhancer."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(self._section("IMAGE ENHANCER"))

        row, self._cb_enhancer_autosave = self._toggle_row(
            "Быстрое сохранение",
            "Кнопка «Сохранить» сразу кладёт файл в папку ниже",
            self.cfg.get("enhancer_autosave", True),
        )
        lay.addWidget(row)

        path_frame = QFrame()
        path_frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        path_lay = QVBoxLayout(path_frame)
        path_lay.setContentsMargins(14, 12, 14, 12)
        path_lay.setSpacing(8)

        path_hdr = QHBoxLayout()
        path_hdr.addWidget(self._row_title("Папка для сохранения"))
        path_hdr.addStretch()
        path_lay.addLayout(path_hdr)

        path_box = QFrame()
        path_box.setStyleSheet(
            "QFrame{background:#141414;border-radius:10px;border:1px solid #2e2e2e;}"
        )
        path_box_lay = QHBoxLayout(path_box)
        path_box_lay.setContentsMargins(12, 10, 12, 10)

        self._enhancer_path_edit = QLineEdit()
        saved = self.cfg.get("enhancer_save_path", "") or default_save_folder()
        self._enhancer_path_edit.setText(saved)
        self._enhancer_path_edit.setPlaceholderText(r"C:\Users\…\Pictures\EdgeTools")
        self._enhancer_path_edit.setFont(QFont("Segoe UI", 10))
        self._enhancer_path_edit.setStyleSheet("""
            QLineEdit {
                background:transparent; color:#e8e8e8; border:none;
                font-size:11px; selection-background-color:#0078d7;
            }
        """)
        path_box_lay.addWidget(self._enhancer_path_edit, 1)
        path_lay.addWidget(path_box)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_browse = self._sorter_btn_secondary("Обзор…")
        btn_browse.clicked.connect(self._choose_enhancer_save_path)
        btn_pics = self._sorter_btn_secondary("Картинки")
        btn_pics.clicked.connect(self._set_enhancer_pictures)
        btn_row.addWidget(btn_browse)
        btn_row.addWidget(btn_pics)
        btn_row.addStretch()
        path_lay.addLayout(btn_row)
        lay.addWidget(path_frame)

        format_frame = QFrame()
        format_frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        format_lay = QHBoxLayout(format_frame)
        format_lay.setContentsMargins(14, 12, 14, 12)

        format_col = QVBoxLayout()
        format_col.setSpacing(2)
        format_col.addWidget(self._row_title("Формат файла"))

        self._combo_enhancer_format = QComboBox()
        self._combo_enhancer_format.addItems(["PNG", "JPEG", "WEBP"])
        self._combo_enhancer_format.setCurrentText(self.cfg.get("enhancer_format", "JPEG"))
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

        quality_frame = QFrame()
        quality_frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        quality_lay = QVBoxLayout(quality_frame)
        quality_lay.setContentsMargins(14, 12, 14, 12)
        quality_lay.setSpacing(6)

        quality_val = self.cfg.get("enhancer_jpeg_quality", 95)
        quality_hdr = QHBoxLayout()
        quality_hdr.addWidget(self._row_title("Качество JPEG / WebP"))
        quality_hdr.addStretch()

        self._lbl_enhancer_quality = QLabel(f"{quality_val}%")
        self._lbl_enhancer_quality.setFont(QFont("Segoe UI", 11))
        self._lbl_enhancer_quality.setStyleSheet(ss.STYLE_LABEL_BLUE)
        quality_hdr.addWidget(self._lbl_enhancer_quality)

        self._slider_enhancer_quality = QSlider(Qt.Horizontal)
        self._slider_enhancer_quality.setRange(70, 100)
        self._slider_enhancer_quality.setValue(quality_val)
        self._slider_enhancer_quality.setStyleSheet(self._enhancer_slider_style())
        self._slider_enhancer_quality.valueChanged.connect(
            lambda v: self._lbl_enhancer_quality.setText(f"{v}%")
        )

        quality_lay.addLayout(quality_hdr)
        quality_lay.addWidget(self._slider_enhancer_quality)
        lay.addWidget(quality_frame)

        lay.addStretch()
        return page

    @staticmethod
    def _enhancer_slider_style() -> str:
        return """
            QSlider::groove:horizontal { height:4px; background:rgba(255,255,255,20);
                                         border-radius:2px; }
            QSlider::sub-page:horizontal { background:#0078d7; border-radius:2px; }
            QSlider::handle:horizontal   { width:14px; height:14px; margin:-5px 0;
                                           background:#0078d7; border-radius:7px; }
        """

    def _choose_enhancer_save_path(self) -> None:
        start = self._enhancer_path_edit.text().strip() or default_save_folder()
        folder = QFileDialog.getExistingDirectory(self, "Папка для сохранения", start)
        if folder:
            self._enhancer_path_edit.setText(normalize_path(folder))

    def _set_enhancer_pictures(self) -> None:
        pics = normalize_path(os.path.join(os.path.expanduser("~"), "Pictures", "EdgeTools"))
        self._enhancer_path_edit.setText(pics)
