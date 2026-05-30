"""HOMA (Homeostatic Model Assessment) calculators for insulin resistance
and beta-cell function assessment.

Based on the Matthews 1985 HOMA model, widely used in T2DM clinical
practice as referenced in 《中国2型糖尿病防治指南(2024版)》.
"""

from __future__ import annotations


def calculate_homa_ir(fasting_insulin: float, fasting_glucose: float) -> dict:
    """Calculate HOMA-IR (insulin resistance index).

    Formula: HOMA-IR = (fasting_insulin * fasting_glucose) / 22.5

    Args:
        fasting_insulin: Fasting insulin in μIU/mL (or mU/L).
        fasting_glucose: Fasting glucose in mmol/L.

    Returns:
        dict with keys: homa_ir (float), interpretation (str),
        reference_range (str), clinical_significance (str).

    Reference:
        Matthews DR et al. Diabetologia 1985; 28(7):412-9.
        中国2型糖尿病防治指南(2024版) §4.3
    """
    if fasting_insulin <= 0 or fasting_glucose <= 0:
        return {
            "homa_ir": None,
            "interpretation": "无法计算",
            "reference_range": "N/A",
            "clinical_significance": "胰岛素或血糖值无效，请检查输入数据",
        }

    homa_ir = round((fasting_insulin * fasting_glucose) / 22.5, 2)

    if homa_ir < 1.0:
        interpretation = "胰岛素敏感性正常"
        clinical_significance = "不存在明显胰岛素抵抗，胰岛素外周作用正常"
    elif homa_ir < 1.6:
        interpretation = "临界胰岛素抵抗"
        clinical_significance = "胰岛素敏感性轻度下降，建议结合临床判断，关注生活方式干预"
    elif homa_ir < 2.5:
        interpretation = "轻度胰岛素抵抗"
        clinical_significance = "存在胰岛素抵抗，建议生活方式干预（饮食控制+运动），3-6个月后复查"
    elif homa_ir < 5.0:
        interpretation = "中度胰岛素抵抗"
        clinical_significance = "明显胰岛素抵抗，建议药物干预（二甲双胍为首选），强化生活方式管理"
    else:
        interpretation = "重度胰岛素抵抗"
        clinical_significance = "严重胰岛素抵抗，建议联合药物干预，排除继发性原因（如皮质醇增多症等）"

    return {
        "homa_ir": homa_ir,
        "interpretation": interpretation,
        "reference_range": "正常 < 1.6; 临界 1.6-2.5; 中度 2.5-5.0; 重度 ≥ 5.0",
        "clinical_significance": clinical_significance,
    }


def calculate_homa_beta(fasting_insulin: float, fasting_glucose: float) -> dict:
    """Calculate HOMA-β (beta-cell function index).

    Formula: HOMA-β = (20 * fasting_insulin) / (fasting_glucose - 3.5) * 100

    Args:
        fasting_insulin: Fasting insulin in μIU/mL (or mU/L).
        fasting_glucose: Fasting glucose in mmol/L.

    Returns:
        dict with keys: homa_beta (float or None), interpretation (str),
        reference_range (str), clinical_significance (str).

    Reference:
        Matthews DR et al. Diabetologia 1985; 28(7):412-9.
        中国2型糖尿病防治指南(2024版) §4.3
    """
    if fasting_insulin <= 0 or fasting_glucose <= 3.5:
        return {
            "homa_beta": None,
            "interpretation": "无法计算",
            "reference_range": "N/A",
            "clinical_significance": "胰岛素值无效或血糖 ≤ 3.5 mmol/L，HOMA-β公式不适用",
        }

    homa_beta = round((20.0 * fasting_insulin) / (fasting_glucose - 3.5), 2)

    if homa_beta < 50:
        interpretation = "β细胞功能严重减退"
        clinical_significance = "胰岛素分泌显著不足，可能需要外源性胰岛素治疗"
    elif homa_beta < 80:
        interpretation = "β细胞功能中度减退"
        clinical_significance = "胰岛素分泌代偿不足，建议评估是否需要胰岛素促泌剂或早期胰岛素治疗"
    elif homa_beta < 120:
        interpretation = "β细胞功能轻度减退"
        clinical_significance = "胰岛素分泌功能在正常低限，建议定期监测，关注β细胞功能保护"
    elif homa_beta <= 200:
        interpretation = "β细胞功能正常"
        clinical_significance = "胰岛素分泌功能正常，提示β细胞储备良好"
    else:
        interpretation = "β细胞功能亢进"
        clinical_significance = "胰岛素高分泌状态，常见于肥胖相关的胰岛素抵抗代偿期，提示β细胞负荷大"

    return {
        "homa_beta": homa_beta,
        "interpretation": interpretation,
        "reference_range": "严重减退 < 50%; 中度 50-80%; 轻度 80-120%; 正常 120-200%; 亢进 > 200%",
        "clinical_significance": clinical_significance,
    }
