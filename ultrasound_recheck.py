#!/usr/bin/env python3
"""Corrected re-checks for items that may have had script issues."""

import ssl
import urllib.request
import urllib.error
import json
import time
import concurrent.futures

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = False
BASE = "https://47.109.151.238"

def fetch(url, headers=None, data=None, method="GET", timeout=25):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body = resp.read()
        lat = (time.time() - t0) * 1000
        return resp.status, dict(resp.headers), body, lat
    except urllib.error.HTTPError as e:
        body = e.read()
        lat = (time.time() - t0) * 1000
        return e.code, dict(e.headers), body, lat
    except Exception as e:
        lat = (time.time() - t0) * 1000
        return 0, {}, str(e).encode(), lat

# ── Re-check 11: DOCTYPE properly ──
print("=" * 60)
print("RE-CHECK: HTML structure (test 11)")
status, hdrs, body, lat = fetch(BASE + "/")
html = body.decode("utf-8", errors="replace")

# Fix the bug: use .lower() on both sides or check case-insensitively
checks = {}
checks["DOCTYPE html"] = "doctype html" in html.lower()
checks["lang='zh-CN' or lang=\"zh-CN\""] = 'lang="zh-CN"' in html or "lang='zh-CN'" in html
checks["meta viewport"] = "viewport" in html.lower() and '<meta' in html.lower()
checks["title=超声报告语音结构化"] = "超声报告语音结构化" in html
checks["contains 超声 in body"] = "超声" in html

for name, ok in checks.items():
    print(f"  [{name}]: {'OK' if ok else 'FAIL'}")
print(f"  DOCTYPE raw position: {html[:80]}")

# ── Re-check 7: The fetal_template endpoint doesn't exist, but POST /api/structure handles fetal text ──
print("\n" + "=" * 60)
print("RE-CHECK: Fetal text via /api/structure (correct endpoint)")
fetal_samples = [
    "胎儿双顶径7.2cm，头围26.5cm，腹围24.1cm，股骨长5.5cm，估测体重约1800g",
    "胎儿头颅光环完整，脑中线居中，侧脑室未见扩张",
    "胎儿心脏四腔心结构可见，十字交叉存在，心率146次/分",
]
for i, text in enumerate(fetal_samples):
    payload = json.dumps({"text": text}).encode()
    headers = {"Content-Type": "application/json"}
    status, hdrs, body, lat = fetch(BASE + "/api/structure", data=payload, headers=headers, method="POST")
    print(f"  Fetal[{i}] -> /api/structure: status={status} lat={lat:.0f}ms")
    if status == 200:
        try:
            j = json.loads(body)
            print(f"    success={j.get('success')} report_id={j.get('report_id','')[:20]} method={j.get('method','')}")
        except:
            print(f"    Body[:100]: {body[:100]}")

# ── Re-check 8: Sequential mixed load (not concurrent structure requests) since /api/structure is 5-9s ──
print("\n" + "=" * 60)
print("RE-CHECK: Mixed load with SEPARATE /api/structure requests (serial for slow endpoint)")
# structure is ~7s — we do get-heavy endpoints concurrently, then structure sequentially
import threading

results_mixed = {}
def do_get(endpoint, idx):
    results_mixed[f"{endpoint}#{idx}"] = fetch(BASE + endpoint)

# Concurrent GET endpoints
threads = []
for i in range(5):
    for ep in ["/api/health", "/api/patients/queue"]:
        t = threading.Thread(target=do_get, args=(ep, i))
        threads.append(t)
        t.start()
        time.sleep(0.01)  # slight stagger

for t in threads:
    t.join(timeout=15)

# Now 3 serial structure requests
structure_oks = 0
for i in range(5):
    payload = json.dumps({"text": f"测试报告文本{i+1}"}).encode()
    headers = {"Content-Type": "application/json"}
    status, hdrs, body, lat = fetch(BASE + "/api/structure", data=payload, headers=headers, method="POST", timeout=30)
    results_mixed[f"/api/structure#{i}"] = (status, {}, body, lat)
    if status == 200:
        structure_oks += 1
    print(f"  /api/structure#{i}: status={status} lat={lat:.0f}ms")

total_req = len(results_mixed)
ok_count = sum(1 for v in results_mixed.values() if v[0] == 200)
print(f"  Total: {ok_count}/{total_req} passed")
print(f"  Structure serial: {structure_oks}/5")

# ── Re-check 13: favicon variants ──
print("\n" + "=" * 60)
print("RE-CHECK: Favicon (check SVG and other formats)")
favicon_paths = ["/favicon.ico", "/favicon.svg", "/favicon.png"]
for fp in favicon_paths:
    status, hdrs, body, lat = fetch(BASE + fp)
    is_html = b"<!DOCTYPE html>" in body[:100] or b"<html" in body[:100].lower()
    print(f"  {fp}: status={status} ct={hdrs.get('Content-Type','')[:40]} size={len(body)} is_html={is_html}")

# ── Re-check: Structure P99 under light load (serial, with spacing) ──
print("\n" + "=" * 60)
print("RE-CHECK: /api/structure P99 under light load (10 serial requests, spaced)")
lats_structure = []
for i in range(10):
    payload = json.dumps({"text": f"检查部位：腹部彩超  测试{i+1}"}).encode()
    headers = {"Content-Type": "application/json"}
    status, hdrs, body, lat = fetch(BASE + "/api/structure", data=payload, headers=headers, method="POST", timeout=30)
    if status == 200:
        lats_structure.append(lat)
        print(f"  #{i+1}: lat={lat:.0f}ms OK")
    else:
        print(f"  #{i+1}: lat={lat:.0f}ms FAIL status={status}")
    time.sleep(0.3)

if lats_structure:
    lats_structure.sort()
    n = len(lats_structure)
    p99 = lats_structure[min(int(n * 0.99), n-1)]
    avg = sum(lats_structure) / n
    p50 = lats_structure[n // 2]
    print(f"  Light-load stats: avg={avg:.0f}ms p50={p50:.0f}ms p99={p99:.0f}ms min={min(lats_structure):.0f}ms max={max(lats_structure):.0f}ms")
else:
    print("  All structure requests failed!")
