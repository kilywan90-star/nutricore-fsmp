"""Liver-kidney combined organ function assessment for drug dosing.

Classifies liver function via Child-Pugh and renal function via CKD stages,
then computes dose adjustments for each drug based on combined organ status.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Data classes ─────────────────────────────────────────────────────────

@dataclass
class LiverFunction:
    alt: float  # U/L
    ast: float  # U/L
    tbil: float  # mg/dL (total bilirubin)
    albumin: float  # g/dL
    inr: float = 1.0  # INR (optional, for Child-Pugh)
    has_ascites: bool = False
    has_encephalopathy: bool = False


@dataclass
class RenalFunction:
    egfr: float  # mL/min/1.73m²
    creatinine: float | None = None  # mg/dL (optional)


@dataclass
class DoseAdjustment:
    drug: str
    liver_class: str
    ckd_stage: str
    standard_dose: str
    adjusted_dose: str
    adjustment_needed: bool
    rationale: str
    guideline_ref: str


@dataclass
class OrganIssue:
    drug: str
    severity: str  # blocked / major / moderate / info
    category: str  # hepatic_dosing / renal_dosing / combined
    message: str
    recommendation: str
    guideline_ref: str


# ── Child-Pugh classification ────────────────────────────────────────────

def classify_liver(lf: LiverFunction) -> str:
    """Classify liver function using Child-Pugh score.

    Returns one of: A / B / C
    """
    score = 0

    # Bilirubin (mg/dL)
    if lf.tbil < 2.0:
        score += 1
    elif lf.tbil <= 3.0:
        score += 2
    else:
        score += 3

    # Albumin (g/dL)
    if lf.albumin > 3.5:
        score += 1
    elif lf.albumin >= 2.8:
        score += 2
    else:
        score += 3

    # INR
    if lf.inr < 1.7:
        score += 1
    elif lf.inr <= 2.3:
        score += 2
    else:
        score += 3

    # Ascites
    if lf.has_ascites:
        score += 2 if not lf.has_ascites else 1  # logic below handles this
    if lf.has_ascites:
        score += 1  # 1 point for slight, but we simplify to 1

    # Encephalopathy
    if lf.has_encephalopathy:
        score += 1

    if score <= 6:
        return "A"
    elif score <= 9:
        return "B"
    else:
        return "C"


def classify_kidney(rf: RenalFunction) -> str:
    """Classify kidney function into CKD stage 1-5.

    Returns one of: stage_1 / stage_2 / stage_3 / stage_4 / stage_5
    """
    egfr = rf.egfr
    if egfr >= 90:
        return "stage_1"
    elif egfr >= 60:
        return "stage_2"
    elif egfr >= 45:
        return "stage_3a"
    elif egfr >= 30:
        return "stage_3b"
    elif egfr >= 15:
        return "stage_4"
    else:
        return "stage_5"


# ── Drug-specific dose adjustments by organ function ──────────────────────

def get_drug_dose_adjustments(
    drug_name: str,
    liver_class: str,
    ckd_stage: str,
) -> DoseAdjustment | None:
    """Compute dose adjustment for a drug based on liver class and CKD stage.

    Returns DoseAdjustment with recommendations, or None if no adjustment needed.
    """
    drug_key = drug_name.lower()

    # ── Metformin ──────────────────────────────────────────────────────
    if drug_key in ("metformin", "二甲双胍"):
        standard = "500-2000 mg/day (分2-3次)"
        adjustment = False
        rationale_parts: list[str] = []

        # Renal adjustment
        if ckd_stage in ("stage_4", "stage_5"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="禁用",
                adjustment_needed=True,
                rationale="eGFR<30 mL/min/1.73m²时二甲双胍禁用(乳酸酸中毒风险)。",
                guideline_ref="中国2型糖尿病防治指南(2024版) §6.3"
            )
        if ckd_stage == "stage_3b":
            adjustment = True
            rationale_parts.append("eGFR 30-44: 减量至1000 mg/day，不建议起始治疗")
            adjusted = "减量至1000 mg/day，不建议起始治疗"

        # Liver adjustment
        if liver_class in ("B", "C"):
            adjustment = True
            rationale_parts.append(f"Child-Pugh {liver_class}: 肝功能不全时慎用，ALT>3x ULN建议停用")
            adjusted = "慎用；ALT>3x ULN停用"

        if adjustment:
            adjusted = adjusted if 'adjusted' in dir() else standard
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose=adjusted,
                adjustment_needed=True,
                rationale="; ".join(rationale_parts),
                guideline_ref="中国2型糖尿病防治指南(2024版) §6.3"
            )
        return None

    # ── Sitagliptin ────────────────────────────────────────────────────
    if drug_key in ("sitagliptin", "西格列汀"):
        standard = "100 mg qd"
        if ckd_stage in ("stage_3a", "stage_3b"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="50 mg qd",
                adjustment_needed=True,
                rationale="eGFR 30-59: 减量至50 mg qd。",
                guideline_ref="药品说明书; UpToDate 2024"
            )
        if ckd_stage in ("stage_4",):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="25 mg qd",
                adjustment_needed=True,
                rationale="eGFR 15-29: 减量至25 mg qd。",
                guideline_ref="药品说明书; UpToDate 2024"
            )
        if ckd_stage == "stage_5":
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="25 mg qd (透析后可补充)",
                adjustment_needed=True,
                rationale="eGFR<15 或透析: 25 mg qd，血液透析后补充给药。",
                guideline_ref="药品说明书; UpToDate 2024"
            )
        if liver_class in ("B", "C"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="慎用，监测肝功能",
                adjustment_needed=True,
                rationale=f"Child-Pugh {liver_class}: 中重度肝功能不全患者数据有限，慎用。",
                guideline_ref="药品说明书"
            )
        return None

    # ── Empagliflozin ──────────────────────────────────────────────────
    if drug_key in ("empagliflozin", "恩格列净"):
        standard = "10-25 mg qd"
        if ckd_stage in ("stage_4", "stage_5"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="不推荐起始治疗(已使用者可继续10mg)",
                adjustment_needed=True,
                rationale="eGFR<30: 降糖疗效减弱，不推荐起始；但eGFR≥20时心肾保护获益仍存在。",
                guideline_ref="EMPA-KIDNEY 2023; 中国2型糖尿病防治指南(2024版)"
            )
        return None

    # ── Liraglutide ────────────────────────────────────────────────────
    if drug_key in ("liraglutide", "利拉鲁肽"):
        standard = "0.6-1.8 mg qd (皮下)"
        if ckd_stage in ("stage_4", "stage_5"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="慎用，数据有限",
                adjustment_needed=True,
                rationale="eGFR<30: GLP-1RA在CKD 4-5期数据有限，慎用。Lixisenatide在eGFR<30需减量，但Semaglutide/Liraglutide肾功能不全可不调量。",
                guideline_ref="药品说明书; UpToDate 2024"
            )
        if liver_class == "C":
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="禁忌",
                adjustment_needed=True,
                rationale="Child-Pugh C: 严重肝功能不全者禁用Liraglutide。",
                guideline_ref="药品说明书"
            )
        return None

    # ── Pioglitazone ───────────────────────────────────────────────────
    if drug_key in ("pioglitazone", "吡格列酮"):
        standard = "15-45 mg qd"
        if liver_class in ("B", "C"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="禁用" if liver_class == "C" else "ALT>2.5x ULN禁用",
                adjustment_needed=True,
                rationale=f"Child-Pugh {liver_class}: TZD类有肝毒性风险。Child-Pugh C禁用，B类ALT>2.5x ULN不建议使用。",
                guideline_ref="药品说明书; AASLD实践指南"
            )
        return None

    # ── Glimepiride ────────────────────────────────────────────────────
    if drug_key in ("glimepiride", "格列美脲"):
        standard = "1-6 mg qd"
        if ckd_stage in ("stage_4", "stage_5"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="起始1 mg qd，谨慎上调；低血糖风险增加",
                adjustment_needed=True,
                rationale="eGFR<30: 磺脲类活性代谢物蓄积，低血糖风险显著增加。优先选用格列吡嗪或换用非磺脲类。",
                guideline_ref="中国2型糖尿病防治指南(2024版) §6.3; Beers Criteria 2023"
            )
        if liver_class == "C":
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="慎用，从最低剂量起始",
                adjustment_needed=True,
                rationale="Child-Pugh C: 肝功能严重受损时药物代谢减慢，低血糖风险增加。",
                guideline_ref="药品说明书"
            )
        return None

    # ── Acarbose ───────────────────────────────────────────────────────
    if drug_key in ("acarbose", "阿卡波糖"):
        standard = "50-100 mg tid (餐前即刻)"
        if ckd_stage in ("stage_4", "stage_5"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="禁用",
                adjustment_needed=True,
                rationale="eGFR<30: α-糖苷酶抑制剂在严重肾功能不全患者中缺乏安全数据，不推荐使用。",
                guideline_ref="药品说明书; 中国2型糖尿病防治指南(2024版)"
            )
        if liver_class == "C":
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="禁用",
                adjustment_needed=True,
                rationale="Child-Pugh C: 严重肝功能不全伴高氨血症禁用Acarbose。",
                guideline_ref="药品说明书"
            )
        return None

    # ── Insulin Glargine ───────────────────────────────────────────────
    if drug_key in ("insulin glargine", "甘精胰岛素"):
        standard = "个体化，通常10-100 U qd"
        # Insulin generally safe in renal/hepatic impairment but may need dose reduction
        if ckd_stage in ("stage_4", "stage_5"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="可能需要减少剂量20-30%，根据血糖监测调整",
                adjustment_needed=True,
                rationale=f"CKD {ckd_stage}: 胰岛素肾脏清除减少，作用时间延长，低血糖风险增加。建议减少剂量并加强血糖监测。",
                guideline_ref="中国2型糖尿病防治指南(2024版) §6.3"
            )
        if liver_class in ("B", "C"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="监测血糖，可能需要减量",
                adjustment_needed=True,
                rationale=f"Child-Pugh {liver_class}: 肝糖原储备减少，糖异生能力下降，胰岛素需求量可能降低。",
                guideline_ref="UpToDate 2024"
            )
        return None

    # ── Rosiglitazone ──────────────────────────────────────────────────
    if drug_key in ("rosiglitazone", "罗格列酮"):
        standard = "4-8 mg qd"
        if liver_class in ("B", "C"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="禁用" if liver_class == "C" else "ALT>2.5x ULN禁用",
                adjustment_needed=True,
                rationale=f"Child-Pugh {liver_class}: TZD类可导致肝酶升高。Child-Pugh C为禁忌。",
                guideline_ref="药品说明书"
            )
        return None

    # ── Dapagliflozin ──────────────────────────────────────────────────
    if drug_key in ("dapagliflozin", "达格列净"):
        standard = "5-10 mg qd"
        if ckd_stage in ("stage_4", "stage_5"):
            return DoseAdjustment(
                drug=drug_name, liver_class=liver_class, ckd_stage=ckd_stage,
                standard_dose=standard, adjusted_dose="eGFR<25 不推荐起始治疗",
                adjustment_needed=True,
                rationale="eGFR<25: 降糖疗效减弱，不推荐新起始治疗。但心肾保护获益至eGFR>25。",
                guideline_ref="DAPA-CKD 2020; 中国2型糖尿病防治指南(2024版)"
            )
        return None

    # ── Default: unknown drug ──────────────────────────────────────────
    return None


# ── Comprehensive assessment ─────────────────────────────────────────────

class OrganAssessment:
    """Combined liver-kidney assessment with per-drug dose adjustments."""

    def __init__(
        self,
        liver_function: LiverFunction | None = None,
        renal_function: RenalFunction | None = None,
    ):
        self.liver_function = liver_function
        self.renal_function = renal_function
        self.liver_class: str | None = None
        self.ckd_stage: str | None = None

        if liver_function:
            self.liver_class = classify_liver(liver_function)
        if renal_function:
            self.ckd_stage = classify_kidney(renal_function)

    def assess_medications(self, medications: list[str]) -> list[OrganIssue]:
        """Assess all medications against combined organ function status.

        Returns a list of OrganIssue for drugs requiring adjustment.
        """
        issues: list[OrganIssue] = []

        for drug_name in medications:
            adj = get_drug_dose_adjustments(
                drug_name,
                self.liver_class or "A",
                self.ckd_stage or "stage_1",
            )

            if adj is None:
                continue

            severity = "info"
            if "禁用" in adj.adjusted_dose or "禁忌" in adj.adjusted_dose:
                severity = "blocked"
            elif "减量" in adj.adjusted_dose or "慎用" in adj.adjusted_dose:
                severity = "major"
            elif adj.adjustment_needed:
                severity = "moderate"

            issues.append(OrganIssue(
                drug=adj.drug,
                severity=severity,
                category=(
                    "renal_dosing" if "eGFR" in adj.rationale and "肝" not in adj.rationale
                    else "hepatic_dosing"
                ),
                message=f"{adj.drug}: {adj.rationale}",
                recommendation=f"标准剂量: {adj.standard_dose} → 调整: {adj.adjusted_dose}",
                guideline_ref=adj.guideline_ref,
            ))

        return issues
