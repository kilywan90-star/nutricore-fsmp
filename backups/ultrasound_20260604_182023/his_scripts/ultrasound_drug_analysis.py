#!/usr/bin/env python3
"""
超声检查相关用药规则提取脚本
Extract ultrasound-related medication rules from HIS data.

Output: structured JSON with:
1. 超声造影剂/增强剂
2. 检查前准备用药
3. 高频诊断-药品配对
4. 处方药品组合模式
5. 超声相关诊断-用药关联规则
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

BASEDIR = r"C:\Users\Administrator\Desktop\HIS数据"
OUTPUT = os.path.join(BASEDIR, "ultrasound_drug_rules.json")

# ── 超声相关关键词 ──
ULTRASOUND_KEYWORDS = [
    "超声", "B超", "彩超", "C超", "M超",
    "多普勒", "造影", "声诺维", "SonoVue",
    "增强超声", "超声造影", "心脏超声", "腹部超声",
    "血管超声", "甲状腺超声", "乳腺超声", "腔内超声",
    "超声心动", "彩色多普勒",
]

CONTRAST_KEYWORDS = [
    "声诺维", "SonoVue", "六氟化硫", "超声造影",
    "造影剂", "对比剂", "增强剂", "显影剂",
    "欧乃派克", "碘海醇", "碘帕醇", "碘普罗胺",
    "钆喷酸", "钆贝葡胺", "马根维显", "普美显",
    "欧乃影", "威视派克", "优维显", "碘佛醇",
    "碘克沙醇", "碘比醇",
]

PREP_DRUG_KEYWORDS = [
    "二甲硅油", "西甲硅油", "胃镜润滑", "消泡",
    "甘露醇", "硫酸镁", "聚乙二醇", "番泻叶",
    "复方匹克", "磷酸钠", "清洁灌肠",
    "胃复安", "山莨菪碱", "654-2", "阿托品",
    "解痉", "平滑肌松弛",
    "丁溴东莨菪碱", "间苯三酚",
    "呋塞米", "速尿", "膀胱充盈",
]

POST_PROCEDURE_KEYWORDS = [
    "地塞米松", "异丙嗪", "苯海拉明", "肾上腺素",
    "葡萄糖酸钙", "氢化可的松", "甲泼尼龙",
    "观察", "留观",
]

# ── Helper functions ──
def safe_read_csv(filepath, encoding='utf-8-sig', nrows=None, skiprows=None):
    """Read CSV with fallback encodings."""
    encodings = [encoding, 'utf-8', 'gbk', 'gb18030', 'latin1']
    for enc in encodings:
        try:
            rows = []
            with open(filepath, 'r', encoding=enc, errors='replace') as fh:
                reader = csv.reader(fh)
                headers = [h.strip() for h in next(reader)]
                if skiprows:
                    for _ in range(skiprows):
                        try:
                            next(reader)
                        except StopIteration:
                            break
                count = 0
                for row in reader:
                    rows.append([v.strip() for v in row])
                    count += 1
                    if nrows and count >= nrows:
                        break
            return headers, rows, enc
        except Exception as e:
            continue
    raise Exception(f"Failed to read {filepath} with any encoding")

def match_keywords(text, keywords):
    """Check if text matches any keyword (case-insensitive)."""
    if not text:
        return False
    text = text.lower()
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False

def find_keywords(text, keywords):
    """Return list of matched keywords."""
    if not text:
        return []
    text = text.lower()
    return [kw for kw in keywords if kw.lower() in text]

# ══════════════════════════════════════════════════════════════
#  ANALYSIS 1: 药品字典 — 超声造影剂和增强剂
# ══════════════════════════════════════════════════════════════
def analyze_dict_drug():
    """Search dict_drug and drug_master for ultrasound contrast agents."""
    print("[1] Analyzing dict_drug.csv and drug_master.csv for contrast agents...")

    results = {
        "dict_drug_matches": [],
        "drug_master_matches": [],
        "contrast_agents": [],
        "prep_drugs": [],
        "all_ultrasound_related": [],
    }

    # dict_drug.csv
    try:
        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "dict_drug.csv"))
        for row in rows:
            if len(row) < 6:
                continue
            ypmc = row[1]  # 药品名称
            if match_keywords(ypmc, CONTRAST_KEYWORDS):
                results["dict_drug_matches"].append({
                    "id": row[0], "name": ypmc, "code": row[2],
                    "spec": row[5], "form": row[6],
                    "matched_keywords": find_keywords(ypmc, CONTRAST_KEYWORDS),
                    "type": "contrast_agent",
                    "source": "dict_drug",
                })
            if match_keywords(ypmc, PREP_DRUG_KEYWORDS):
                results["dict_drug_matches"].append({
                    "id": row[0], "name": ypmc, "code": row[2],
                    "spec": row[5], "form": row[6],
                    "matched_keywords": find_keywords(ypmc, PREP_DRUG_KEYWORDS),
                    "type": "prep_drug",
                    "source": "dict_drug",
                })
        print(f"  dict_drug: {len(results['dict_drug_matches'])} ultrasound-related entries found")
    except Exception as e:
        print(f"  dict_drug ERROR: {e}")

    # drug_master.csv
    try:
        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "drug_master.csv"))
        # Find relevant column indices
        name_col = headers.index('ypmc') if 'ypmc' in headers else 4
        spec_col = headers.index('ypgg') if 'ypgg' in headers else 10
        form_col = headers.index('jxdm') if 'jxdm' in headers else 11
        syfw_col = headers.index('syfw') if 'syfw' in headers else -1
        memo_col = headers.index('memo') if 'memo' in headers else -1
        cfsm_col = headers.index('cfsm') if 'cfsm' in headers else -1
        sfflbm_col = headers.index('sfflbm') if 'sfflbm' in headers else -1
        ATCbm_col = headers.index('ATCbm') if 'ATCbm' in headers else -1

        for row in rows:
            ypmc = row[name_col] if name_col < len(row) else ""
            syfw = row[syfw_col] if syfw_col >= 0 and syfw_col < len(row) else ""
            memo = row[memo_col] if memo_col >= 0 and memo_col < len(row) else ""
            cfsm = row[cfsm_col] if cfsm_col >= 0 and cfsm_col < len(row) else ""
            combined = f"{ypmc} {syfw} {memo} {cfsm}"

            if match_keywords(combined, CONTRAST_KEYWORDS + PREP_DRUG_KEYWORDS + ULTRASOUND_KEYWORDS):
                matched = find_keywords(combined, CONTRAST_KEYWORDS + PREP_DRUG_KEYWORDS + ULTRASOUND_KEYWORDS)
                drug_type = "ultrasound_related"
                if match_keywords(combined, CONTRAST_KEYWORDS):
                    drug_type = "contrast_agent"
                elif match_keywords(combined, PREP_DRUG_KEYWORDS):
                    drug_type = "prep_drug"

                entry = {
                    "id": row[0], "name": ypmc, "code": row[5] if len(row) > 5 else "",
                    "spec": row[spec_col] if spec_col < len(row) else "",
                    "form": row[form_col] if form_col < len(row) else "",
                    "usage_scope": syfw,
                    "prescription_note": cfsm,
                    "matched_keywords": matched,
                    "type": drug_type,
                    "source": "drug_master",
                }
                results["drug_master_matches"].append(entry)

        print(f"  drug_master: {len(results['drug_master_matches'])} ultrasound-related entries found")
    except Exception as e:
        print(f"  drug_master ERROR: {e}")

    # Separate by type
    results["contrast_agents"] = [x for x in results["dict_drug_matches"] + results["drug_master_matches"]
                                   if x.get("type") == "contrast_agent"]
    results["prep_drugs"] = [x for x in results["dict_drug_matches"] + results["drug_master_matches"]
                              if x.get("type") == "prep_drug"]
    results["all_ultrasound_related"] = results["dict_drug_matches"] + results["drug_master_matches"]

    return results

# ══════════════════════════════════════════════════════════════
#  ANALYSIS 2: drug_orders 采样 — 超声检查关联用药模式
# ══════════════════════════════════════════════════════════════
def analyze_drug_orders():
    """Sample drug_orders.csv to find ultrasound-related drug patterns."""
    print("[2] Sampling drug_orders.csv (100k+100k rows)...")

    results = {
        "drug_order_stats": {},
        "ultrasound_drugs_in_orders": [],
        "common_drugs_freq": [],
        "common_route_freq": [],
        "potential_ultrasound_pairs": [],
        "sample_summary": {},
    }

    order_drugs = Counter()
    order_routes = Counter()
    order_drug_route = defaultdict(Counter)
    ultrasound_orders = []
    total_rows = 0
    error_rows = 0

    def process_chunk(headers, rows, chunk_label):
        nonlocal total_rows, error_rows
        name_idx = headers.index('ypmc') if 'ypmc' in headers else 1
        route_idx = headers.index('ypyf') if 'ypyf' in headers else 5
        spec_idx = headers.index('ypgg') if 'ypgg' in headers else 2
        dose_idx = headers.index('ypjl') if 'ypjl' in headers else 3
        unit_idx = headers.index('jldw') if 'jldw' in headers else 4
        date_idx = headers.index('ksrq') if 'ksrq' in headers else 6

        for row in rows:
            try:
                total_rows += 1
                ypmc = row[name_idx] if name_idx < len(row) else ""
                ypyf = row[route_idx] if route_idx < len(row) else ""
                ypgg = row[spec_idx] if spec_idx < len(row) else ""
                ypjl = row[dose_idx] if dose_idx < len(row) else ""
                jldw = row[unit_idx] if unit_idx < len(row) else ""

                order_drugs[ypmc] += 1
                if ypyf:
                    order_routes[ypyf] += 1
                if ypmc and ypyf:
                    order_drug_route[ypmc][ypyf] += 1

                if match_keywords(ypmc, CONTRAST_KEYWORDS + PREP_DRUG_KEYWORDS + ULTRASOUND_KEYWORDS):
                    ultrasound_orders.append({
                        "drug_name": ypmc,
                        "spec": ypgg,
                        "dose": ypjl,
                        "unit": jldw,
                        "route": ypyf,
                        "matched": find_keywords(ypmc, CONTRAST_KEYWORDS + PREP_DRUG_KEYWORDS + ULTRASOUND_KEYWORDS),
                    })
            except Exception:
                error_rows += 1

    # Read first 100k
    try:
        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "drug_orders.csv"), nrows=100000)
        process_chunk(headers, rows, "first_100k")
        print(f"  First 100k: {total_rows} rows processed, {len(ultrasound_orders)} ultrasound matches")
    except Exception as e:
        print(f"  drug_orders first 100k ERROR: {e}")

    # Read last 100k by counting lines first, then skipping
    try:
        # Count total lines (fast, using raw counting)
        total_lines = 0
        with open(os.path.join(BASEDIR, "drug_orders.csv"), 'rb') as f:
            for _ in f:
                total_lines += 1
        skip_to = max(1, total_lines - 100000)
        print(f"  Total lines: {total_lines}, skipping to line {skip_to}")

        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "drug_orders.csv"), nrows=100000, skiprows=skip_to)
        before = len(ultrasound_orders)
        process_chunk(headers, rows, "last_100k")
        print(f"  Last 100k: matched {len(ultrasound_orders) - before} more ultrasound orders")
    except Exception as e:
        print(f"  drug_orders last 100k ERROR: {e}")

    # Summarize
    results["drug_order_stats"] = {
        "total_sampled_rows": total_rows,
        "error_rows": error_rows,
        "unique_drugs_in_sample": len(order_drugs),
        "ultrasound_related_orders_found": len(ultrasound_orders),
    }

    results["common_drugs_freq"] = order_drugs.most_common(50)
    results["common_route_freq"] = order_routes.most_common(20)

    if ultrasound_orders:
        # Group by drug name
        drug_counts = Counter(o["drug_name"] for o in ultrasound_orders)
        results["ultrasound_drugs_in_orders"] = [
            {"drug_name": name, "count": cnt,
             "matched_keywords": list(set(kw for o in ultrasound_orders if o["drug_name"] == name for kw in o["matched"]))}
            for name, cnt in drug_counts.most_common(30)
        ]

    results["sample_summary"] = {
        "sampling_method": "first_100k + last_100k rows from drug_orders.csv",
        "note": "388MB file, full scan not feasible. Sample is ~5% of total rows."
    }

    return results

# ══════════════════════════════════════════════════════════════
#  ANALYSIS 3: 处方审核数据 — 药品组合模式 + 诊断-药品配对
# ══════════════════════════════════════════════════════════════
def analyze_audit_data():
    """Analyze audit_hjcfk.csv and audit_hjcfk_mx.csv for prescription patterns."""
    print("[3] Analyzing audit_hjcfk.csv and audit_hjcfk_mx.csv...")

    results = {
        "prescription_count": 0,
        "detail_count": 0,
        "diagnosis_drug_pairs": [],
        "drug_combinations": [],
        "ultrasound_related_diagnoses": [],
        "high_freq_pairs": [],
        "common_administration_routes": [],
    }

    # ── Read audit_hjcfk.csv (prescription master) ──
    prescriptions = {}  # cfxh -> {diagnosis, drugs, etc.}
    diag_counter = Counter()
    route_counter = Counter()

    try:
        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "audit_hjcfk.csv"))
        # Find relevant columns
        cfxh_col = headers.index('xh') if 'xh' in headers else 0
        diag_code_col = headers.index('cfzddm') if 'cfzddm' in headers else -1
        diag_name_col = headers.index('cfzdmc') if 'cfzdmc' in headers else -1
        route_col = headers.index('cfjyfs') if 'cfjyfs' in headers else -1
        diag2_col = headers.index('cftszddm') if 'cftszddm' in headers else -1

        for row in rows:
            try:
                cfxh = row[cfxh_col] if cfxh_col < len(row) else ""
                diag_code = row[diag_code_col] if diag_code_col >= 0 and diag_code_col < len(row) else ""
                diag_name = row[diag_name_col] if diag_name_col >= 0 and diag_name_col < len(row) else ""
                route = row[route_col] if route_col >= 0 and route_col < len(row) else ""

                if diag_name:
                    diag_counter[diag_name] += 1
                if route:
                    route_counter[route] += 1

                prescriptions[cfxh] = {
                    "cfxh": cfxh,
                    "diag_code": diag_code,
                    "diag_name": diag_name,
                    "route": route,
                    "drugs": [],
                }
            except Exception:
                continue

        results["prescription_count"] = len(prescriptions)
        print(f"  audit_hjcfk: {len(prescriptions)} prescriptions loaded")
    except Exception as e:
        print(f"  audit_hjcfk ERROR: {e}")

    # ── Read audit_hjcfk_mx.csv (prescription details) ──
    drug_counter = Counter()
    diag_drug_pairs = Counter()
    diag_drug_details = defaultdict(list)
    all_drug_names = set()

    try:
        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "audit_hjcfk_mx.csv"))
        cfxh_col = headers.index('cfxh') if 'cfxh' in headers else 1
        ypmc_col = headers.index('ypmc') if 'ypmc' in headers else -1
        ypdm_col = headers.index('ypdm') if 'ypdm' in headers else -1
        ypgg_col = headers.index('ypgg') if 'ypgg' in headers else -1
        ypjl_col = headers.index('ypjl') if 'ypjl' in headers else -1
        ypsl_col = headers.index('ypsl') if 'ypsl' in headers else -1
        ypyf_col = headers.index('ypyf') if 'ypyf' in headers else -1

        for row in rows:
            try:
                cfxh = row[cfxh_col] if cfxh_col < len(row) else ""
                ypmc = row[ypmc_col] if ypmc_col >= 0 and ypmc_col < len(row) else ""
                ypdm = row[ypdm_col] if ypdm_col >= 0 and ypdm_col < len(row) else ""

                if not cfxh or not ypmc:
                    continue

                drug_counter[ypmc] += 1
                all_drug_names.add(ypmc)
                results["detail_count"] += 1

                # Link to prescription
                if cfxh in prescriptions:
                    prescriptions[cfxh]["drugs"].append({
                        "name": ypmc,
                        "code": ypdm,
                        "spec": row[ypgg_col] if ypgg_col >= 0 and ypgg_col < len(row) else "",
                        "dose": row[ypjl_col] if ypjl_col >= 0 and ypjl_col < len(row) else "",
                        "qty": row[ypsl_col] if ypsl_col >= 0 and ypsl_col < len(row) else "",
                        "route_code": row[ypyf_col] if ypyf_col >= 0 and ypyf_col < len(row) else "",
                    })
                    diag_name = prescriptions[cfxh]["diag_name"]
                    if diag_name:
                        pair_key = f"{diag_name} | {ypmc}"
                        diag_drug_pairs[pair_key] += 1
                        if len(diag_drug_details[diag_name]) < 50:
                            diag_drug_details[diag_name].append(ypmc)
            except Exception:
                continue

        print(f"  audit_hjcfk_mx: {results['detail_count']} detail records loaded")
        print(f"  Matched prescriptions: {sum(1 for p in prescriptions.values() if p['drugs'])}")
    except Exception as e:
        print(f"  audit_hjcfk_mx ERROR: {e}")

    # ── Drug combination analysis ──
    drug_combos = Counter()
    for cfxh, presc in prescriptions.items():
        if len(presc["drugs"]) >= 2:
            drug_names = tuple(sorted(d["name"] for d in presc["drugs"]))
            if len(drug_names) >= 2:
                drug_combos[drug_names] += 1

    # ── Ultrasound-related diagnoses ──
    ultrasound_diags = {d: c for d, c in diag_counter.items()
                         if match_keywords(d, ULTRASOUND_KEYWORDS)}
    ultrasound_diag_drugs = {}
    for diag in ultrasound_diags:
        if diag in diag_drug_details:
            drug_freq = Counter(diag_drug_details[diag])
            ultrasound_diag_drugs[diag] = drug_freq.most_common(20)

    results["diagnosis_drug_pairs"] = diag_drug_pairs.most_common(100)
    results["drug_combinations"] = [
        {"drugs": list(combo), "count": cnt}
        for combo, cnt in drug_combos.most_common(50)
    ]
    results["ultrasound_related_diagnoses"] = [
        {"diagnosis": d, "prescription_count": c,
         "common_drugs": ultrasound_diag_drugs.get(d, [])}
        for d, c in sorted(ultrasound_diags.items(), key=lambda x: -x[1])[:30]
    ]
    results["high_freq_pairs"] = [
        {"pair": k, "count": v} for k, v in diag_drug_pairs.most_common(30)
    ]
    results["common_administration_routes"] = route_counter.most_common(20)

    # ── Also check for contrast/prep drugs in the audit data ──
    contrast_drugs_in_audit = {}
    for drug, count in drug_counter.items():
        if match_keywords(drug, CONTRAST_KEYWORDS + PREP_DRUG_KEYWORDS):
            contrast_drugs_in_audit[drug] = count
    results["contrast_prep_in_audit"] = dict(sorted(contrast_drugs_in_audit.items(), key=lambda x: -x[1]))

    return results


# ══════════════════════════════════════════════════════════════
#  ANALYSIS 4: diagnoses — 超声相关诊断
# ══════════════════════════════════════════════════════════════
def analyze_diagnoses():
    """Search diagnoses.csv for ultrasound-related diagnoses."""
    print("[4] Analyzing diagnoses.csv for ultrasound-related diagnoses...")

    results = {
        "ultrasound_diagnoses": [],
        "diag_stats": {},
    }

    try:
        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "diagnoses.csv"))
        zddm_col = headers.index('ZDDM') if 'ZDDM' in headers else 3
        zdmc_col = headers.index('ZDMC') if 'ZDMC' in headers else 4
        zdms_col = headers.index('ZDMS') if 'ZDMS' in headers else 5
        zdlx_col = headers.index('ZDLX') if 'ZDLX' in headers else 2

        ultrasound_diags = []
        all_diags = Counter()
        for row in rows:
            try:
                zdmc = row[zdmc_col] if zdmc_col < len(row) else ""
                zdms = row[zdms_col] if zdms_col < len(row) else ""
                zddm = row[zddm_col] if zddm_col < len(row) else ""
                combined = f"{zdmc} {zdms}"
                all_diags[zdmc] += 1

                if match_keywords(combined, ULTRASOUND_KEYWORDS):
                    ultrasound_diags.append({
                        "code": zddm,
                        "name": zdmc,
                        "description": zdms,
                        "matched": find_keywords(combined, ULTRASOUND_KEYWORDS),
                    })
            except Exception:
                continue

        # Deduplicate by name
        seen = set()
        unique_ultrasound = []
        for d in ultrasound_diags:
            if d["name"] not in seen:
                seen.add(d["name"])
                unique_ultrasound.append(d)

        results["ultrasound_diagnoses"] = unique_ultrasound[:100]
        results["diag_stats"] = {
            "total_diagnoses": len(rows),
            "unique_diagnosis_names": len(all_diags),
            "ultrasound_related_count": len(ultrasound_diags),
            "ultrasound_unique_count": len(unique_ultrasound),
        }
        print(f"  diagnoses: {len(unique_ultrasound)} unique ultrasound-related diagnoses found")
    except Exception as e:
        print(f"  diagnoses ERROR: {e}")

    return results

# ══════════════════════════════════════════════════════════════
#  ANALYSIS 5: exam_items — 超声类检查项目
# ══════════════════════════════════════════════════════════════
def analyze_exam_items():
    """Search exam_items for ultrasound exam types."""
    print("[5] Analyzing exam_items.csv for ultrasound exams...")

    results = {
        "ultrasound_exam_items": [],
        "exam_stats": {},
    }

    try:
        headers, rows, enc = safe_read_csv(os.path.join(BASEDIR, "exam_items.csv"))
        name_col = headers.index('TJXM_NAME') if 'TJXM_NAME' in headers else 2
        id_col = headers.index('TJXM_ID') if 'TJXM_ID' in headers else 1

        ultrasound_exams = []
        all_exam_counter = Counter()
        for row in rows:
            try:
                name = row[name_col] if name_col < len(row) else ""
                eid = row[id_col] if id_col < len(row) else ""
                all_exam_counter[name] += 1

                if match_keywords(name, ULTRASOUND_KEYWORDS):
                    ultrasound_exams.append({
                        "exam_id": eid,
                        "exam_name": name,
                        "matched": find_keywords(name, ULTRASOUND_KEYWORDS),
                    })
            except Exception:
                continue

        # Deduplicate
        seen = set()
        unique_exams = []
        for e in ultrasound_exams:
            if e["exam_name"] not in seen:
                seen.add(e["exam_name"])
                unique_exams.append(e)

        # Also check exam_charges.csv
        exam_charges = {"ultrasound_charges": []}
        try:
            h2, r2, _ = safe_read_csv(os.path.join(BASEDIR, "exam_charges.csv"))
            charge_name_col = h2.index('SFXM_NAME') if 'SFXM_NAME' in h2 else 2
            for row in r2:
                name = row[charge_name_col] if charge_name_col < len(row) else ""
                if match_keywords(name, ULTRASOUND_KEYWORDS):
                    exam_charges["ultrasound_charges"].append(name)
            # dedup
            exam_charges["ultrasound_charges"] = list(set(exam_charges["ultrasound_charges"]))
        except Exception:
            pass

        results["ultrasound_exam_items"] = unique_exams[:50]
        results["exam_stats"] = {
            "total_exam_items": len(rows),
            "unique_exam_names": len(all_exam_counter),
            "ultrasound_exam_count": len(ultrasound_exams),
            "ultrasound_unique_count": len(unique_exams),
            "ultrasound_exam_charges": exam_charges.get("ultrasound_charges", []),
        }
        print(f"  exam_items: {len(unique_exams)} unique ultrasound exam types found")
        if exam_charges["ultrasound_charges"]:
            print(f"  exam_charges: {len(exam_charges['ultrasound_charges'])} ultrasound exam charges found")
    except Exception as e:
        print(f"  exam_items ERROR: {e}")

    return results


# ══════════════════════════════════════════════════════════════
#  ANALYSIS 6: 综合规则提取
# ══════════════════════════════════════════════════════════════
def extract_rules(all_results):
    """Synthesize findings into structured rules."""
    print("[6] Synthesizing ultrasound drug rules...")

    rules = {
        "contrast_agents": [],
        "pre_ultrasound_prep_drugs": [],
        "diagnosis_drug_associations": [],
        "drug_combinations_frequent": [],
        "administration_routes": [],
        "summary_statistics": {},
    }

    # Rule 1: 超声造影剂
    for agent in all_results.get("dict_drug", {}).get("contrast_agents", []):
        rules["contrast_agents"].append({
            "drug_name": agent.get("name", ""),
            "drug_code": agent.get("code", ""),
            "spec": agent.get("spec", ""),
            "form": agent.get("form", ""),
            "keywords_matched": agent.get("matched_keywords", []),
            "category": "超声造影增强剂",
            "source_table": agent.get("source", ""),
        })

    # Rule 2: 检查前准备用药
    for drug in all_results.get("dict_drug", {}).get("prep_drugs", []):
        rules["pre_ultrasound_prep_drugs"].append({
            "drug_name": drug.get("name", ""),
            "drug_code": drug.get("code", ""),
            "spec": drug.get("spec", ""),
            "keywords_matched": drug.get("matched_keywords", []),
            "usage_note": drug.get("usage_scope", ""),
            "category": "检查前准备/辅助用药",
            "source_table": drug.get("source", ""),
        })

    # Rule 3: 诊断-用药关联
    audit_data = all_results.get("audit", {})
    for diag in audit_data.get("ultrasound_related_diagnoses", [])[:20]:
        rules["diagnosis_drug_associations"].append({
            "diagnosis": diag["diagnosis"],
            "prescription_count": diag["prescription_count"],
            "frequently_paired_drugs": [
                {"drug_name": d[0], "frequency": d[1]}
                for d in diag.get("common_drugs", [])[:10]
            ],
        })

    # Rule 4: 高频药品组合
    for combo in audit_data.get("drug_combinations", [])[:20]:
        rules["drug_combinations_frequent"].append({
            "drugs": combo["drugs"],
            "co_occurrence_count": combo["count"],
        })

    # Rule 5: 给药途径
    drug_order_data = all_results.get("drug_orders", {})
    for route, count in drug_order_data.get("common_route_freq", []):
        rules["administration_routes"].append({
            "route_code": route,
            "frequency": count,
        })

    # Summary statistics
    rules["summary_statistics"] = {
        "hospital": "锦州市某三甲医院",
        "data_period": "2014-12-24 ~ 2016-06-24 (18个月)",
        "total_prescriptions_audited": audit_data.get("prescription_count", 0),
        "total_diagnoses": all_results.get("diagnoses", {}).get("diag_stats", {}).get("total_diagnoses", 0),
        "ultrasound_related_diagnoses_count": all_results.get("diagnoses", {}).get("diag_stats", {}).get("ultrasound_unique_count", 0),
        "ultrasound_exam_types_count": all_results.get("exams", {}).get("exam_stats", {}).get("ultrasound_unique_count", 0),
        "contrast_agents_in_hospital_formulary": len(rules["contrast_agents"]),
        "prep_drugs_in_hospital_formulary": len(rules["pre_ultrasound_prep_drugs"]),
        "drug_order_sample_size": drug_order_data.get("sample_summary", {}).get("note", ""),
        "note": "2014-2016年数据，超声造影(SonoVue/声诺维)在中国获批于2004年，此数据可能为早期超声造影应用实践",
    }

    return rules


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("HIS超声检查用药规则提取分析")
    print(f"数据目录: {BASEDIR}")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("=" * 60)

    all_results = {}

    # Run all analyses
    try:
        all_results["dict_drug"] = analyze_dict_drug()
    except Exception as e:
        print(f"FATAL dict_drug: {e}")
        all_results["dict_drug"] = {}

    try:
        all_results["drug_orders"] = analyze_drug_orders()
    except Exception as e:
        print(f"FATAL drug_orders: {e}")
        all_results["drug_orders"] = {}

    try:
        all_results["audit"] = analyze_audit_data()
    except Exception as e:
        print(f"FATAL audit: {e}")
        all_results["audit"] = {}

    try:
        all_results["diagnoses"] = analyze_diagnoses()
    except Exception as e:
        print(f"FATAL diagnoses: {e}")
        all_results["diagnoses"] = {}

    try:
        all_results["exams"] = analyze_exam_items()
    except Exception as e:
        print(f"FATAL exams: {e}")
        all_results["exams"] = {}

    # Extract structured rules
    rules = extract_rules(all_results)

    # Build final output
    output = {
        "metadata": {
            "analysis_name": "超声检查相关用药规则提取",
            "analysis_date": datetime.now().isoformat(),
            "source": "锦州HIS数据库 (THIS4/Winning)",
            "data_period": "2014-12-24 ~ 2016-06-24",
        },
        "rules": rules,
        "raw_findings": {
            "contrast_agents_in_dict": all_results.get("dict_drug", {}).get("contrast_agents", []),
            "prep_drugs_in_dict": all_results.get("dict_drug", {}).get("prep_drugs", []),
            "ultrasound_diagnoses_found": all_results.get("diagnoses", {}).get("ultrasound_diagnoses", []),
            "ultrasound_exam_items_found": all_results.get("exams", {}).get("ultrasound_exam_items", []),
            "ultrasound_exam_charges_found": all_results.get("exams", {}).get("exam_stats", {}).get("ultrasound_exam_charges", []),
            "ultrasound_drugs_in_orders": all_results.get("drug_orders", {}).get("ultrasound_drugs_in_orders", []),
            "contrast_prep_in_audit": all_results.get("audit", {}).get("contrast_prep_in_audit", {}),
            "top_diagnosis_drug_pairs": all_results.get("audit", {}).get("diagnosis_drug_pairs", [])[:30],
            "top_drug_combinations": all_results.get("audit", {}).get("drug_combinations", [])[:20],
            "top_drugs_in_orders": all_results.get("drug_orders", {}).get("common_drugs_freq", [])[:20],
        },
    }

    # Write output
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"分析完成！输出文件: {OUTPUT}")
    print(f"文件大小: {os.path.getsize(OUTPUT) / 1024:.1f} KB")
    print(f"{'=' * 60}")

    # Print summary to console
    print("\n## 快速摘要")
    print(f"- 医院药典超声造影/增强剂: {len(rules['contrast_agents'])} 种")
    print(f"- 检查前准备用药: {len(rules['pre_ultrasound_prep_drugs'])} 种")
    print(f"- 超声相关诊断-用药关联: {len(rules['diagnosis_drug_associations'])} 组")
    print(f"- 高频药品组合: {len(rules['drug_combinations_frequent'])} 组")
    print(f"- 超声检查收费项目: {all_results.get('exams', {}).get('exam_stats', {}).get('ultrasound_unique_count', 0)} 种")

if __name__ == "__main__":
    main()
