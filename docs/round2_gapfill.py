#!/usr/bin/env python3
"""Gap-filling tests for Round 2 audit."""
import ssl, urllib.request, json, time, concurrent.futures
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = False
BASE = 'https://47.109.151.238'

def req(method, path, body=None, ct='application/json', timeout=15):
    url = BASE + path
    data = None
    if body is not None:
        if isinstance(body, str): data = body.encode()
        else: data = json.dumps(body).encode()
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header('Content-Type', ct)
    r.add_header('Accept', 'application/json')
    start = time.time()
    try:
        resp = urllib.request.urlopen(r, context=ctx, timeout=timeout)
        lat = (time.time() - start) * 1000
        b = resp.read().decode(errors='replace')
        return resp.status, dict(resp.getheaders()), b, lat
    except urllib.error.HTTPError as e:
        lat = (time.time() - start) * 1000
        b = e.read().decode(errors='replace') if e.fp else ''
        return e.code, dict(e.headers), b, lat
    except Exception as e:
        lat = (time.time() - start) * 1000
        return 0, {}, str(e), lat

print("=" * 60)
print("GAP 1: Patient CRUD with exam_type field")
print("=" * 60)

# Step 1: Create with exam_type
payload = {"name": "CRUD_R2_Final", "age": 35, "gender": "male", "exam_type": "产科超声"}
code, h, b, lat = req('POST', '/api/patients/quick-add', payload)
print(f"  CREATE: {code}")
print(f"  Body: {b[:300]}")

j = {}
try: j = json.loads(b)
except: pass

pid = None
# Extract ID from various response shapes
if isinstance(j, dict):
    pid = j.get('id') or j.get('patient_id')
    if 'data' in j and isinstance(j['data'], dict):
        pid = j['data'].get('id') or j['data'].get('patient_id')
    if 'patient' in j and isinstance(j['patient'], dict):
        pid = j['patient'].get('id')
    # Check if success wrapper
    if not pid and j.get('success'):
        # Try to find any id in the response
        for k in ['report_id', 'patient_id', 'id']:
            if k in j:
                pid = j[k]
                break

print(f"  Extracted ID: {pid}")

# Step 2: Check queue for the patient if needed
if not pid:
    code, h, b, lat = req('GET', '/api/patients/queue')
    data = json.loads(b)
    patients = data.get('patients', data.get('data', []))
    if not isinstance(patients, list):
        patients = []
    # Find our patient
    for p in patients:
        if isinstance(p, dict) and p.get('name') == 'CRUD_R2_Final':
            pid = p.get('id')
            print(f"  Found in queue: id={pid}")
            break

if pid:
    # Read
    code, h, b, lat = req('GET', f'/api/patients/{pid}')
    print(f"  READ GET /api/patients/{pid}: {code}")
    print(f"  Body: {b[:300]}")

    # Update - try multiple methods
    for method in ['PUT', 'PATCH']:
        update_payload = {"name": "CRUD_R2_Final_UPD", "age": 36, "gender": "female", "exam_type": "腹部超声"}
        code, h, b, lat = req(method, f'/api/patients/{pid}', update_payload)
        if code not in [404, 405]:
            print(f"  UPDATE {method}: {code}, body={b[:200]}")
            break
        else:
            print(f"  UPDATE {method}: {code} (not available)")

    # Try update via queue endpoint if available
    code_upd, h_upd, b_upd, _ = req('PUT', f'/api/patients/{pid}/status',
        {"status": "已缴费"})
    if code_upd not in [404, 405]:
        print(f"  UPDATE STATUS PUT: {code_upd}, body={b_upd[:200]}")
    else:
        code_upd2, h_upd2, b_upd2, _ = req('PATCH', f'/api/patients/{pid}/status',
            {"status": "已缴费"})
        print(f"  UPDATE STATUS PATCH: {code_upd2}, body={b_upd2[:200]}")

    # Delete
    code, h, b, lat = req('DELETE', f'/api/patients/{pid}')
    print(f"  DELETE: {code}, body={b[:200]}")

    # Verify delete
    code, h, b, lat = req('GET', f'/api/patients/{pid}')
    deleted_ok = code in [404, 410]
    print(f"  VERIFY DELETE (expect 404): {code}, deleted={deleted_ok}")

    # Also try soft delete / status change
    if not deleted_ok:
        # Maybe patient has a status field
        pass
else:
    print("  FAILED to get patient ID after create")

print()
print("=" * 60)
print("GAP 2: /api/structure latency - 10 requests (fetal template)")
print("=" * 60)
ob_text = "中孕 双顶径5.6cm 头围21cm 腹围19cm 股骨长4.2cm 胎心145次/分 胎盘后壁"
latencies = []
for i in range(10):
    code, h, b, lat = req('POST', '/api/structure', {"text": ob_text})
    latencies.append(lat)
    success = code == 200
    print(f"  Req {i+1}: {code} ({lat:.1f}ms) - {'OK' if success else 'FAIL'}")

avg_lat = sum(latencies) / len(latencies)
sorted_lats = sorted(latencies)
max_lat = max(latencies)
min_lat = min(latencies)
p50 = sorted_lats[5] if len(sorted_lats) > 5 else sorted_lats[-1]
p95 = sorted_lats[9] if len(sorted_lats) > 9 else sorted_lats[-1]
success_rate = (sum(1 for l in [req('POST','/api/structure',{"text":ob_text})[0] for _ in range(10)]) / 10) * 100
# Actually recalculate properly
successes = sum(1 for _ in range(10) if req('POST','/api/structure',{"text":ob_text})[0] == 200)
print(f"\n  Fetal structure 10x: Avg={avg_lat:.1f}ms, P50={p50:.1f}ms, P95={p95:.1f}ms, Min={min_lat:.1f}ms, Max={max_lat:.1f}ms")

print()
print("=" * 60)
print("GAP 3: /api/transcribe endpoint (file-based?)")
print("=" * 60)
# /api/transcribe seems to require a 'file' field, not 'text'
# Check if it accepts multipart file upload
# For now, document the API interface

# Try with text in a request body field called 'file'
code, h, b, lat = req('POST', '/api/transcribe',
    {"file": "中孕四为二十二到二十六 胎心一百四十五 后壁"})
print(f"  /api/transcribe with file=text: {code}, body={b[:300]}")

# Check what the success response from /api/structure looks like for OB
print()
print("=" * 60)
print("GAP 4: Check initial /api/health response for version patterns")
print("=" * 60)
code, h, b, lat = req('GET', '/api/health')
print(f"  Body: {b}")
print(f"  'version' in body: {'version' in b.lower()}")
print(f"  '0.3.0' in body: {'0.3.0' in b}")

# Additional header checks
print()
print("=" * 60)
print("GAP 5: Check HSTS and other advanced headers")
print("=" * 60)
for path in ['/api/health', '/', '/api/structure']:
    code, h, b, lat = req('GET', path)
    sts = h.get('Strict-Transport-Security', 'MISSING')
    csp = h.get('Content-Security-Policy', 'MISSING')
    cto = h.get('X-Content-Type-Options', 'MISSING')
    xfo = h.get('X-Frame-Options', 'MISSING')
    print(f"  {path}: HSTS={sts}, CSP={csp}, CTO={cto}, XFO={xfo}")

# Check for proper error when sending request with wrong Content-Type to /api/structure
print()
print("=" * 60)
print("GAP 6: Content-Type validation")
print("=" * 60)
code, h, b, lat = req('POST', '/api/structure',
    'just plain text not json', ct='text/plain')
print(f"  /api/structure with text/plain: {code}, body={b[:200]}")

code, h, b, lat = req('POST', '/api/structure',
    '<xml>test</xml>', ct='application/xml')
print(f"  /api/structure with application/xml: {code}, body={b[:200]}")

# Check if path traversal within query params is caught
print()
print("=" * 60)
print("GAP 7: Path traversal in query params")
print("=" * 60)
for param_val in ['../../etc/passwd', '..%2f..%2fetc%2fpasswd', '%00../../etc/passwd']:
    code, h, b, lat = req('GET', f'/api/patients/{param_val}')
    print(f"  GET /api/patients/{param_val[:30]}: {code}, body len={len(b)}, is_spa={'<!DOCTYPE html>' in b}")

# Null byte injection
code, h, b, lat = req('GET', '/api/patients/%00')
print(f"  GET /api/patients/%00: {code}, body={b[:200]}")

# Double-encoded
code, h, b, lat = req('GET', '/api/patients/%252e%252e%252f%252e%252e%252fetc%252fpasswd')
print(f"  GET double-encoded path traversal: {code}, body={b[:200]}")

print()
print("=" * 60)
print("GAP 8: SQL injection in query params")
print("=" * 60)
for inj in ["' OR '1'='1", "1; DROP TABLE patients--", "1' UNION SELECT * FROM users--"]:
    import urllib.parse
    encoded = urllib.parse.quote(inj)
    code, h, b, lat = req('GET', f'/api/patients/{encoded}')
    print(f"  GET /api/patients/{inj[:30]}: {code}, body len={len(b)}")
