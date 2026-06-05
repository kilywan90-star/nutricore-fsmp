#!/usr/bin/env python3
"""Deep retest with correct API endpoints from SPA HTML analysis."""
import ssl, urllib.request, json, time, re
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = False
BASE = 'https://47.109.151.238'

def req(method, path, body=None, ct='application/json', timeout=15):
    url = BASE + path
    data = None
    if body is not None:
        if isinstance(body, str):
            data = body.encode()
        else:
            data = json.dumps(body).encode()
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

# ====== ITEM 2: Security Headers ======
print("="*60)
print("ITEM 2: Security Headers (retest on /api/health and /)")
code, headers, body, lat = req('GET', '/api/health')
print("On /api/health:")
for h in ['X-Content-Type-Options','X-Frame-Options','X-XSS-Protection',
          'Referrer-Policy','Content-Security-Policy','Strict-Transport-Security',
          'X-Permitted-Cross-Domain-Policies','Server']:
    print(f"  {h}: {headers.get(h, 'MISSING')}")

code2, h2, b2, _ = req('GET', '/')
print("On / (SPA root):")
for h in ['X-Content-Type-Options','X-Frame-Options','X-XSS-Protection',
          'Referrer-Policy','Server']:
    print(f"  {h}: {h2.get(h, 'MISSING')}")

# ====== ITEM 3: Version Leak ======
print()
print("="*60)
print("ITEM 3: Version Leak (retest)")
print(f"  /api/health body: {body[:300]}")
print(f"  Server header on /api/health: {headers.get('Server','MISSING')}")
print(f"  Server header on /: {h2.get('Server','MISSING')}")

# ====== ITEM 4: Age Validation ======
print()
print("="*60)
print("ITEM 4: Age Validation via /api/patients/quick-add")
for age_val, desc in [(-1,'age=-1'), (999,'age=999'), (0,'age=0'),
                       (150,'age=150'), (25,'age=25(valid)')]:
    code, h, b, lat = req('POST', '/api/patients/quick-add',
        {'name': f'Test{desc}', 'age': age_val, 'gender': 'male'})
    print(f"  {desc}: status={code}, body={b[:200]}")

# ====== ITEM 5: Name Length ======
print()
print("="*60)
print("ITEM 5: Name Length Validation via /api/patients/quick-add")
for name_len in [300, 5000]:
    code, h, b, lat = req('POST', '/api/patients/quick-add',
        {'name': 'A' * name_len, 'age': 30, 'gender': 'male'})
    print(f"  name={name_len}chars: status={code}, body={b[:200]}")

# ====== ITEM 7: Static files deeper check ======
print()
print("="*60)
print("ITEM 7: Static files - verify content is SPA HTML, not actual config")
# Check if .env returns SPA HTML (not actual env)
code, h, b, lat = req('GET', '/.env')
print(f"  GET /.env: {code}")
print(f"  Is SPA HTML: {'<!DOCTYPE html>' in b}")
print(f"  Contains secrets: {'DATABASE_URL' in b or 'SECRET' in b or 'PASSWORD' in b}")

code, h, b, lat = req('GET', '/nginx.conf')
print(f"  GET /nginx.conf: {code}")
print(f"  Is SPA HTML: {'<!DOCTYPE html>' in b}")

# Check for .git/HEAD or other sensitive files
for path in ['/.git/HEAD', '/.env.production', '/.env.local', '/Dockerfile',
             '/docker-compose.yml', '/package.json', '/requirements.txt',
             '/Procfile', '/runtime.txt']:
    code, h, b, lat = req('GET', path)
    is_spa = '<!DOCTYPE html>' in b
    print(f"  GET {path}: {code}, SPA HTML={is_spa}")

# ====== ITEM 11: Patient CRUD ======
print()
print("="*60)
print("ITEM 11: Patient CRUD (retest)")
# Step 1: Create
code, h, b, lat = req('POST', '/api/patients/quick-add',
    {'name': 'CRUDFullR2', 'age': 42, 'gender': 'male'})
print(f"  CREATE: {code}")
j = {}
try: j = json.loads(b)
except: pass
pid = None
if j:
    pid = j.get('id') or j.get('patient_id')
    if not pid and 'data' in j and isinstance(j['data'], dict):
        pid = j['data'].get('id') or j['data'].get('patient_id')
print(f"  Response: {json.dumps(j, ensure_ascii=False)[:400]}")
print(f"  Extracted ID: {pid}")

if pid:
    # Read
    code, h, b, lat = req('GET', f'/api/patients/{pid}')
    print(f"  READ GET /api/patients/{pid}: {code}, body={b[:200]}")

    # Update
    code, h, b, lat = req('PUT', f'/api/patients/{pid}',
        {'name': 'CRUDFullR2_Updated', 'age': 43, 'gender': 'male'})
    print(f"  UPDATE PUT: {code}, body={b[:200]}")
    if code in [404, 405]:
        code, h, b, lat = req('PATCH', f'/api/patients/{pid}',
            {'name': 'CRUDFullR2_Updated', 'age': 43, 'gender': 'male'})
        print(f"  UPDATE PATCH: {code}, body={b[:200]}")

    # Verify update
    code, h, b, lat = req('GET', f'/api/patients/{pid}')
    updated = 'CRUDFullR2_Updated' in b
    print(f"  VERIFY UPDATE: {code}, name updated: {updated}")

    # Delete
    code, h, b, lat = req('DELETE', f'/api/patients/{pid}')
    print(f"  DELETE: {code}, body={b[:200]}")

    # Verify delete
    code, h, b, lat = req('GET', f'/api/patients/{pid}')
    print(f"  VERIFY DELETE (expect 404): {code}")
else:
    print("  FAILED to get patient ID. Trying alternate create...")
    # Try POST /api/patients (not quick-add)
    code, h, b, lat = req('POST', '/api/patients',
        {'name': 'CRUDFullR2_v2', 'age': 42, 'gender': 'male'})
    print(f"  POST /api/patients: {code}, body={b[:300]}")

# ====== ITEM 12: OB Chinese Numbers ======
print()
print("="*60)
print("ITEM 12: OB Chinese Number Recognition")
# /api/transcribe
code, h, b, lat = req('POST', '/api/transcribe',
    {'text': '中孕四为二十二到二十六 胎心一百四十五 后壁'})
print(f"  POST /api/transcribe (OB text): {code}")
print(f"  Body: {b[:600]}")
ob_ok = any(kw in b for kw in ['22','26','145','后壁','胎心','trimester','week','FHR','BPD','biparietal'])
print(f"  Contains structured OB data: {ob_ok}")

# /api/structure
code, h, b, lat = req('POST', '/api/structure',
    {'text': '中孕四为二十二到二十六 胎心一百四十五 后壁'})
print(f"  POST /api/structure (OB text): {code}")
print(f"  Body: {b[:600]}")
ob_ok2 = any(kw in b for kw in ['22','26','145','后壁','胎心','trimester','week'])
print(f"  Contains structured data: {ob_ok2}")

# Try empty text
code, h, b, lat = req('POST', '/api/transcribe', {'text': ''})
print(f"  POST /api/transcribe (empty text): {code}, body={b[:200]}")

code, h, b, lat = req('POST', '/api/structure', {'text': ''})
print(f"  POST /api/structure (empty text): {code}, body={b[:200]}")

# ====== ITEM 13: Abdominal LLM ======
print()
print("="*60)
print("ITEM 13: Abdominal LLM Structure")
abd_text = '肝脏形态大小正常 包膜光滑 实质回声均匀 肝内管道结构清晰 胆囊大小约6.5x2.5cm 壁光滑 腔内未见异常回声'

code, h, b, lat = req('POST', '/api/transcribe',
    {'text': abd_text})
print(f"  POST /api/transcribe (ABD): {code}")
print(f"  Body: {b[:600]}")
abd_ok = any(kw in b for kw in ['肝脏','胆囊','liver','gallbladder','肝','size','normal'])
print(f"  Contains structured abdominal data: {abd_ok}")

code, h, b, lat = req('POST', '/api/structure',
    {'text': abd_text})
print(f"  POST /api/structure (ABD): {code}")
print(f"  Body: {b[:600]}")
abd_ok2 = any(kw in b for kw in ['肝脏','胆囊','liver','gallbladder','size'])
print(f"  Contains structured data: {abd_ok2}")

# ====== ITEM 14: Illegal Input ======
print()
print("="*60)
print("ITEM 14: Illegal Input Rejection (retest)")
tests_14 = [
    ('empty body', '', 'application/json'),
    ('null str', 'null', 'application/json'),
    ('bad json', 'not json{{{', 'application/json'),
    ('empty obj', '{}', 'application/json'),
    ('wrong CT', 'some text', 'text/plain'),
    ('massive body 100KB', 'X' * 100000, 'application/json'),
]
for desc, payload, ct in tests_14:
    code, h, b, lat = req('POST', '/api/patients/quick-add', payload, ct=ct)
    is_4xx = 400 <= code < 500
    print(f"  {desc}: {code} (4xx={is_4xx}), body={b[:150]}")

# Also test /api/transcribe and /api/structure with bad input
for ep, desc, payload in [
    ('/api/transcribe', 'empty text', {'text': ''}),
    ('/api/transcribe', 'missing text', {}),
    ('/api/transcribe', 'null text', 'null'),
    ('/api/structure', 'empty text', {'text': ''}),
    ('/api/structure', 'missing text', {}),
]:
    code, h, b, lat = req('POST', ep, payload)
    print(f"  {ep} ({desc}): {code}, body={b[:150]}")

# ====== Additional: Check queue for existing data ======
print()
print("="*60)
print("ADDITIONAL: Check /api/patients/queue response")
code, h, b, lat = req('GET', '/api/patients/queue')
print(f"  GET /api/patients/queue: {code}")
print(f"  Body (first 1000): {b[:1000]}")
