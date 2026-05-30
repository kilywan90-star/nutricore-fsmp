"""Pregnancy safety checker — evaluates medication risk against pregnancy status.

Drug pregnancy categories based on FDA legacy categories A/B/C/D/X,
supplemented with NMPA 药品说明书 and UpToDate evidence.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PregnancyStatus(str, Enum):
    PREGNANT = "pregnant"
    NOT_PREGNANT = "not_pregnant"
    UNKNOWN = "unknown"


@dataclass
class PregnancyIssue:
    drug: str
    category: str
    severity: str  # blocked / warning / info
    message: str
    recommendation: str


# ── Pregnancy category database (100+ common drugs) ──────────────────────

PREGNANCY_CATEGORIES: dict[str, dict] = {
    # A (controlled studies show no risk)
    "Levothyroxine": {"category": "A", "note": "生理替代治疗，孕期安全"},
    "Folic acid": {"category": "A", "note": "孕期推荐补充"},
    "Ferrous sulfate": {"category": "A", "note": "孕期常规补铁"},
    "Vitamin D": {"category": "A", "note": "孕期常规补充"},
    "Calcium carbonate": {"category": "A", "note": "孕期常规补充"},

    # B (animal studies show no risk; no human studies, or animal risk not confirmed in humans)
    "Metformin": {"category": "B", "note": "PCOS及GDM常用，LactMed哺乳安全"},
    "Insulin Glargine": {"category": "B", "note": "GDM首选药物"},
    "Insulin Aspart": {"category": "B", "note": "餐时胰岛素，孕期安全"},
    "Insulin Lispro": {"category": "B", "note": "餐时胰岛素，孕期数据充分"},
    "Insulin Detemir": {"category": "B", "note": "基础胰岛素，孕期数据支持"},
    "Insulin Degludec": {"category": "B", "note": "数据有限，暂无明确致畸信号"},
    "NPH Insulin": {"category": "B", "note": "传统基础胰岛素，孕期数据充分"},
    "Regular Insulin": {"category": "B", "note": "短效胰岛素，孕期数据充分"},
    "Glyburide": {"category": "B", "note": "部分指南GDM二线，胎盘透过率低"},
    "Amoxicillin": {"category": "B", "note": "孕期常用广谱抗生素"},
    "Cephalexin": {"category": "B", "note": "孕期常用头孢类"},
    "Azithromycin": {"category": "B", "note": "大环内酯类，孕期数据充分"},
    "Clindamycin": {"category": "B", "note": "孕期常用"},
    "Metronidazole": {"category": "B", "note": "孕早期避免，中晚期可用"},
    "Clotrimazole": {"category": "B", "note": "局部抗真菌，孕期安全"},
    "Acetaminophen": {"category": "B", "note": "孕期首选解热镇痛"},
    "Diphenhydramine": {"category": "B", "note": "孕期可用抗组胺"},
    "Loratadine": {"category": "B", "note": "孕期首选抗组胺"},
    "Cetirizine": {"category": "B", "note": "孕期可选抗组胺"},
    "Ranitidine": {"category": "B", "note": "孕期烧心可短期用"},
    "Famotidine": {"category": "B", "note": "孕期烧心可短期用"},
    "Ondansetron": {"category": "B", "note": "妊娠剧吐二线，孕早期慎用"},
    "Heparin": {"category": "B", "note": "孕期抗凝首选（不透过胎盘）"},
    "Enoxaparin": {"category": "B", "note": "孕期LMWH首选"},
    "Labetalol": {"category": "B", "note": "孕期高血压一线"},
    "Methyldopa": {"category": "B", "note": "孕期高血压经典用药"},
    "Nifedipine": {"category": "B", "note": "孕期高血压/宫缩抑制"},

    # C (animal studies show risk; no human studies — only if benefit > risk)
    "Sitagliptin": {"category": "C", "note": "孕期数据不足，以胰岛素替代"},
    "Linagliptin": {"category": "C", "note": "孕期数据不足，以胰岛素替代"},
    "Saxagliptin": {"category": "C", "note": "孕期数据不足，以胰岛素替代"},
    "Alogliptin": {"category": "C", "note": "孕期数据不足，以胰岛素替代"},
    "Vildagliptin": {"category": "C", "note": "孕期数据不足，以胰岛素替代"},
    "Dapagliflozin": {"category": "C", "note": "孕中晚期动物研究显示肾脏发育不良"},
    "Empagliflozin": {"category": "C", "note": "孕中晚期动物研究显示风险信号"},
    "Canagliflozin": {"category": "C", "note": "孕中晚期动物研究显示风险信号"},
    "Ertugliflozin": {"category": "C", "note": "数据不足，应避免"},
    "Liraglutide": {"category": "C", "note": "动物研究显示甲状腺C细胞肿瘤"},
    "Semaglutide": {"category": "C", "note": "动物研究显示胚胎毒性"},
    "Dulaglutide": {"category": "C", "note": "动物研究显示致畸风险"},
    "Exenatide": {"category": "C", "note": "动物研究显示骨骼变异"},
    "Pioglitazone": {"category": "C", "note": "数据不足，应避免"},
    "Rosiglitazone": {"category": "C", "note": "数据不足，应避免"},
    "Glimepiride": {"category": "C", "note": "传统磺脲类，孕晚期可能导致新生儿低血糖"},
    "Glipizide": {"category": "C", "note": "应换为胰岛素"},
    "Gliclazide": {"category": "C", "note": "应换为胰岛素"},
    "Repaglinide": {"category": "C", "note": "数据不足，应避免"},
    "Nateglinide": {"category": "C", "note": "数据不足，应避免"},
    "Acarbose": {"category": "C", "note": "数据不足，应避免"},
    "Voglibose": {"category": "C", "note": "数据不足，应避免"},
    "Miglitol": {"category": "C", "note": "数据不足，应避免"},
    "Gabapentin": {"category": "C", "note": "孕早期暴露可能增加出生缺陷"},
    "Pregabalin": {"category": "C", "note": "孕早期暴露可能增加出生缺陷"},
    "Aspirin": {"category": "C", "note": "低剂量(81-150mg)孕中晚期安全，全量孕晚期避免"},
    "Ibuprofen": {"category": "C", "note": "孕30周后D类（动脉导管早闭）"},
    "Naproxen": {"category": "C", "note": "孕30周后D类"},
    "Prednisone": {"category": "C", "note": "孕早期可能增加口裂风险"},
    "Hydrochlorothiazide": {"category": "C", "note": "可能导致胎儿电解质紊乱"},
    "Furosemide": {"category": "C", "note": "仅限心力衰竭等强烈指征"},
    "Metoprolol": {"category": "C", "note": "孕晚期可能IUGR，拉贝洛尔优先"},
    "Atenolol": {"category": "C", "note": "全程可能IUGR，拉贝洛尔优先"},
    "Amlodipine": {"category": "C", "note": "拉贝洛尔/硝苯地平优先"},
    "Clonidine": {"category": "C", "note": "数据有限"},
    "Fluconazole": {"category": "C", "note": "单剂量(150mg)外用C类；长期口服D类"},
    "Metoclopramide": {"category": "C", "note": "孕早期可用，晚期可能锥体外系症状"},
    "Omeprazole": {"category": "C", "note": "数据有限，H2RA优先"},
    "Doxylamine": {"category": "C", "note": "妊娠剧吐一线（与B6联用）"},
    "Codeine": {"category": "C", "note": "孕晚期D类（新生儿戒断）"},

    # D (human studies show risk, but benefit may justify use)
    "Lisinopril": {"category": "D", "note": "孕中晚期肾发育异常、羊水过少"},
    "Enalapril": {"category": "D", "note": "孕中晚期ACEI胎儿肾病"},
    "Captopril": {"category": "D", "note": "孕中晚期ACEI胎儿肾病"},
    "Ramipril": {"category": "D", "note": "孕中晚期ACEI胎儿肾病"},
    "Perindopril": {"category": "D", "note": "孕中晚期ACEI胎儿肾病"},
    "Losartan": {"category": "D", "note": "孕中晚期ARB胎儿肾病"},
    "Valsartan": {"category": "D", "note": "孕中晚期ARB胎儿肾病"},
    "Irbesartan": {"category": "D", "note": "孕中晚期ARB胎儿肾病"},
    "Candesartan": {"category": "D", "note": "孕中晚期ARB胎儿肾病"},
    "Telmisartan": {"category": "D", "note": "孕中晚期ARB胎儿肾病"},
    "Spironolactone": {"category": "D", "note": "抗雄激素作用，男胎女性化风险"},
    "Warfarin": {"category": "D", "note": "孕6-12周胚胎病，孕晚期颅内出血"},
    "Phenytoin": {"category": "D", "note": "胎儿乙内酰脲综合征"},
    "Valproic acid": {"category": "D", "note": "致畸率高达10%（神经管缺陷）"},
    "Carbamazepine": {"category": "D", "note": "神经管缺陷、心脏畸形"},
    "Lithium": {"category": "D", "note": "孕早期Ebstein畸形"},
    "Tetracycline": {"category": "D", "note": "孕中晚期乳牙变色、骨骼发育抑制"},
    "Doxycycline": {"category": "D", "note": "孕中晚期骨骼发育影响"},
    "Gentamicin": {"category": "D", "note": "耳毒性，仅在败血症等致命情况使用"},
    "Amikacin": {"category": "D", "note": "氨基糖苷类耳毒性"},
    "Atorvastatin": {"category": "D", "note": "胆固醇合成抑制，胚胎发育必需"},
    "Simvastatin": {"category": "D", "note": "胆固醇合成抑制，胚胎发育必需"},
    "Rosuvastatin": {"category": "D", "note": "胆固醇合成抑制，胚胎发育必需"},
    "Methotrexate": {"category": "D", "note": "低剂量D类，高剂量X类"},
    "Cyclophosphamide": {"category": "D", "note": "化疗药，仅在母体生存必要时使用"},
    "Azathioprine": {"category": "D", "note": "移植/自身免疫病维持用药，严重疾病权衡"},
    "Phenobarbital": {"category": "D", "note": "新生儿戒断、出生缺陷"},

    # X (contraindicated in pregnancy)
    "Isotretinoin": {"category": "X", "note": "致畸率高达25-35%，妊娠必须排除后使用"},
    "Acitretin": {"category": "X", "note": "维A酸类，强致畸"},
    "Thalidomide": {"category": "X", "note": "海豹肢畸形，历史上最著名的致畸药物"},
    "Diethylstilbestrol": {"category": "X", "note": "阴道透明细胞腺癌"},
    "Ergotamine": {"category": "X", "note": "子宫收缩，胎儿缺氧"},
    "Dihydroergotamine": {"category": "X", "note": "子宫动脉收缩"},
    "Misoprostol": {"category": "X", "note": "子宫收缩、流产，孕晚期子宫破裂"},
    "Danazol": {"category": "X", "note": "雄激素作用，女胎男性化"},
    "Finasteride": {"category": "X", "note": "5a-还原酶抑制，男胎外生殖器发育异常"},
    "Dutasteride": {"category": "X", "note": "5a-还原酶抑制，避孕需持续至停药后6个月"},
    "Ribavirin": {"category": "X", "note": "动物胚胎致死/致畸，男女均需避孕"},
    "Temozolomide": {"category": "X", "note": "烷化剂化疗药，强致畸"},
    "Lepirudin": {"category": "X", "note": "孕期安全性未建立"},
}


def check_pregnancy_safety(
    medications: list[str],
    pregnancy_status: PregnancyStatus,
    patient_age: int = 0,
    patient_gender: str = "",
) -> list[PregnancyIssue]:
    """Check medication safety against pregnancy status.

    Parameters
    ----------
    medications : list[str]
        Drug names (generic English or Chinese).
    pregnancy_status : PregnancyStatus
        Known pregnancy status.
    patient_age : int
        Patient age (used for UNKNOWN status prompt logic).
    patient_gender : str
        Patient gender (used for UNKNOWN status prompt logic).

    Returns
    -------
    list[PregnancyIssue]
        Issues found; may include a prompt-to-confirm issue for unknown status.
    """
    issues: list[PregnancyIssue] = []

    # If pregnancy status unknown + female 15-50: prompt to confirm
    if pregnancy_status == PregnancyStatus.UNKNOWN:
        if (
            patient_gender.upper() in ("F", "女", "FEMALE")
            and 15 <= patient_age <= 50
        ):
            issues.append(PregnancyIssue(
                drug="N/A",
                category="N/A",
                severity="info",
                message="患者为育龄期女性(15-50岁)，妊娠状态未知。某些药物（如ACEI/ARB、他汀类）可能对胎儿造成严重伤害。",
                recommendation="建议在进行药物安全性评估前，确认患者是否可能妊娠。如有妊娠可能，优先使用胰岛素控制血糖。",
            ))
            return issues
        else:
            # Not a female of childbearing age, no restrictions
            return issues

    if pregnancy_status == PregnancyStatus.NOT_PREGNANT:
        return issues  # No pregnancy-related restrictions

    # PREGNANT: check all medications
    for drug_name in medications:
        lookup_key = drug_name
        drug_info = PREGNANCY_CATEGORIES.get(lookup_key)
        if drug_info is None:
            # Try case-insensitive
            for k, v in PREGNANCY_CATEGORIES.items():
                if k.lower() == drug_name.lower():
                    drug_info = v
                    break

        if drug_info is None:
            # Unknown drug in our database
            issues.append(PregnancyIssue(
                drug=drug_name,
                category="未知",
                severity="warning",
                message=f"{drug_name} 不在已知妊娠安全性数据库中",
                recommendation="请查阅药品说明书或咨询药学部门确认妊娠安全性",
            ))
            continue

        category = drug_info["category"]
        note = drug_info.get("note", "")

        if category in ("X", "D"):
            issues.append(PregnancyIssue(
                drug=drug_name,
                category=category,
                severity="blocked",
                message=f"{drug_name} 属于妊娠用药 {category} 类：{note}",
                recommendation=f"禁忌使用 {drug_name}。孕期降糖首选胰岛素（除甘精胰岛素外均可）。血压管理首选拉贝洛尔/硝苯地平/甲基多巴。",
            ))
        elif category == "C":
            issues.append(PregnancyIssue(
                drug=drug_name,
                category=category,
                severity="warning",
                message=f"{drug_name} 属于妊娠用药 C 类：{note}",
                recommendation=f"仅在获益大于风险时使用 {drug_name}，优先考虑孕期安全性更明确的替代药物",
            ))
        # Category A and B pass without issue

    return issues
