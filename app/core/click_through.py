"""
Click-through режим для стикеров.
"""
import ctypes
from ctypes import wintypes


def set_click_through(hwnd: int, enabled: bool):
    """
    Включить/выключить click-through режим для окна.

    Args:
        hwnd: handle окна
        enabled: True = игнорировать клики, False = нормальный режим
    """
    try:
        # WinAPI константы
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_LAYERED = 0x00080000

        user32 = ctypes.windll.user32

        # Получаем текущий extended style
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        if enabled:
            # Добавляем WS_EX_TRANSPARENT и WS_EX_LAYERED
            ex_style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            # Убираем WS_EX_TRANSPARENT
            ex_style &= ~WS_EX_TRANSPARENT

        # Устанавливаем новый style
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

        print(f"[click_through] Window {hwnd}: {'enabled' if enabled else 'disabled'}")

    except Exception as e:
        print(f"[click_through] Error: {e}")


def is_click_through(hwnd: int) -> bool:
    """
    Проверить включен ли click-through режим.

    Args:
        hwnd: handle окна

    Returns:
        True если click-through включен
    """
    try:
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020

        user32 = ctypes.windll.user32
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        return bool(ex_style & WS_EX_TRANSPARENT)

    except Exception:
        return False
