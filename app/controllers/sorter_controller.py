from app.features.file_sorter.sorter import FileSorter


class SorterController:
    def __init__(self, view):
        self.view   = view
        self.sorter = FileSorter()

        view.sort_files_requested.connect(self._on_sort_files)
        view.sort_folder_requested.connect(self._on_sort_folder)
        print(f"[sorter_ctrl] initialized, sorter={self.sorter}")

    def _on_sort_files(self, paths: list):
        print(f"[sorter_ctrl] sort_files called: {paths}")
        results = [self.sorter.sort_file(p) for p in paths]
        print(f"[sorter_ctrl] results: {results}")
        self.view.show_results(results)

    def _on_sort_folder(self, folder: str):
        print(f"[sorter_ctrl] sort_folder called: {folder}")
        results = self.sorter.sort_folder(folder)
        print(f"[sorter_ctrl] results: {results}")
        self.view.show_results(results)