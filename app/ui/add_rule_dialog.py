from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QFileDialog, QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont


class AddRuleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._folder     = None
        self._rule_type  = "extension"
        self._patterns   = []
        self._drag_pos   = None
        self._active_tab = 0   # 0=расширения, 1=ключевые слова
        self._build_ui()
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40); sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self._card.setGraphicsEffect(sh)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        self._card = QFrame(); self._card.setObjectName("card")
        self._card.setStyleSheet("""
            QFrame#card { background:#141414; border-radius:18px;
                          border:1px solid #2a2a2a; }
        """)
        lay = QVBoxLayout(self._card)
        lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(14)

        # Заголовок
        hdr = QHBoxLayout()
        title = QLabel("Новое правило")
        title.setFont(QFont("Segoe UI Semibold", 13))
        title.setStyleSheet("color:#f0f0f0;")
        btn_x = QPushButton("✕"); btn_x.setFixedSize(28, 28)
        btn_x.setCursor(Qt.PointingHandCursor)
        btn_x.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#888; border:none;
                          border-radius:8px; font-size:13px; }
            QPushButton:hover { background:#c0392b; color:white; }
        """)
        btn_x.clicked.connect(self.reject)
        hdr.addWidget(title); hdr.addStretch(); hdr.addWidget(btn_x)
        lay.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#2a2a2a;"); lay.addWidget(sep)

        # Папка назначения
        lay.addWidget(self._section("ПАПКА НАЗНАЧЕНИЯ"))
        folder_row = QHBoxLayout(); folder_row.setSpacing(8)
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Выберите папку...")
        self._folder_edit.setStyleSheet("""
            QLineEdit { background:rgba(255,255,255,6); color:white;
                        border:1px solid #2a2a2a; border-radius:8px;
                        padding:6px 10px; font-size:12px; }
            QLineEdit:focus { border-color:#0078d7; }
        """)
        btn_browse = QPushButton("Обзор")
        btn_browse.setFixedHeight(34); btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#ccc; border:none;
                          border-radius:8px; padding:0 14px; font-size:12px; }
            QPushButton:hover { background:#333; color:white; }
        """)
        btn_browse.clicked.connect(self._choose_folder)
        folder_row.addWidget(self._folder_edit, stretch=1)
        folder_row.addWidget(btn_browse)
        lay.addLayout(folder_row)

        # Переключатель тип правила
        lay.addWidget(self._section("ТИП ПРАВИЛА"))
        tab_row = QHBoxLayout(); tab_row.setSpacing(8)
        self._btn_ext = self._tab_btn("По расширению", 0)
        self._btn_kw  = self._tab_btn("По ключевому слову", 1)
        tab_row.addWidget(self._btn_ext); tab_row.addWidget(self._btn_kw)
        tab_row.addStretch()
        lay.addLayout(tab_row)
        self._btn_ext.setChecked(True)

        # Поле ввода паттернов
        self._input = QLineEdit()
        self._input.returnPressed.connect(self._save)
        self._input.setPlaceholderText("Например: jpg, png, mp4")
        self._input.setStyleSheet("""
            QLineEdit { background:rgba(255,255,255,6); color:white;
                        border:1px solid #2a2a2a; border-radius:8px;
                        padding:8px 10px; font-size:12px; }
            QLineEdit:focus { border-color:#0078d7; }
        """)
        lay.addWidget(self._input)

        self._hint = QLabel("Введите расширения через запятую (без точки)")
        self._hint.setFont(QFont("Segoe UI", 9))
        self._hint.setStyleSheet("color:#555;")
        lay.addWidget(self._hint)

        lay.addStretch()

        # Кнопки
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setFixedHeight(40); btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#aaa; border:none;
                          border-radius:10px; font-size:13px; }
            QPushButton:hover { background:#333; color:white; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Сохранить")
        btn_save.setFixedHeight(40); btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton { background:#0078d7; color:white; border:none;
                          border-radius:10px; font-size:13px; font-weight:600; }
            QPushButton:hover { background:#1a8fe3; }
        """)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel); btn_row.addWidget(btn_save)
        lay.addLayout(btn_row)
        root.addWidget(self._card)

    def _tab_btn(self, text: str, idx: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True); btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(30)
        btn.setFont(QFont("Segoe UI", 10))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:#666; border:none;
                          border-radius:8px; padding:0 12px; }
            QPushButton:hover { color:#aaa; background:rgba(255,255,255,5); }
            QPushButton:checked { background:#0078d7; color:white; }
        """)
        btn.clicked.connect(lambda: self._switch_tab(idx))
        return btn

    def _switch_tab(self, idx: int):
        self._active_tab = idx
        self._btn_ext.setChecked(idx == 0)
        self._btn_kw.setChecked(idx == 1)
        if idx == 0:
            self._input.setPlaceholderText("Например: jpg, png, mp4")
            self._hint.setText("Введите расширения через запятую (без точки)")
        else:
            self._input.setPlaceholderText("Например: отчет, фото, музыка")
            self._hint.setText("Слово должно содержаться в имени файла")

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#555; letter-spacing:1.5px;"); return lbl

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self._folder = folder
            self._folder_edit.setText(folder)

    def _save(self):
        if not self._folder_edit.text().strip():
            self._folder_edit.setPlaceholderText("⚠ Выберите папку!")
            return
        text = self._input.text().strip()
        if not text:
            self._input.setPlaceholderText("⚠ Введите паттерн!")
            return
        
        if self._active_tab == 0:
            # Расширения — убираем точку если пользователь написал .txt или .TXT
            self._patterns = [p.strip().lower().lstrip(".") for p in text.split(",") if p.strip()]
        else:
            # Ключевые слова — просто нижний регистр
            self._patterns = [p.strip().lower() for p in text.split(",") if p.strip()]
        
        self._folder    = self._folder_edit.text().strip()
        self._rule_type = "extension" if self._active_tab == 0 else "keyword"
        self.accept()


    def get_result(self) -> dict | None:
        if self._patterns and self._folder:
            return {"type": self._rule_type, "patterns": self._patterns, "folder": self._folder}
        return None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._drag_pos = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()
    def mouseReleaseEvent(self, e): self._drag_pos = None