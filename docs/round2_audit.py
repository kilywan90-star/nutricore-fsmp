#!/usr/bin/env python3
"""
Round 2 Comprehensive Security + Functional + Performance Audit
Target: https://47.109.151.238/
All items verified with actual HTTP requests — no inference.
"""

import ssl
import urllib.request
import urllib.error
import json
import time
import sys
import re
import concurrent.futures
from collections import defaultdict

BASE = "https://47.109.151.238"
HEADERS_DEFAULT = {"Content-Type": "application/json", "Accept": "application/json"}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = False

RESULTS = []

def P(i, test, result, key_data="", delta=""):
    RESULTS.append((i, test, result, key_data, delta))

def request(method, path, body=None, headers=None, timeout=30):
    url = BASE + path
    data = None
    if body is not None:
        if isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    h = dict(HEADERS_DEFAULT)
    if headers:
        h.update(headers)
    for k, v in h.items():
        req.add_header(k, v)
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
        latency = (time.time() - start) * 1000
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, dict(resp.getheaders()), body, latency
    except urllib.error.HTTPError as e:
        latency = (time.time() - start) * 1000
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, dict(e.headers), body, latency
    except Exception as e:
        latency = (time.time() - start) * 1000
        return 0, {}, str(e), latency

# ============================================================
# ITEM 1: CORS - Access-Control-Allow-Credentials should NOT appear
# ============================================================
def test_1_cors():
    print("="*60)
    print("[1] CORS: Access-Control-Allow-Credentials check")
    # Test both a GET and an OPTIONS preflight
    for path in ["/api/health", "/api/patients/queue"]:
        # OPTIONS preflight
        code, headers, body, lat = request("OPTIONS", path, headers={"Origin": "https://evil.com"})
        acac = headers.get("Access-Control-Allow-Credentials", None)
        acao = headers.get("Access-Control-Allow-Origin", None)
        if acac and acac.lower() == "true":
            P(1, f"CORS creds {path}", "FAIL", f"ACA-Credentials=true present", "Round1 FAIL")
            return
        print(f"  OPTIONS {path}: ACA-Credentials={acac}, ACA-Origin={acao}")
    P(1, "CORS ACA-Credentials", "PASS", "No ACA-Credentials=true found", "Round1 FAIL -> now PASS")

# ============================================================
# ITEM 2: Security Headers
# ============================================================
def test_2_security_headers():
    print("="*60)
    print("[2] Security Headers check")
    code, headers, body, lat = request("GET", "/api/health")
    checks = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": None,  # just check presence
    }
    all_pass = True
    details = []
    for h, expected in checks.items():
        val = headers.get(h, None)
        if expected is None:
            if val is not None:
                details.append(f"{h}={val}")
            else:
                details.append(f"{h}=MISSING")
                all_pass = False
        else:
            if val and val.lower() == expected.lower():
                details.append(f"{h}={val}")
            else:
                details.append(f"{h}={val} (expected {expected})")
                all_pass = False
    result = "PASS" if all_pass else "FAIL"
    P(2, "Security Headers", result, "; ".join(details), "Round1 FAIL -> verify")

# ============================================================
# ITEM 3: Version leak via /api/health
# ============================================================
def test_3_version_leak():
    print("="*60)
    print("[3] Version leak via /api/health")
    code, headers, body, lat = request("GET", "/api/health")
    has_version = False
    version_found = ""
    # Check body for version patterns
    for pattern in [r'"version"\s*:\s*"[^"]*"', r'"version"\s*:\s*[\d.]+', r'version.*[\d]+\.[\d]+\.[\d]+']:
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            has_version = True
            version_found = m.group(0)
            break
    # Also check headers
    for h in ["Server", "X-Powered-By", "X-Version"]:
        if h in headers:
            has_version = True
            version_found = f"{h}={headers[h]}"
    if has_version:
        P(3, "Version Leak", "FAIL", f"Version found: {version_found}", "Round1 had 0.3.0")
    else:
        P(3, "Version Leak", "PASS", "No version info in response", "Round1 FAIL (0.3.0) -> now PASS")
    print(f"  Body (first 300): {body[:300]}")
    # Also check response headers for version
    print(f"  Server={headers.get('Server','N/A')}, X-Powered-By={headers.get('X-Powered-By','N/A')}")

# ============================================================
# ITEM 4: Age validation (age=-1, age=999 should return 422)
# ============================================================
def test_4_age_validation():
    print("="*60)
    print("[4] Age validation - extreme values")
    # First create a patient or get queue to understand the API shape
    # Test age=-1
    payload_neg = {"name": "TestAgeNeg", "age": -1, "gender": "male"}
    code, headers, body, lat = request("POST", "/api/patients", payload_neg)
    neg_pass = (code == 422)

    # Test age=999 (unlikely but should fail)
    payload_999 = {"name": "TestAge999", "age": 999, "gender": "male"}
    code, headers, body, lat = request("POST", "/api/patients", payload_999)
    big_pass = (code == 422)

    # Test age=0 (should also be rejected for newborns? depends on system)
    payload_0 = {"name": "TestAge0", "age": 0, "gender": "male"}
    code_0, _, body_0, _ = request("POST", "/api/patients", payload_0)
    zero_pass = (code_0 == 422)

    result = "PASS" if (neg_pass and big_pass) else "FAIL"
    details = f"age=-1 -> {code} (expect 422); age=999 -> {code} (expect 422); age=0 -> {code_0}"
    P(4, "Age Validation", result, details, "Round1 0-age accepted -> verify fix")

# ============================================================
# ITEM 5: Name length validation
# ============================================================
def test_5_name_length():
    print("="*60)
    print("[5] Name length validation")
    long_name = "A" * 300  # 300 chars
    payload = {"name": long_name, "age": 30, "gender": "male"}
    code, headers, body, lat = request("POST", "/api/patients", payload)
    result = "PASS" if code == 422 else "FAIL"
    P(5, "Name Length (300 chars)", result, f"Status={code}, expect 422", "Round1 verify")

# ============================================================
# ITEM 6: Path traversal
# ============================================================
def test_6_path_traversal():
    print("="*60)
    print("[6] Path traversal tests")
    paths = [
        "/../../etc/passwd",
        "/..%2f..%2fetc%2fpasswd",
        "/%2e%2e/%2e%2e/etc/passwd",
        "/api/../etc/passwd",
    ]
    all_blocked = True
    details = []
    for p in paths:
        code, h, b, lat = request("GET", p)
        # Should get 400, 403, 404 or similar — NOT 200 with file content
        is_blocked = (code in [400, 403, 404, 405]) or ("root:" not in b.lower())
        if not is_blocked:
            all_blocked = False
        details.append(f"{p} -> {code}")
        print(f"  {p} -> {code} (body len={len(b)})")
    result = "PASS" if all_blocked else "FAIL"
    P(6, "Path Traversal", result, "; ".join(details), "Round1 verify")

# ============================================================
# ITEM 7: Static file access - nginx config
# ============================================================
def test_7_static_files():
    print("="*60)
    print("[7] Static files - nginx config access")
    paths = [
        "/nginx.conf",
        "/etc/nginx/nginx.conf",
        "/.env",
        "/.git/config",
        "/static/../nginx.conf",
    ]
    all_blocked = True
    details = []
    for p in paths:
        code, h, b, lat = request("GET", p)
        is_blocked = code != 200
        if not is_blocked:
            all_blocked = False
        details.append(f"{p} -> {code}")
        print(f"  {p} -> {code}")
    result = "PASS" if all_blocked else "FAIL"
    P(7, "Static File Access", result, "; ".join(details), "Round1 verify")

# ============================================================
# ITEM 8: /api/health concurrency 30 requests
# ============================================================
def test_8_health_concurrency():
    print("="*60)
    print("[8] /api/health concurrency 30")
    def one_req():
        return request("GET", "/api/health")
    latencies = []
    successes = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(one_req) for _ in range(30)]
        for f in concurrent.futures.as_completed(futures):
            code, h, b, lat = f.result()
            latencies.append(lat)
            if code == 200:
                successes += 1
    success_rate = (successes / 30) * 100
    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    max_lat = max(latencies) if latencies else 0
    min_lat = min(latencies) if latencies else 0
    sorted_lats = sorted(latencies)
    p50 = sorted_lats[15] if len(sorted_lats) > 15 else sorted_lats[-1]
    p95 = sorted_lats[int(29 * 0.95)] if len(sorted_lats) > 1 else sorted_lats[-1]
    result = "PASS" if success_rate == 100 else "FAIL"
    P(8, "Health Concurrency 30", result,
      f"Rate={success_rate}%, Avg={avg_lat:.1f}ms, P50={p50:.1f}ms, P95={p95:.1f}ms, Min={min_lat:.1f}ms, Max={max_lat:.1f}ms",
      "Baseline")

# ============================================================
# ITEM 9: /api/patients/queue 100 requests sequential
# ============================================================
def test_9_queue_100():
    print("="*60)
    print("[9] /api/patients/queue 100 sequential")
    latencies = []
    successes = 0
    errors = []
    for i in range(100):
        code, h, b, lat = request("GET", "/api/patients/queue")
        latencies.append(lat)
        if code == 200:
            successes += 1
        else:
            errors.append(f"req{i}:{code}")
    success_rate = (successes / 100) * 100
    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    sorted_lats = sorted(latencies)
    p50 = sorted_lats[50] if len(sorted_lats) > 50 else sorted_lats[-1]
    p95 = sorted_lats[95] if len(sorted_lats) > 95 else sorted_lats[-1]
    result = "PASS" if success_rate == 100 else "FAIL"
    P(9, "Queue 100 Sequential", result,
      f"Rate={success_rate}%, Avg={avg_lat:.1f}ms, P50={p50:.1f}ms, P95={p95:.1f}ms",
      "Baseline")

# ============================================================
# ITEM 10: fetal_template structured 10 requests latency
# ============================================================
def test_10_fetal_template():
    print("="*60)
    print("[10] fetal_template structured 10 requests")
    # Need to find the correct endpoint - try common paths
    endpoints = [
        "/api/templates/fetal",
        "/api/template/fetal",
        "/api/reports/template/fetal",
        "/api/ultrasound/fetal-template",
    ]
    working_ep = None
    for ep in endpoints:
        code, h, b, lat = request("GET", ep)
        print(f"  Try {ep} -> {code}")
        if code in [200, 201, 405]:  # 405 = method not allowed, try POST
            working_ep = ep
            if code == 405:
                # Try POST
                code2, h2, b2, lat2 = request("POST", ep, {"text": "中孕四为二十二到二十六 胎心一百四十五 后壁"})
                if code2 in [200, 201, 422]:
                    # 422 is OK - means it's processing
                    working_ep = (ep, "POST")
            break

    if working_ep is None:
        # Try more paths
        for ep in ["/api/fetal/template", "/api/ob/template", "/api/obstetric/template"]:
            code, h, b, lat = request("POST", ep, {"text": "中孕四为二十二到二十六 胎心一百四十五 后壁"})
            print(f"  Try POST {ep} -> {code}")
            if code in [200, 201, 422]:
                working_ep = (ep, "POST")
                break

    if working_ep is None:
        P(10, "Fetal Template 10x", "SKIP", "Could not find fetal_template endpoint", "Need endpoint info")
        return

    latencies = []
    successes = 0
    for i in range(10):
        start = time.time()
        if isinstance(working_ep, tuple):
            code, h, b, lat = request(working_ep[1], working_ep[0],
                                       {"text": "中孕四为二十二到二十六 胎心一百四十五 后壁"})
        else:
            code, h, b, lat = request("GET", working_ep)
        latencies.append(lat)
        if code in [200, 201]:
            successes += 1

    success_rate = (successes / 10) * 100
    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    max_lat = max(latencies) if latencies else 0
    result = "PASS" if success_rate >= 80 else "FAIL"
    P(10, "Fetal Template 10x", result,
      f"Rate={success_rate}%, Avg={avg_lat:.1f}ms, Max={max_lat:.1f}ms, EP={working_ep}",
      "Baseline")

# ============================================================
# ITEM 11: Patient CRUD full flow
# ============================================================
def test_11_patient_crud():
    print("="*60)
    print("[11] Patient CRUD full flow")
    patient_id = None
    details = []

    # Create
    payload = {"name": "Round2TestPatient", "age": 35, "gender": "female"}
    code, h, b, lat = request("POST", "/api/patients", payload)
    details.append(f"Create={code}")
    if code in [200, 201]:
        try:
            data = json.loads(b)
            patient_id = data.get("id") or data.get("patient_id") or data.get("_id")
            # If nested
            if patient_id is None and "data" in data:
                patient_id = data["data"].get("id") or data["data"].get("patient_id")
        except:
            pass
    print(f"  Create: code={code}, id={patient_id}, body={b[:200]}")

    if patient_id is None:
        # Try to get from queue
        code2, h2, b2, _ = request("GET", "/api/patients/queue")
        try:
            data2 = json.loads(b2)
            if isinstance(data2, list) and len(data2) > 0:
                patient_id = data2[-1].get("id") or data2[-1].get("_id") or data2[-1].get("patient_id")
        except:
            pass
        print(f"  Fallback ID from queue: {patient_id}")

    if patient_id is None:
        P(11, "Patient CRUD", "FAIL", "Could not get patient ID: " + ";".join(details), "Round1 verify")
        return

    # Read
    code, h, b, lat = request("GET", f"/api/patients/{patient_id}")
    details.append(f"Read={code}")
    print(f"  Read: code={code}")

    # Update
    update_payload = {"name": "Round2TestUpdated", "age": 36, "gender": "female"}
    code, h, b, lat = request("PUT", f"/api/patients/{patient_id}", update_payload)
    if code in [404, 405]:
        code, h, b, lat = request("PATCH", f"/api/patients/{patient_id}", update_payload)
    details.append(f"Update={code}")
    print(f"  Update: code={code}")

    # Verify update
    code, h, b, lat = request("GET", f"/api/patients/{patient_id}")
    name_updated = "Round2TestUpdated" in b
    details.append(f"VerifyUpdate={'OK' if name_updated else 'FAIL'}")

    # Delete
    code, h, b, lat = request("DELETE", f"/api/patients/{patient_id}")
    details.append(f"Delete={code}")

    # Verify delete
    code, h, b, lat = request("GET", f"/api/patients/{patient_id}")
    deleted_ok = code in [404, 410]
    details.append(f"VerifyDelete={'OK' if deleted_ok else 'FAIL'}")

    all_ok = deleted_ok and name_updated and (code in [200, 201, 204] for code in [code])
    result = "PASS" if deleted_ok and name_updated else "PARTIAL"
    P(11, "Patient CRUD", result, "; ".join(details), "Round1 verify")

# ============================================================
# ITEM 12: Obstetric Chinese number recognition
# ============================================================
def test_12_ob_chinese():
    print("="*60)
    print("[12] Obstetric Chinese number recognition")
    text = "中孕四为二十二到二十六 胎心一百四十五 后壁"
    # Try multiple endpoints
    endpoints = [
        ("POST", "/api/reports/structure", {"text": text, "type": "obstetric"}),
        ("POST", "/api/reports/obstetric", {"text": text}),
        ("POST", "/api/ob/structure", {"text": text}),
        ("POST", "/api/ultrasound/structure", {"text": text, "modality": "obstetric"}),
        ("POST", "/api/llm/structure", {"text": text, "template": "obstetric"}),
    ]
    found = False
    for method, path, payload in endpoints:
        code, h, b, lat = request(method, path, payload)
        print(f"  {method} {path} -> {code}, body={b[:300]}")
        if code in [200, 201]:
            found = True
            # Check for Chinese number parsing
            # Expect: "中孕" -> second trimester, "二十二到二十六" -> 22-26 (weeks)
            # "胎心一百四十五" -> FHR 145, "后壁" -> posterior wall
            has_structure = False
            checks = []
            for kw in ["22", "26", "145", "后壁", "胎盘", "胎心"]:
                if kw in b:
                    has_structure = True
                    checks.append(kw)
            if has_structure:
                P(12, "OB Chinese Numbers", "PASS", f"Parsed: {','.join(checks)}", "Round1 verify")
            else:
                P(12, "OB Chinese Numbers", "PARTIAL", f"Response but unclear parsing: {b[:200]}", "Round1 verify")
            return
        elif code == 422:
            found = True
            P(12, "OB Chinese Numbers", "PARTIAL", f"Returned 422, body={b[:200]}", "Round1 verify")
            return
    if not found:
        P(12, "OB Chinese Numbers", "SKIP", "No working obstetric endpoint found", "Need endpoint info")

# ============================================================
# ITEM 13: Abdominal LLM structure
# ============================================================
def test_13_abdominal_llm():
    print("="*60)
    print("[13] Abdominal LLM structure")
    text = "肝脏形态大小正常 包膜光滑 实质回声均匀 肝内管道结构清晰 胆囊大小约6.5x2.5cm 壁光滑 腔内未见异常回声"
    endpoints = [
        ("POST", "/api/reports/structure", {"text": text, "type": "abdominal"}),
        ("POST", "/api/reports/abdominal", {"text": text}),
        ("POST", "/api/abdominal/structure", {"text": text}),
        ("POST", "/api/llm/structure", {"text": text, "template": "abdominal"}),
        ("POST", "/api/ultrasound/structure", {"text": text, "modality": "abdominal"}),
    ]
    found = False
    for method, path, payload in endpoints:
        code, h, b, lat = request(method, path, payload)
        print(f"  {method} {path} -> {code}, body={b[:300]}")
        if code in [200, 201]:
            found = True
            has_structure = any(kw in b for kw in ["肝脏", "胆囊", "liver", "gallbladder", "肝"])
            result = "PASS" if has_structure else "PARTIAL"
            P(13, "Abdominal LLM", result, f"Response contains structure: {has_structure}", "Round1 verify")
            return
        elif code == 422:
            found = True
            P(13, "Abdominal LLM", "PARTIAL", f"422: {b[:200]}", "Round1 verify")
            return
    if not found:
        P(13, "Abdominal LLM", "SKIP", "No working abdominal endpoint found", "Need endpoint info")

# ============================================================
# ITEM 14: Empty text / illegal JSON rejection
# ============================================================
def test_14_illegal_input():
    print("="*60)
    print("[14] Empty text / illegal JSON rejection")
    results_14 = []

    # Empty text body
    code, h, b, lat = request("POST", "/api/patients", "")
    results_14.append(f"empty_body={code}")

    # Null body (just sending empty)
    code, h, b, lat = request("POST", "/api/patients", "null")
    results_14.append(f"null_body={code}")

    # Illegal JSON
    code, h, b, lat = request("POST", "/api/patients", "this is not json")
    results_14.append(f"bad_json={code}")

    # Missing required fields
    code, h, b, lat = request("POST", "/api/patients", {"foo": "bar"})
    results_14.append(f"missing_fields={code}")

    # Massive payload
    massive = {"name": "X" * 100000, "age": 30}
    code, h, b, lat = request("POST", "/api/patients", massive)
    results_14.append(f"massive={code}")

    # All should be 4xx
    all_rejected = all(c in [400, 413, 415, 422] for _, c, _, _ in
                       [request("POST", "/api/patients", x) for x in ["", "null", "this is not json"]])
    # Re-verify properly
    codes_14 = []
    for desc, payload in [("empty", ""), ("null", "null"), ("bad_json", "this is not json"),
                           ("missing", {"foo": "bar"}), ("massive", {"name": "X" * 100000, "age": 30})]:
        code, h, b, lat = request("POST", "/api/patients", payload)
        codes_14.append(f"{desc}={code}")
        print(f"  {desc}: {code}")

    all_4xx = all(c in [400, 413, 415, 422] for c in [request("POST", "/api/patients", x)[0]
                   for x in ["", "null", "this is not json", {"foo": "bar"}, {"name": "X" * 100000, "age": 30}]])

    P(14, "Illegal Input Rejection", "PASS" if all_4xx else "FAIL",
       "; ".join(codes_14), "Round1 verify")

# ============================================================
# Print results table
# ============================================================
def print_table():
    print("\n\n")
    print("=" * 120)
    print("ROUND 2 COMPREHENSIVE AUDIT RESULTS")
    print("=" * 120)
    hdr = f"{'#':>2} | {'Test Item':<40} | {'Result':<8} | {'Key Data':<50} | {'Delta vs R1'}"
    print(hdr)
    print("-" * 120)
    for i, test, result, key_data, delta in RESULTS:
        print(f"{i:>2} | {test:<40} | {result:<8} | {key_data:<50} | {delta}")
    print("-" * 120)
    pass_count = sum(1 for _, _, r, _, _ in RESULTS if r == "PASS")
    fail_count = sum(1 for _, _, r, _, _ in RESULTS if r == "FAIL")
    partial_count = sum(1 for _, _, r, _, _ in RESULTS if r == "PARTIAL")
    skip_count = sum(1 for _, _, r, _, _ in RESULTS if r == "SKIP")
    total = len(RESULTS)
    print(f"SUMMARY: {pass_count} PASS, {fail_count} FAIL, {partial_count} PARTIAL, {skip_count} SKIP (of {total})")
    print("=" * 120)

# ============================================================
# MAIN
# ============================================================
def main():
    print("Starting Round 2 Audit against", BASE)
    print("SSL: check_hostname=False, verify_mode=False")
    print()

    # First do a connectivity check
    print("--- Connectivity check ---")
    code, h, b, lat = request("GET", "/api/health")
    print(f"GET /api/health -> {code}, latency={lat:.1f}ms")
    print(f"Response body: {b[:500]}")
    print()

    if code == 0:
        print("FATAL: Cannot connect to server")
        sys.exit(1)

    tests = [
        test_1_cors,
        test_2_security_headers,
        test_3_version_leak,
        test_4_age_validation,
        test_5_name_length,
        test_6_path_traversal,
        test_7_static_files,
        test_8_health_concurrency,
        test_9_queue_100,
        test_10_fetal_template,
        test_11_patient_crud,
        test_12_ob_chinese,
        test_13_abdominal_llm,
        test_14_illegal_input,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  ERROR in {t.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print_table()

if __name__ == "__main__":
    main()
