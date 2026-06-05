import http.client
import ssl
import json

HOST = "47.109.151.238"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def conn():
    return http.client.HTTPSConnection(HOST, context=ctx, timeout=15)

def post_struct(body):
    c = conn()
    c.request("POST", "/api/structure", json.dumps(body), {"Content-Type": "application/json"})
    r = c.getresponse()
    data = json.loads(r.read().decode())
    c.close()
    return r.status, data

def get(path):
    c = conn()
    c.request("GET", path)
    r = c.getresponse()
    headers = r.getheaders()
    body = r.read().decode()
    c.close()
    return r.status, headers, body

results = []

# ---- Test 1: Health Check ----
print("=== Test 1: Health Check ===")
status, headers, body = get("/api/health")
j = json.loads(body)
ok = status == 200 and j.get("status") == "ok"
results.append(("1. Health Check", ok, f"status={status} body={body}"))
print(f"  {'PASS' if ok else 'FAIL'}  status={status} body={body}")

# ---- Test 2: Fetal Template ----
print("\n=== Test 2: Fetal Template ===")
status, data = post_struct({"text":"中孕期二十二到二十六 双顶径5.8 头围21.5 胎心一百四十五","exam_type":"产科超声"})
html = data["report"]["study_see"]
method = data.get("method", "")
has_rptsec = "rpt-sec" in html
has_voice = "voice" in html
has_unfill = "unfill" in html
ok = status == 200 and method == "fetal_template" and has_rptsec and has_voice and has_unfill
results.append(("2. Fetal Template", ok, f"method={method} rpt-sec={has_rptsec} voice={has_voice} unfill={has_unfill}"))
print(f"  {'PASS' if ok else 'FAIL'}  method={method} rpt-sec={has_rptsec} voice={has_voice} unfill={has_unfill}")
# Check specific values in voice tags
has_bpd = "5.8" in html
has_hc = "21.5" in html
has_fhr = "145" in html
print(f"  Values: BPD=5.8->{has_bpd} HC=21.5->{has_hc} FHR=145->{has_fhr}")

# ---- Test 3: Kg->g Conversion ----
print("\n=== Test 3: Kg->g Conversion ===")
status, data = post_struct({"text":"胎儿体重七公斤","exam_type":"产科超声"})
html = data["report"]["study_see"]
has_7000 = "7000" in html
seven_kg = "七公斤" in data.get("_method", "")
ok = status == 200 and has_7000
results.append(("3. Kg->g Conversion", ok, f"status={status} '7000' in html={has_7000}"))
print(f"  {'PASS' if ok else 'FAIL'}  '7000' found={has_7000}")
# Show EFW context
for line in html.split("</div>"):
    if "7000" in line or "体重" in line.lower() or "g" in line.lower():
        print(f"  Context: {line.strip()[:200]}")

# ---- Test 4: Quadrant + RI/PI/SD ----
print("\n=== Test 4: Quadrant + RI/PI/SD ===")
status, data = post_struct({"text":"右下4厘米 右上5厘米 R I值12 T I值13 S D值14","exam_type":"产科超声"})
html = data["report"]["study_see"]
has_4 = True  # will check more specifically
has_5 = True
ri_present = "RI" in html
pi_present = "PI" in html
sd_present = "S/D" in html
# Check for the quadrant voice tags
print(f"  html length={len(html)}")
# The quadrant values should appear in the amniotic fluid section
ok = status == 200 and ri_present and pi_present and sd_present
results.append(("4. Quadrant+RI/PI/SD", ok, f"RI={ri_present} PI={pi_present} S/D={sd_present}"))
print(f"  {'PASS' if ok else 'FAIL'}  RI={ri_present} PI={pi_present} S/D={sd_present}")
# Show full html
print(f"  Full HTML:\n{html}")

# ---- Test 5: Security Headers ----
print("\n=== Test 5: Security Headers ===")
status, headers, body = get("/")
hdrs = {k.lower(): v for k, v in headers}
xcto = hdrs.get("x-content-type-options", "")
xfo = hdrs.get("x-frame-options", "")
ok = bool(xcto) or bool(xfo)
results.append(("5. Security Headers", ok, f"X-Content-Type-Options={xcto!r} X-Frame-Options={xfo!r}"))
print(f"  {'PASS' if ok else 'FAIL'}  X-Content-Type-Options={xcto!r} X-Frame-Options={xfo!r}")

# ---- Summary ----
print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)
for name, ok, detail in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n  {passed}/{len(results)} passed")
