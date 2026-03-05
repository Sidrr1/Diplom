import sys, os

APP_NAME = "EdgeTools"

def _get_cmd() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    main_py = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "main.py")
    )
    return f'"{pythonw}" "{main_py}"'

def is_enabled() -> bool:
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