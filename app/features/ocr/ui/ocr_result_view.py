# app/ui/ocr_result_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QApplication, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor


class OcrResultView(QWidget):
    """Попап с результатом OCR."""

    def __init__(self, text: str = ""):
        super().__init__()
        self._drag_pos = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._build_ui(text)
        self._center_on_screen()
        self._apply_shadow()

    def _build_ui(self, text: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        card = QFrame(); card.setObjectName("ocrCard")
        card.setStyleSheet("""
            QFrame#ocrCard {
                background: #141414;
                border-radius: 16px;
                border: 1px solid #2a2a2a;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 16); lay.setSpacing(0)

        # Заголовок
        hdr = QFrame()
        hdr.setStyleSheet("background:#0f0f0f; border-radius:16px 16px 0 0;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(16, 12, 12, 12)
        title = QLabel("🔍  Распознанный текст")
        title.setFont(QFont("Segoe UI Semibold", 12))
        title.setStyleSheet("color:#f0f0f0;")
        btn_close = self._make_close_btn()
        hdr_lay.addWidget(title); hdr_lay.addStretch(); hdr_lay.addWidget(btn_close)
        lay.addWidget(hdr)

        # Текстовое поле
        self._text_edit = QTextEdit()
        self._text_edit.setPlainText(text)
        self._text_edit.setFont(QFont("Segoe UI", 11))
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background: #1a1a1a;
                color: #e0e0e0;
                border: none;
                border-radius: 8px;
                padding: 10px;
                selection-background-color: #0078d7;
            }
        """)
        self._text_edit.setMinimumHeight(120)
        self._text_edit.setMaximumHeight(320)

        lay.addSpacing(12)
        text_wrap = QWidget()
        tl = QVBoxLayout(text_wrap); tl.setContentsMargins(12, 0, 12, 0)
        tl.addWidget(self._text_edit)
        lay.addWidget(text_wrap)
        lay.addSpacing(12)

        # Кнопки
        btn_row = QHBoxLayout(); btn_row.setContentsMargins(12, 0, 12, 0); btn_row.setSpacing(8)

        btn_copy = QPushButton("📋  Копировать")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setFixedHeight(38)
        btn_copy.setFont(QFont("Segoe UI", 10))
        btn_copy.setStyleSheet("""
            QPushButton { background:#0078d7; color:white; border:none;
                          border-radius:8px; font-weight:600; }
            QPushButton:hover { background:#1a8fe3; }
        """)
        btn_copy.clicked.connect(self._copy)

        btn_new = QPushButton("✂  Новый скриншот")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setFixedHeight(38)
        btn_new.setFont(QFont("Segoe UI", 10))
        btn_new.setStyleSheet("""
            QPushButton { background:#1e1e1e; color:#ccc; border:1px solid #2a2a2a;
                          border-radius:8px; }
            QPushButton:hover { background:#2a2a2a; color:white; border-color:#0078d7; }
        """)
        btn_new.clicked.connect(self._new_screenshot)

        btn_row.addWidget(btn_copy, stretch=1)
        btn_row.addWidget(btn_new, stretch=1)
        lay.addLayout(btn_row)

        root.addWidget(card)

    def set_text(self, text: str):
        self._text_edit.setPlainText(text)

    def set_loading(self, msg: str = "Распознавание..."):
        self._text_edit.setPlainText(msg)
        self._text_edit.setEnabled(False)

    def set_done(self, text: str):
        self._text_edit.setEnabled(True)
        self._text_edit.setPlainText(text)

    def _copy(self):
        text = self._text_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            # Коротко мигаем кнопкой
            btn = self.sender()
            btn.setText("✓  Скопировано!")
            QTimer.singleShot(1500, lambda: btn.setText("📋  Копировать"))

    def _new_screenshot(self):
        self.close()
        # Импортируем здесь чтобы избежать цикл
        from app.features.ocr.ui.ocr_overlay import OcrOverlay
        overlay = OcrOverlay()
        overlay.area_selected.connect(_launch_ocr)
        overlay.cancelled.connect(overlay.deleteLater)

    def _make_close_btn(self) -> QPushButton:
        btn = QPushButton("✕"); btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#888; border:none; border-radius:8px; font-size:13px; }
            QPushButton:hover { background:#c0392b; color:white; }
        """)
        btn.clicked.connect(self.close)
        return btn

    def _center_on_screen(self):
        geo = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(
            geo.center().x() - self.width() // 2,
            geo.center().y() - self.height() // 2,
        )

    def _apply_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40); sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self.findChild(QFrame, "ocrCard").setGraphicsEffect(sh)

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


# ── Глобальная функция запуска OCR ────────────────────────────────────────────

def _launch_ocr(pixmap):
    """Запускает OCR и показывает результат."""
    from app.features.ocr.core.ocr_worker import OcrWorker

    result_view = OcrResultView()
    result_view.set_loading("⏳  Распознавание текста...")
    result_view.show()

    from app.features.ocr.core.ocr_settings import get_ocr_langs

    worker = OcrWorker(pixmap, langs=get_ocr_langs())
    worker.result.connect(result_view.set_done)
    worker.error.connect(lambda e: result_view.set_done(f"Ошибка: {e}"))
    worker.progress.connect(result_view.set_loading)
    worker.start()

    # Держим ссылку чтобы GC не убил
    result_view._worker = worker


def launch_ocr_flow():
    """Точка входа — открывает оверлей выделения."""
    from app.features.ocr.ui.ocr_overlay import OcrOverlay
    overlay = OcrOverlay()
    overlay.area_selected.connect(_launch_ocr)
    overlay.cancelled.connect(overlay.deleteLater)
    # Держим ссылку
    launch_ocr_flow._overlay = overlay