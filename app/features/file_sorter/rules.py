import os
import json
from app.core.config import load, save


RULES_PATH = os.path.join(
    os.path.expanduser("~"), "AppData", "Roaming", "EdgeTools", "rules.json"
)


class RulesManager:
    def __init__(self):
        os.makedirs(os.path.dirname(RULES_PATH), exist_ok=True)
        if not os.path.exists(RULES_PATH):
            self._write([])

    def load(self) -> list:
        try:
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def add(self, folder: str, rule_type: str, patterns: list):
        rules = self.load()
        rules.append({"type": rule_type, "patterns": patterns, "folder": folder})
        self._write(rules)

    def delete(self, index: int):
        rules = self.load()
        if 0 <= index < len(rules):
            rules.pop(index)
            self._write(rules)

    def _write(self, rules: list):
        with open(RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)