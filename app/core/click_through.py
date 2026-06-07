"""
Click-through режим окон EdgeTools (Smart Notes).

Позволяет стикерам-заметкам пропускать клики мыши сквозь себя к окнам под ними
через WinAPI-флаги WS_EX_TRANSPARENT и WS_EX_LAYERED.
"""
import ctypes
from ctypes import wintypes


def set_click_through(hwnd: int, enabled: bool):
    """
    Включить или выключить click-through для окна Win32.

    Args:
        hwnd: дескриптор окна (HWND).
        enabled: True — клики проходят сквозь окно, False — обычный режим.
    """
    try:
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_LAYERED = 0x00080000

        user32 = ctypes.windll.user32

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        if enabled:
            ex_style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            ex_style &= ~WS_EX_TRANSPARENT

        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

        print(f"[click_through] Window {hwnd}: {'enabled' if enabled else 'disabled'}")

    except Exception as e:
        print(f"[click_through] Error: {e}")


def is_click_through(hwnd: int) -> bool:
    """
    Проверить, включён ли click-through у окна.

    Args:
        hwnd: дескриптор окна (HWND).

    Returns:
        True, если установлен флаг WS_EX_TRANSPARENT.
    """
    try:
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020

        user32 = ctypes.windll.user32
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        return bool(ex_style & WS_EX_TRANSPARENT)

    except Exception:
        return False
