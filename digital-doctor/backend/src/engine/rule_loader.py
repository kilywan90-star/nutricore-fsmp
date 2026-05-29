import json
from pathlib import Path
from datetime import datetime


class RuleLoader:
    def __init__(self, rules_dir: str | None = None):
        if rules_dir is None:
            rules_dir = str(Path(__file__).parent / "rules")
        self.rules_dir = Path(rules_dir)

    def load(self, rule_set_name: str) -> dict:
        file_path = self.rules_dir / f"{rule_set_name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Rule set not found: {file_path}")
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def list_versions(self, rule_set_base: str) -> list[str]:
        versions = []
        for f in self.rules_dir.glob(f"{rule_set_base}_v*.json"):
            versions.append(f.stem)
        return sorted(versions)

    def get_effective_date(self, rules: dict) -> datetime:
        return datetime.fromisoformat(rules.get("effective_date", "2000-01-01"))
