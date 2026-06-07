"""自动分析 test_results_1000.csv，检测10类潜在质量问题

检测项:
  1. 数值丢失: 输入中的测量数值在输出中消失(无数值保全警告)
  2. 正常矛盾: 输入描述异常但输出说正常(无ASR覆盖警告)
  3. 模板错配: 模板所属检查类型与输入不匹配
  4. 单位偷换: 输入cm输出变mm(或反之)且无原始值保留
  5. 器官幻觉: 输出出现输入中未提及的器官/部位
  6. 诊断缺失: 输入有明显异常但诊断提示为空
  7. 内容截断: 输出明显短于输入(信息丢失)
  8. 重复内容: 输出中有重复的短语/句子
  9. 占位符残留: 输出中有 ___ 或 __ 或 未测 等未填充占位符
 10. 模板选择偏差: 异常报告匹配到"正常"模板且无ASR覆盖
"""

import csv
import re
import json
import sys
from collections import Counter, defaultdict

CSV_PATH = r"e:\qoder\ultrasound-report-mvp\backend\test_results_1000.csv"

# ============================================================
# 领域知识
# ============================================================

# 各检查类型对应的器官/部位关键词
EXAM_ORGANS = {
    "腹部超声": ["肝", "胆囊", "胆总管", "胰腺", "脾", "肾", "左肾", "右肾"],
    "甲状腺超声": ["甲状腺"],
    "乳腺超声": ["乳腺", "乳", "腋窝", "淋巴结", "象限"],
    "前列腺超声": ["前列腺", "精囊", "膀胱"],
    "妇产超声": ["子宫", "宫腔", "卵巢", "附件", "盆腔", "宫内"],
    "血管超声": ["颈动脉", "椎动脉", "锁骨下动脉", "内中膜", "斑块", "管腔"],
    "心脏超声": ["心", "瓣", "室间隔", "房", "主动脉"],
}

# 异常指示词
ABNORMAL_SIGNS = (
    "结节", "钙化", "增生", "增大", "稍大", "偏大", "饱满",
    "囊肿", "息肉", "肌瘤", "积液", "积水", "肿瘤", "占位",
    "结石", "斑块", "血栓", "狭窄", "炎", "癌", "扩张",
    "欠均匀", "欠光滑", "毛糙", "增厚", "衰减",
    "回声增强", "回声减低", "无回声", "低回声", "高回声",
    "不规则", "模糊", "渗出", "粘连", "反流", "增厚",
)

# 正常指示短语
NORMAL_PHRASES = (
    "未见明显异常", "未见异常", "未见明显结节", "未见明显占位",
    "未见异常回声", "未见明显包块", "分布均匀", "形态规则",
    "大小正常", "回声均匀", "未见明显异常回声",
)

# 正常模板名称关键词
NORMAL_TPL_KEYWORDS = ("正常", "未见异常")


def strip_html(html):
    return re.sub(r'<[^>]+>', '', html or "").strip()


def extract_numbers(text):
    """提取文本中所有数值"""
    return set(re.findall(r'\d+(?:\.\d+)?', text))


def extract_measurements(text):
    """提取所有测量表达式 (如 约2.5cm, 约1.2×1.8cm)"""
    patterns = [
        r'(?:约|大?小约?|厚约?|长约?|深约?|宽约?|内径约?)?\s*\d+(?:\.\d+)?\s*[×xX\*乘]\s*\d+(?:\.\d+)?\s*(?:mm|毫米|cm|厘米)?',
        r'(?:约|大?小约?|厚约?|长约?|深约?|宽约?|内径约?)\s*\d+(?:\.\d+)?\s*(?:mm|毫米|cm|厘米)',
    ]
    results = []
    for p in patterns:
        results.extend(re.findall(p, text))
    return list(dict.fromkeys(results))


def get_exam_organs_for_type(exam_type):
    """获取检查类型对应的器官列表"""
    return EXAM_ORGANS.get(exam_type, [])


def input_has_abnormal(input_text):
    """判断输入是否描述异常"""
    return any(sign in input_text for sign in ABNORMAL_SIGNS)


def output_says_normal(output_text):
    """判断输出是否说正常"""
    clean = strip_html(output_text)
    match_count = sum(1 for p in NORMAL_PHRASES if p in clean)
    abnormal_count = sum(1 for s in ABNORMAL_SIGNS if s in clean)
    return match_count >= 2 and abnormal_count == 0


# ============================================================
# 10类质量检测器
# ============================================================

def check_1_data_loss(row):
    """数值丢失: 输入有测量值但输出中找不到, 且无数值保全警告"""
    inp = row["输入文本"]
    out = strip_html(row["最终输出"])
    warning = row["警告信息"]

    inp_nums = extract_numbers(inp)
    out_nums = extract_numbers(out)

    if not inp_nums:
        return None

    missing = inp_nums - out_nums
    # 过滤掉太小的数字(可能是模板自带的)
    missing = {n for n in missing if float(n) >= 0.3}

    if missing and "数值保全" not in warning:
        # 输出中也没有"补充测量"
        if "补充测量" not in out:
            return {
                "severity": "high",
                "detail": f"输入数值{missing}在输出中丢失, 且无数值保全",
                "missing_nums": sorted(missing),
            }
    return None


def check_2_normal_contradiction(row):
    """正常矛盾: 输入描述异常但输出说正常, 且无ASR覆盖"""
    inp = row["输入文本"]
    out = strip_html(row["最终输出"])
    warning = row["警告信息"]

    if not input_has_abnormal(inp):
        return None

    if output_says_normal(row["最终输出"]):
        if "ASR覆盖" not in warning and "ASR" not in warning:
            return {
                "severity": "critical",
                "detail": "输入描述异常但输出说正常, 未触发ASR覆盖",
            }
    return None


def check_3_template_mismatch(row):
    """模板错配: 模板对应的检查类型与输入不匹配"""
    exam_type = row["检查类型"]
    template = row["意图模板"]

    if not template or "自由生成" in template:
        return None  # 自由生成无模板

    # 检查模板名中是否包含其他检查类型的专属器官词
    other_types = {k: v for k, v in EXAM_ORGANS.items() if k != exam_type}
    for other_type, organs in other_types.items():
        # 检查模板名是否明显属于另一个检查类型
        if other_type == "心脏超声":
            if any(kw in template for kw in ["心脏", "心室", "瓣膜"]):
                if exam_type != "心脏超声":
                    return {"severity": "high", "detail": f"{exam_type}匹配到心脏模板: {template}"}
        elif other_type == "妇产超声":
            if any(kw in template for kw in ["子宫", "卵巢", "胎儿"]):
                if exam_type not in ("妇产超声",):
                    return {"severity": "high", "detail": f"{exam_type}匹配到妇产模板: {template}"}

    return None


def check_4_unit_conversion(row):
    """单位偷换: 输入cm输出变mm(或反之), 且无原始值保留"""
    inp = row["输入文本"]
    out = strip_html(row["最终输出"])
    warning = row["警告信息"]

    # 找输入中的 cm 值
    inp_cm = re.findall(r'(\d+(?:\.\d+)?)\s*cm', inp)
    inp_mm = re.findall(r'(\d+(?:\.\d+)?)\s*mm', inp)

    issues = []
    if inp_cm and not inp_mm:
        # 输入全是cm, 检查输出是否偷偷换成mm
        out_mm = re.findall(r'(\d+(?:\.\d+)?)\s*mm', out)
        if out_mm:
            # 检查原始cm值是否还在
            for cm_val in inp_cm:
                if cm_val not in out and "补充测量" not in out:
                    issues.append(f"输入{cm_val}cm在输出中消失, 可能被转换为mm")

    if inp_mm and not inp_cm:
        out_cm = re.findall(r'(\d+(?:\.\d+)?)\s*cm', out)
        if out_cm:
            for mm_val in inp_mm:
                if mm_val not in out and "补充测量" not in out:
                    issues.append(f"输入{mm_val}mm在输出中消失, 可能被转换为cm")

    if issues and "数值保全" not in warning:
        return {"severity": "medium", "detail": "; ".join(issues)}
    return None


def check_5_organ_hallucination(row):
    """器官幻觉: 输出出现输入中未提及的器官"""
    inp = row["输入文本"]
    out = strip_html(row["最终输出"])
    exam_type = row["检查类型"]

    # 获取当前检查类型的器官
    expected_organs = get_exam_organs_for_type(exam_type)

    # 检查所有检查类型的器官关键词
    all_organs = {}
    for et, organs in EXAM_ORGANS.items():
        for o in organs:
            all_organs[o] = et

    hallucinations = []
    for organ, et in all_organs.items():
        if et == exam_type:
            continue  # 跳过本类型的器官
        # 器官词在输出中但不在输入中
        if organ in out and organ not in inp:
            # 排除通用词 (如"大小"、"形态"等)
            if len(organ) >= 2 and organ not in ("大小", "形态", "边界", "内部", "分布"):
                hallucinations.append(f"输出含{et}器官'{organ}'但输入未提及")

    if hallucinations:
        return {"severity": "medium", "detail": "; ".join(hallucinations[:3])}
    return None


def check_6_missing_diagnosis(row):
    """诊断缺失: 输入有明显异常但诊断提示为空"""
    inp = row["输入文本"]
    diagnosis = row["诊断提示"]

    if not input_has_abnormal(inp):
        return None

    if not diagnosis or not diagnosis.strip():
        return {"severity": "medium", "detail": "输入有异常但诊断提示为空"}

    return None


def check_7_content_truncation(row):
    """内容截断: 输出纯文本明显短于输入"""
    inp = row["输入文本"]
    out = strip_html(row["最终输出"])

    inp_len = len(re.sub(r'[\s\W]', '', inp))
    out_len = len(re.sub(r'[\s\W]', '', out))

    # 输出不到输入的50%且输入有异常描述
    if inp_len > 20 and out_len < inp_len * 0.4 and input_has_abnormal(inp):
        return {
            "severity": "medium",
            "detail": f"输入{inp_len}字→输出{out_len}字, 压缩率{out_len/inp_len:.0%}",
        }
    return None


def check_8_duplicate_content(row):
    """重复内容: 输出中有重复的短语"""
    out = strip_html(row["最终输出"])

    # 检查连续重复的句子片段
    if len(out) < 20:
        return None

    # 按句号分割
    sentences = re.split(r'[。；]', out)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    # 检查重复句
    seen = set()
    dupes = []
    for s in sentences:
        if s in seen:
            dupes.append(s[:30])
        seen.add(s)

    if dupes:
        return {"severity": "low", "detail": f"输出含重复内容: {dupes[0]}..."}

    # 检查10字以上重复子串
    for length in range(15, min(len(out)//2, 40)):
        for i in range(len(out) - length):
            sub = out[i:i+length]
            if out.count(sub) > 1 and not all(c in '，。、；' for c in sub):
                return {"severity": "low", "detail": f"输出含重复子串({length}字): '{sub[:30]}'"}

    return None


def check_9_placeholder_residual(row):
    """占位符残留: 输出中有未填充的占位符"""
    out = strip_html(row["最终输出"])

    placeholders = re.findall(r'_{2,}|未测|未填|x\s*(?:mm|cm)', out, re.IGNORECASE)
    if placeholders:
        return {"severity": "high", "detail": f"输出含未填充占位符: {placeholders[:5]}"}
    return None


def check_10_template_bias(row):
    """模板选择偏差: 异常报告匹配到正常模板且无ASR覆盖"""
    inp = row["输入文本"]
    template = row["意图模板"]
    warning = row["警告信息"]

    if not input_has_abnormal(inp):
        return None

    if not template or "自由生成" in template:
        return None

    # 模板名含"正常"但输入有异常
    is_normal_tpl = any(kw in template for kw in NORMAL_TPL_KEYWORDS)
    if is_normal_tpl and "ASR覆盖" not in warning:
        return {
            "severity": "high",
            "detail": f"异常报告匹配到正常模板'{template}'且无ASR覆盖",
        }
    return None


# ============================================================
# 主分析逻辑
# ============================================================

ALL_CHECKS = [
    ("数值丢失", check_1_data_loss),
    ("正常矛盾", check_2_normal_contradiction),
    ("模板错配", check_3_template_mismatch),
    ("单位偷换", check_4_unit_conversion),
    ("器官幻觉", check_5_organ_hallucination),
    ("诊断缺失", check_6_missing_diagnosis),
    ("内容截断", check_7_content_truncation),
    ("重复内容", check_8_duplicate_content),
    ("占位符残留", check_9_placeholder_residual),
    ("模板偏差", check_10_template_bias),
]


def analyze():
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    print(f"分析 {len(rows)} 条测试结果...")
    print("=" * 70)

    # 统计
    issue_counts = Counter()           # 问题类型 → 次数
    severity_counts = Counter()        # 严重度 → 次数
    issue_rows = defaultdict(list)     # 问题类型 → [(row_id, detail)]
    row_issues = defaultdict(list)     # row_id → [问题类型]

    total_issues = 0
    clean_rows = 0

    for row in rows:
        row_id = row["序号"]
        has_issue = False

        for check_name, check_fn in ALL_CHECKS:
            result = check_fn(row)
            if result:
                sev = result["severity"]
                detail = result["detail"]
                issue_counts[check_name] += 1
                severity_counts[sev] += 1
                issue_rows[check_name].append((row_id, row["检查类型"], detail, row["输入文本"][:60], row["最终输出"][:60]))
                row_issues[row_id].append((check_name, sev, detail))
                total_issues += 1
                has_issue = True

        if not has_issue:
            clean_rows += 1

    # ==================== 输出报告 ====================
    print(f"\n{'='*70}")
    print(f"自动化质量分析报告")
    print(f"{'='*70}")
    print(f"\n总测试: {len(rows)} 条")
    print(f"无问题: {clean_rows} 条 ({clean_rows/len(rows)*100:.1f}%)")
    print(f"有问题: {len(rows)-clean_rows} 条 ({(len(rows)-clean_rows)/len(rows)*100:.1f}%)")
    print(f"总问题数: {total_issues}")

    print(f"\n--- 严重度分布 ---")
    for sev, cnt in severity_counts.most_common():
        label = {"critical": "严重", "high": "高", "medium": "中", "low": "低"}[sev]
        print(f"  [{label}] {cnt}")

    print(f"\n--- 问题类型分布 ---")
    for name, cnt in issue_counts.most_common():
        print(f"  {name}: {cnt} ({cnt/len(rows)*100:.1f}%)")

    # 按严重度排序输出详细问题
    for check_name, cnt in issue_counts.most_common():
        print(f"\n{'='*70}")
        print(f"[{check_name}] 共 {cnt} 条 (示例前10条)")
        print(f"{'='*70}")
        for i, (rid, etype, detail, inp_short, out_short) in enumerate(issue_rows[check_name][:10]):
            print(f"  #{rid} [{etype}]")
            print(f"    问题: {detail}")
            print(f"    输入: {inp_short}...")
            print(f"    输出: {out_short}...")
            print()

    # 多问题叠加的行
    multi_issue = {rid: issues for rid, issues in row_issues.items() if len(issues) >= 2}
    if multi_issue:
        print(f"\n{'='*70}")
        print(f"多问题叠加 (>=2个问题): {len(multi_issue)} 条")
        print(f"{'='*70}")
        for rid, issues in sorted(multi_issue.items(), key=lambda x: -len(x[1]))[:15]:
            issue_names = ", ".join(f"{n}({s})" for n, s, _ in issues)
            row = next(r for r in rows if r["序号"] == rid)
            print(f"  #{rid} [{row['检查类型']}] ({len(issues)}个问题)")
            print(f"    问题: {issue_names}")
            print(f"    输入: {row['输入文本'][:80]}")
            print(f"    输出: {strip_html(row['最终输出'])[:80]}")
            print()

    # 输出JSON格式的详细结果供后续修复使用
    fix_report = {
        "total": len(rows),
        "clean": clean_rows,
        "issues_total": total_issues,
        "by_type": dict(issue_counts),
        "by_severity": dict(severity_counts),
        "critical_cases": [],
        "high_cases": [],
        "fix_suggestions": [],
    }

    for rid, issues in row_issues.items():
        row = next(r for r in rows if r["序号"] == rid)
        for name, sev, detail in issues:
            entry = {
                "id": rid, "exam_type": row["检查类型"],
                "input": row["输入文本"][:120], "output": strip_html(row["最终输出"])[:120],
                "issue": name, "severity": sev, "detail": detail,
                "template": row["意图模板"], "warning": row["警告信息"],
            }
            if sev == "critical":
                fix_report["critical_cases"].append(entry)
            elif sev == "high":
                fix_report["high_cases"].append(entry)

    # 生成修复建议
    if issue_counts.get("正常矛盾", 0) > 0:
        fix_report["fix_suggestions"].append({
            "target": "main.py L7 ASR覆盖",
            "action": "扩展_tpl_normal_phrases和_asr_abnormal_signs覆盖范围",
            "reason": f"有{issue_counts['正常矛盾']}条异常报告输出为正常但未触发ASR覆盖",
        })
    if issue_counts.get("数值丢失", 0) > 0:
        fix_report["fix_suggestions"].append({
            "target": "main.py L2 数值保全",
            "action": "增强数值提取正则, 覆盖更多格式(如百分比、面积单位)",
            "reason": f"有{issue_counts['数值丢失']}条数值丢失且未触发保全",
        })
    if issue_counts.get("模板偏差", 0) > 0:
        fix_report["fix_suggestions"].append({
            "target": "template_engine_v2 / search_candidates",
            "action": "调整模板匹配评分权重, 异常关键词匹配优先级提升",
            "reason": f"有{issue_counts['模板偏差']}条异常报告匹配到正常模板",
        })
    if issue_counts.get("占位符残留", 0) > 0:
        fix_report["fix_suggestions"].append({
            "target": "template_filler.py",
            "action": "对未填充占位符用ASR原文中的对应值填充, 或移除含占位符的句子",
            "reason": f"有{issue_counts['占位符残留']}条输出含未填充占位符",
        })
    if issue_counts.get("诊断缺失", 0) > 0:
        fix_report["fix_suggestions"].append({
            "target": "llm_client.py / B路 study_hint",
            "action": "确保B路自由生成始终返回study_hint, 异常报告必须有诊断",
            "reason": f"有{issue_counts['诊断缺失']}条异常报告无诊断提示",
        })
    if issue_counts.get("器官幻觉", 0) > 0:
        fix_report["fix_suggestions"].append({
            "target": "llm_client.py EF prompt",
            "action": "在prompt中明确禁止引入ASR原文未提及的器官/结构",
            "reason": f"有{issue_counts['器官幻觉']}条输出含输入未提及的器官",
        })
    if issue_counts.get("内容截断", 0) > 0:
        fix_report["fix_suggestions"].append({
            "target": "llm_client.py B路 prompt",
            "action": "要求B路保留ASR原文的全部描述, 不得省略任何发现",
            "reason": f"有{issue_counts['内容截断']}条输出明显短于输入",
        })

    # 保存JSON报告
    report_path = CSV_PATH.replace("test_results_1000.csv", "analysis_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(fix_report, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存: {report_path}")

    return fix_report


if __name__ == "__main__":
    analyze()
