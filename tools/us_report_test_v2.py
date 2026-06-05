#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultrasound Report System — Full Test Suite (corrected endpoints)
Target: https://47.109.151.238/
"""

import http.client, ssl, json, time, re, sys

HOST = "47.109.151.238"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = False


def http_get(path, ua=None):
    conn = http.client.HTTPSConnection(HOST, context=ctx, timeout=15)
    headers = {}
    if ua:
        headers["User-Agent"] = ua
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
    b = json.dumps(body_dict).encode("utf-8")
    try:
        conn.request("POST", path, body=b, headers=headers)
        resp = conn.getresponse()
        resp_body = resp.read()
        conn.close()
        return resp.status, dict(resp.getheaders()), resp_body
    except Exception as e:
        conn.close()
        return 0, {}, str(e).encode()


all_rows = []


def record(no, cat, test, result, detail, note=""):
    all_rows.append((no, cat, test, result, detail, note))
    return result

# ============================================================
# SECTION 1: Browser Compatibility (Tests 1-7)
# ============================================================
print("=" * 70)
print("SECTION 1: Browser Compatibility (User-Agent simulation)")
print("=" * 70)

uas = [
    ("1-Chrome120-Win",
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("2-Safari17-macOS",
     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"),
    ("3-Firefox120",
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0"),
    ("4-Mobile-Chrome",
     "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"),
    ("5-WeChat-Browser",
     "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.5304.141 Mobile Safari/537.36 MicroMessenger/8.0.43(0x28002d33)"),
    ("6-IE11-Trident",
     "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko"),
    ("7-curl-noUA", ""),
]

for label, ua in uas:
    s, h, body = http_get("/", ua=ua)
    ct = h.get("Content-Type", "")
    sz = len(body)
    has_us = "超声" in body.decode("utf-8", errors="replace")
    ok = s == 200 and "text/html" in ct and has_us and sz > 1024
    r = "PASS" if ok else "FAIL"
    print(f"  {label:25s} | status={s} | size={sz}B | US={'Y' if has_us else 'N'} | {r}")
    record(label.split("-")[0], "UA兼容", label, r,
           f"status={s} size={sz}B US={'Y' if has_us else 'N'}")

# ============================================================
# SECTION 2: API Reliability (Tests 8-12)
# ============================================================

# --- Test 8: Stability ---
print("\n[Test 8] Stability: GET /api/patients/queue x200")
succ = fail = 0
t0 = time.time()
for i in range(200):
    try:
        s, _, _ = http_get("/api/patients/queue")
        if s == 200: succ += 1
        else: fail += 1
    except:
        fail += 1
elapsed = time.time() - t0
r8 = "PASS" if fail == 0 else ("WARN" if fail <= 2 else "FAIL")
print(f"  => {r8} | succ={succ}/200 fail={fail} | t={elapsed:.1f}s | rate={succ/2:.1f}%")
record("8", "API稳定", "queue x200", r8,
       f"succ={succ}/200 fail={fail} t={elapsed:.1f}s")

# --- Test 9: Jitter ---
print("\n[Test 9] Jitter/Latency: GET /api/health x50")
times = []
for _ in range(50):
    t0 = time.time()
    s, _, _ = http_get("/api/health")
    dt = (time.time() - t0) * 1000
    if s == 200:
        times.append(dt)
    time.sleep(0.03)

if times:
    b1 = sum(1 for t in times if t < 50)
    b2 = sum(1 for t in times if 50 <= t < 100)
    b3 = sum(1 for t in times if 100 <= t < 200)
    b4 = sum(1 for t in times if t >= 200)
    avg = sum(times)/len(times)
    p95 = sorted(times)[int(len(times)*0.95)]
    p99 = sorted(times)[int(len(times)*0.99)] if len(times) >= 100 else sorted(times)[-1]
    r9 = "PASS" if avg < 500 else "WARN"
    print(f"  => {r9} | avg={avg:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms | <50:{b1} 50-100:{b2} 100-200:{b3} >200:{b4}")
    record("9", "API抖动", "health x50", r9,
           f"avg={avg:.1f}ms p95={p95:.1f}ms [{b1}/{b2}/{b3}/{b4}]")
else:
    record("9", "API抖动", "health x50", "FAIL", "no response")

# --- Test 10: Flow dependency ---
print("\n[Test 10] Flow: quick-add -> queue x10 rounds")
# real endpoints: POST /api/patients/quick-add (minimal) + POST /api/structure + POST /api/transcribe
flow_ok = 0
for rnd in range(5):
    try:
        # Step 1: quick-add a patient
        s1, _, b1 = http_post("/api/patients/quick-add", {
            "name": f"FlowTest{rnd}",
            "age": 30,
            "gender": "男",
            "exam_type": "腹部超声"
        })
        data1 = json.loads(b1) if s1 in (200,201) else {}
        pid = data1.get("id") or data1.get("patient_id")

        # Step 2: structure report
        s2, _, b2 = http_post("/api/structure", {
            "text": f"超声所见：测试报告内容第{rnd}轮。超声提示：未见明显异常。"
        })

        # Step 3: get queue
        s3, _, _ = http_get("/api/patients/queue")

        ok = (s1 in (200,201)) and (s2 in (200,201,422)) and (s3 == 200)
        if ok:
            flow_ok += 1
            print(f"  Round {rnd+1} OK:  add={s1} pid={pid}  structure={s2}  queue={s3}")
        else:
            print(f"  Round {rnd+1} FAIL: add={s1} structure={s2} queue={s3}")
    except Exception as e:
        print(f"  Round {rnd+1} ERR: {e}")

r10 = "PASS" if flow_ok == 5 else ("WARN" if flow_ok >= 3 else "FAIL")
record("10", "顺序依赖", "quick-add->structure->queue x5", r10,
       f"ok={flow_ok}/5")

# --- Test 11: Reconnect ---
print("\n[Test 11] Reconnect: wait 60s then re-fetch")
s_before, _, _ = http_get("/api/patients/queue")
print(f"  Before: {s_before}")
print("  Sleeping 60s...")
time.sleep(60)
s_after, _, _ = http_get("/api/patients/queue")
print(f"  After:  {s_after}")
r11 = "PASS" if s_before == s_after == 200 else "WARN"
record("11", "重连", "60s reconnect", r11,
       f"before={s_before} after={s_after}")

# --- Test 12: Boundary values ---
print("\n[Test 12] Boundary value tests")
boundary_tests = [
    ("12a-age=0", {"name": "新生儿", "age": 0, "gender": "男", "exam_type": "腹部超声"}),
    ("12b-age=150", {"name": "高龄者", "age": 150, "gender": "男", "exam_type": "腹部超声"}),
    ("12c-name=1char", {"name": "张", "age": 25, "gender": "女", "exam_type": "腹部超声"}),
    ("12d-exam=long", {"name": "超长测试", "age": 25, "gender": "男", "exam_type": "A" * 100}),
]

for label, data in boundary_tests:
    s, _, b = http_post("/api/patients/quick-add", data)
    try:
        j = json.loads(b)
        preview = json.dumps(j, ensure_ascii=False)[:120]
    except:
        preview = b.decode("utf-8", errors="replace")[:120]
    # 200/201=accepted, 400/422=rejected correctly, both fine
    r = "PASS" if s in (200, 201, 400, 422) else "WARN"
    print(f"  {label:20s} => {r} | status={s} | {preview}")
    record(label.split("-")[0], "边界值", label, r, f"status={s}")

# ============================================================
# SECTION 3: Accessibility (Tests 13-14)
# ============================================================
print("\n" + "=" * 70)
print("SECTION 3: Page Accessibility")
print("=" * 70)

# --- Test 13: HTML structure ---
print("\n[Test 13] HTML structure checks")
s, h, body = http_get("/")
html = body.decode("utf-8", errors="replace")

checks = [
    ("lang=zh-CN", bool(re.search(r'<html[^>]*lang\s*=\s*["\']zh[-]?CN["\']', html))),
    ("meta viewport", bool(re.search(r'<meta[^>]*name\s*=\s*["\']viewport', html))),
    ("<title> present", "<title>" in html.lower() and "</title>" in html.lower()),
    ("No onerror handler", "onerror=" not in html.lower() and "onerror =" not in html.lower()),
    ("DOCTYPE present", html.lower().startswith("<!doctype") or "<!doctype" in html[:200].lower()),
    ("charset declared", "charset" in html[:500].lower() or "charset" in h.get("Content-Type","").lower()),
]

for label, ok in checks:
    r = "PASS" if ok else "FAIL"
    print(f"  {label:25s} => {r} | {'YES' if ok else 'NO'}")
    record("13", "可访问性", label, r, "YES" if ok else "NO")

# --- Test 14: API response format consistency ---
print("\n[Test 14] API response format consistency")
# known working endpoints from discovery
eps = [
    ("/api/patients/queue", "GET"),
    ("/api/health", "GET"),
    ("/api/patients/", "GET"),   # 404 but valid JSON
    ("/api/patients/quick-add", "POST"),
    ("/api/structure", "POST"),
    ("/api/transcribe", "POST"),
]

for ep, method in eps:
    if method == "GET":
        s, h, b = http_get(ep)
    else:
        # POST with minimal body to trigger validation
        payloads = {
            "/api/patients/quick-add": {"name":"x","age":1,"gender":"男","exam_type":"x"},
            "/api/structure": {"text":"x"},
            "/api/transcribe": {"file":"x"},
        }
        s, h, b = http_post(ep, payloads.get(ep, {}))
    ct = h.get("Content-Type", "")
    is_json = "application/json" in ct
    try:
        data = json.loads(b)
        has_struct = isinstance(data, (dict, list))
        has_flag = isinstance(data, dict) and any(k in data for k in ("success","detail","status","patients","message","data"))
        if isinstance(data, list):
            has_flag = True
    except:
        has_struct = has_flag = False
    ok = is_json and has_struct
    r = "PASS" if ok else "WARN"
    print(f"  {method:4s} {ep:30s} => {r} | {s} | json={'Y' if is_json else 'N'} | struct={'OK' if has_struct else 'NO'}")
    record("14", "API格式", f"{method} {ep}", r, f"status={s} json={'Y' if is_json else 'N'} struct={'OK' if has_struct else 'NO'}")

# ============================================================
# FINAL SUMMARY TABLE
# ============================================================
print("\n\n")
print("=" * 130)
print("FINAL TEST RESULTS SUMMARY TABLE")
print("Target: https://47.109.151.238/")
print("Date: 2026-06-03")
print("=" * 130)

def sym(r):
    return {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}.get(r, r)

head = f"| {'No.':<4} | {'Category':<10} | {'Test Item':<40} | {'Result':<6} | {'Data / Latency'} |"
sep_line = f"|{'-'*6}+{'-'*12}+{'-'*42}+{'-'*8}+{'-'*67}|"

print(sep_line)
print(head)
print(sep_line)

for no, cat, item, result, detail, note in all_rows:
    print(f"| {no:<4} | {cat:<10} | {item:<40} | {sym(result):<6} | {detail[:65]:<65} |")

print(sep_line)

p = sum(1 for r in all_rows if r[3] == "PASS")
w = sum(1 for r in all_rows if r[3] == "WARN")
f = sum(1 for r in all_rows if r[3] == "FAIL")
t = len(all_rows)
print(f"\nSummary: PASS={p}  WARN={w}  FAIL={f}  TOTAL={t}")
print(f"Pass rate: {(p/t*100):.1f}% ({(p+w)/t*100:.1f}% with warnings)")
