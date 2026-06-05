#!/usr/bin/env python3
"""Deep probe: check actual endpoints and HTML structure."""

import ssl
import urllib.request
import urllib.error
import json
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = False
BASE = "https://47.109.151.238"

def fetch(url, headers=None, data=None, method="GET", timeout=20):
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

# 1. Check DOCTYPE in raw HTML
print("=" * 60)
print("HTML RAW FIRST 500 BYTES:")
status, headers, body, lat = fetch(BASE + "/")
print(body[:500].decode("utf-8", errors="replace"))
print(f"\nContent-Type: {headers.get('Content-Type', 'N/A')}")
print(f"Content-Length: {headers.get('Content-Length', 'N/A')}")
print(f"Server: {headers.get('Server', 'N/A')}")

# 2. Probe alternative fetal endpoints
print("\n" + "=" * 60)
print("PROBING FETAL ENDPOINTS:")
fetal_endpoints = [
    "/api/fetal_template",
    "/api/fetal",
    "/api/template/fetal",
    "/api/templates/fetal",
    "/api/report/fetal",
    "/api/reports/fetal",
    "/api/v1/fetal_template",
    "/api/structure",  # maybe they use /api/structure for everything
]
for ep in fetal_endpoints:
    status, headers, body, lat = fetch(BASE + ep)
    print(f"  GET {ep}: {status} [{lat:.0f}ms]")
    if status == 200:
        try:
            print(f"    Body: {body[:200].decode('utf-8', errors='replace')}")
        except:
            pass

# 3. Check if POST /api/structure with fetal text works
print("\n" + "=" * 60)
print("CHECKING /api/structure WITH FETAL TEXT:")
payload = json.dumps({"text": "胎儿双顶径7.2cm，头围26.5cm，腹围24.1cm，股骨长5.5cm"}).encode()
headers = {"Content-Type": "application/json"}
status, hdrs, body, lat = fetch(BASE + "/api/structure", data=payload, headers=headers, method="POST")
print(f"  POST /api/structure (fetal): {status} [{lat:.0f}ms]")
try:
    print(f"  Body: {body[:500].decode('utf-8', errors='replace')}")
except:
    print(f"  Body (raw): {body[:500]}")

# 4. Check /api/structure timing more carefully
print("\n" + "=" * 60)
print("DETAILED /api/structure TIMING (3 samples):")
for i in range(3):
    payload = json.dumps({"text": f"测试超声报告文本{i+1}"}).encode()
    status, hdrs, body, lat = fetch(BASE + "/api/structure", data=payload, headers={"Content-Type": "application/json"}, method="POST", timeout=30)
    print(f"  Sample {i+1}: status={status} lat={lat:.0f}ms body_len={len(body)}")
    if status == 200:
        try:
            j = json.loads(body)
            print(f"    JSON keys: {list(j.keys()) if isinstance(j, dict) else 'list('+str(len(j))+')'}")
        except:
            print(f"    Body preview: {body[:200]}")

# 5. Check if /api/report endpoint exists
print("\n" + "=" * 60)
print("PROBING REPORT ENDPOINTS:")
report_eps = [
    "/api/report",
    "/api/reports",
    "/api/template",
    "/api/templates",
]
for ep in report_eps:
    status, hdrs, body, lat = fetch(BASE + ep)
    print(f"  GET {ep}: {status} [{lat:.0f}ms]")

# 6. List all common endpoints
print("\n" + "=" * 60)
print("BROAD ENDPOINT PROBE:")
broad_eps = [
    "/api/",
    "/api/docs",
    "/api/openapi.json",
    "/api/swagger",
    "/",
]
for ep in broad_eps:
    status, hdrs, body, lat = fetch(BASE + ep)
    print(f"  GET {ep}: {status} [{lat:.0f}ms] ct={hdrs.get('Content-Type','')[:40]}")
