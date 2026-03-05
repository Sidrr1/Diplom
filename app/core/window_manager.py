# app/core/window_manager.py
import ctypes
import ctypes.wintypes as wt

GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

def set_click_through(hwnd: int, enabled: bool):
    user32 = ctypes.windll.user32
    style  = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enabled:
        style |= (WS_EX_LAYERED | WS_EX_TRANSPARENT)
    else:
        style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
