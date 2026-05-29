from typing import Any


class RuleEngine:
    def __init__(self, rules: dict):
        self.rules = rules
        self.guideline_source = rules.get("guideline_source", "")
        self.version = rules.get("version", "unknown")

    def evaluate(self, patient_data: dict[str, Any], category: str | None = None) -> list[dict]:
        matches: list[dict] = []
        rule_groups = self.rules.get("rules", {})
        for cat_name, cat_rules in rule_groups.items():
            if category and cat_name != category:
                continue
            for rule in cat_rules:
                if self._match_rule(rule, patient_data):
                    matches.append(rule)
        return matches

    def _match_rule(self, rule: dict, patient_data: dict[str, Any]) -> bool:
        conditions = rule.get("conditions", [])
        if not conditions:
            return False
        for cond in conditions:
            field = cond["field"]
            operator = cond["operator"]
            target = cond["value"]
            actual = patient_data.get(field)
            if actual is None:
                return False
            if not self._evaluate_condition(actual, operator, target):
                return False
        return True

    def _evaluate_condition(self, actual: Any, operator: str, target: Any) -> bool:
        ops = {
            "eq": lambda a, t: a == t,
            "neq": lambda a, t: a != t,
            "gt": lambda a, t: a > t,
            "gte": lambda a, t: a >= t,
            "lt": lambda a, t: a < t,
            "lte": lambda a, t: a <= t,
        }
        op_fn = ops.get(operator)
        if op_fn is None:
            raise ValueError(f"Unknown operator: {operator}")
        return op_fn(actual, target)

    def get_alert_severity(self, alert_id: str) -> str:
        for cat_rules in self.rules.get("rules", {}).values():
            for rule in cat_rules:
                if rule["id"] == alert_id:
                    return rule.get("severity", "info")
        return "info"
