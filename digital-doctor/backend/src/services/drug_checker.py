"""Drug interaction checker, renal dosing, and contraindication verifier.

Loads drug data from `engine/rules/drug_database.json` and provides three
inspection functions used by the prescription review pipeline.
"""

from pathlib import Path
from typing import Optional


class DrugChecker:
    """Stateless drug safety checker backed by JSON knowledge base."""

    def __init__(self, db_path: Optional[str] = None):
        import json

        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "engine" / "rules" / "drug_database.json")

        with open(db_path, encoding="utf-8") as f:
            self.db = json.load(f)

        self._lookup: dict[str, dict] = {}
        for drug in self.db["drugs"]:
            self._lookup[drug["generic_name_en"].lower()] = drug
            self._lookup[drug["generic_name"].lower()] = drug
            for bn in drug.get("brand_names", []):
                self._lookup[bn.lower()] = drug

        self._matrix = {}
        for entry in self.db.get("drug_interactions_matrix", []):
            key = self._pair_key(entry["drug_a"], entry["drug_b"])
            self._matrix[key] = entry

    # ── public API ──────────────────────────────────────────────────────────────

    def check_interactions(self, medications: list[str]) -> list[dict]:
        """Check all unique pairs of ``medications`` for known interactions.

        Returns a list of dicts, each containing:
            drug_a, drug_b, severity, mechanism, recommendation
        """
        results: list[dict] = []
        resolved = self._resolve_list(medications)
        n = len(resolved)

        for i in range(n):
            for j in range(i + 1, n):
                results.extend(self._find_interactions(resolved[i], resolved[j], medications[i], medications[j]))

        return results

    def check_renal_dosing(self, medications: list[str], egfr: float) -> list[dict]:
        """Check whether each drug's dose needs adjustment for the given *egfr* (mL/min/1.73m²).

        Returns a list of dicts with:
            drug, current_dose, recommended_dose, adjustment_needed, rationale
        """
        results: list[dict] = []
        resolved = self._resolve_list(medications)

        for idx, drug_entry in enumerate(resolved):
            adj = drug_entry.get("renal_adjustment", [])
            dose = self._format_dosage(drug_entry)
            rec_dose = dose
            adjustment = False
            rationale = "在正常范围内无需调整"

            for tier in adj:
                lo = tier["egfr_min"]
                hi = tier.get("egfr_max")
                if egfr >= lo and (hi is None or egfr < hi):
                    rec_dose = tier["dose"]
                    if "无需调整" not in tier["dose"] and "标准" not in tier["dose"]:
                        adjustment = True
                    rationale = tier["dose"]
                    break

            results.append({
                "drug": medications[idx],
                "generic_name": drug_entry["generic_name"],
                "current_dose": dose,
                "recommended_dose": rec_dose,
                "egfr": egfr,
                "adjustment_needed": adjustment,
                "rationale": rationale,
            })

        return results

    def check_contraindications(
        self, medications: list[str], patient_conditions: list[str]
    ) -> list[dict]:
        """Check whether any of the medications are contraindicated with
        *patient_conditions* (e.g. ["heart_failure", "egfr<30"]).

        Returns a list of dicts with:
            drug, condition, contraindication_detail, severity, recommendation
        """
        results: list[dict] = []
        resolved = self._resolve_list(medications)

        for idx, drug_entry in enumerate(resolved):
            contras = drug_entry.get("contraindications", [])
            for ci in contras:
                for pc in patient_conditions:
                    if self._condition_matches(ci, pc):
                        results.append({
                            "drug": medications[idx],
                            "generic_name": drug_entry["generic_name"],
                            "condition": pc,
                            "contraindication_detail": ci,
                            "severity": "contraindicated",
                            "recommendation": f"停用{drug_entry['generic_name']}，选择替代药物",
                            "guideline_ref": drug_entry.get("guideline_ref", ""),
                        })
        return results

    def search_drugs(self, query: str) -> list[dict]:
        """Search the drug database by generic name, English name, or brand name."""
        q = query.lower().strip()
        results: list[dict] = []
        seen: set[str] = set()

        for drug in self.db["drugs"]:
            if drug["generic_name_en"].lower() in seen:
                continue
            match = (
                q in drug["generic_name"].lower()
                or q in drug["generic_name_en"].lower()
                or any(q in bn.lower() for bn in drug.get("brand_names", []))
                or q in drug["drug_class"].lower()
            )
            if match:
                seen.add(drug["generic_name_en"].lower())
                results.append(self._summarise_drug(drug))

        return results[:20]

    def get_drug(self, name: str) -> dict | None:
        """Look up a drug by generic_name, generic_name_en, or brand name."""
        key = name.lower()
        drug = self._lookup.get(key)
        if drug is None:
            return None
        return self._summarise_drug(drug)

    # ── helpers ─────────────────────────────────────────────────────────────────

    def _resolve_list(self, names: list[str]) -> list[dict]:
        resolved: list[dict] = []
        for name in names:
            key = name.lower()
            entry = self._lookup.get(key)
            if entry is not None:
                resolved.append(entry)
        return resolved

    @staticmethod
    def _pair_key(a: str, b: str) -> str:
        return f"{a}|{b}" if a <= b else f"{b}|{a}"

    def _find_interactions(
        self, drug_a: dict, drug_b: dict, name_a: str, name_b: str
    ) -> list[dict]:
        results: list[dict] = []

        # Check per-drug interaction lists
        for di in drug_a.get("drug_interactions", []):
            tgt = di["drug"].lower()
            if tgt in drug_b["generic_name"].lower() or tgt in drug_b["generic_name_en"].lower():
                results.append({
                    "drug_a": name_a,
                    "drug_b": name_b,
                    "severity": di["severity"],
                    "mechanism": di["mechanism"],
                    "recommendation": di["recommendation"],
                })

        # Check the matrix using individual drug names
        key_a = drug_a["generic_name"]
        key_b = drug_b["generic_name"]
        mat_key = self._pair_key(key_a, key_b)
        if mat_key in self._matrix:
            entry = self._matrix[mat_key]
            if not any(r["drug_a"] == name_a and r["drug_b"] == name_b for r in results):
                results.append({
                    "drug_a": name_a,
                    "drug_b": name_b,
                    "severity": entry["severity"],
                    "mechanism": entry["mechanism"],
                    "recommendation": entry["recommendation"],
                })

        # Also check matrix using drug class names (e.g. "磺脲类" for sulfonylureas)
        class_a = self.db["drug_classes"].get(drug_a["drug_class"], {}).get("name", "")
        class_b = self.db["drug_classes"].get(drug_b["drug_class"], {}).get("name", "")
        if class_a and class_b:
            class_key = self._pair_key(f"class:{class_a}", f"class:{class_b}")
        else:
            class_key = ""

        # Check class+individual combos
        for class_name in (class_a, class_b):
            if not class_name:
                continue
            # Check against matrix entries keyed by class name
            for mat_k, mat_entry in self._matrix.items():
                parts = mat_k.split("|")
                if class_name in parts and (key_a in parts or key_b in parts or class_b in parts or class_a in parts):
                    if not any(r["drug_a"] == name_a and r["drug_b"] == name_b for r in results):
                        results.append({
                            "drug_a": name_a,
                            "drug_b": name_b,
                            "severity": mat_entry["severity"],
                            "mechanism": mat_entry["mechanism"],
                            "recommendation": mat_entry["recommendation"],
                        })
                    break

        return results

    @staticmethod
    def _format_dosage(drug: dict) -> str:
        d = drug.get("dosage_range", {})
        return f"{d.get('starting', '个体化')} / 维持 {d.get('usual', '个体化')} (最大{d.get('max', '个体化')})"

    @staticmethod
    def _condition_matches(ci: str, pc: str) -> bool:
        """Loose matching between contraindication text and patient condition label.

        Uses a medical concept table so that "heart_failure", "心衰", and
        "心力衰竭" are recognised as the same underlying condition.
        """
        ci_l = ci.lower()
        pc_l = pc.lower()

        # Direct substring match
        if pc_l in ci_l:
            return True

        # Medical concept mapping: groups of synonyms that mean the same condition
        concept_groups: list[set[str]] = [
            {"心力衰竭", "心衰", "heart_failure", "心功能不全", "心功能", "cardiac_failure"},
            {"肝功能不全", "肝功能", "肝病", "liver_disease", "hepatic", "liver", "肝硬化"},
            {"酮症酸中毒", "dka", "糖尿病酮症酸中毒", "ketoacidosis"},
            {"肾衰竭", "肾衰", "renal_failure", "kidney_failure", "肾功能不全"},
            {"膀胱癌", "bladder_cancer"},
        ]

        # Check if both terms belong to the same concept group
        for group in concept_groups:
            ci_match = any(g in ci_l for g in group)
            pc_match = any(g in pc_l for g in group)
            if ci_match and pc_match:
                return True

        # eGFR numeric comparison
        if "egfr" in ci_l and "egfr" in pc_l:
            import re
            ci_nums = re.findall(r'[\d.]+', ci)
            pc_nums = re.findall(r'[\d.]+', pc)
            if ci_nums and pc_nums:
                ci_val = float(ci_nums[0])
                pc_val = float(pc_nums[0])
                if "<" in ci and "<" in pc:
                    return pc_val <= ci_val

        return False

    @staticmethod
    def _summarise_drug(drug: dict) -> dict:
        return {
            "generic_name": drug["generic_name"],
            "generic_name_en": drug["generic_name_en"],
            "drug_class": drug["drug_class"],
            "class_name": drug.get("_class_name", ""),
            "brand_names": drug.get("brand_names", []),
            "dosage_range": drug.get("dosage_range", {}),
            "renal_adjustment": drug.get("renal_adjustment", []),
            "hepatic_warning": drug.get("hepatic_warning", ""),
            "common_side_effects": drug.get("common_side_effects", []),
            "contraindications": drug.get("contraindications", []),
            "drug_interactions": drug.get("drug_interactions", []),
            "pregnancy_category": drug.get("pregnancy_category", ""),
        }


# Module-level convenience instance
_drug_checker: DrugChecker | None = None


def get_drug_checker() -> DrugChecker:
    global _drug_checker
    if _drug_checker is None:
        _drug_checker = DrugChecker()
    return _drug_checker
