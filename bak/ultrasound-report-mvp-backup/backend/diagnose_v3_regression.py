"""诊断v3回归根因: 对比v1和v3的具体案例差异
重点排查:
1. 数值丢失为何从4增至21
2. 异常发现消失为何从1增至19
3. 补充测量触发为何从24降至8
"""
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

v1_all = load_csv(CSV_V1)
v3 = load_csv(CSV_V3)
v1 = v1_all[:100]

print("=" * 80)
print("v3回归根因诊断")
print("=" * 80)

# ============================================================
# 诊断1: 数值丢失 - 找出v3新增的丢失案例
# ============================================================
print("\n" + "=" * 80)
print("诊断1: 数值丢失加剧 (v1: 4 -> v3: 21)")
print("=" * 80)

def get_missing_nums(inp, out):
    inp_nums = set(re.findall(r'\d+(?:\.\d+)?', inp))
    out_nums = set(re.findall(r'\d+(?:\.\d+)?', out))
    return {n for n in inp_nums - out_nums if float(n) >= 0.3}

v1_num_loss_ids = set()
v3_num_loss_ids = set()
v1_num_loss_cases = {}
v3_num_loss_cases = {}

for r in v1:
    out = strip_html(r["最终输出"])
    missing = get_missing_nums(r["输入文本"], out)
    if missing and "补充测量" not in out:
        v1_num_loss_ids.add(r["序号"])
        v1_num_loss_cases[r["序号"]] = {"missing": missing, "row": r}

for r in v3:
    out = strip_html(r["最终输出"])
    missing = get_missing_nums(r["输入文本"], out)
    if missing and "补充测量" not in out:
        v3_num_loss_ids.add(r["序号"])
        v3_num_loss_cases[r["序号"]] = {"missing": missing, "row": r}

# 新增丢失
new_loss = v3_num_loss_ids - v1_num_loss_ids
print(f"\nv1数值丢失: {len(v1_num_loss_ids)}条")
print(f"v3数值丢失: {len(v3_num_loss_ids)}条")
print(f"v3新增丢失: {len(new_loss)}条")

# 分析新增丢失案例
if new_loss:
    print(f"\n--- v3新增数值丢失案例 (最多显示10条) ---")
    for rid in sorted(new_loss)[:10]:
        case = v3_num_loss_cases[rid]
        r = case["row"]
        inp = r["输入文本"]
        out = strip_html(r["最终输出"])
        raw_out = r["最终输出"] or ""
        method = r["处理方式"]
        warn = r["警告信息"] or ""
        
        print(f"\n  #{rid} [{r['检查类型']}] method={method}")
        print(f"    输入: {inp[:150]}")
        print(f"    输出: {out[:150]}")
        print(f"    丢失数值: {sorted(case['missing'])[:8]}")
        print(f"    含补充测量: {'补充测量' in out}")
        print(f"    含unfill标记: {'class=\"unfill\"' in raw_out}")
        print(f"    警告: {warn[:80]}")
        
        # 检查L2数值保全是否执行
        has_supplement = "补充测量" in out
        has_unfill = 'class="unfill"' in raw_out
        # 检查输出中是否有占位符(可能L2被P0-4干扰)
        placeholders = re.findall(r'_{2,}', out)
        print(f"    输出中占位符数量: {len(placeholders)}")
        if placeholders:
            print(f"    占位符示例: {placeholders[:5]}")

# 检查v3中"补充测量"触发情况
print(f"\n--- 补充测量触发对比 ---")
v1_supplement = sum(1 for r in v1 if "补充测量" in strip_html(r["最终输出"]))
v3_supplement = sum(1 for r in v3 if "补充测量" in strip_html(r["最终输出"]))
print(f"v1补充测量触发: {v1_supplement}次")
print(f"v3补充测量触发: {v3_supplement}次")

# 检查v3中有数值丢失但有占位符标记的案例(可能L2逻辑被P0-4干扰)
v3_loss_with_unfill = 0
v3_loss_without_unfill = 0
for rid in v3_num_loss_ids:
    case = v3_num_loss_cases[rid]
    raw_out = case["row"]["最终输出"] or ""
    if 'class="unfill"' in raw_out:
        v3_loss_with_unfill += 1
    else:
        v3_loss_without_unfill += 1
print(f"\nv3数值丢失案例中:")
print(f"  有unfill标记: {v3_loss_with_unfill} (L2可能正常但占位符标记后干扰检测)")
print(f"  无unfill标记: {v3_loss_without_unfill} (L2可能未执行)")


# ============================================================
# 诊断2: 异常发现消失 (v1: 1 -> v3: 19)
# ============================================================
print("\n" + "=" * 80)
print("诊断2: 异常发现消失加剧 (v1: 1 -> v3: 19)")
print("=" * 80)

def find_disappeared_signs(inp, out):
    disappeared = []
    for sign in ABNORMAL_SIGNS:
        if sign not in inp:
            continue
        if sign not in out:
            sign_idx = inp.find(sign)
            prefix = inp[max(0, sign_idx-5):sign_idx]
            if "未见" in prefix:
                continue
            disappeared.append(sign)
    return disappeared

v1_abn_loss_ids = set()
v3_abn_loss_ids = set()
v3_abn_loss_cases = {}

for r in v1:
    out = strip_html(r["最终输出"])
    disappeared = find_disappeared_signs(r["输入文本"], out)
    if disappeared:
        v1_abn_loss_ids.add(r["序号"])

for r in v3:
    out = strip_html(r["最终输出"])
    disappeared = find_disappeared_signs(r["输入文本"], out)
    if disappeared:
        v3_abn_loss_ids.add(r["序号"])
        v3_abn_loss_cases[r["序号"]] = {"disappeared": disappeared, "row": r}

new_abn_loss = v3_abn_loss_ids - v1_abn_loss_ids
print(f"\nv1异常消失: {len(v1_abn_loss_ids)}条")
print(f"v3异常消失: {len(v3_abn_loss_ids)}条")
print(f"v3新增异常消失: {len(new_abn_loss)}条")

if new_abn_loss:
    print(f"\n--- v3新增异常消失案例 (最多显示10条) ---")
    for rid in sorted(new_abn_loss)[:10]:
        case = v3_abn_loss_cases[rid]
        r = case["row"]
        inp = r["输入文本"]
        out = strip_html(r["最终输出"])
        method = r["处理方式"]
        tpl = r["意图模板"] or ""
        
        print(f"\n  #{rid} [{r['检查类型']}] method={method}")
        print(f"    输入: {inp[:150]}")
        print(f"    输出: {out[:150]}")
        print(f"    消失的异常词: {case['disappeared']}")
        print(f"    模板: {tpl[:80]}")
        
        # 检查是否走了胎儿模板(可能丢失了非胎儿内容)
        if method == "fetal_template":
            print(f"    *** 走了胎儿模板路径 ***")
        
        # 检查输出长度对比
        inp_len = len(re.sub(r'[\s\W]', '', inp))
        out_len = len(re.sub(r'[\s\W]', '', out))
        print(f"    输入有效长度: {inp_len}, 输出有效长度: {out_len} ({out_len/max(inp_len,1):.0%})")


# ============================================================
# 诊断3: 检查v3的P0-4和L2交互
# ============================================================
print("\n" + "=" * 80)
print("诊断3: P0-4占位符标记与L2数值保全的交互")
print("=" * 80)

# 检查v3中L2是否正常执行
# L2逻辑: 提取ASR数值 -> 检查输出是否包含 -> 缺失则追加"补充测量"
# P0-4逻辑: 将占位符标记为<i class="unfill">
# 潜在冲突: P0-4在L2之前执行可能改变输出格式, 影响L2的数值检测

v3_methods = Counter()
for r in v3:
    v3_methods[r["处理方式"]] += 1
print(f"\nv3处理方式分布:")
for method, count in v3_methods.most_common():
    print(f"  {method}: {count}")

# 检查走不同路径时的数值丢失率
print(f"\n按处理方式分析数值丢失:")
for method in set(r["处理方式"] for r in v3):
    method_rows = [r for r in v3 if r["处理方式"] == method]
    loss_count = 0
    supplement_count = 0
    for r in method_rows:
        out = strip_html(r["最终输出"])
        missing = get_missing_nums(r["输入文本"], out)
        if missing and "补充测量" not in out:
            loss_count += 1
        if "补充测量" in out:
            supplement_count += 1
    total = len(method_rows)
    print(f"  {method}: {total}条, 丢失{loss_count}条({loss_count/total*100:.0f}%), 补充{supplement_count}条")


# ============================================================
# 诊断4: 检查EF prompt是否导致LLM过度保守
# ============================================================
print("\n" + "=" * 80)
print("诊断4: LLM输出内容完整性分析")
print("=" * 80)

# 对比v1和v3中, 自由生成路径的输出长度
v1_free_lengths = []
v3_free_lengths = []

for r in v1:
    if "自由生成" in (r["意图模板"] or ""):
        out = strip_html(r["最终输出"])
        inp = r["输入文本"]
        inp_len = len(re.sub(r'[\s\W]', '', inp))
        out_len = len(re.sub(r'[\s\W]', '', out))
        v1_free_lengths.append(out_len / max(inp_len, 1))

for r in v3:
    if "自由生成" in (r["意图模板"] or ""):
        out = strip_html(r["最终输出"])
        inp = r["输入文本"]
        inp_len = len(re.sub(r'[\s\W]', '', inp))
        out_len = len(re.sub(r'[\s\W]', '', out))
        v3_free_lengths.append(out_len / max(inp_len, 1))

if v1_free_lengths:
    avg_v1 = sum(v1_free_lengths) / len(v1_free_lengths)
    print(f"\nv1自由生成路径: {len(v1_free_lengths)}条")
    print(f"  平均输出/输入比: {avg_v1:.2%}")
    print(f"  最小: {min(v1_free_lengths):.2%}, 最大: {max(v1_free_lengths):.2%}")

if v3_free_lengths:
    avg_v3 = sum(v3_free_lengths) / len(v3_free_lengths)
    print(f"\nv3自由生成路径: {len(v3_free_lengths)}条")
    print(f"  平均输出/输入比: {avg_v3:.2%}")
    print(f"  最小: {min(v3_free_lengths):.2%}, 最大: {max(v3_free_lengths):.2%}")

if v1_free_lengths and v3_free_lengths:
    if avg_v3 < avg_v1 * 0.9:
        print(f"\n  *** 警告: v3输出/输入比下降{((avg_v1-avg_v3)/avg_v1*100):.0f}%, LLM可能过度保守 ***")
    elif avg_v3 > avg_v1 * 1.1:
        print(f"\n  *** 注意: v3输出/输入比上升{((avg_v3-avg_v1)/avg_v1*100):.0f}% ***")


# ============================================================
# 诊断5: 模板路径的输出对比
# ============================================================
print("\n" + "=" * 80)
print("诊断5: 模板路径输出分析(非自由生成)")
print("=" * 80)

# 检查模板路径中, v3是否因为"保留占位符"指令导致LLM少填了内容
v3_tpl_cases = []
for r in v3:
    method = r["处理方式"]
    tpl = r["意图模板"] or ""
    if "自由生成" not in tpl and method != "fetal_template":
        out = strip_html(r["最终输出"])
        inp = r["输入文本"]
        missing = get_missing_nums(inp, out)
        if missing:
            v3_tpl_cases.append({
                "id": r["序号"],
                "exam": r["检查类型"],
                "input": inp,
                "output": out,
                "raw_output": r["最终输出"] or "",
                "missing": missing,
                "method": method,
                "template": tpl,
            })

print(f"\n模板路径数值丢失案例: {len(v3_tpl_cases)}条")
for case in v3_tpl_cases[:8]:
    print(f"\n  #{case['id']} [{case['exam']}] method={case['method']}")
    print(f"    输入: {case['input'][:150]}")
    print(f"    输出: {case['output'][:150]}")
    print(f"    丢失数值: {sorted(case['missing'])[:8]}")
    has_unfill = 'class="unfill"' in case["raw_output"]
    print(f"    有unfill标记: {has_unfill}")
    # 检查丢失的数值在模板中是否对应占位符
    for num in sorted(case["missing"])[:5]:
        # 看数值是否在输入中的上下文
        num_pattern = re.escape(num)
        m = re.search(num_pattern, case["input"])
        if m:
            ctx_start = max(0, m.start() - 15)
            ctx_end = min(len(case["input"]), m.end() + 15)
            ctx = case["input"][ctx_start:ctx_end]
            print(f"      数值'{num}'在输入中的上下文: ...{ctx}...")


# ============================================================
# 诊断6: 检查重复内容(P0-5去重是否正常工作)
# ============================================================
print("\n" + "=" * 80)
print("诊断6: P0-5去重效果检查")
print("=" * 80)

v1_dupe = 0
v3_dupe = 0
for r in v1:
    if r["处理方式"] == "fetal_template":
        continue
    out = strip_html(r["最终输出"])
    sents = re.split(r'[。；]', out)
    sents = [s.strip() for s in sents if len(s.strip()) > 8]
    seen = set()
    for s in sents:
        sn = re.sub(r'\s+', '', s)
        if sn in seen:
            v1_dupe += 1
            break
        seen.add(sn)

for r in v3:
    if r["处理方式"] == "fetal_template":
        continue
    out = strip_html(r["最终输出"])
    sents = re.split(r'[。；]', out)
    sents = [s.strip() for s in sents if len(s.strip()) > 8]
    seen = set()
    for s in sents:
        sn = re.sub(r'\s+', '', s)
        if sn in seen:
            v3_dupe += 1
            break
        seen.add(sn)

print(f"\nv1重复内容: {v1_dupe}条")
print(f"v3重复内容: {v3_dupe}条")
if v3_dupe > v1_dupe:
    print(f"*** 警告: v3重复内容增加{v3_dupe - v1_dupe}条, P0-5去重可能未生效 ***")
elif v3_dupe < v1_dupe:
    print(f"v3重复内容减少{v1_dupe - v3_dupe}条, P0-5去重有效")


# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 80)
print("诊断总结")
print("=" * 80)
print(f"""
数值丢失加剧:
  v1: {len(v1_num_loss_ids)}条 -> v3: {len(v3_num_loss_ids)}条
  新增丢失: {len(new_loss)}条
  补充测量触发: v1={v1_supplement}次, v3={v3_supplement}次

异常发现消失:
  v1: {len(v1_abn_loss_ids)}条 -> v3: {len(v3_abn_loss_ids)}条
  新增消失: {len(new_abn_loss)}条

重复内容:
  v1: {v1_dupe}条 -> v3: {v3_dupe}条
""")
