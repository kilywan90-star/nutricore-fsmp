"""对比v1 vs v3三维核验结果"""
import csv, re, json, sys
from collections import Counter, defaultdict

CSV_V1 = r"e:\qoder\ultrasound-report-mvp\backend\test_results_1000.csv"
CSV_V3 = r"e:\qoder\ultrasound-report-mvp\backend\test_results_100_v3.csv"

def load_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def strip_html(h):
    return re.sub(r'<[^>]+>', '', h or '').strip()

ABNORMAL_SIGNS = (
    "结节","钙化","增生","增大","稍大","囊肿","息肉","肌瘤","积液","积水",
    "结石","斑块","狭窄","炎","扩张","欠均匀","毛糙","增厚","衰减",
    "回声增强","回声减低","无回声","低回声","高回声","不规则","模糊",
    "占位","包块","反流","饱满","不均匀",
)
NORMAL_TPL_KW = ("正常", "未见异常")
CROSS_ORGANS = {
    "腹部超声": {"甲状腺","乳腺","前列腺","精囊","子宫","卵巢","颈动脉","椎动脉","心室","心房"},
    "甲状腺超声": {"肝","胆囊","脾","肾","乳腺","前列腺","子宫","卵巢","颈动脉","心室"},
    "乳腺超声": {"肝","胆囊","脾","肾","甲状腺","前列腺","子宫","卵巢","颈动脉","心室"},
    "前列腺超声": {"肝","胆囊","脾","肾","甲状腺","乳腺","子宫","卵巢","颈动脉","心室"},
    "妇产超声": {"肝","胆囊","脾","肾","甲状腺","乳腺","前列腺","精囊","颈动脉","心室"},
    "血管超声": {"肝","胆囊","脾","肾","甲状腺","乳腺","前列腺","子宫","卵巢"},
    "心脏超声": {"肝","胆囊","脾","肾","甲状腺","乳腺","前列腺","子宫","卵巢","颈动脉","椎动脉"},
}
EARLY_PREGNANCY_SIGNS = ("孕囊", "卵黄囊", "胚芽", "心管搏动", "胎芽")
FETAL_MEAS_SIGNS = ("双顶径", "BPD", "头围", "HC", "腹围", "AC", "股骨长", "FL", "肱骨长")

def analyze(rows, label):
    # D1: 意图识别
    d1_fetal_misroute = 0
    d1_abn_to_normal = 0
    d1_normal_to_abn = 0
    d1_ids = set()

    # D2: 输出匹配
    d2_placeholder = 0
    d2_duplicate = 0
    d2_cross_organ = 0
    d2_ids = set()

    # D3: 补充内容
    d3_num_loss = 0
    d3_abn_disappear = 0
    d3_pct_loss = 0
    d3_supplement_ok = 0
    d3_ids = set()

    for r in rows:
        rid = r["序号"]
        exam = r["检查类型"]
        inp = r["输入文本"]
        tpl = r["意图模板"]
        out = strip_html(r["最终输出"])
        warn = r["警告信息"]
        method = r["处理方式"]
        has_abn = any(s in inp for s in ABNORMAL_SIGNS)

        # D1 checks
        if exam == "妇产超声" and method == "fetal_template":
            has_fm = any(s in inp for s in FETAL_MEAS_SIGNS)
            if not has_fm:
                d1_fetal_misroute += 1
                d1_ids.add(rid)

        is_normal_tpl = any(kw in tpl for kw in NORMAL_TPL_KW) if tpl else False
        asr_overridden = "ASR覆盖" in tpl or "ASR覆盖" in warn
        if has_abn and is_normal_tpl and not asr_overridden:
            d1_abn_to_normal += 1
            d1_ids.add(rid)
        if not has_abn and tpl and "自由生成" not in tpl:
            if any(s in tpl for s in ABNORMAL_SIGNS):
                d1_normal_to_abn += 1
                d1_ids.add(rid)

        # D2 checks
        phs = re.findall(r'_{2,}|(?<!\w)x\s*(?:mm|cm)(?!\w)|未测', out, re.IGNORECASE)
        if phs:
            # 检查占位符是否被标记为unfill (v3新行为: 保留是正确设计)
            has_unfill_tag = 'class="unfill"' in (r["最终输出"] or "")
            if not has_unfill_tag:
                d2_placeholder += 1
                d2_ids.add(rid)
            # 有unfill标记的占位符是预期行为, 不算问题

        # 重复内容
        if method != "fetal_template":
            sents = re.split(r'[。；]', out)
            sents = [s.strip() for s in sents if len(s.strip()) > 8]
            seen = set()
            for s in sents:
                sn = re.sub(r'\s+', '', s)
                if sn in seen:
                    d2_duplicate += 1
                    d2_ids.add(rid)
                    break
                seen.add(sn)

        # 跨类型器官
        cross = CROSS_ORGANS.get(exam, set())
        for o in cross:
            if len(o) >= 2 and o in out and o not in inp:
                idx = out.find(o)
                prefix = out[max(0, idx-8):idx]
                if "未见" not in prefix and "未探及" not in prefix:
                    d2_cross_organ += 1
                    d2_ids.add(rid)
                    break

        # D3 checks
        inp_nums = set(re.findall(r'\d+(?:\.\d+)?', inp))
        out_nums = set(re.findall(r'\d+(?:\.\d+)?', out))
        missing = {n for n in inp_nums - out_nums if float(n) >= 0.3}
        if missing and "补充测量" not in out:
            d3_num_loss += 1
            d3_ids.add(rid)

        if "补充测量" in out:
            d3_supplement_ok += 1

        inp_pcts = re.findall(r'\d+(?:\.\d+)?\s*%', inp)
        for pct in inp_pcts:
            pn = re.findall(r'\d+(?:\.\d+)?', pct)
            if pn and pn[0] not in out:
                d3_pct_loss += 1
                d3_ids.add(rid)

        # 异常发现消失
        for sign in ABNORMAL_SIGNS:
            if sign not in inp:
                continue
            if sign not in out:
                sign_idx = inp.find(sign)
                prefix = inp[max(0, sign_idx-5):sign_idx]
                if "未见" in prefix:
                    break
                d3_abn_disappear += 1
                d3_ids.add(rid)
                break

    all_ids = d1_ids | d2_ids | d3_ids
    clean = len(rows) - len(all_ids)

    return {
        "label": label,
        "total": len(rows),
        "clean": clean,
        "clean_pct": f"{clean/len(rows)*100:.1f}%",
        "d1": {
            "total_issues": len(d1_ids),
            "fetal_misroute": d1_fetal_misroute,
            "abn_to_normal": d1_abn_to_normal,
            "normal_to_abn": d1_normal_to_abn,
        },
        "d2": {
            "total_issues": len(d2_ids),
            "placeholder_raw": d2_placeholder,  # 未标记的占位符(问题)
            "duplicate": d2_duplicate,
            "cross_organ": d2_cross_organ,
        },
        "d3": {
            "total_issues": len(d3_ids),
            "num_loss": d3_num_loss,
            "abn_disappear": d3_abn_disappear,
            "pct_loss": d3_pct_loss,
            "supplement_ok": d3_supplement_ok,
        },
    }

v1 = load_csv(CSV_V1)
v3 = load_csv(CSV_V3)

# v1只取前100条做公平对比
v1_100 = v1[:100]

r1 = analyze(v1_100, "v1(前100条基线)")
r3 = analyze(v3, "v3(100条修复后)")

print("=" * 70)
print("v1 vs v3 三维核验对比 (各100条)")
print("=" * 70)

print(f"\n{'指标':<35} {'v1基线':>10} {'v3修复后':>10} {'变化':>10}")
print("-" * 70)

def fmt_change(old, new, lower_better=True):
    diff = new - old
    if diff == 0:
        return "="
    elif (diff < 0 and lower_better) or (diff > 0 and not lower_better):
        return f"{diff:+d} ↓好"
    else:
        return f"{diff:+d} ↑差"

print(f"{'三维全通过':<35} {r1['clean']:>10} {r3['clean']:>10} {fmt_change(len(v1_100)-r1['clean'], len(v3)-r3['clean']):>10}")
print(f"{'通过率':<35} {r1['clean_pct']:>10} {r3['clean_pct']:>10}")
print()
print(f"--- 维度1: 意图识别 ---")
print(f"{'  妇产→胎儿误判':<35} {r1['d1']['fetal_misroute']:>10} {r3['d1']['fetal_misroute']:>10} {fmt_change(r1['d1']['fetal_misroute'], r3['d1']['fetal_misroute']):>10}")
print(f"{'  异常→正常模板(无覆盖)':<35} {r1['d1']['abn_to_normal']:>10} {r3['d1']['abn_to_normal']:>10} {fmt_change(r1['d1']['abn_to_normal'], r3['d1']['abn_to_normal']):>10}")
print(f"{'  正常→异常模板':<35} {r1['d1']['normal_to_abn']:>10} {r3['d1']['normal_to_abn']:>10} {fmt_change(r1['d1']['normal_to_abn'], r3['d1']['normal_to_abn']):>10}")
print()
print(f"--- 维度2: 输出-模板匹配 ---")
print(f"{'  占位符(未标记,问题)':<35} {r1['d2']['placeholder_raw']:>10} {r3['d2']['placeholder_raw']:>10} {fmt_change(r1['d2']['placeholder_raw'], r3['d2']['placeholder_raw']):>10}")
print(f"{'  重复内容':<35} {r1['d2']['duplicate']:>10} {r3['d2']['duplicate']:>10} {fmt_change(r1['d2']['duplicate'], r3['d2']['duplicate']):>10}")
print(f"{'  跨类型器官':<35} {r1['d2']['cross_organ']:>10} {r3['d2']['cross_organ']:>10} {fmt_change(r1['d2']['cross_organ'], r3['d2']['cross_organ']):>10}")
print()
print(f"--- 维度3: 补充内容 ---")
print(f"{'  数值丢失无补充':<35} {r1['d3']['num_loss']:>10} {r3['d3']['num_loss']:>10} {fmt_change(r1['d3']['num_loss'], r3['d3']['num_loss']):>10}")
print(f"{'  异常发现消失':<35} {r1['d3']['abn_disappear']:>10} {r3['d3']['abn_disappear']:>10} {fmt_change(r1['d3']['abn_disappear'], r3['d3']['abn_disappear']):>10}")
print(f"{'  百分比丢失':<35} {r1['d3']['pct_loss']:>10} {r3['d3']['pct_loss']:>10} {fmt_change(r1['d3']['pct_loss'], r3['d3']['pct_loss']):>10}")
print(f"{'  补充测量已触发(正面)':<35} {r1['d3']['supplement_ok']:>10} {r3['d3']['supplement_ok']:>10}")

# 保存对比结果
comparison = {"v1_baseline": r1, "v3_fixed": r3}
path = CSV_V3.replace("test_results_100_v3.csv", "comparison_v1_v3.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(comparison, f, ensure_ascii=False, indent=2)
print(f"\n对比报告已保存: {path}")
