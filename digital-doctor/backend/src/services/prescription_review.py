"""Comprehensive prescription review combining guideline concordance,
drug interaction checks, renal/hepatic dosing, and contraindication screening.
"""

from src.services.drug_checker import DrugChecker


class PrescriptionReviewer:
    """Orchestrates a multi-step prescription review for T2DM patients."""

    def __init__(self, drug_checker: DrugChecker):
        self.checker = drug_checker

    def review_prescription(
        self,
        diagnosis: str,
        medications: list[dict],
        patient_data: dict,
        lab_results: dict,
    ) -> dict:
        """Run a comprehensive prescription review.

        Parameters
        ----------
        diagnosis : str
            Primary diagnosis (e.g. "type2_diabetes", "type2_diabetes_newly_diagnosed")
        medications : list[dict]
            Each entry: {"name": str, "dose": str, "frequency": str}
        patient_data : dict
            Keys: age, gender, conditions (list[str]), allergies (list[str])
        lab_results : dict
            Keys: egfr (float), alt (float), ast (float), hba1c (float)

        Returns
        -------
        dict with keys: overall_rating, issues, summary
        """
        drug_names = [m["name"] for m in medications]
        conditions = patient_data.get("conditions", [])

        issues: list[dict] = []

        # 1. Guideline concordance
        issues.extend(self._check_guideline_concordance(diagnosis, medications, lab_results))

        # 2. Drug-drug interactions
        interactions = self.checker.check_interactions(drug_names)
        for ix in interactions:
            issues.append({
                "severity": ix["severity"],
                "category": "drug_interaction",
                "description": f"{ix['drug_a']} + {ix['drug_b']}: {ix['mechanism']}",
                "recommendation": ix["recommendation"],
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §6",
            })

        # 3. Renal/Hepatic dosing
        egfr = lab_results.get("egfr")
        if egfr is not None:
            renals = self.checker.check_renal_dosing(drug_names, egfr)
            for rn in renals:
                if rn.get("adjustment_needed"):
                    issues.append({
                        "severity": "major" if "禁用" in rn.get("rationale", "") else "moderate",
                        "category": "renal_dosing",
                        "description": f"{rn['drug']}: eGFR={egfr} — {rn['rationale']}",
                        "recommendation": f"推荐方案: {rn['recommended_dose']}",
                        "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.3",
                    })

        alt_val = lab_results.get("alt")
        if alt_val is not None and alt_val > 120:
            for idx, drug_entry in enumerate(
                self.checker._resolve_list(drug_names)
            ):
                hw = drug_entry.get("hepatic_warning", "")
                if "禁用" in hw or "停用" in hw:
                    issues.append({
                        "severity": "major",
                        "category": "hepatic_dosing",
                        "description": f"{drug_names[idx]}: ALT={alt_val} U/L — {hw}",
                        "recommendation": f"ALT显著升高，评估{drug_names[idx]}是否继续使用",
                        "guideline_ref": "中国2型糖尿病防治指南(2024版) §6",
                    })

        # 4. Contraindication check
        contras = self.checker.check_contraindications(drug_names, conditions)
        for c in contras:
            issues.append({
                "severity": "contraindicated",
                "category": "contraindication",
                "description": f"{c['drug']}: {c['contraindication_detail']} (患者存在 {c['condition']})",
                "recommendation": c["recommendation"],
                "guideline_ref": c.get("guideline_ref", "中国2型糖尿病防治指南(2024版)"),
            })

        overall = self._calc_rating(issues)
        summary = self._build_summary(overall, issues, diagnosis)

        return {
            "overall_rating": overall,
            "issues": issues,
            "summary": summary,
            "diagnosis": diagnosis,
            "medication_count": len(medications),
            "issue_count": len(issues),
        }

    # ── private helpers ─────────────────────────────────────────────────────────

    def _check_guideline_concordance(
        self, diagnosis: str, medications: list[dict], lab_results: dict
    ) -> list[dict]:
        issues: list[dict] = []
        drug_names = [m["name"].lower() for m in medications]
        drug_names_set = set(drug_names)
        hba1c = lab_results.get("hba1c")
        egfr = lab_results.get("egfr")

        # Check 1: Newly-diagnosed T2DM should have metformin unless contraindicated
        if "newly_diagnosed" in diagnosis:
            has_metformin = any(
                "metformin" in dn or "二甲双胍" in dn for dn in drug_names
            )
            if not has_metformin and (egfr is None or egfr >= 45):
                issues.append({
                    "severity": "moderate",
                    "category": "guideline_concordance",
                    "description": "新诊断2型糖尿病：未包含二甲双胍（一线治疗）",
                    "recommendation": "如无禁忌证(eGFR>=45, 无严重肝功能不全)，建议起始二甲双胍500mg bid",
                    "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.3",
                })

        # Check 2: HbA1c not at target, check if combination therapy is in place
        if hba1c is not None and hba1c >= 7.0 and len(medications) < 2:
            issues.append({
                "severity": "moderate",
                "category": "guideline_concordance",
                "description": f"HbA1c={hba1c}%, 未达标(目标<7.0%)，目前仅1种降糖药",
                "recommendation": "如HbA1c持续不达标>3个月，建议联合第二种药物(SGLT-2i/DPP-4i/GLP-1RA/磺脲类)",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.5",
            })

        # Check 3: HbA1c very high, consider insulin
        if hba1c is not None and hba1c >= 9.0:
            has_insulin = any(
                "insulin" in dn or "胰岛素" in dn for dn in drug_names
            )
            if not has_insulin:
                issues.append({
                    "severity": "major",
                    "category": "guideline_concordance",
                    "description": f"HbA1c={hba1c}% >= 9.0%，血糖水平较高",
                    "recommendation": "指南推荐HbA1c>=9.0%可考虑起始胰岛素治疗",
                    "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.8",
                })

        # Check 4: Sulfonylurea + insulin combination high risk
        has_sulfonylurea = any(
            "glimepiride" in dn or "glipizide" in dn or "glyburide" in dn
            or "gliclazide" in dn or "格列美脲" in dn or "格列吡嗪" in dn
            or "格列本脲" in dn or "格列齐特" in dn
            for dn in drug_names
        )
        has_insulin = any(
            "insulin" in dn or "胰岛素" in dn for dn in drug_names
        )
        if has_sulfonylurea and has_insulin:
            issues.append({
                "severity": "major",
                "category": "guideline_concordance",
                "description": "磺脲类+胰岛素联合：低血糖风险显著增加",
                "recommendation": "起始胰岛素后通常应停用或大幅减少磺脲类剂量(如减量50%以上)，加强血糖监测",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.4, §6.8",
            })

        # Check 5: Rosiglitazone + insulin contraindicated
        has_rosiglitazone = any(
            "rosiglitazone" in dn or "罗格列酮" in dn for dn in drug_names
        )
        if has_rosiglitazone and has_insulin:
            issues.append({
                "severity": "contraindicated",
                "category": "guideline_concordance",
                "description": "罗格列酮+胰岛素：显著增加心衰和心肌缺血风险，中国和欧盟均禁止联用",
                "recommendation": "立即停用其中一种药物，选用其他联合方案",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.9; EMA 2010",
            })

        # Check 6: AGI + insulin — patient education for hypoglycemia
        has_agi = any(
            "acarbose" in dn or "阿卡波糖" in dn or "voglibose" in dn
            or "伏格列波糖" in dn or "miglitol" in dn or "米格列醇" in dn
            for dn in drug_names
        )
        if has_agi and has_insulin:
            issues.append({
                "severity": "moderate",
                "category": "guideline_concordance",
                "description": "α-糖苷酶抑制剂+胰岛素：低血糖时须口服葡萄糖纠正",
                "recommendation": "教育患者：发生低血糖时服用葡萄糖片/糖水，蔗糖/果汁无效",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.10",
            })

        return issues

    def _calc_rating(self, issues: list[dict]) -> str:
        has_contraindicated = any(i.get("severity") == "contraindicated" for i in issues)
        has_major = any(i.get("severity") == "major" for i in issues)
        has_moderate = any(i.get("severity") == "moderate" for i in issues)

        if has_contraindicated:
            return "unsafe"
        if has_major:
            return "caution"
        if has_moderate:
            return "caution"
        return "safe"

    def _build_summary(self, overall: str, issues: list[dict], diagnosis: str) -> str:
        if overall == "safe":
            return f"处方审核通过：未发现严重用药问题，治疗方案符合指南推荐。共{len(issues)}条提示。"
        elif overall == "caution":
            sev_counts = {}
            for i in issues:
                sev_counts[i.get("severity", "minor")] = sev_counts.get(i.get("severity", "minor"), 0) + 1
            parts = [f"{sev}: {cnt}条" for sev, cnt in sev_counts.items()]
            return f"处方存在用药风险(需关注)：共{len(issues)}条问题（{'; '.join(parts)}）。建议调整后再确认。"
        else:
            return f"处方存在禁忌用药！共{len(issues)}条问题，含禁忌联用，必须修改处方。"
