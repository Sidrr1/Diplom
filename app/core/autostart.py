"""
Автозапуск EdgeTools при входе в Windows.

Управляет записью в реестре HKCU\\...\\Run для запуска приложения вместе с системой.
"""
import sys, os

APP_NAME = "EdgeTools"


def _get_cmd() -> str:
    """
    Сформировать команду запуска для записи в автозагрузку.

    Returns:
        Путь к exe (frozen) или строка «pythonw.exe main.py» для разработки.
    """
    if getattr(sys, "frozen", False):
        return sys.executable
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    main_py = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "main.py")
    )
    return f'"{pythonw}" "{main_py}"'


def is_enabled() -> bool:
    """
    Проверить, включён ли автозапуск EdgeTools в реестре Windows.

    Returns:
        True, если запись EdgeTools есть в Run.
    """
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME); return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_autostart(enabled: bool):
    """
    Включить или отключить автозапуск EdgeTools.

    Args:
        enabled: True — добавить в Run, False — удалить запись.
    """
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_cmd())
        else:
            try: winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError: pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[autostart] {e}")
