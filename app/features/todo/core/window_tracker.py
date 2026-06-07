"""
Отслеживание активного окна Windows для контекстных заметок.

Определяет процесс и заголовок foreground-окна, игнорирует EdgeTools
и системные процессы, эмитит сигнал при смене контекста.
"""
import os
import ctypes
from ctypes import wintypes
import psutil
from PySide6.QtCore import QObject, QTimer, Signal


class WindowTracker(QObject):
    """Отслеживает активное окно и определяет контекст приложения."""

    context_changed = Signal(str, str)  # (process_name, window_title)

    def __init__(self, interval_ms: int = 1000):
        """
        Args:
            interval_ms: интервал проверки активного окна (мс)
        """
        super().__init__()
        self._current_process = None
        self._current_title = None
        self._interval = interval_ms
        self._our_pid = os.getpid()  # Запоминаем PID нашего процесса

        # WinAPI функции
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        # Таймер для периодической проверки
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_active_window)

    def start(self):
        """Запустить отслеживание."""
        print(f"[window_tracker] Started (interval: {self._interval}ms)")
        self._timer.start(self._interval)

    def stop(self):
        """Остановить отслеживание."""
        self._timer.stop()
        print("[window_tracker] Stopped")

    def get_current_context(self) -> str:
        """
        Получить текущий контекст (имя процесса).

        Returns:
            process_name (например 'chrome.exe' или 'global')
        """
        # Если контекст ещё не определён, проверяем сейчас
        if self._current_process is None:
            self._check_active_window()

        return self._current_process or 'global'

    def _check_active_window(self):
        """Проверить активное окно и определить контекст."""
        try:
            # Получаем handle активного окна
            hwnd = self._user32.GetForegroundWindow()
            if not hwnd:
                # Нет активного окна — рабочий стол
                if self._current_process != 'global':
                    self._current_process = 'global'
                    self._current_title = 'Desktop'
                    print("[window_tracker] Context changed: global (Desktop)")
                    self.context_changed.emit('global', 'Desktop')
                return

            # Получаем PID процесса
            pid = wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            if not pid.value:
                return

            # Получаем имя процесса через psutil
            try:
                process = psutil.Process(pid.value)
                process_name = process.name().lower()

                # Проверяем командную строку процесса
                try:
                    cmdline = ' '.join(process.cmdline()).lower()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    cmdline = ''
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return

            # Игнорируем наш процесс EdgeTools
            # Проверяем по командной строке (main.py в пути)
            if 'python' in process_name and 'main.py' in cmdline:
                # Это наш EdgeTools процесс
                return

            # Fallback: игнорируем по PID
            if 'python' in process_name and pid.value == self._our_pid:
                return

            # Игнорируем системные процессы
            ignored_processes = {
                'searchhost.exe',      # Windows Search
                'dwm.exe',             # Desktop Window Manager
                'taskmgr.exe',         # Диспетчер задач
                'applicationframehost.exe',  # UWP приложения
                'shellexperiencehost.exe',   # Меню Пуск
                'startmenuexperiencehost.exe',
                'searchapp.exe',       # Windows Search App
                'lockapp.exe',         # Экран блокировки
                'runtimebroker.exe',   # Runtime Broker
                'sihost.exe',          # Shell Infrastructure Host
                'ctfmon.exe',          # Text Services Framework
            }

            if process_name in ignored_processes:
                print(f"[window_tracker] Ignoring system process: {process_name}")
                return

            # Explorer.exe (рабочий стол) → global контекст
            if process_name == 'explorer.exe':
                if self._current_process != 'global':
                    self._current_process = 'global'
                    self._current_title = 'Desktop'
                    print("[window_tracker] Context changed: global (Desktop via explorer.exe)")
                    self.context_changed.emit('global', 'Desktop')
                return

            # Получаем заголовок окна
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                self._user32.GetWindowTextW(hwnd, buffer, length + 1)
                window_title = buffer.value
            else:
                window_title = ""

            # Игнорируем окна заметок (sticky notes)
            if self._is_sticky_note_window(hwnd, process_name, window_title):
                print(f"[window_tracker] Ignoring sticky note window: {window_title[:30]}")
                return

            # Проверяем изменился ли контекст
            if process_name != self._current_process:
                self._current_process = process_name
                self._current_title = window_title
                print(f"[window_tracker] Context changed: {process_name} - {window_title[:50]}")
                self.context_changed.emit(process_name, window_title)
            elif window_title != self._current_title:
                # Заголовок изменился (например, новая вкладка в браузере)
                self._current_title = window_title
                # Можно добавить более детальное отслеживание вкладок браузера
                # Пока просто обновляем title без сигнала

        except Exception as e:
            from app.core.logger import log_error
            log_error("Window Tracker Error", f"Failed to check active window: {e}", e)

            # Сбрасываем контекст на global при ошибке
            if self._current_process != 'global':
                self._current_process = 'global'
                self._current_title = 'Error'
                self.context_changed.emit('global', 'Error')

    def _is_sticky_note_window(self, hwnd, process_name: str, window_title: str) -> bool:
        """
        Проверить, является ли окно окном заметки.

        Args:
            hwnd: handle окна
            process_name: имя процесса
            window_title: заголовок окна

        Returns:
            True если это окно заметки
        """
        # Проверяем, что это наш процесс
        if 'python' not in process_name:
            return False

        # Проверяем заголовок окна (заметки имеют эмодзи 📌)
        if '📌' in window_title:
            return True

        # Проверяем стиль окна (Tool window без заголовка)
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000

        ex_style = self._user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex_style & WS_EX_TOOLWINDOW and ex_style & WS_EX_NOACTIVATE:
            # Дополнительно проверяем размер окна (заметки небольшие)
            rect = wintypes.RECT()
            self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
            width = rect.right - rect.left
            height = rect.bottom - rect.top

            # Заметки обычно 250x200 или около того
            if 150 <= width <= 400 and 40 <= height <= 600:
                return True

        return False

    def get_browser_context(self, process_name: str, window_title: str) -> str:
        """
        Определить более точный контекст для браузера (например YouTube).

        Args:
            process_name: имя процесса браузера
            window_title: заголовок окна

        Returns:
            уточнённый контекст (например 'chrome.exe:youtube')
        """
        if not window_title:
            return process_name

        title_lower = window_title.lower()

        # Определяем популярные сайты
        if 'youtube' in title_lower:
            return f"{process_name}:youtube"
        elif 'github' in title_lower:
            return f"{process_name}:github"
        elif 'stackoverflow' in title_lower:
            return f"{process_name}:stackoverflow"
        elif 'google' in title_lower and 'search' in title_lower:
            return f"{process_name}:google"

        return process_name
