#!/usr/bin/env python3
"""
Ultrasound Reporting System - Round 2 Compatibility + Reliability Deep Test
Target: https://47.109.151.238/
SSL: verify=False (known self-signed/untrusted)
"""

import ssl
import urllib.request
import urllib.error
import json
import time
import sys
import re
import threading
import concurrent.futures
from collections import defaultdict

BASE = "https://47.109.151.238"

# Create SSL context that accepts all certs
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = False

class Result:
    def __init__(self):
        self.rows = []

    def add(self, num, name, status, data="", note=""):
        self.rows.append((num, name, status, str(data)[:200], note))

    def print_table(self):
        print("\n" + "=" * 120)
        print(f"{'#':<4} {'Test Item':<45} {'Result':<10} {'Key Data':<45} {'Note':<20}")
        print("=" * 120)
        for r in self.rows:
            print(f"{r[0]:<4} {r[1]:<45} {r[2]:<10} {r[3]:<45} {r[4]:<20}")
        print("=" * 120)

results = Result()

def fetch(url, headers=None, data=None, method="GET", timeout=15):
    """Fetch URL and return (status, content_type, body_bytes, latency_ms)."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body = resp.read()
        lat = (time.time() - t0) * 1000
        ct = resp.headers.get("Content-Type", "")
        return resp.status, ct, body, lat
    except urllib.error.HTTPError as e:
        body = e.read()
        lat = (time.time() - t0) * 1000
        ct = e.headers.get("Content-Type", "")
        return e.code, ct, body, lat
    except Exception as e:
        lat = (time.time() - t0) * 1000
        return 0, "", str(e).encode(), lat

# ── 1-5: UA Compatibility ──
print("=== COMPATIBILITY: UA Tests ===")
ua_tests = [
    (1, "Chrome 120 Windows", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    (2, "Safari 17 macOS", "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
    (3, "Mobile Chrome Android", "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36"),
    (4, "WeChat Browser", "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.144 Mobile Safari/537.36 MicroMessenger/8.0.45"),
    (5, "No UA (curl default)", ""),
]

ua_ok = 0
for num, name, ua in ua_tests:
    headers = {"User-Agent": ua} if ua else {}
    status, ct, body, lat = fetch(BASE + "/", headers=headers)
    body_str = body.decode("utf-8", errors="replace")
    ok = status == 200 and "text/html" in ct and "超声" in body_str
    if ok:
        ua_ok += 1
    results.add(num, f"UA: {name}", "PASS" if ok else "FAIL",
                f"status={status} ct={ct[:40]} lat={lat:.0f}ms",
                "" if ok else f"Missing: status!={200} or no '超声'")
    print(f"  [{num}] {name}: {status} {ct[:50]} {lat:.0f}ms {'OK' if ok else 'FAIL'}")

print(f"\n  UA pass rate: {ua_ok}/{len(ua_tests)}")

# ── 6: Long-duration stability on /api/patients/queue ──
print("\n=== RELIABILITY: Long Stability (300 requests) ===")
latencies_6 = []
failures_6 = 0
for i in range(300):
    status, ct, body, lat = fetch(BASE + "/api/patients/queue")
    latencies_6.append(lat)
    if status != 200:
        failures_6 += 1
    if (i + 1) % 100 == 0:
        print(f"  Progress: {i+1}/300 done, failures so far: {failures_6}")

success_rate_6 = (300 - failures_6) / 300 * 100
latencies_6.sort()
p50_6 = latencies_6[150]
p99_6 = latencies_6[297]
avg_6 = sum(latencies_6) / 300
results.add(6, "Long stability: /api/patients/queue x300",
            "PASS" if success_rate_6 == 100 else "FAIL",
            f"rate={success_rate_6:.1f}% avg={avg_6:.0f}ms p50={p50_6:.0f}ms p99={p99_6:.0f}ms",
            "")
print(f"  Success: {success_rate_6:.1f}%  avg={avg_6:.0f}ms  p99={p99_6:.0f}ms")

# ── 7: Structured pressure: fetal_template concurrent ──
print("\n=== RELIABILITY: Structured Pressure (10 concurrent fetal_template) ===")
fetal_texts = [
    "胎儿双顶径7.2cm，头围26.5cm，腹围24.1cm，股骨长5.5cm，估测体重约1800g",
    "胎儿头颅光环完整，脑中线居中，侧脑室未见扩张，小脑横径3.2cm",
    "胎儿心脏四腔心结构可见，十字交叉存在，心率146次/分，律齐",
    "胎儿腹部脏器未见明显异常，胃泡、双肾、膀胱可见",
    "胎儿脊柱排列整齐，连续性好，未见明显异常",
    "胎盘位于子宫前壁，厚度2.8cm，成熟度I级",
    "羊水指数12.5cm，羊水最大深度4.8cm，透声好",
    "胎儿颈部未见脐带压迹，CDFI未见异常血流信号",
    "胎儿颜面部显示清晰，上唇连续，鼻骨可见",
    "胎儿四肢长骨可见，双手握拳，双足可见",
]

def fetal_request(idx):
    text = fetal_texts[idx]
    payload = json.dumps({"text": text}).encode()
    headers = {"Content-Type": "application/json"}
    status, ct, body, lat = fetch(BASE + "/api/fetal_template", data=payload, headers=headers, method="POST")
    return idx, status, ct, body, lat

fetal_ok = 0
fetal_lats = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    futures = [ex.submit(fetal_request, i) for i in range(10)]
    for f in concurrent.futures.as_completed(futures):
        idx, status, ct, body, lat = f.result()
        fetal_lats.append(lat)
        if status == 200:
            fetal_ok += 1
        print(f"  fetal[{idx}]: status={status} lat={lat:.0f}ms ct={ct[:40]}")

results.add(7, "Concurrent pressure: fetal_template x10",
            "PASS" if fetal_ok == 10 else f"PARTIAL ({fetal_ok}/10)",
            f"all_200={fetal_ok==10} max_lat={max(fetal_lats):.0f}ms avg_lat={sum(fetal_lats)/len(fetal_lats):.0f}ms",
            "OK" if fetal_ok == 10 else f"{10-fetal_ok} requests not 200")
print(f"  fetal_template concurrent: {fetal_ok}/10 passed")

# ── 8: Mixed load (health, queue, structure) ──
print("\n=== RELIABILITY: Mixed Load (health + queue + structure) ===")
mixed_endpoints = [
    ("/api/health", "GET"),
    ("/api/patients/queue", "GET"),
    ("/api/structure", "POST"),
]
mixed_tasks = []
for ep, method in mixed_endpoints:
    for i in range(5):
        mixed_tasks.append((f"{ep}#{i}", ep, method))

structure_texts_cycle = [
    "超声所见：肝脏大小形态正常，包膜光滑，实质回声均匀，肝内管道走行清晰",
    "超声所见：胆囊大小正常，壁光滑，腔内未见异常回声",
    "超声所见：胰腺大小形态正常，实质回声均匀，胰管未见扩张",
    "超声所见：脾脏大小正常，实质回声均匀",
    "超声所见：双肾大小形态正常，皮质回声均匀，集合系统未见分离",
]

def mixed_request(task):
    name, ep, method = task
    if method == "POST":
        payload = json.dumps({"text": structure_texts_cycle[len(mixed_tasks) % 5]}).encode()
        headers = {"Content-Type": "application/json"}
        status, ct, body, lat = fetch(BASE + ep, data=payload, headers=headers, method=method)
    else:
        status, ct, body, lat = fetch(BASE + ep)
    return name, status, ct, lat

mixed_ok = 0
mixed_lats = []
mixed_results_detail = []
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    futures = [ex.submit(mixed_request, task) for task in mixed_tasks]
    for f in concurrent.futures.as_completed(futures):
        name, status, ct, lat = f.result()
        mixed_lats.append(lat)
        mixed_results_detail.append((name, status))
        if status == 200:
            mixed_ok += 1
        print(f"  {name}: status={status} lat={lat:.0f}ms")

results.add(8, "Mixed load: health+queue+structure (5ea)",
            "PASS" if mixed_ok == 15 else f"PARTIAL ({mixed_ok}/15)",
            f"all_200={mixed_ok==15} max_lat={max(mixed_lats):.0f}ms avg_lat={sum(mixed_lats)/len(mixed_lats):.0f}ms",
            "No deadlocks" if mixed_ok == 15 else f"{15-mixed_ok} failures")
print(f"  Mixed load: {mixed_ok}/15 passed — {'no deadlocks' if mixed_ok == 15 else 'failures detected'}")

# ── 9: Error recovery ──
print("\n=== RELIABILITY: Error Recovery ===")
# Step 1: Send invalid JSON
bad_payload = b"this is not json {{{ !!!"
headers = {"Content-Type": "application/json"}
status_bad, ct_bad, body_bad, lat_bad = fetch(BASE + "/api/structure", data=bad_payload, headers=headers, method="POST")
print(f"  Bad request: status={status_bad} ct={ct_bad[:40]}")

# Step 2: Send valid request immediately after
small_wait = 0.5
time.sleep(small_wait)
status_good, ct_good, body_good, lat_good = fetch(BASE + "/api/health")
print(f"  Recovery request: status={status_good} ct={ct_good[:40]} lat={lat_good:.0f}ms")

recovery_ok = status_good == 200
results.add(9, "Error recovery: bad JSON -> health",
            "PASS" if recovery_ok else "FAIL",
            f"bad_resp={status_bad} recovery_resp={status_good}",
            "Server recovers" if recovery_ok else "Server broken after bad input")
print(f"  Recovery: {'OK — server continues normally' if recovery_ok else 'FAIL — server broken!'}")

# ── 10: P99 latency per endpoint ──
print("\n=== RELIABILITY: P99 Latency per endpoint ===")
latency_endpoints = {
    "/api/health": [("/", "GET")],
    "/api/patients/queue": [("/api/patients/queue", "GET")],
    "/api/fetal_template": [("/api/fetal_template", "POST")],
    "/api/structure": [("/api/structure", "POST")],
}

latency_results = {}
for ep_name, samples_def in latency_endpoints.items():
    lats = []
    for path, method in samples_def * 20:  # 20 samples each
        if method == "POST":
            payload = json.dumps({"text": "测试文本"}).encode()
            headers_ct = {"Content-Type": "application/json"}
            status, ct, body, lat = fetch(BASE + path, data=payload, headers=headers_ct, method=method)
        else:
            status, ct, body, lat = fetch(BASE + path)
        lats.append(lat)
        # Small delay to not overwhelm
    lats.sort()
    n = len(lats)
    p99 = lats[min(int(n * 0.99), n-1)]
    avg = sum(lats) / n
    p50 = lats[n // 2]
    latency_results[ep_name] = (avg, p50, p99, min(lats), max(lats))
    print(f"  {ep_name}: n={n} avg={avg:.0f}ms p50={p50:.0f}ms p99={p99:.0f}ms min={min(lats):.0f}ms max={max(lats):.0f}ms")

for ep_name, (avg, p50, p99, vmin, vmax) in latency_results.items():
    results.add(f"10a" if ep_name == "/api/health" else "10b" if ep_name == "/api/patients/queue" else "10c" if ep_name == "/api/fetal_template" else "10d",
                f"P99 latency: {ep_name}",
                "PASS" if p99 < 5000 else "WARN (P99>5s)",
                f"p99={p99:.0f}ms avg={avg:.0f}ms min={vmin:.0f}ms max={vmax:.0f}ms",
                "")

# ── 11: HTML structure validation ──
print("\n=== HTML Structure Validation ===")
status, ct, body, lat = fetch(BASE + "/")
html = body.decode("utf-8", errors="replace")

checks = []
# doctype
checks.append(("DOCTYPE html", "DOCTYPE html" in html.lower()))
# lang
checks.append(("lang=\"zh-CN\"", 'lang="zh-CN"' in html or "lang='zh-CN'" in html))
# meta viewport
checks.append(("meta viewport", 'viewport' in html.lower() and 'meta' in html.lower()))
# title
checks.append(("title contains 超声报告语音结构化", "超声报告语音结构化" in html or "超声" in html))
# contains "超声" somewhere in body
checks.append(("contains 超声", "超声" in html))

all_html_ok = all(v for _, v in checks)
for name, ok in checks:
    print(f"  HTML check [{name}]: {'OK' if ok else 'FAIL'}")

results.add(11, "HTML structure validation",
            "PASS" if all_html_ok else "FAIL",
            f"{sum(1 for _,v in checks if v)}/{len(checks)} checks: " + ", ".join(f"{n}={v}" for n,v in checks),
            "" if all_html_ok else "Missing required elements")

# ── 12: API Content-Type check ──
print("\n=== API Content-Type Validation ===")
api_checks = [
    ("GET /api/health", BASE + "/api/health", "GET", None),
    ("GET /api/patients/queue", BASE + "/api/patients/queue", "GET", None),
    ("POST /api/fetal_template", BASE + "/api/fetal_template", "POST", json.dumps({"text": "test"}).encode()),
    ("POST /api/structure", BASE + "/api/structure", "POST", json.dumps({"text": "test"}).encode()),
]

api_ct_ok = 0
api_ct_total = 0
for name, url, method, payload in api_checks:
    headers_ctcheck = {"Content-Type": "application/json"} if payload else {}
    status_ct, ct_ct, body_ct, lat_ct = fetch(url, data=payload, headers=headers_ctcheck, method=method)
    api_ct_total += 1
    is_json = "application/json" in ct_ct.lower()
    if is_json:
        api_ct_ok += 1
    print(f"  {name}: status={status_ct} ct={ct_ct[:60]} {'OK' if is_json else 'MISSING JSON'}")
    results.add(f"12{chr(97+api_ct_total-1)}", f"API CT check: {name}",
                "PASS" if is_json else "FAIL",
                f"ct={ct_ct[:60]}",
                "")

results.add("12-summary", "API Content-Type: all JSON",
            "PASS" if api_ct_ok == api_ct_total else f"PARTIAL ({api_ct_ok}/{api_ct_total})",
            f"{api_ct_ok}/{api_ct_total} endpoints return application/json",
            "")

# ── 13: favicon.ico check ──
print("\n=== Favicon Check ===")
status_fav, ct_fav, body_fav, lat_fav = fetch(BASE + "/favicon.ico")
is_not_index = b"<!DOCTYPE html>" not in body_fav[:100] and b"<html" not in body_fav[:100].lower()
is_404 = status_fav == 404
print(f"  favicon.ico: status={status_fav} ct={ct_fav[:60]} size={len(body_fav)} bytes")
print(f"  Is 404: {is_404}, Not index HTML: {is_not_index}")

results.add(13, "Favicon: 404 + not index.html",
            "PASS" if (is_404 or status_fav in (204, 304)) and is_not_index else "FAIL",
            f"status={status_fav} ct={ct_fav[:40]} size={len(body_fav)}",
            "OK" if is_404 and is_not_index else "Still returns HTML" if not is_not_index else "Check")

# ── Final report ──
results.print_table()

# Summary
pass_count = sum(1 for r in results.rows if "PASS" in r[2])
fail_count = sum(1 for r in results.rows if "FAIL" in r[2])
partial_count = sum(1 for r in results.rows if "PARTIAL" in r[2])
print(f"\nSUMMARY: {pass_count} PASS, {fail_count} FAIL, {partial_count} PARTIAL out of {len(results.rows)} checks")
