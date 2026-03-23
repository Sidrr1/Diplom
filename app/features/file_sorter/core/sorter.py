import os
import shutil
from app.features.file_sorter.core.rules import RulesManager


class FileSorter:
    def __init__(self):
        self.rm = RulesManager()

    # ── Публичные методы ─────────────────────────────────────────────────

    def sort_file(self, file_path: str) -> tuple[bool, str]:
        if not os.path.isfile(file_path):
            return False, f"Не файл: {file_path}"
        target = self._find_target(file_path)
        if not target:
            ext = self._get_ext(file_path)
            return False, f"Нет правила для .{ext}"
        return self._move_file(file_path, target)

    def sort_folder(self, folder_path: str) -> list[tuple[bool, str]]:
        if not os.path.isdir(folder_path):
            return [(False, "Папка не найдена")]
        return [
            self.sort_file(os.path.join(folder_path, name))
            for name in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, name))
        ]

    # ── Приватные методы ─────────────────────────────────────────────────

    def _get_ext(self, file_path: str) -> str:
        """Расширение файла без точки, нижний регистр."""
        return os.path.splitext(file_path)[1].lower().lstrip(".")

    def _normalize_rules(self, rules: list) -> list:
        """Нормализует паттерны — убирает точки и пробелы, нижний регистр."""
        for r in rules:
            if r["type"] == "extension":
                r["patterns"] = [p.strip().lower().lstrip(".") for p in r["patterns"]]
            else:
                r["patterns"] = [p.strip().lower() for p in r["patterns"]]
        return rules

    def _find_target(self, file_path: str) -> str | None:
        """Ищет папку назначения. Keyword важнее extension."""
        filename_lower = os.path.basename(file_path).lower()
        ext            = self._get_ext(file_path)
        rules          = self._normalize_rules(self.rm.load())

        # Сначала только ключевые слова
        for r in rules:
            if r["type"] == "keyword":
                if any(p in filename_lower for p in r["patterns"]):
                    return r["folder"]

        # Потом расширения
        for r in rules:
            if r["type"] == "extension":
                if ext in r["patterns"]:
                    return r["folder"]

        return None

    def _move_file(self, file_path: str, target: str) -> tuple[bool, str]:
        """Перемещает файл в папку назначения. Не переименовывает если уже там."""
        filename = os.path.basename(file_path)
        dest     = os.path.join(target, filename)

        # Файл уже в нужной папке
        if os.path.abspath(file_path) == os.path.abspath(dest):
            return False, f"Уже в нужной папке: {filename}"

        try:
            os.makedirs(target, exist_ok=True)

            # Разрешаем конфликт имён
            if os.path.exists(dest):
                base, ex = os.path.splitext(filename)
                i = 1
                while os.path.exists(dest):
                    dest = os.path.join(target, f"{base}_{i}{ex}")
                    i += 1

            shutil.move(file_path, dest)
            return True, f"{filename} → {os.path.basename(target)}"
        except Exception as e:
            return False, f"Ошибка: {e}"