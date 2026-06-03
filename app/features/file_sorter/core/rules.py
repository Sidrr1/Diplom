"""Правила сортировки — SQLite (sorter_rules)."""
from app.core.database import db


class RulesManager:
    def load(self) -> list:
        return db.get_sorter_rules()

    def add(self, folder: str, rule_type: str, patterns: list):
        db.add_sorter_rule(folder, rule_type, patterns)

    def delete(self, index: int):
        db.delete_sorter_rule_by_index(index)
