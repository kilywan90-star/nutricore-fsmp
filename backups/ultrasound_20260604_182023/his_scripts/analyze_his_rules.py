#!/usr/bin/env python3
"""
HIS医疗数据规则提取脚本
分析：ris_result（检查结果）、exam_items（体检项目）、diagnoses（诊断）、dict_icd（ICD字典）、patients（患者）
输出：结构化JSON结果
"""
import csv
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path(r"C:\Users\Administrator\Desktop\HIS数据")
OUTPUT_FILE = DATA_DIR / "his_medical_rules.json"

# ============================================================
# 1. ris_result.csv — 检查结果明细
# ============================================================
def analyze_ris_result():
    """提取高频检查项目和常见结论"""
    conclusions = []  # 所有检查结论 (XMDM=jcjl)
    bw_texts = []     # 检查部位
    jcsj_texts = []   # 检查所见

    with open(DATA_DIR / "ris_result.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xmdm = row.get("XMDM", "").strip()
            xmmc = row.get("XMMC", "").strip()
            xmjg = row.get("XMJG", "").strip()

            if xmdm == "jcjl" and xmjg:
                # Clean up: remove leading quote, strip whitespace
                text = xmjg.lstrip('"').strip()
                if text and text not in ("12312312", "2342345234234234"):
                    conclusions.append(text)
            elif xmdm == "bw" and xmjg:
                bw_texts.append(xmjg.strip())
            elif xmdm == "jcsj" and xmjg:
                # Check findings - often very long narrative text
                jcsj_texts.append(xmjg.strip())

    # Frequency analysis
    conclusion_freq = Counter(conclusions)

    # Categorize conclusions
    categories = {
        "正常/未见异常": [],
        "肝脏": [],
        "胆囊": [],
        "肾脏": [],
        "前列腺": [],
        "甲状腺": [],
        "乳腺": [],
        "子宫附件": [],
        "心脏": [],
        "血管/脑": [],
        "其他异常": [],
    }

    keyword_map = {
        "正常/未见异常": ["未见", "未见异常", "未见确切异常", "未见明显异常", "无异常"],
        "肝脏": ["肝", "脂肪肝"],
        "胆囊": ["胆囊", "胆"],
        "肾脏": ["肾", "囊肿"],
        "前列腺": ["前列腺"],
        "甲状腺": ["甲状腺"],
        "乳腺": ["乳腺"],
        "子宫附件": ["子宫", "附件", "盆腔", "宫颈", "卵巢"],
        "心脏": ["心脏", "二尖瓣", "三尖瓣", "主动脉瓣", "左房", "左室", "右房", "右室", "心包"],
        "血管/脑": ["动脉", "椎动脉", "颈动脉", "基底动脉", "脑动脉", "多普勒", "血管", "血流"],
    }

    for text in conclusions:
        matched = False
        for cat, keywords in keyword_map.items():
            if matched:
                break
            for kw in keywords:
                if kw in text:
                    categories[cat].append(text)
                    matched = True
                    break
        if not matched:
            categories["其他异常"].append(text)

    # Top conclusions per category
    top_per_category = {}
    for cat, texts in categories.items():
        top_per_category[cat] = [
            {"conclusion": t, "count": c}
            for t, c in Counter(texts).most_common(30)
        ]

    # Overall top conclusions (positive findings only - exclude normal)
    positive_conclusions = [t for t in conclusions if not any(
        kw in t for kw in ["未见", "未见异常", "未见确切异常", "未见明显异常"]
    )]
    positive_top = [
        {"conclusion": t, "count": c}
        for t, c in Counter(positive_conclusions).most_common(50)
    ]

    total_normal = sum(1 for t in conclusions if any(
        kw in t for kw in ["未见", "未见异常", "未见确切异常", "未见明显异常"]
    ))
    total_conclusions = len(conclusions)
    positive_rate = (len(positive_conclusions) / total_conclusions * 100) if total_conclusions else 0

    return {
        "total_conclusions": total_conclusions,
        "normal_count": total_normal,
        "positive_count": len(positive_conclusions),
        "positive_rate_pct": round(positive_rate, 1),
        "overall_top_conclusions": positive_top,
        "category_breakdown": {
            cat: {
                "count": len(texts),
                "top": top_per_category[cat],
            }
            for cat, texts in categories.items()
        },
    }


# ============================================================
# 2. ris_report.csv — 完整报告 (RIS_XMMC, JCBW, JCSJ)
# ============================================================
def analyze_ris_report():
    """从ris_report提取超声检查的完整报告分析"""
    exam_reports = defaultdict(list)  # RIS_XMMC -> list of {部位, 所见}

    with open(DATA_DIR / "ris_report.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xmmc = row.get("RIS_XMMC", "").strip()
            jcbw = row.get("JCBW", "").strip()
            jcsj = row.get("JCSJ", "").strip()

            if not xmmc:
                continue

            exam_reports[xmmc].append({
                "部位": jcbw if jcbw else None,
                "所见": jcsj if jcsj else None,
            })

    # Categorize findings for top exam types
    exam_findings_summary = {}
    us_keywords = [
        ("正常", r"未见.*异常|未见.*确切|正常|未见.*明显"),
        ("脂肪肝", r"脂肪肝"),
        ("肝囊肿", r"肝囊肿"),
        ("肾囊肿", r"肾囊肿|多囊肾"),
        ("肾结石", r"肾结石|肾.*结石|肾内.*强回声"),
        ("胆囊结石", r"胆囊结石|胆囊.*结石|胆囊内.*强回声"),
        ("胆囊息肉", r"胆囊息肉|固醇息肉|附壁.*高回声"),
        ("胆囊炎", r"胆囊.*炎|胆囊.*粗糙|胆囊.*不光滑"),
        ("前列腺增生", r"前列腺增生|前列腺.*增大"),
        ("前列腺钙化", r"前列腺钙化|前列腺.*钙化"),
        ("肝血管瘤", r"肝血管瘤"),
        ("肝内钙化", r"肝内.*钙化|肝.*钙化灶"),
        ("子宫肌瘤", r"子宫肌瘤"),
        ("盆腔积液", r"盆腔积液"),
        ("甲状腺结节", r"甲状腺.*结节|甲状腺.*低回声"),
        ("乳腺增生", r"乳腺增生"),
        ("乳腺结节", r"乳腺.*结节|乳腺.*占位"),
        ("二尖瓣反流", r"二尖瓣反流|二尖瓣.*返流"),
        ("三尖瓣反流", r"三尖瓣反流|三尖瓣.*返流"),
        ("主动脉瓣反流", r"主动脉瓣反流|主动脉瓣.*返流"),
        ("左房增大", r"左房增大"),
        ("心包积液", r"心包积液"),
        ("动脉硬化/斑块", r"动脉.*硬化|动脉.*斑块|内膜.*增厚"),
    ]

    for xmmc, reports in exam_reports.items():
        if len(reports) < 5:
            continue

        total = len(reports)
        finding_counts = {}
        for label, pattern in us_keywords:
            count = sum(1 for r in reports if r["所见"] and re.search(pattern, r["所见"]))
            if count > 0:
                finding_counts[label] = {
                    "count": count,
                    "rate_pct": round(count / total * 100, 1),
                }

        if finding_counts:
            exam_findings_summary[xmmc] = {
                "total_reports": total,
                "findings": dict(sorted(finding_counts.items(), key=lambda x: -x[1]["count"])),
            }

    # Report counts per exam type
    exam_counts = {k: len(v) for k, v in exam_reports.items()}
    exam_counts_sorted = sorted(exam_counts.items(), key=lambda x: -x[1])

    return {
        "exam_types": [{"name": k, "count": v} for k, v in exam_counts_sorted if v >= 5],
        "ultrasound_findings_detail": exam_findings_summary,
    }


# ============================================================
# 3. exam_items.csv — 体检项目 & 套餐组合
# ============================================================
def analyze_exam_items():
    """提取超声类体检项目列表及套餐组合模式"""
    packages = defaultdict(list)  # TJXH -> list of TJXM_NAME

    with open(DATA_DIR / "exam_items.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tjxh = row.get("TJXH", "").strip()
            tjxm_name = row.get("TJXM_NAME", "").strip()

            if tjxh and tjxm_name:
                packages[tjxh].append(tjxm_name)

    # Ultrasound items
    us_items = set()
    for items in packages.values():
        for item in items:
            if "超声" in item or "彩超" in item:
                us_items.add(item)

    us_items_sorted = sorted(us_items)

    # Find packages containing ultrasound
    us_packages = {}
    for tjxh, items in packages.items():
        us_in_pkg = [i for i in items if i in us_items]
        if us_in_pkg:
            us_packages[tjxh] = us_in_pkg

    # Package combination patterns
    combo_counter = Counter()
    for items in us_packages.values():
        combo = " + ".join(sorted(set(items)))
        combo_counter[combo] += 1

    # Co-occurrence analysis: which us items appear together
    us_item_pairs = Counter()
    for items in us_packages.values():
        unique_us = sorted(set(items))
        for i in range(len(unique_us)):
            for j in range(i + 1, len(unique_us)):
                us_item_pairs[(unique_us[i], unique_us[j])] += 1

    cooccurrence = [
        {"pair": list(pair), "count": c}
        for pair, c in us_item_pairs.most_common(30)
    ]

    # Individual frequency
    us_freq = Counter()
    for items in us_packages.values():
        for item in set(items):
            us_freq[item] += 1

    return {
        "ultrasound_items": us_items_sorted,
        "total_packages": len(packages),
        "packages_with_us": len(us_packages),
        "us_package_rate_pct": round(len(us_packages) / len(packages) * 100, 1),
        "us_item_frequency": [
            {"item": item, "package_count": c}
            for item, c in us_freq.most_common()
        ],
        "top_combos": [
            {"combo": combo, "count": c}
            for combo, c in combo_counter.most_common(30)
        ],
        "cooccurrence_pairs": cooccurrence,
    }


# ============================================================
# 4. diagnoses.csv & dict_icd.csv — 超声相关诊断 + ICD映射
# ============================================================
def analyze_diagnoses_and_icd():
    """提取超声相关诊断及ICD编码映射"""
    # First pass: find ultrasound-related diagnoses
    us_diagnoses = Counter()
    us_zdms = Counter()

    with open(DATA_DIR / "diagnoses.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zdmc = row.get("ZDMC", "").strip()
            zdms = row.get("ZDMS", "").strip()

            if _is_us_related_diag(zdmc) or _is_us_related_diag(zdms):
                us_diagnoses[zdmc] += 1
                if zdms:
                    us_zdms[zdms] += 1

    # Second pass: collect ICD codes for ultrasound diagnoses
    diag_icd_map = {}  # ZDMC -> list of ZDDM
    with open(DATA_DIR / "diagnoses.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zdmc = row.get("ZDMC", "").strip()
            zddm = row.get("ZDDM", "").strip()
            if zdmc in us_diagnoses and zddm:
                if zdmc not in diag_icd_map:
                    diag_icd_map[zdmc] = set()
                diag_icd_map[zdmc].add(zddm)

    # Load ICD-10 dictionary
    icd_dict = {}  # code -> {name, py}
    with open(DATA_DIR / "dict_icd.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("ID", "").strip()
            name = row.get("NAME", "").strip()
            icd10 = row.get("ICD10", "").strip()
            py_code = row.get("PY", "").strip()
            if code:
                icd_dict[code] = {
                    "name": name,
                    "icd10": icd10,
                    "py": py_code,
                }

    # Check which diagnosis ICDs are in the dictionary
    diag_with_icd = {}
    missing_from_dict = {}

    for zdmc, codes in diag_icd_map.items():
        diag_with_icd[zdmc] = {
            "icd_codes": sorted(codes),
            "count": us_diagnoses[zdmc],
        }
        for code in codes:
            if code not in icd_dict:
                missing_from_dict[code] = zdmc

    return {
        "total_us_related_diagnoses_distinct": len(us_diagnoses),
        "top_us_diagnoses": [
            {"diagnosis": d, "count": c}
            for d, c in us_diagnoses.most_common(60)
        ],
        "top_us_diag_descriptions": [
            {"description": d, "count": c}
            for d, c in us_zdms.most_common(30)
        ],
        "diagnosis_icd_mapping": diag_with_icd,
        "icd_codes_missing_from_dict": {
            code: {"diagnosis": zdmc}
            for code, zdmc in sorted(missing_from_dict.items())
        },
    }


def _is_us_related_diag(text):
    """Check if a diagnosis is ultrasound-related"""
    if not text:
        return False
    keywords = [
        "结石", "囊肿", "脂肪肝", "钙化", "占位", "息肉", "增生",
        "结节", "肌瘤", "积液", "反流", "肝硬化", "血管瘤",
        "胆道梗阻", "胆囊炎", "胰腺炎", "肾积水", "肾萎缩",
        "肝损伤", "肝大", "脾大", "肾盂", "输尿管",
        "前列腺", "子宫", "卵巢", "附件", "盆腔", "宫颈",
        "乳腺", "甲状腺", "心脏扩大", "心肌病", "心包",
        "瓣膜", "动脉硬化", "动脉斑块", "血栓", "狭窄",
        "椎动脉", "基底动脉", "颈动脉",
    ]
    return any(kw in text for kw in keywords)


# ============================================================
# 5. patients.csv — 患者信息（通过ris_report交叉分析超声患者）
# ============================================================
def analyze_patients():
    """分析超声检查患者的年龄性别分布"""
    # Build index: HZXM + JCSJ -> HZXM (from ris_report)
    # But ris_report only has HZXM (name), not SYXH. patients has SYXH and HZXM.
    # We'll need to build a name-based lookup (fuzzy).

    # First, collect patient info
    patients_data = {}  # SYXH -> {sex, age, ...}
    name_to_patients = defaultdict(list)  # HZXM -> list of SYXH

    with open(DATA_DIR / "patients.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            syxh = row.get("SYXH", "").strip()
            hzxm = row.get("HZXM", "").strip()
            sex = row.get("SEX", "").strip()
            brnl = row.get("BRNL", "").strip()

            if not syxh:
                continue

            # Parse age from BRNL (format varies: 20000 = 2000年0月?, 680715=YYMMDD)
            age = _parse_age(brnl)

            patients_data[syxh] = {"name": hzxm, "sex": sex, "age": age}
            if hzxm:
                name_to_patients[hzxm].append(syxh)

    # Get ultrasound patient names from ris_report
    us_patient_names = set()
    us_exam_by_name = defaultdict(list)
    with open(DATA_DIR / "ris_report.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hzxm = row.get("HZXM", "").strip()
            xmmc = row.get("RIS_XMMC", "").strip()
            if hzxm and xmmc:
                us_patient_names.add(hzxm)
                us_exam_by_name[hzxm].append(xmmc)

    # Match names to patients
    matched_patients = []
    unmatched_names = []
    for name in us_patient_names:
        if name in name_to_patients:
            for syxh in name_to_patients[name]:
                p = patients_data[syxh]
                matched_patients.append({
                    "syxh": syxh,
                    "name": name,
                    "sex": p["sex"],
                    "age": p["age"],
                    "exams": us_exam_by_name.get(name, []),
                })
        else:
            unmatched_names.append(name)

    # Age/sex distribution
    sex_counter = Counter()
    age_groups = Counter()
    age_list = []

    for p in matched_patients:
        sex = p["sex"].strip()
        if sex:
            sex_counter[sex] += 1

        age = p["age"]
        if age is not None and 0 < age < 150:
            age_list.append(age)
            if age < 20:
                age_groups["0-19"] += 1
            elif age < 30:
                age_groups["20-29"] += 1
            elif age < 40:
                age_groups["30-39"] += 1
            elif age < 50:
                age_groups["40-49"] += 1
            elif age < 60:
                age_groups["50-59"] += 1
            elif age < 70:
                age_groups["60-69"] += 1
            elif age < 80:
                age_groups["70-79"] += 1
            else:
                age_groups["80+"] += 1

    # Age by exam type
    age_by_exam = defaultdict(list)
    for p in matched_patients:
        if p["age"] is not None and 0 < p["age"] < 150:
            for exam in set(p["exams"]):
                if exam:
                    age_by_exam[exam].append(p["age"])

    age_stats_by_exam = {}
    for exam, ages in age_by_exam.items():
        if len(ages) >= 5:
            ages_sorted = sorted(ages)
            age_stats_by_exam[exam] = {
                "count": len(ages),
                "min": ages_sorted[0],
                "max": ages_sorted[-1],
                "median": ages_sorted[len(ages_sorted) // 2],
                "mean": round(sum(ages) / len(ages), 1),
            }

    # Sex by exam type
    sex_by_exam = defaultdict(lambda: Counter())
    for p in matched_patients:
        sex = p["sex"].strip()
        if not sex:
            continue
        for exam in set(p["exams"]):
            if exam:
                sex_by_exam[exam][sex] += 1

    sex_stats_by_exam = {}
    for exam, sc in sex_by_exam.items():
        total = sum(sc.values())
        if total >= 5:
            sex_stats_by_exam[exam] = {
                "total": total,
                "male": sc.get("男", 0) + sc.get("男  ", 0),
                "female": sc.get("女", 0) + sc.get("女  ", 0),
            }

    return {
        "total_us_patients_in_report": len(us_patient_names),
        "matched_to_patient_record": len(matched_patients),
        "unmatched_names": unmatched_names[:50],
        "sex_distribution": dict(sex_counter.most_common()),
        "age_distribution": dict(sorted(age_groups.items())),
        "age_stats": {
            "count": len(age_list),
            "median": sorted(age_list)[len(age_list) // 2] if age_list else None,
            "mean": round(sum(age_list) / len(age_list), 1) if age_list else None,
            "min": min(age_list) if age_list else None,
            "max": max(age_list) if age_list else None,
        },
        "age_by_exam_type": age_stats_by_exam,
        "sex_by_exam_type": sex_stats_by_exam,
    }


def _parse_age(brnl):
    """Parse BRNL field to age in years"""
    if not brnl:
        return None
    brnl = brnl.strip()
    try:
        val = int(brnl)
    except ValueError:
        return None

    # If value is 0 or very small, it might be an error
    if val == 0:
        return None

    # Pattern 1: YYMMDD (e.g., 680715 -> age at time of visit around 2015 = 47)
    if 150000 <= val <= 999999:
        # Likely YYMMDD format
        yy = val // 10000
        mm = (val // 100) % 100
        dd = val % 100
        if 0 <= mm <= 12 and 1 <= dd <= 31:
            # Assuming year 19xx or 20xx
            if yy > 50:  # 19xx
                birth_year = 1900 + yy
            else:
                birth_year = 2000 + yy
            return 2015 - birth_year  # approximate based on data date range
        return None

    # Pattern 2: YYYYMMDD (e.g., 19680715)
    if 19000101 <= val <= 20200101:
        yy = val // 10000
        mm = (val // 100) % 100
        dd = val % 100
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            return 2015 - yy
        return None

    # Pattern 3: Age already (e.g., 20000 = 20 years, 650000 = 65? no that's too big)
    # The format 20000 looks like 20 years 0 months
    # 650000 would be 65 years 0 months
    if 1 <= val <= 150:
        return val

    # Pattern 4: Other encoded (e.g., 20000 -> 20 years)
    if 10000 <= val <= 150000:
        return val // 1000

    # Fallback: try dividing
    if val > 150 and val < 150000:
        return val // 1000

    return None


# ============================================================
# 6. 综合输出
# ============================================================
def main():
    print("=" * 60)
    print("HIS医疗数据规则提取")
    print("=" * 60)

    print("\n[1/5] 分析 ris_result.csv ...")
    result_rules = analyze_ris_result()
    print(f"  结论总数: {result_rules['total_conclusions']}")
    print(f"  阳性率: {result_rules['positive_rate_pct']}%")

    print("\n[2/5] 分析 ris_report.csv ...")
    report_rules = analyze_ris_report()
    print(f"  检查类型数: {len(report_rules['exam_types'])}")
    print(f"  详细分析类型数: {len(report_rules['ultrasound_findings_detail'])}")

    print("\n[3/5] 分析 exam_items.csv ...")
    exam_rules = analyze_exam_items()
    print(f"  超声项目数: {len(exam_rules['ultrasound_items'])}")
    print(f"  含超声套餐: {exam_rules['packages_with_us']}/{exam_rules['total_packages']}")

    print("\n[4/5] 分析 diagnoses.csv + dict_icd.csv ...")
    diag_rules = analyze_diagnoses_and_icd()
    print(f"  超声相关诊断: {diag_rules['total_us_related_diagnoses_distinct']} 种")
    print(f"  缺失ICD编码: {len(diag_rules['icd_codes_missing_from_dict'])} 个")

    print("\n[5/5] 分析 patients.csv ...")
    patient_rules = analyze_patients()
    print(f"  匹配患者: {patient_rules['matched_to_patient_record']}")
    print(f"  年龄中位数: {patient_rules['age_stats']['median']}")

    # Assemble output
    output = {
        "source": "HIS数据医疗规则提取",
        "extraction_date": "2026-06-04",
        "1_ris_result_conclusions": result_rules,
        "2_ris_report_analysis": report_rules,
        "3_exam_items_ultrasound": exam_rules,
        "4_diagnoses_icd": diag_rules,
        "5_patients_distribution": patient_rules,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n输出文件: {OUTPUT_FILE}")
    print(f"文件大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
