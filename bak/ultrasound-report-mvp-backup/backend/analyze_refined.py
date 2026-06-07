"""精化分析: 排除误报, 定位真正需要修复的问题"""
import csv, re, json, sys
from collections import Counter, defaultdict

CSV = r"e:\qoder\ultrasound-report-mvp\backend\test_results_1000.csv"
rows = []
with open(CSV, "r", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append(r)

def strip_html(h):
    return re.sub(r'<[^>]+>', '', h or '').strip()

ABN = ('结节','钙化','增大','稍大','低回声','高回声','无回声','占位','包块','不均匀',
       '毛糙','增厚','斑块','息肉','囊肿','结石','增生','饱满','反流','扩张')

# ===== 1. 真正模板偏差: 排除ASR覆盖已触发 =====
real_template_bias = []
for r in rows:
    tpl = r["意图模板"]
    warn = r["警告信息"]
    inp = r["输入文本"]
    has_abn = any(s in inp for s in ABN)
    if not has_abn:
        continue
    normal_kw = ("正常", "未见异常")
    is_normal_tpl = any(kw in tpl for kw in normal_kw)
    if not is_normal_tpl or "自由生成" in tpl:
        continue
    asr_overridden = "ASR覆盖" in tpl or "ASR覆盖" in warn
    if asr_overridden:
        continue
    real_template_bias.append(r)

print(f"=== 真正模板偏差(无ASR覆盖): {len(real_template_bias)}条 ===")
for r in real_template_bias[:5]:
    rid, et, tpl = r["序号"], r["检查类型"], r["意图模板"]
    inp, out = r["输入文本"][:80], strip_html(r["最终输出"])[:80]
    print(f"  #{rid} [{et}] 模板={tpl}")
    print(f"    输入: {inp}")
    print(f"    输出: {out}\n")

# ===== 2. 占位符残留: 分类胎儿 vs 非胎儿 =====
fetal_placeholder = []
real_placeholder = []
for r in rows:
    out = strip_html(r["最终输出"])
    phs = re.findall(r'_{2,}|(?<!\w)x\s*(?:mm|cm)(?!\w)|未测', out, re.IGNORECASE)
    if not phs:
        continue
    method = r["处理方式"]
    if method == "fetal_template" or "胎儿" in r["意图模板"]:
        fetal_placeholder.append(r)
    else:
        real_placeholder.append((r, phs))

print(f"\n=== 胎儿路径占位符(已知): {len(fetal_placeholder)}条 ===")
print(f"=== 非胎儿占位符(需修复): {len(real_placeholder)}条 ===")
for r, phs in real_placeholder[:10]:
    rid, et, tpl = r["序号"], r["检查类型"], r["意图模板"]
    inp, out = r["输入文本"][:80], strip_html(r["最终输出"])[:100]
    print(f"  #{rid} [{et}] 模板={tpl} 占位符={phs[:3]}")
    print(f"    输入: {inp}")
    print(f"    输出: {out}\n")

# ===== 3. 重复内容: 排除胎儿模板 =====
real_dup = []
for r in rows:
    out = strip_html(r["最终输出"])
    method = r["处理方式"]
    if method == "fetal_template":
        continue
    sentences = re.split(r'[。；]', out)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
    seen = set()
    dupes = []
    for s in sentences:
        if s in seen:
            dupes.append(s[:40])
        seen.add(s)
    if dupes:
        real_dup.append((r, dupes))
        continue
    found = False
    for length in range(15, min(len(out)//2, 40)):
        for i in range(len(out) - length):
            sub = out[i:i+length]
            if out.count(sub) > 1 and not all(c in '，。、；' for c in sub):
                real_dup.append((r, [sub[:40]]))
                found = True
                break
        if found:
            break

print(f"\n=== 非胎儿重复内容(需修复): {len(real_dup)}条 ===")
for r, dupes in real_dup[:5]:
    rid, et, tpl = r["序号"], r["检查类型"], r["意图模板"]
    print(f"  #{rid} [{et}] 模板={tpl}")
    print(f"    重复: {dupes[0]}")
    print(f"    输出: {strip_html(r['最终输出'])[:120]}\n")

# ===== 4. 器官幻觉: 排除胎儿模板和正常描述 =====
EXAM_ORGANS = {
    "腹部超声": ["肝","胆囊","胆总管","胰腺","脾","肾"],
    "甲状腺超声": ["甲状腺"],
    "乳腺超声": ["乳腺","腋窝"],
    "前列腺超声": ["前列腺","精囊","膀胱"],
    "妇产超声": ["子宫","宫腔","卵巢","附件","盆腔"],
    "血管超声": ["颈动脉","椎动脉","锁骨下动脉","内中膜"],
    "心脏超声": ["心室","心房","室间隔","瓣膜"],
}
real_halluc = []
for r in rows:
    out = strip_html(r["最终输出"])
    inp = r["输入文本"]
    exam = r["检查类型"]
    method = r["处理方式"]
    if method == "fetal_template":
        continue
    if "淋巴结" in out and "淋巴结" not in inp and exam == "甲状腺超声":
        if any(p in out for p in ("未见明显肿大淋巴结","未见肿大淋巴结","未见肿大")):
            continue
    if "管腔" in out and "管腔" not in inp and exam == "血管超声":
        continue
    halluc = []
    for et, organs in EXAM_ORGANS.items():
        if et == exam:
            continue
        for o in organs:
            if len(o) >= 2 and o in out and o not in inp:
                halluc.append(f"{et}:{o}")
    if halluc:
        real_halluc.append((r, halluc))

print(f"\n=== 真正器官幻觉(需修复): {len(real_halluc)}条 ===")
for r, hall in real_halluc[:5]:
    rid, et = r["序号"], r["检查类型"]
    print(f"  #{rid} [{et}] 幻觉={hall[:3]}")
    print(f"    输入: {r['输入文本'][:80]}")
    print(f"    输出: {strip_html(r['最终输出'])[:100]}\n")

# ===== 5. 诊断缺失: 排除输入实际正常 =====
real_no_diag = []
for r in rows:
    diag = r["诊断提示"]
    if diag and diag.strip():
        continue
    inp = r["输入文本"]
    cleaned = inp
    for pat in [r'未见明显?\S{0,4}(?:结节|异常|占位|包块|积液|钙化|异常回声)',
                r'未见\S{0,2}(?:肿大|增厚|扩张)',
                r'未探及\S{0,4}(?:异常|血流)']:
        cleaned = re.sub(pat, '', cleaned)
    true_abn = ('结节','钙化','增大','囊肿','息肉','肌瘤','积液','积水','结石','斑块',
                '狭窄','扩张','增厚','毛糙','反流','占位','低回声','高回声','无回声',
                '不均匀','增生','饱满')
    has_true_abn = any(s in cleaned for s in true_abn)
    if has_true_abn:
        real_no_diag.append(r)

print(f"\n=== 真正诊断缺失(需修复): {len(real_no_diag)}条 ===")
for r in real_no_diag[:5]:
    rid, et = r["序号"], r["检查类型"]
    print(f"  #{rid} [{et}]")
    print(f"    输入: {r['输入文本'][:80]}")
    print(f"    输出: {strip_html(r['最终输出'])[:80]}\n")

# ===== 汇总 =====
print("=" * 60)
print("精化后真正需要修复的问题汇总:")
print(f"  1. 模板偏差(无覆盖):     {len(real_template_bias)}条")
print(f"  2. 非胎儿占位符残留:     {len(real_placeholder)}条")
print(f"  3. 胎儿占位符残留:       {len(fetal_placeholder)}条")
print(f"  4. 非胎儿重复内容:       {len(real_dup)}条")
print(f"  5. 真正器官幻觉:         {len(real_halluc)}条")
print(f"  6. 真正诊断缺失:         {len(real_no_diag)}条")
print(f"  7. 正常矛盾:             2条(需人工确认)")
print(f"  8. 数值丢失:             1条")

# 保存精化报告
fix_targets = {
    "fetal_placeholder": [int(r["序号"]) for r in fetal_placeholder],
    "non_fetal_placeholder": [(r["序号"], phs) for r, phs in real_placeholder],
    "duplicate_content": [(r["序号"], d[0]) for r, d in real_dup],
    "organ_hallucination": [(r["序号"], h[:2]) for r, h in real_halluc],
    "missing_diagnosis": [int(r["序号"]) for r in real_no_diag],
    "template_bias_no_override": [int(r["序号"]) for r in real_template_bias],
    "summary": {
        "fetal_placeholder": len(fetal_placeholder),
        "non_fetal_placeholder": len(real_placeholder),
        "duplicate_content": len(real_dup),
        "organ_hallucination": len(real_halluc),
        "missing_diagnosis": len(real_no_diag),
        "template_bias": len(real_template_bias),
    }
}
path = CSV.replace("test_results_1000.csv", "fix_targets.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(fix_targets, f, ensure_ascii=False, indent=2, default=str)
print(f"\n修复目标已保存: {path}")
