"""验证v4修复效果 - 针对性测试关键场景"""
import requests, json, re, sys, time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API = "https://localhost:8700/api/structure"

def strip_html(h):
    return re.sub(r'<[^>]+>', '', h or '').strip()

def test_case(name, exam_type, text, checks):
    """发送测试用例并验证"""
    payload = {"exam_type": exam_type, "text": text}
    try:
        resp = requests.post(API, json=payload, timeout=60, verify=False)
        data = resp.json()
    except Exception as e:
        print(f"  [{name}] ERROR: {e}")
        return False

    if not data.get("success"):
        print(f"  [{name}] FAIL: API返回失败")
        return False

    report = data.get("report", {})
    see = report.get("study_see", "")
    plain = strip_html(see)
    method = data.get("method", "")
    warnings = data.get("warnings", [])

    passed = True
    details = []
    for check_name, check_fn in checks.items():
        ok, msg = check_fn(plain, see, method, warnings)
        if not ok:
            passed = False
            details.append(f"FAIL: {check_name} - {msg}")
        else:
            details.append(f"OK: {check_name}")

    status = "PASS" if passed else "FAIL"
    print(f"  [{name}] {status} (method={method})")
    for d in details:
        print(f"    {d}")
    if not passed:
        print(f"    输出前150字: {plain[:150]}")
    return passed

# ============================================================
# 测试用例
# ============================================================
print("=" * 70)
print("v4修复验证 - 针对性测试")
print("=" * 70)

results = []

# --- 测试1: fast_normal路径的L2数值保全 ---
print("\n--- 测试组1: fast_normal L2数值保全 ---")

# 正常输入但含数值(应走fast_normal, L2应保全数值)
def check_num_preserved(plain, html, method, warnings):
    """检查特定数值是否在输出中或通过补充测量追加"""
    has_supplement = "补充测量" in plain
    has_warning = any("数值保全" in w for w in warnings)
    # 数值1.4和0.9至少有一个在输出中或有补充测量
    has_14 = "1.4" in plain
    has_09 = "0.9" in plain or "9" in plain
    if has_14 and has_09:
        return True, "数值均在输出中"
    if has_supplement or has_warning:
        return True, "L2补充测量已触发"
    return False, f"数值丢失(1.4={'Y' if has_14 else 'N'}, 0.9={'Y' if has_09 else 'N'}) 无补充"

results.append(test_case(
    "fast_normal-L2",
    "腹部超声",
    "肝脏大小形态正常，表面光滑，实质回声均匀，肝内未见明显占位性病变。胆囊大小约1.4cm，壁不毛糙，内见一强回声灶约0.9cm。",
    {"L2数值保全": check_num_preserved}
))

# --- 测试组2: P0-5去重 ---
print("\n--- 测试组2: P0-5去重效果 ---")

def check_no_duplicate(plain, html, method, warnings):
    """检查输出无重复句子"""
    if method == "fetal_template":
        return True, "胎儿模板跳过去重检查"
    sents = re.split(r'[。；]', plain)
    sents = [s.strip() for s in sents if len(s.strip()) > 8]
    seen = set()
    dupes = []
    for s in sents:
        sn = re.sub(r'\s+', '', s)
        if sn in seen:
            dupes.append(sn[:30])
        seen.add(sn)
    if dupes:
        return False, f"重复: '{dupes[0]}'"
    return True, "无重复"

results.append(test_case(
    "dedup-thyroid",
    "甲状腺超声",
    "甲状腺双侧叶形态正常，大小正常，实质回声均匀，未见明显结节及占位性病变。CDFI:甲状腺内血流分布正常。",
    {"无重复": check_no_duplicate}
))

# --- 测试组3: 早孕排除 ---
print("\n--- 测试组3: 早孕排除逻辑 ---")

def check_not_fetal(plain, html, method, warnings):
    """检查不走胎儿模板"""
    if method == "fetal_template":
        return False, "误入胎儿模板路径"
    return True, f"路径正确({method})"

results.append(test_case(
    "early-pregnancy",
    "妇产超声",
    "子宫前位，增大，宫腔内见一囊性回声，大小约2.9x0.7cm，可见胚芽及原始心管搏动。",
    {"非胎儿路径": check_not_fetal}
))

# --- 测试组4: abcdef_v3路径L2 ---
print("\n--- 测试组4: abcdef_v3 L2数值保全 ---")

def check_values_present(plain, html, method, warnings):
    """检查关键数值是否保留"""
    has_supplement = "补充测量" in plain
    has_28 = "2.8" in plain
    has_18 = "1.8" in plain
    if has_28 and has_18:
        return True, "数值均保留"
    if has_supplement:
        return True, "补充测量已触发"
    return False, f"2.8={'Y' if has_28 else 'N'}, 1.8={'Y' if has_18 else 'N'}"

results.append(test_case(
    "abcdef-l2",
    "腹部超声",
    "胆囊大小形态正常，壁不毛糙，内见一强回声灶约1.8cm，后方伴声影。胆总管内径约2.8cm。",
    {"L2数值": check_values_present}
))

# --- 测试组5: 占位符标记 ---
print("\n--- 测试组5: 占位符unfill标记 ---")

def check_unfill_tag(plain, html, method, warnings):
    """检查占位符是否有unfill标记"""
    if method == "fetal_template":
        return True, "胎儿模板跳过"
    has_unfill = 'class="unfill"' in html
    has_placeholder = bool(re.search(r'_{2,}', plain))
    if has_placeholder and has_unfill:
        return True, "占位符已标记unfill"
    if not has_placeholder:
        return True, "无占位符"
    return False, "有占位符但无unfill标记"

results.append(test_case(
    "unfill-tag",
    "腹部超声",
    "肝脏大小形态正常，表面光滑，实质回声均匀，肝内未见明显异常。",
    {"占位符标记": check_unfill_tag}
))

# --- 测试组6: 异常发现保留 ---
print("\n--- 测试组6: 异常发现保留 ---")

def check_abnormal_kept(plain, html, method, warnings):
    """检查异常发现是否保留"""
    abnormal_words = ["低回声", "结节", "不均"]
    found = [w for w in abnormal_words if w in plain]
    if found:
        return True, f"异常词保留: {found}"
    return False, "异常词全部消失"

results.append(test_case(
    "abnormal-keep",
    "甲状腺超声",
    "甲状腺右叶可见一低回声结节，大小约0.5x0.3cm，边界清晰，形态规则，内部回声不均。",
    {"异常保留": check_abnormal_kept}
))

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 70)
passed = sum(1 for r in results if r)
total = len(results)
print(f"结果: {passed}/{total} 通过")
if passed == total:
    print("全部通过!")
else:
    print(f"失败: {total - passed}项")
