"""
Контроллер модуля AutoSort в EdgeTools.

Принимает запросы из UI (файлы или папка), запускает сортировку и возвращает результат во view.
"""
from app.features.file_sorter.core.sorter import FileSorter
from app.features.file_sorter.core.rules import RulesManager


class SorterController:
    """Связка между SorterView и движком FileSorter."""

    def __init__(self, view):
        """
        Args:
            view: SorterView — источник сигналов sort_files_requested / sort_folder_requested.
        """
        self.view   = view
        self.sorter = FileSorter()

        view.sort_files_requested.connect(self._on_sort_files)
        view.sort_folder_requested.connect(self._on_sort_folder)
        print(f"[sorter_ctrl] initialized, sorter={self.sorter}")

    def _on_sort_files(self, paths: list):
        """Сортировка списка файлов по правилам RulesManager."""
        print(f"[sorter_ctrl] sort_files called: {paths}")
        results = [self.sorter.sort_file(p) for p in paths]
        print(f"[sorter_ctrl] results: {results}")
        self.view.show_results(results)

    def _on_sort_folder(self, folder: str):
        """Рекурсивная сортировка всех файлов в указанной папке."""
        print(f"[sorter_ctrl] sort_folder called: {folder}")
        results = self.sorter.sort_folder(folder)
        print(f"[sorter_ctrl] results: {results}")
        self.view.show_results(results)