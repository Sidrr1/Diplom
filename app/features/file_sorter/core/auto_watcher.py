"""
Фоновая автосортировка: только папка-источник из настроек модуля «Сортировщик».

Включается переключателем в Настройки → вкладка сортировщика.
Пока запущен EdgeTools следит за одной папкой (например «Загрузки»),
не за всей системой. Файлы из подпапок и других дисков не трогает.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.database import db
from app.features.file_sorter.core.sorter import FileSorter
from app.features.file_sorter.core.source_folder import get_source_folder


def _setting_bool(key: str, module: str = "sorter", default: bool = False) -> bool:
    raw = db.get_setting(key, module, "1" if default else "0")
    return str(raw).lower() in ("1", "true", "yes", "on")


class SorterAutoWatcher(QObject):
    """Следит за папкой-источником и сортирует новые файлы."""

    sorted = Signal(bool, str)  # ok, message

    _SKIP_SUFFIXES = (".tmp", ".part", ".crdownload", ".download", ".partial")
    _DEBOUNCE_MS = 1600

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sorter = FileSorter()
        self._watcher = None
        self._watched_dir: str | None = None
        self._dest_roots: list[str] = []
        self._pending: dict[str, QTimer] = {}

    def start(self):
        from PySide6.QtCore import QFileSystemWatcher

        if self._watcher is None:
            self._watcher = QFileSystemWatcher(self)
            self._watcher.directoryChanged.connect(self._on_directory_changed)
        self.reload()

    def stop(self):
        for timer in self._pending.values():
            timer.stop()
        self._pending.clear()
        if self._watcher is not None:
            for path in list(self._watcher.directories()):
                self._watcher.removePath(path)
        self._watched_dir = None

    def reload(self):
        if self._watcher is None:
            return
        self.stop()
        if not _setting_bool("sorter_auto_enabled", "sorter", False):
            print("[sorter_auto] disabled")
            return

        src = self._source_folder()
        if not src:
            print("[sorter_auto] no valid source folder (set in sorter settings)")
            return

        self._refresh_destinations()
        src_abs = os.path.abspath(src)
        self._watcher.addPath(src_abs)
        self._watched_dir = src_abs
        print(f"[sorter_auto] watching {src_abs}")

    def _refresh_destinations(self):
        self._dest_roots = []
        for rule in self._sorter.rm.load():
            folder = rule.get("folder")
            if folder:
                self._dest_roots.append(os.path.abspath(folder))

    def _is_enabled(self) -> bool:
        return _setting_bool("sorter_auto_enabled", "sorter", False)

    @staticmethod
    def _source_folder() -> str | None:
        """Только папка-входящие из настроек сортировщика (не весь диск)."""
        path = get_source_folder()
        if not path or not os.path.isdir(path):
            return None
        return os.path.abspath(path)

    def _is_in_source_folder(self, file_path: str) -> bool:
        if not self._watched_dir:
            return False
        abs_path = os.path.abspath(file_path)
        return os.path.normcase(os.path.dirname(abs_path)) == os.path.normcase(
            self._watched_dir
        )

    def _on_directory_changed(self, directory: str):
        if not self._is_enabled() or not self._watched_dir:
            return
        if os.path.normcase(os.path.abspath(directory)) != os.path.normcase(
            self._watched_dir
        ):
            return
        try:
            names = os.listdir(directory)
        except OSError:
            return
        for name in names:
            full = os.path.join(directory, name)
            if os.path.isfile(full):
                self._schedule(full)

    def _schedule(self, file_path: str):
        if self._should_skip(file_path):
            return

        abs_path = os.path.abspath(file_path)
        old = self._pending.pop(abs_path, None)
        if old is not None:
            old.stop()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self._DEBOUNCE_MS)
        timer.timeout.connect(lambda p=abs_path: self._process(p))
        self._pending[abs_path] = timer
        timer.start()

    def _should_skip(self, file_path: str) -> bool:
        if not os.path.isfile(file_path):
            return True

        name = os.path.basename(file_path)
        lower = name.lower()
        if name.startswith(".") or name.startswith("~"):
            return True
        if lower.endswith(self._SKIP_SUFFIXES):
            return True

        abs_path = os.path.abspath(file_path)
        for dest in self._dest_roots:
            if abs_path == dest or abs_path.startswith(dest + os.sep):
                return True

        if not self._is_in_source_folder(abs_path):
            return True

        return False

    def _process(self, file_path: str):
        self._pending.pop(file_path, None)
        if not self._is_enabled() or self._should_skip(file_path):
            return

        self._refresh_destinations()
        ok, msg = self._sorter.sort_file(file_path, trigger="auto")
        if ok:
            print(f"[sorter_auto] {msg}")
        self.sorted.emit(ok, f"[авто] {msg}" if ok else f"[авто] {msg}")


_instance: SorterAutoWatcher | None = None


def get_auto_watcher() -> SorterAutoWatcher:
    global _instance
    if _instance is None:
        _instance = SorterAutoWatcher()
    return _instance
