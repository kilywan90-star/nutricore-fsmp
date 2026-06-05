#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超声报告系统 — 兼容性/API可靠性/可访问性 综合测试
目标: https://47.109.151.238/
"""

import http.client
import ssl
import json
import time
import re
import sys

HOST = "47.109.151.238"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = False


def http_get(path, ua=None, headers_extra=None):
    conn = http.client.HTTPSConnection(HOST, context=ctx, timeout=15)
    headers = {}
    if ua:
        headers["User-Agent"] = ua
    else:
        headers["User-Agent"] = ""
    if headers_extra:
        headers.update(headers_extra)
    try:
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp.status, dict(resp.getheaders()), body
    except Exception as e:
        conn.close()
        return 0, {}, str(e).encode()


def http_post(path, body_dict):
    conn = http.client.HTTPSConnection(HOST, context=ctx, timeout=15)
    headers = {"Content-Type": "application/json"}
    body = json.dumps(body_dict).encode("utf-8")
    try:
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        resp_body = resp.read()
        conn.close()
        return resp.status, dict(resp.getheaders()), resp_body
    except Exception as e:
        conn.close()
        return 0, {}, str(e).encode()


# ============================================================
# 一、浏览器兼容性测试 (1-7)
# ============================================================
print("=" * 70)
print("一、浏览器兼容性测试 (User-Agent 模拟)")
print("=" * 70)

uas = [
    ("1. Chrome 120 Win",
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("2. Safari 17 macOS",
     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"),
    ("3. Firefox 120",
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0"),
    ("4. Mobile Chrome",
     "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"),
    ("5. WeChat Browser",
     "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.5304.141 Mobile Safari/537.36 MicroMessenger/8.0.43(0x28002d33)"),
    ("6. IE11 Trident",
     "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko"),
    ("7. curl (no UA)",
     ""),
]

comp_results = []

for label, ua in uas:
    try:
        status, headers, body = http_get("/", ua=ua)
        ct = headers.get("Content-Type", "")
        size = len(body)
        has_cs = "超声" in body.decode("utf-8", errors="replace")

        if status == 200 and "text/html" in ct and has_cs and size > 1024:
            result = "PASS"
        elif status == 200 and "text/html" not in ct:
            result = "WARN"
        elif status >= 400 and "IE" in label:
            result = "OK-DEGRADE"
        else:
            result = "FAIL"

        print(f"  {label:30s} => [{result}] status={status} size={size}B CT={ct[:40]} US={'Y' if has_cs else 'N'}")
        comp_results.append((label, result, f"status={status} size={size}B", ""))
    except Exception as e:
        print(f"  {label:30s} => [FAIL] {e}")
        comp_results.append((label, "FAIL", str(e)[:60], ""))

# ============================================================
# 二、API可靠性测试 (8-12)
# ============================================================
print("\n" + "=" * 70)
print("二、API可靠性测试")
print("=" * 70)

api_results = []

# ---- Test 8: 连续请求稳定性 ----
print("\n[Test 8] 连续请求稳定性: GET /api/patients/queue x200")
succ, fail = 0, 0
t0 = time.time()
for i in range(200):
    try:
        s, _, _ = http_get("/api/patients/queue")
        if s == 200:
            succ += 1
        else:
            fail += 1
    except:
        fail += 1
elapsed = time.time() - t0
rate_pct = succ / 200 * 100
result_8 = "PASS" if fail == 0 else ("WARN" if fail <= 2 else "FAIL")
print(f"  => [{result_8}] 成功={succ} 失败={fail} 耗时={elapsed:.1f}s 成功率={rate_pct:.1f}%")
api_results.append(("8. 连续稳定性", result_8, f"succ={succ}/200 fail={fail} t={elapsed:.1f}s", f"rate={rate_pct:.1f}%"))

# ---- Test 9: 请求抖动 ----
print("\n[Test 9] 请求抖动: GET /api/health x50")
times = []
for _ in range(50):
    t0 = time.time()
    s, _, b = http_get("/api/health")
    dt = (time.time() - t0) * 1000
    if s in (200, 404):
        times.append(dt)
    # short delay between requests
    time.sleep(0.02)

if times:
    b1 = sum(1 for t in times if t < 50)
    b2 = sum(1 for t in times if 50 <= t < 100)
    b3 = sum(1 for t in times if 100 <= t < 200)
    b4 = sum(1 for t in times if t >= 200)
    avg = sum(times) / len(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    p99 = sorted(times)[int(len(times) * 0.99)] if len(times) >= 100 else sorted(times)[-1]
    detail = f"avg={avg:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms [{b1}/{b2}/{b3}/{b4}]"
    result_9 = "PASS" if avg < 500 else "WARN"
    print(f"  => [{result_9}] {detail}")
    api_results.append(("9. 请求抖动", result_9, detail, ""))
else:
    print("  => [FAIL] 无有效响应")
    api_results.append(("9. 请求抖动", "FAIL", "no valid response", ""))

# ---- Test 10: 顺序依赖 ----
print("\n[Test 10] 顺序依赖流程: create patient -> get queue x5轮")
flow_ok = 0
flow_fail = 0
for r in range(5):
    try:
        s1, _, b1 = http_post("/api/patients", {
            "name": "TestPatient" + str(r),
            "age": 28 + r,
            "gender": "male" if r % 2 == 0 else "female",
            "phone": "1380000" + str(r).zfill(4)
        })
        s2, _, _ = http_get("/api/patients/queue")
        if s1 in (200, 201) and s2 == 200:
            flow_ok += 1
            print(f"  第{r+1}轮 OK: create={s1} queue={s2}")
        else:
            flow_fail += 1
            print(f"  第{r+1}轮 FAIL: create={s1} queue={s2}")
    except Exception as e:
        flow_fail += 1
        print(f"  第{r+1}轮 ERROR: {e}")
result_10 = "PASS" if flow_ok == 5 else ("WARN" if flow_ok >= 3 else "FAIL")
api_results.append(("10. 顺序依赖", result_10, f"ok={flow_ok}/5 fail={flow_fail}", ""))

# ---- Test 11: 服务器重连 ----
print("\n[Test 11] 服务器重连: 间隔60秒后重连")
s_before, _, _ = http_get("/api/patients/queue")
print(f"  首次请求: status={s_before}")
print(f"  等待60秒...")
time.sleep(60)
s_after, _, _ = http_get("/api/patients/queue")
print(f"  60秒后: status={s_after}")
result_11 = "PASS" if s_before == 200 and s_after == 200 else "WARN"
api_results.append(("11. 服务器重连", result_11, f"before={s_before} after={s_after}", ""))

# ---- Test 12: 边界值 ----
print("\n[Test 12] 边界值测试")
boundary_tests = [
    ("age=0 (新生儿)", {"name": "新生儿", "age": 0, "gender": "male"}),
    ("age=150 (高龄)", {"name": "高龄老人", "age": 150, "gender": "male"}),
    ("name=单字符", {"name": "张", "age": 25, "gender": "male"}),
]

for label, data in boundary_tests:
    s, _, b = http_post("/api/patients", data)
    try:
        resp = json.loads(b)
        resp_str = json.dumps(resp, ensure_ascii=False)[:120]
    except:
        resp_str = b.decode("utf-8", errors="replace")[:120]
    # 200/201 = accepted, 400/422 = correctly rejected
    ok = s in (200, 201, 400, 422)
    result = "PASS" if ok else "WARN"
    print(f"  {label:30s} => [{result}] status={s} resp={resp_str[:80]}")
    api_results.append(("12. 边界-" + label.split("(")[0].strip(), result, f"status={s}", resp_str[:50]))

# exam_type 超长
s, _, b = http_post("/api/exams", {"exam_type": "超" * 100, "patient_id": 99999, "status": "pending"})
try:
    resp = json.loads(b)
    resp_str = json.dumps(resp, ensure_ascii=False)[:120]
except:
    resp_str = b.decode("utf-8", errors="replace")[:120]
ok = s in (200, 201, 400, 422)
result = "PASS" if ok else "WARN"
print(f"  exam_type超长(100字) => [{result}] status={s} resp={resp_str[:80]}")
api_results.append(("12. 边界-exam超长", result, f"status={s}", resp_str[:50]))

# ============================================================
# 三、页面可访问性 (13-14)
# ============================================================
print("\n" + "=" * 70)
print("三、页面可访问性测试")
print("=" * 70)

acc_results = []

# ---- Test 13: HTML结构 ----
print("\n[Test 13] 首页HTML结构分析")
_, _, html = http_get("/")
html_str = html.decode("utf-8", errors="replace")
html_lower = html_str.lower()

structure_checks = [
    ("lang=zh-CN", bool(re.search(r'<html[^>]*lang\s*=\s*["\']zh-CN["\']', html_str))),
    ("meta viewport", bool(re.search(r'<meta[^>]*name\s*=\s*["\']viewport["\']', html_str))),
    ("<title>标签", bool(re.search(r'<title[^>]*>', html_str)) and bool(re.search(r'</title>', html_str))),
    ("无onerror处理器", "onerror=" not in html_lower),
    ("DOCTYPE声明", html_lower.startswith("<!doctype") or "<!doctype" in html_lower[:200]),
    ("charset声明", "charset" in html_lower[:500] or "charset" in dict(http_get("/")[1]).get("Content-Type", "")),
]

for check_name, ok in structure_checks:
    result = "PASS" if ok else "FAIL"
    print(f"  {check_name:30s} => [{result}] {'YES' if ok else 'NO'}")
    acc_results.append(("13. " + check_name, result, "YES" if ok else "NO", ""))

# ---- Test 14: API格式一致性 ----
print("\n[Test 14] API响应格式一致性")
api_eps = ["/api/patients/queue", "/api/health", "/api/patients", "/api/exams", "/api/reports"]
for ep in api_eps:
    s, headers, b = http_get(ep)
    ct = headers.get("Content-Type", "")
    is_json = "application/json" in ct
    try:
        data = json.loads(b)
        is_struct = isinstance(data, (dict, list))
        if isinstance(data, dict):
            has_flag = any(k in data for k in ("success", "code", "status", "message", "data"))
        else:
            has_flag = True
    except:
        is_struct = False
        has_flag = False
    ok = is_json and is_struct and has_flag
    result = "PASS" if ok else "WARN"
    print(f"  {ep:30s} => [{result}] status={s} json={'Y' if is_json else 'N'} struct={'OK' if is_struct else 'NO'}")
    acc_results.append((f"14. {ep}", result, f"status={s} json={'Y' if is_json else 'N'}", ""))

# ============================================================
# 汇总表格
# ============================================================
print("\n\n")
print("=" * 120)
print("测 试 结 果 汇 总 表")
print("目标: https://47.109.151.238/")
print("=" * 120)

all_rows = []
for row in comp_results:
    label, result, detail, note = row
    test_id = label.split(".")[0].strip()
    cat = "UA兼容性"
    all_rows.append((test_id, cat, label, result, detail, note))
for row in api_results:
    label, result, detail, note = row
    test_id = label.split(".")[0].strip()
    cat = "API可靠性"
    all_rows.append((test_id, cat, label, result, detail, note))
for row in acc_results:
    label, result, detail, note = row
    test_id = label.split(".")[0].strip()
    cat = "可访问性"
    all_rows.append((test_id, cat, label, result, detail, note))

sym_map = {"PASS": "PASS", "OK-DEGRADE": "DEGR", "WARN": "WARN", "FAIL": "FAIL"}

sep = "-" * 120
print(f"{'No.':<5} {'类别':<10} {'测试项':<35} {'结果':<6} {'数据/耗时'}")
print(sep)

for no, cat, item, result, detail, note in all_rows:
    sym = sym_map.get(result, "???")
    print(f"{no:<5} {cat:<10} {item:<35} {sym:<6} {detail}")

print(sep)
p_count = sum(1 for r in all_rows if r[3] == "PASS")
w_count = sum(1 for r in all_rows if r[3] == "WARN")
f_count = sum(1 for r in all_rows if r[3] == "FAIL")
d_count = sum(1 for r in all_rows if r[3] == "OK-DEGRADE")
total = len(all_rows)
print(f"\n总览: PASS={p_count}  WARN={w_count}  FAIL={f_count}  DEGRADE={d_count}  TOTAL={total}")
print(f"通过率: {(p_count+d_count)/total*100:.1f}% (含合理降级)")
