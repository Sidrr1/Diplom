"""
UI Image Enhancer: окно «До/После», слайдеры fidelity/intensity,
запуск улучшения и раскраски через сигналы в фоновый ``EnhanceWorker``.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QProgressBar, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QFont
from PIL import Image

_OPEN_FILTER = (
    "Images ("
    "*.png *.jpg *.jpeg *.jfif *.bmp *.webp "
    "*.tiff *.tif *.gif *.ico *.ppm *.pgm *.pbm *.dib"
    ")"
)
_SAVE_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp);;BMP (*.bmp)"

_SLIDER_STYLE = """
    QSlider::groove:horizontal {
        height: 5px; background: rgba(255,255,255,12);
        border-radius: 3px;
    }
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #005a9e, stop:1 #00a2ff);
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #e8f4ff; width: 14px; height: 14px;
        margin: -5px 0; border-radius: 7px;
        border: 2px solid #0078d7;
    }
    QSlider::handle:horizontal:hover { background: white; }
"""

_CTRL_FRAME = """
    QFrame#ctrl {
        background: rgba(255,255,255,4);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,8);
    }
"""

_BTN_PRIMARY = """
    QPushButton {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1084d8, stop:1 #006cbd);
        color: white; border: 1px solid #0078d7; border-radius: 10px;
        font-weight: 600;
    }
    QPushButton:hover   { background: #1a96ea; }
    QPushButton:pressed { background: #005a9e; }
    QPushButton:disabled { background: rgba(255,255,255,6); color: rgba(255,255,255,35);
                           border: 1px solid rgba(255,255,255,10); font-weight: 400; }
"""


class ImageLabel(QLabel):
    """Метка с масштабированием PIL-изображения по размеру виджета (До / После)."""

    def __init__(self, placeholder: str = ""):
        super().__init__()
        self._pixmap_orig = None
        self._placeholder = placeholder
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background:rgba(255,255,255,5); border-radius:10px;")
        self.setText(placeholder)
        self.setFont(QFont("Segoe UI", 10))

    def set_image(self, img: Image.Image):
        """Показать PIL-изображение с сохранением пропорций."""
        data = img.convert("RGB").tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height,
                      img.width * 3, QImage.Format_RGB888)
        self._pixmap_orig = QPixmap.fromImage(qimg)
        self._refresh()

    def clear_image(self):
        self._pixmap_orig = None
        self.setPixmap(QPixmap())
        self.setText(self._placeholder)

    def resizeEvent(self, e):
        self._refresh()
        super().resizeEvent(e)

    def _refresh(self):
        if self._pixmap_orig:
            scaled = self._pixmap_orig.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)


class EnhancerView(QWidget):
    """
    Главное окно Image Enhancer.

    Эмитирует ``enhance_requested`` и ``colorize_requested``;
    принимает результат через ``show_result`` / ``show_error`` / ``set_progress``.
    """

    enhance_requested  = Signal(object)
    colorize_requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(520, 620)
        self.resize(580, 670)
        self._pil_original  = None   # загруженный кадр «До»
        self._pil_result    = None   # результат enhance/colorize «После»
        self._source_path   = None
        self._source_format = "png"
        self._drag_pos      = None
        self._build()
        self.setAcceptDrops(True)

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self._card = QFrame(); self._card.setObjectName("card")
        self._card.setStyleSheet("""
            QFrame#card { background:rgba(18,18,18,240); border-radius:18px;
                          border:1px solid rgba(255,255,255,10); }
        """)
        lay = QVBoxLayout(self._card)
        lay.setContentsMargins(16, 14, 16, 16); lay.setSpacing(10)
        lay.addWidget(self._make_titlebar())
        lay.addWidget(self._make_image_area())
        lay.addWidget(self._make_status_row())
        lay.addWidget(self._make_info_label())
        lay.addWidget(self._make_progress())
        lay.addWidget(self._make_buttons())
        root.addWidget(self._card)

    def _make_titlebar(self) -> QWidget:
        bar = QWidget(); lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        title = QLabel("🖼  Image Enhancer")
        title.setFont(QFont("Segoe UI Semibold", 11))
        title.setStyleSheet("color:white;")
        close = QPushButton("✕"); close.setFixedSize(28, 28)
        close.setCursor(Qt.PointingHandCursor)
        close.setStyleSheet("""
            QPushButton { background:transparent; color:rgba(255,85,85,160);
                          border:none; font-size:14px; border-radius:6px; }
            QPushButton:hover { background:rgba(192,57,43,40); color:#ff5555; }
        """)
        close.clicked.connect(self.close)
        lay.addWidget(title); lay.addStretch(); lay.addWidget(close)
        return bar

    def _make_image_area(self) -> QWidget:
        container = QWidget(); lay = QHBoxLayout(container)
        lay.setSpacing(8); lay.setContentsMargins(0, 0, 0, 0)
        self._lbl_before = ImageLabel("Перетащите изображение\nили нажмите «Открыть»")
        self._lbl_after  = ImageLabel("Результат появится здесь")
        lay.addWidget(self._wrap_labeled(self._lbl_before, "До"))
        lay.addWidget(self._wrap_labeled(self._lbl_after,  "После"))
        return container

    def _wrap_labeled(self, widget: QWidget, text: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background:transparent; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(4)
        lbl = QLabel(text); lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color:rgba(200,200,200,120);")
        lay.addWidget(lbl); lay.addWidget(widget)
        return frame

    _PHASES = (
        # Пороги прогресса пайплайна → текст статуса для пользователя
        (0, "Подготовка…"),
        (8, "Анализ изображения…"),
        (15, "Предобработка…"),
        (20, "Нейро-апскейл (SwinIR)…"),
        (45, "Сегментация и лица…"),
        (60, "Улучшение лиц (CodeFormer)…"),
        (85, "Зоны и финальная полировка…"),
        (96, "Сохранение результата…"),
    )

    def _make_status_row(self) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        self._phase_lbl = QLabel("Готово к работе")
        self._phase_lbl.setFont(QFont("Segoe UI", 9))
        self._phase_lbl.setStyleSheet("color:rgba(160,200,255,200);")
        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFont(QFont("Segoe UI", 9))
        self._pct_lbl.setStyleSheet("color:rgba(200,200,200,120); min-width:36px;")
        self._pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self._phase_lbl, stretch=1)
        lay.addWidget(self._pct_lbl)
        return row

    def _make_info_label(self) -> QLabel:
        self._info_lbl = QLabel("")
        self._info_lbl.setAlignment(Qt.AlignCenter)
        self._info_lbl.setFont(QFont("Segoe UI", 9))
        self._info_lbl.setStyleSheet("color:rgba(200,200,200,140);")
        self._info_lbl.setWordWrap(True)
        return self._info_lbl

    def _make_progress(self) -> QProgressBar:
        self._progress = QProgressBar()
        self._progress.setFixedHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,10);
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #005a9e, stop:1 #00a2ff);
                border-radius: 4px;
            }
        """)
        return self._progress

    def _make_buttons(self) -> QWidget:
        from PySide6.QtWidgets import QSlider

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self._btn_open = self._btn("📂  Открыть", self._open_file)
        self._btn_save = self._btn("💾  Сохранить", self._save_file, enabled=False)
        row1.addWidget(self._btn_open)
        row1.addWidget(self._btn_save)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self._btn_enhance = self._btn("⬆  Улучшить", self._run_enhance, enabled=False)
        self._btn_enhance.setStyleSheet(_BTN_PRIMARY)
        self._btn_colorize = self._btn("🎨  Раскрасить", self._run_colorize, enabled=False)
        row2.addWidget(self._btn_enhance)
        row2.addWidget(self._btn_colorize)
        lay.addLayout(row2)

        ctrl = QFrame()
        ctrl.setObjectName("ctrl")
        ctrl.setStyleSheet(_CTRL_FRAME)
        ctrl_lay = QVBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(12, 10, 12, 10)
        ctrl_lay.setSpacing(10)

        # fidelity → похожесть на оригинал (CodeFormer w), 85% по умолчанию
        self._fidelity_slider = QSlider(Qt.Horizontal)
        self._fidelity_slider.setRange(0, 100)
        self._fidelity_slider.setValue(85)
        self._fidelity_slider.setStyleSheet(_SLIDER_STYLE)
        self._fidelity_value_lbl = QLabel("85%")
        ctrl_lay.addWidget(self._make_slider_row(
            "🎯", "Похожесть", "как было",
            self._fidelity_slider, self._fidelity_value_lbl,
            lambda v: self._fidelity_value_lbl.setText(f"{v}%"),
        ))

        # intensity → сила зональных эффектов и постобработки, 55% — «natural mode»
        self._intensity_slider = QSlider(Qt.Horizontal)
        self._intensity_slider.setRange(0, 100)
        self._intensity_slider.setValue(55)
        self._intensity_slider.setStyleSheet(_SLIDER_STYLE)
        self._intensity_value_lbl = QLabel("55%")
        ctrl_lay.addWidget(self._make_slider_row(
            "✨", "Сила", "эффекта",
            self._intensity_slider, self._intensity_value_lbl,
            lambda v: self._intensity_value_lbl.setText(f"{v}%"),
        ))

        lay.addWidget(ctrl)
        self._refresh_save_button_label()
        return w

    def _make_slider_row(
        self, icon: str, title: str, hint: str,
        slider: "QSlider", value_lbl: QLabel, on_change,
    ) -> QWidget:
        row = QWidget()
        lay = QVBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        ico = QLabel(icon)
        ico.setFixedWidth(18)
        ico.setStyleSheet("color:rgba(200,220,255,200); border:none; background:transparent;")
        name = QLabel(title)
        name.setFont(QFont("Segoe UI Semibold", 9))
        name.setStyleSheet("color:rgba(230,230,230,220);")
        tail = QLabel(hint)
        tail.setFont(QFont("Segoe UI", 8))
        tail.setStyleSheet("color:rgba(160,160,160,140);")
        value_lbl.setFont(QFont("Segoe UI Semibold", 10))
        value_lbl.setStyleSheet("color:#5eb8ff; min-width:40px;")
        value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hdr.addWidget(ico)
        hdr.addWidget(name)
        hdr.addWidget(tail)
        hdr.addStretch()
        hdr.addWidget(value_lbl)
        lay.addLayout(hdr)
        lay.addWidget(slider)
        slider.valueChanged.connect(on_change)
        return row

    def _btn(self, text: str, slot, enabled=True) -> QPushButton:
        b = QPushButton(text); b.setCursor(Qt.PointingHandCursor)
        b.setEnabled(enabled); b.setFont(QFont("Segoe UI", 10))
        b.setFixedHeight(38)
        b.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,8); color:rgba(220,220,220,220);
                          border:1px solid rgba(255,255,255,12); border-radius:10px; }
            QPushButton:hover   { background:rgba(0,120,215,60);
                                  border:1px solid #0078d7; color:white; }
            QPushButton:pressed { background:rgba(0,120,215,90); }
            QPushButton:disabled { color:rgba(255,255,255,35); }
        """)
        b.clicked.connect(slot)
        return b

    # ── Файлы ────────────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение", "", _OPEN_FILTER)
        if path:
            self._load_image(path)

    def _load_image(self, path: str):
        try:
            from app.features.image_enhancer.core.enhancer import open_image
            img = open_image(path)
        except Exception as e:
            self._info_lbl.setText(f"Не удалось открыть: {e}")
            return

        ext = os.path.splitext(path)[1].lower().lstrip(".")
        self._source_format = ext if ext in ("png","jpg","jpeg","webp","bmp") else "png"
        self._source_path   = path
        self._pil_original  = img
        self._pil_result    = None

        self._lbl_before.set_image(img)
        self._lbl_after.clear_image()
        self._info_lbl.setText(f"{img.width}×{img.height}  |  {os.path.basename(path)}")
        self._btn_enhance.setEnabled(True)
        self._btn_save.setEnabled(False)
        self._progress.setValue(0)

        from app.features.image_enhancer.core.colorizer import is_grayscale
        self._btn_colorize.setEnabled(is_grayscale(img))

    def _refresh_save_button_label(self):
        from app.features.image_enhancer.core.save_utils import get_save_settings
        if not hasattr(self, "_btn_save"):
            return
        if get_save_settings()["autosave"]:
            self._btn_save.setText("💾  В папку")
            self._btn_save.setToolTip("Сохранить в папку из настроек")
        else:
            self._btn_save.setText("💾  Сохранить как…")
            self._btn_save.setToolTip("Выбрать место и имя файла")

    def _save_file(self):
        if not self._pil_result:
            return

        from app.features.image_enhancer.core.save_utils import (
            build_output_path, get_save_settings, save_image,
        )

        settings = get_save_settings()
        self._refresh_save_button_label()

        if settings["autosave"]:
            folder = settings["folder"]
            if not folder:
                self._info_lbl.setStyleSheet("color:#ffb347;")
                self._info_lbl.setText("Укажите папку: Настройки → Image Enhancer")
                return
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError as e:
                self._info_lbl.setStyleSheet("color:#ff6b6b;")
                self._info_lbl.setText(f"Папка недоступна: {e}")
                return
            out_path = build_output_path(self._source_path, settings)
        else:
            stem = "enhanced"
            if self._source_path:
                stem = os.path.splitext(os.path.basename(self._source_path))[0] + "_enhanced"
            ext_map = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
            ext = ext_map.get(settings["format"], ".png")
            start_dir = settings["folder"] if os.path.isdir(settings["folder"]) else ""
            default_name = os.path.join(start_dir, stem + ext) if start_dir else stem + ext
            out_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить как", default_name, _SAVE_FILTER)
            if not out_path:
                return

        try:
            saved = save_image(self._pil_result, out_path, settings)
            self._info_lbl.setStyleSheet("color:rgba(180,230,180,200);")
            folder = os.path.dirname(saved)
            self._info_lbl.setText(f"✅ {os.path.basename(saved)}  →  {folder}")
        except Exception as e:
            self._info_lbl.setStyleSheet("color:#ff6b6b;")
            self._info_lbl.setText(f"Не удалось сохранить: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_save_button_label()

    # ── Обработка ────────────────────────────────────────────────────────

    def _run_enhance(self):
        if self._pil_original:
            self._set_busy(True, "Запуск улучшения качества…")
            self.enhance_requested.emit(self._pil_original)

    def _run_colorize(self):
        if not self._pil_original:
            return
        self._set_busy(True, "Раскраска (модель может грузиться при первом запуске)…")
        self.colorize_requested.emit(self._pil_original)

    def show_result(self, img: Image.Image, info: str):
        """Отобразить результат улучшения и обновить панель «После»."""
        self._pil_result = img
        self._lbl_after.set_image(img)
        self._lbl_after.setStyleSheet(
            "background:rgba(255,255,255,5); border-radius:10px;"
            "border:1px solid rgba(0,162,255,40);"
        )
        low = info.lower()
        if any(x in low for x in ("fallback", "partial", "пропущены", "lanczos")):
            self._info_lbl.setStyleSheet("color:#ffb347;")
            self._phase_lbl.setText("Готово (упрощённый режим)")
        else:
            self._info_lbl.setStyleSheet("color:rgba(180,230,180,200);")
            self._phase_lbl.setText("Готово")
        self._info_lbl.setText(info)
        self._pct_lbl.setText("100%")
        self._progress.setValue(100)
        self._btn_save.setEnabled(True)
        self._refresh_save_button_label()
        self._set_busy(False)

    def show_error(self, msg: str):
        """Показать ошибку пайплайна и снять блокировку UI."""
        self._info_lbl.setStyleSheet("color:#ff6b6b;")
        self._info_lbl.setText(f"Ошибка: {msg}")
        self._phase_lbl.setText("Ошибка")
        self._set_busy(False)

    def set_progress(self, v: int):
        """Обновить прогресс-бар и фазу обработки по таблице ``_PHASES``."""
        v = max(0, min(100, int(v)))
        self._progress.setValue(v)
        self._pct_lbl.setText(f"{v}%")
        phase = self._PHASES[0][1]
        for threshold, text in self._PHASES:
            if v >= threshold:
                phase = text
        self._phase_lbl.setText(phase)

    def _set_busy(self, busy: bool, status: str = ""):
        """Заблокировать/разблокировать кнопки и слайдеры на время обработки."""
        can_enhance = not busy and self._pil_original is not None
        self._btn_enhance.setEnabled(can_enhance)
        self._btn_enhance.setStyleSheet(_BTN_PRIMARY if can_enhance else """
            QPushButton { background:rgba(255,255,255,6); color:rgba(255,255,255,35);
                          border:1px solid rgba(255,255,255,10); border-radius:10px; }
        """)
        from app.features.image_enhancer.core.colorizer import is_grayscale
        can_color = self._pil_original is not None and is_grayscale(self._pil_original)
        self._btn_colorize.setEnabled(not busy and can_color)
        self._btn_open.setEnabled(not busy)
        self._btn_save.setEnabled(not busy and self._pil_result is not None)
        self._fidelity_slider.setEnabled(not busy)
        self._intensity_slider.setEnabled(not busy)
        if busy:
            self._progress.setValue(0)
            self._pct_lbl.setText("0%")
            self._phase_lbl.setText(status or "Обработка…")
            self._info_lbl.setStyleSheet("color:rgba(200,200,200,140);")
            self._lbl_after.clear_image()
            self._lbl_after.setText("Обработка…")
            self._lbl_after.setStyleSheet(
                "background:rgba(0,120,215,18); border-radius:10px;"
                "border:1px dashed rgba(0,162,255,55); color:rgba(200,220,255,180);"
            )
        else:
            if self._pil_result is None:
                self._lbl_after.setStyleSheet("background:rgba(255,255,255,5); border-radius:10px;")
                if not self._lbl_after._pixmap_orig:
                    self._lbl_after.setText("Результат появится здесь")

    # ── Drag & Drop ──────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in {".png",".jpg",".jpeg",".jfif",".bmp",".webp",
                       ".tiff",".tif",".gif",".ico",".ppm",".pgm",".pbm",".dib"}:
                self._load_image(path)
                break

    # ── Перетаскивание окна ──────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None