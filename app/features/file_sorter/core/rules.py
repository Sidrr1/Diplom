"""Правила сортировки — SQLite (sorter_rules)."""
from app.core.database import db
from app.core.paths import normalize_path


class RulesManager:
    """CRUD-обёртка над правилами сортировки в SQLite."""

    def load(self) -> list:
        """Загрузить все правила из БД."""
        return db.get_sorter_rules()

    def add(self, folder: str, rule_type: str, patterns: list):
        """Добавить правило: extension или keyword."""
        db.add_sorter_rule(normalize_path(folder), rule_type, patterns)

    def delete(self, index: int):
        """Удалить правило по индексу в таблице."""
        db.delete_sorter_rule_by_index(index)
