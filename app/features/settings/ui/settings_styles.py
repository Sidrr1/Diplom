"""Стили и константы диалога настроек."""

STYLE_CARD = "QFrame#card{background:#141414;border-radius:18px;border:1px solid #2a2a2a;}"
STYLE_ROW_FRAME = "QFrame{background:#1e1e1e;border-radius:12px;border:1px solid #2a2a2a;}"
STYLE_LABEL_TITLE = "color:#e0e0e0; border:none; background:transparent;"
STYLE_LABEL_SUB = "color:#555; border:none; background:transparent;"
STYLE_LABEL_BLUE = "color:#0078d7; border:none; background:transparent;"

SAVE_BTN_ACTIVE = """
    QPushButton { background:#0078d7; color:white; border:none;
                  border-radius:10px; font-size:13px; font-weight:600;
                  margin:0 16px; }
    QPushButton:hover   { background:#1a8fe3; }
    QPushButton:pressed { background:#006cbf; }
"""

SAVE_BTN_IDLE = """
    QPushButton { background:#2a2a2a; color:#666; border:none;
                  border-radius:10px; font-size:13px; font-weight:600;
                  margin:0 16px; }
    QPushButton:disabled { background:#2a2a2a; color:#555; }
"""

OCR_ARROW = """
    QPushButton {
        background:transparent; color:#555; border:none;
        font-size:20px; font-weight:bold; padding:0;
    }
    QPushButton:hover { color:#0078d7; }
    QPushButton:disabled { color:#2a2a2a; }
"""
OCR_CARD_BASE = """
    QPushButton#ocrCarousel {
        background:#141414; border-radius:14px; border:2px solid #2a2a2a;
    }
    QPushButton#ocrCarousel:hover { border-color:#444; }
"""
OCR_CARD_ON = """
    QPushButton#ocrCarousel {
        background:rgba(0,120,215,0.12); border-radius:14px;
        border:2px solid #0078d7;
    }
    QPushButton#ocrCarousel:hover { border-color:#0094ff; }
"""
OCR_CARD_INSTALLED = """
    QPushButton#ocrCarousel {
        background:rgba(0,120,215,0.08); border-radius:14px;
        border:2px solid rgba(0,120,215,0.45);
    }
    QPushButton#ocrCarousel:hover { border-color:#0078d7; }
"""
OCR_TAG = """
    QPushButton {
        background:rgba(0,120,215,0.2); color:#9ecbff;
        border:1px solid #0078d7; border-radius:6px;
        font-size:10px; font-weight:600; padding:2px 8px; min-height:0;
    }
    QPushButton:hover { background:#0078d7; color:white; }
"""

NOTES_CHIP_ON = """
    QPushButton {
        background:rgba(0,120,215,0.22); color:#9ecbff;
        border:1px solid #0078d7; border-radius:8px; font-size:10px;
    }
"""
NOTES_CHIP_OFF = """
    QPushButton {
        background:#252525; color:#888; border:1px solid #333;
        border-radius:8px; font-size:10px;
    }
    QPushButton:hover { background:#2e2e2e; color:#ccc; }
"""
STYLE_TOGGLE = """
    QCheckBox::indicator { width:44px; height:24px; border-radius:12px;
                           background:#333; border:none; }
    QCheckBox::indicator:checked { background:#0078d7; }
"""
