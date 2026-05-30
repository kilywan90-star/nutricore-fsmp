"""Drug interaction checker, renal dosing, and contraindication verifier.

Loads drug data from `engine/rules/drug_database.json` and provides three
inspection functions used by the prescription review pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.services.pregnancy_checker import check_pregnancy_safety, PregnancyStatus
from src.services.organ_assessment import (
    OrganAssessment, LiverFunction, RenalFunction,
    OrganIssue as OrganDosingIssue,
)


# ── Result dataclasses ─────────────────────────────────────────────────────

@dataclass
class AllergyIssue:
    drug: str
    allergy_substance: str
    severity: str
    message: str
    recommendation: str


@dataclass
class PregnancyIssueResult:
    drug: str
    category: str
    severity: str
    message: str
    recommendation: str


@dataclass
class ComprehensiveCheckResult:
    overall_rating: str
    drug_interactions: list[dict] = field(default_factory=list)
    allergy_issues: list[dict] = field(default_factory=list)
    pregnancy_issues: list[dict] = field(default_factory=list)
    organ_issues: list[dict] = field(default_factory=list)
    contraindications: list[dict] = field(default_factory=list)
    summary: str = ""


# ── Allergy cross-reference table ──────────────────────────────────────────

_ALLERGY_DRUG_MAP: dict[str, list[str]] = {
    "青霉素": ["Penicillin", "Amoxicillin", "Amoxicillin-Clavulanate",
                "Ampicillin", "Piperacillin", "Ticarcillin"],
    "penicillin": ["Penicillin", "Amoxicillin", "Amoxicillin-Clavulanate",
                   "Ampicillin", "Piperacillin", "Ticarcillin"],
    "头孢菌素": ["Cephalexin", "Cefazolin", "Ceftriaxone", "Cefuroxime",
                 "Cefotaxime", "Cefepime"],
    "cephalosporin": ["Cephalexin", "Cefazolin", "Ceftriaxone", "Cefuroxime"],
    "磺胺": ["Sulfamethoxazole", "Trimethoprim-Sulfamethoxazole",
             "Sulfadiazine", "Sulfasalazine", "Cotrimoxazole"],
    "sulfa": ["Sulfamethoxazole", "Trimethoprim-Sulfamethoxazole",
              "Sulfadiazine", "Sulfasalazine", "Cotrimoxazole"],
    "磺胺类": ["Sulfamethoxazole", "Trimethoprim-Sulfamethoxazole",
               "Sulfadiazine", "Sulfasalazine"],
    "阿司匹林": ["Aspirin", "Ibuprofen", "Naproxen", "Diclofenac", "Celecoxib"],
    "aspirin": ["Aspirin", "Ibuprofen", "Naproxen", "Diclofenac"],
    "NSAID": ["Aspirin", "Ibuprofen", "Naproxen", "Diclofenac", "Celecoxib"],
    "nsaid": ["Aspirin", "Ibuprofen", "Naproxen", "Diclofenac", "Celecoxib"],
    "二甲双胍": ["Metformin"],
    "metformin": ["Metformin"],
    "胰岛素": ["Insulin Glargine", "Insulin Aspart", "Insulin Lispro",
               "Insulin Detemir", "NPH Insulin", "Regular Insulin"],
    "insulin": ["Insulin Glargine", "Insulin Aspart", "Insulin Lispro",
                "Insulin Detemir", "NPH Insulin", "Regular Insulin"],
    "碘": ["Iodinated contrast"],
}


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

    # ── New: allergy / pregnancy / organ-dosing / comprehensive ───────────────

    def check_allergy_cross_reference(
        self, medications: list[str], patient_allergies: list[str]
    ) -> list[dict]:
        """Check whether any prescribed medication cross-reacts with patient allergies.

        Returns list of dicts: drug, allergy_substance, severity, message, recommendation
        """
        results: list[dict] = []

        for med in medications:
            med_lower = med.lower()
            for allergy in patient_allergies:
                allergy_lower = allergy.lower()

                # Check direct name match (patient allergic to the exact drug)
                if allergy_lower in med_lower or med_lower in allergy_lower:
                    results.append({
                        "drug": med,
                        "allergy_substance": allergy,
                        "severity": "blocked",
                        "message": f"患者对 {allergy} 过敏，{med} 属于同类别药物",
                        "recommendation": f"禁止使用 {med}，选择非交叉过敏替代药物",
                    })
                    continue

                # Check cross-reactivity map
                crossed_drugs = _ALLERGY_DRUG_MAP.get(allergy_lower, [])
                for crossed in crossed_drugs:
                    if crossed.lower() in med_lower or med_lower in crossed.lower():
                        results.append({
                            "drug": med,
                            "allergy_substance": allergy,
                            "severity": "blocked",
                            "message": f"患者对 {allergy} 过敏，{med} 与 {crossed} 存在交叉过敏风险",
                            "recommendation": f"禁止使用 {med}，选择其他类别替代药物",
                        })
                        break

        return results

    def check_pregnancy(
        self,
        medications: list[str],
        pregnancy_status: str = "unknown",
        patient_age: int = 0,
        patient_gender: str = "",
    ) -> list[dict]:
        """Check pregnancy safety for all medications.

        Delegates to pregnancy_checker module.
        """
        try:
            status = PregnancyStatus(pregnancy_status)
        except ValueError:
            status = PregnancyStatus.UNKNOWN

        issues = check_pregnancy_safety(medications, status, patient_age, patient_gender)
        return [
            {
                "drug": iss.drug,
                "category": iss.category,
                "severity": iss.severity,
                "message": iss.message,
                "recommendation": iss.recommendation,
            }
            for iss in issues
        ]

    def check_organ_dosing(
        self,
        medications: list[str],
        liver_func: dict | None = None,
        renal_func: dict | None = None,
    ) -> list[dict]:
        """Combined liver-kidney dose adjustment check for all medications.

        Parameters
        ----------
        liver_func : dict | None
            Keys: alt, ast, tbil, albumin, inr, has_ascites, has_encephalopathy
        renal_func : dict | None
            Keys: egfr, creatinine
        """
        lf = None
        rf = None

        if liver_func:
            lf = LiverFunction(
                alt=liver_func.get("alt", 0),
                ast=liver_func.get("ast", 0),
                tbil=liver_func.get("tbil", 0.5),
                albumin=liver_func.get("albumin", 4.0),
                inr=liver_func.get("inr", 1.0),
                has_ascites=liver_func.get("has_ascites", False),
                has_encephalopathy=liver_func.get("has_encephalopathy", False),
            )

        if renal_func:
            rf = RenalFunction(
                egfr=renal_func.get("egfr", 90),
                creatinine=renal_func.get("creatinine"),
            )

        assessment = OrganAssessment(lf, rf)
        organ_issues = assessment.assess_medications(medications)

        return [
            {
                "drug": iss.drug,
                "severity": iss.severity,
                "category": iss.category,
                "message": iss.message,
                "recommendation": iss.recommendation,
                "guideline_ref": iss.guideline_ref,
            }
            for iss in organ_issues
        ]

    def comprehensive_safety_check(
        self,
        medications: list[str],
        patient_data: dict,
        lab_results: dict | None = None,
    ) -> ComprehensiveCheckResult:
        """Run all safety checks and return a single aggregated result.

        Parameters
        ----------
        medications : list[str]
            Drug names.
        patient_data : dict
            Keys: conditions (list[str]), allergies (list[str]),
            pregnancy_status (str), age (int), gender (str).
        lab_results : dict | None
            Keys: egfr, alt, ast, tbil, albumin, hba1c, inr,
            has_ascites, has_encephalopathy.

        Returns
        -------
        ComprehensiveCheckResult
        """
        lab = lab_results or {}
        conditions = patient_data.get("conditions", [])
        allergies_list = patient_data.get("allergies", [])
        pregnancy_status = patient_data.get("pregnancy_status", "not_pregnant")
        patient_age = patient_data.get("age", 0)
        patient_gender = patient_data.get("gender", "")

        all_interactions: list[dict] = []
        all_allergy: list[dict] = []
        all_pregnancy: list[dict] = []
        all_organ: list[dict] = []
        all_contra: list[dict] = []

        # 1. Drug-drug interactions
        all_interactions = self.check_interactions(medications)

        # 2. Allergy cross-reference
        if allergies_list:
            all_allergy = self.check_allergy_cross_reference(medications, allergies_list)

        # 3. Pregnancy safety
        all_pregnancy = self.check_pregnancy(
            medications, pregnancy_status, patient_age, patient_gender
        )

        # 4. Organ dosing (kidney + liver)
        liver_input = None
        if any(k in lab for k in ("alt", "ast", "tbil", "albumin")):
            liver_input = {
                "alt": lab.get("alt", 25),
                "ast": lab.get("ast", 25),
                "tbil": lab.get("tbil", 0.5),
                "albumin": lab.get("albumin", 4.0),
                "inr": lab.get("inr", 1.0),
                "has_ascites": lab.get("has_ascites", False),
                "has_encephalopathy": lab.get("has_encephalopathy", False),
            }

        renal_input = None
        if "egfr" in lab:
            renal_input = {"egfr": lab["egfr"], "creatinine": lab.get("creatinine")}

        if liver_input or renal_input:
            all_organ = self.check_organ_dosing(medications, liver_input, renal_input)

        # 5. Contraindications
        all_contra = self.check_contraindications(medications, conditions)

        # Aggregate severity
        has_blocked = False
        has_major = False
        has_moderate = False

        for ix in all_interactions:
            sev = ix.get("severity", "")
            if sev in ("contraindicated", "major"):
                has_blocked = True
            elif sev == "moderate":
                has_major = True
            elif sev == "minor":
                has_moderate = True

        for ax in all_allergy:
            if ax.get("severity") == "blocked":
                has_blocked = True

        for px in all_pregnancy:
            if px.get("severity") == "blocked":
                has_blocked = True
            elif px.get("severity") == "warning":
                has_major = True

        for ox in all_organ:
            if ox.get("severity") == "blocked":
                has_blocked = True
            elif ox.get("severity") == "major":
                has_major = True
            elif ox.get("severity") == "moderate":
                has_moderate = True

        for cx in all_contra:
            has_blocked = True

        if has_blocked:
            rating = "unsafe"
        elif has_major:
            rating = "caution"
        elif has_moderate:
            rating = "caution"
        else:
            rating = "safe"

        total_issues = (
            len(all_interactions) + len(all_allergy) + len(all_pregnancy)
            + len(all_organ) + len(all_contra)
        )

        if rating == "safe":
            summary = f"综合安全评估通过：未发现严重用药问题。共{total_issues}条提示。"
        elif rating == "caution":
            summary = f"综合安全评估需关注：共发现{total_issues}条问题，建议调整后再确认。"
        else:
            summary = f"综合安全评估禁忌！共{total_issues}条问题，含禁忌或严重风险项，必须修改处方。"

        return ComprehensiveCheckResult(
            overall_rating=rating,
            drug_interactions=all_interactions,
            allergy_issues=all_allergy,
            pregnancy_issues=all_pregnancy,
            organ_issues=all_organ,
            contraindications=all_contra,
            summary=summary,
        )

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
