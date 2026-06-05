#!/usr/bin/env python3
"""超声报告系统深度测试脚本 — http.client 原生实现"""
import http.client
import ssl
import json
import time
import threading
import sys
import struct
import os
from urllib.parse import quote

HOST = "47.109.151.238"
PORT = 443
BASE = f"https://{HOST}"

def ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c

def conn():
    return http.client.HTTPSConnection(HOST, PORT, context=ctx(), timeout=20)

# ========== 辅助：生成最小WAV文件 ==========
def make_wav():
    """生成一个最小的合法 WAV 文件（1秒、8kHz、mono、16bit PCM）"""
    sample_rate = 8000
    num_samples = sample_rate  # 1秒
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, 1, sample_rate,
        sample_rate * 2, 2, 16,
        b'data', data_size
    )
    # 填充静音样本
    samples = struct.pack('<' + 'h' * num_samples, *([500] * num_samples))
    return header + samples

WAV_PATH = "/tmp/test_audio.wav"
with open(WAV_PATH, "wb") as f:
    f.write(make_wav())

def api(method, path, body=None, headers=None, timeout=25):
    """统一API调用"""
    c = http.client.HTTPSConnection(HOST, PORT, context=ctx(), timeout=timeout)
    hdrs = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        hdrs.update(headers)
    # http.client 默认 Latin-1，中文需编码为 UTF-8 bytes
    if isinstance(body, str):
        body = body.encode("utf-8")
    t0 = time.time()
    c.request(method, path, body=body, headers=hdrs)
    r = c.getresponse()
    raw = r.read()
    elapsed = (time.time() - t0) * 1000
    c.close()
    try:
        data = json.loads(raw) if raw else None
    except:
        data = raw.decode("utf-8", errors="replace")
    return r.status, data, elapsed

def bench(method, path, body=None, headers=None, n=10):
    """性能测试：n次请求返回 min/max/avg"""
    times = []
    for _ in range(n):
        _, _, t = api(method, path, body, headers, timeout=15)
        times.append(t)
    times.sort()
    return min(times), max(times), sum(times)/len(times), times

def ok(result):
    return "PASS" if result else "FAIL"

def check(cond, msg=""):
    return cond, msg

results = []

def add_result(num, name, passed, data, note=""):
    results.append((num, name, passed, data, note))

# ============================================================
# 一、功能测试
# ============================================================
print("=" * 70)
print("超声报告系统深度测试报告")
print(f"目标: {BASE}")
print("=" * 70)

# 1. 患者管理 — 快速添加
print("\n[1] 患者管理 — 快速添加")
st, data, t1 = api("POST", "/api/patients/quick-add",
    json.dumps({"name": "测试张三", "gender": "男", "age": 45, "exam_type": "腹部超声"}, ensure_ascii=False))
patient_id = data.get("patient", {}).get("id") if data and isinstance(data, dict) else None
p1 = patient_id is not None and st == 200
add_result(1, "POST /api/patients/quick-add", p1,
    f"{t1:.0f}ms, id={patient_id}",
    f"返回patient.id={patient_id}" if p1 else f"status={st} resp={str(data)[:100]}")

# 2. 患者队列验证
print("\n[2] 患者队列验证")
st, data, t2 = api("GET", "/api/patients/queue")
found = False
if isinstance(data, dict) and data.get("patients"):
    for p in data["patients"]:
        if p.get("id") == patient_id:
            found = True
            break
p2 = found
add_result(2, "GET /api/patients/queue 验证新患者",
    p2, f"{t2:.0f}ms, 队列{len(data.get('patients',[]))}人",
    "新患者在队列中" if found else f"未找到id={patient_id}")

# 3. 更新患者状态
print("\n[3] 更新患者状态")
if patient_id:
    st, data, t3 = api("PUT", f"/api/patients/{patient_id}/status?status={quote('检查中')}")
    p3 = st == 200
    add_result(3, f"PUT /api/patients/{patient_id}/status?status=检查中",
        p3, f"{t3:.0f}ms", f"status={st}" + (f" resp={str(data)[:100]}" if not p3 else ""))
else:
    p3 = False
    add_result(3, "PUT /api/patients/{id}/status", False, "N/A", "无有效patient_id，跳过")

# 4. 语音转写
print("\n[4] 语音转写")
boundary = "----TestBoundary12345"
wav_bytes = open(WAV_PATH, "rb").read()
body_bytes = (
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode()
    + wav_bytes
    + f"\r\n--{boundary}--\r\n".encode()
)
c = http.client.HTTPSConnection(HOST, PORT, context=ctx(), timeout=30)
t0 = time.time()
c.request("POST", "/api/transcribe", body=body_bytes,
          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
r = c.getresponse()
raw = r.read()
t_elapsed = (time.time() - t0) * 1000
c.close()
try:
    tdata = json.loads(raw)
except:
    tdata = raw.decode("utf-8", errors="replace")
has_raw = isinstance(tdata, dict) and "raw_text" in tdata
has_text = isinstance(tdata, dict) and "text" in tdata
p4 = has_raw and has_text
add_result(4, "POST /api/transcribe (语音转写)",
    p4, f"{t_elapsed:.0f}ms",
    f"raw_text={'存在' if has_raw else '缺失'}, text={'存在' if has_text else '缺失'}")

# 5. 结构化提取 — 产科模板
print("\n[5] 结构化提取 — 产科 fetal_template")
body5 = json.dumps({
    "text": "中孕期四维大小22到26周 双顶径5.8 头围21.5 腹围19.6 股骨长4.2 胎心145次分 后壁胎盘",
    "exam_type": "产科超声"
}, ensure_ascii=False)
st, data5, t5 = api("POST", "/api/structure", body5)
is_dict5 = isinstance(data5, dict)
method_ok = is_dict5 and data5.get("method") == "fetal_template"
voice_count = 0
if is_dict5 and data5.get("voice"):
    voice_count = len(data5["voice"])
p5 = method_ok and voice_count >= 5
add_result(5, "POST /api/structure 产科 fetal_template",
    p5, f"{t5:.0f}ms, method={data5.get('method') if is_dict5 else 'N/A'}, voice标签={voice_count}个",
    "OK" if p5 else f"method={data5.get('method')}, voice计数={voice_count}")

# 保存产科报告用于后续测试
ob_report = data5 if is_dict5 and data5.get("report") else None
ob_report_id = ob_report.get("id") if ob_report else None

# 6. 结构化提取 — 腹部超声
print("\n[6] 结构化提取 — 腹部超声")
body6 = json.dumps({
    "text": "肝脏形态大小正常实质回声均匀 胆囊大小正常壁光滑未见结石 脾脏大小正常",
    "exam_type": "腹部超声"
}, ensure_ascii=False)
st, data6, t6 = api("POST", "/api/structure", body6)
p6 = st == 200 and isinstance(data6, dict)
add_result(6, "POST /api/structure 腹部超声",
    p6, f"{t6:.0f}ms", f"status={st}" + (f" method={data6.get('method','?')}" if isinstance(data6, dict) else ""))

# 7. 结构化提取 — 中文数字识别
print("\n[7] 结构化提取 — 中文数字识别")
body7 = json.dumps({
    "text": "中孕四为二十二到二十六 胎心一百四十五 后壁",
    "exam_type": "产科超声"
}, ensure_ascii=False)
st, data7, t7 = api("POST", "/api/structure", body7)
voice_labels = []
if isinstance(data7, dict) and data7.get("voice"):
    voice_labels = [v.get("label","") for v in data7["voice"]]
has_22_26 = any("22-26" in lbl or "22-26W" in lbl for lbl in voice_labels)
has_145 = any("145" in lbl for lbl in voice_labels)
p7 = has_22_26 and has_145
add_result(7, "POST /api/structure 中文数字识别",
    p7, f"{t7:.0f}ms, voice_labels={voice_labels[:8]}",
    "OK" if p7 else f"含22-26W={has_22_26}, 含145={has_145}")

# 8. 报告保存
print("\n[8] 报告保存")
if ob_report_id:
    st, data8, t8 = api("POST", f"/api/reports/{ob_report_id}/save")
    p8 = st == 200
    add_result(8, f"POST /api/reports/{ob_report_id}/save",
        p8, f"{t8:.0f}ms", f"status={st}")
else:
    add_result(8, "POST /api/reports/{id}/save", False, "N/A", "无可用report_id")

# 9. 报告发送
print("\n[9] 报告发送")
if ob_report_id:
    st, data9, t9 = api("POST", f"/api/reports/{ob_report_id}/send")
    p9 = st == 200
    add_result(9, f"POST /api/reports/{ob_report_id}/send",
        p9, f"{t9:.0f}ms", f"status={st}")
else:
    add_result(9, "POST /api/reports/{id}/send", False, "N/A", "无可用report_id")

# ============================================================
# 二、性能测试
# ============================================================
print("\n" + "=" * 70)
print("二、性能测试")
print("=" * 70)

# 7. 各端点响应时间 (每个10次)
print("\n[10-15] 端点响应时间测试 (各10次请求)")
endpoints = [
    ("GET /api/health", "GET", "/api/health", None),
    ("GET /api/patients/queue", "GET", "/api/patients/queue", None),
    ("POST /api/patients/quick-add", "POST", "/api/patients/quick-add",
     json.dumps({"name": "perf测试", "gender": "女", "age": 30, "exam_type": "腹部超声"}, ensure_ascii=False)),
    ("POST /api/structure (腹部)", "POST", "/api/structure",
     json.dumps({"text": "肝脏大小正常", "exam_type": "腹部超声"}, ensure_ascii=False)),
    ("POST /api/structure (产科)", "POST", "/api/structure",
     json.dumps({"text": "双顶径5.8 胎心145 后壁胎盘", "exam_type": "产科超声"}, ensure_ascii=False)),
]

perf_results = []
for name, method, path, body in endpoints:
    mn, mx, avg, times = bench(method, path, body, n=10)
    perf_results.append((name, mn, mx, avg, times))
    print(f"  {name:40s} min={mn:6.0f}ms  max={mx:6.0f}ms  avg={avg:6.0f}ms")

# 8. 并发压力测试
print("\n[16] 并发压力测试: 20线程同时对 /api/health")
success_count = [0]
fail_count = [0]
lock = threading.Lock()

def hit_health():
    try:
        st, _, _ = api("GET", "/api/health", timeout=15)
        with lock:
            if st == 200:
                success_count[0] += 1
            else:
                fail_count[0] += 1
    except:
        with lock:
            fail_count[0] += 1

threads = []
t_start = time.time()
for i in range(20):
    t = threading.Thread(target=hit_health)
    threads.append(t)
    t.start()
for t in threads:
    t.join()
t_total = (time.time() - t_start) * 1000

rate = success_count[0] / 20 * 100
p_concurrent = rate >= 95
add_result(16, "并发压力: 20线程 → /api/health",
    p_concurrent, f"总耗时{t_total:.0f}ms, 成功{success_count[0]}/20 ({rate:.0f}%)",
    "通过" if p_concurrent else f"成功率仅{rate:.0f}%")

# ============================================================
# 三、健壮性测试
# ============================================================
print("\n" + "=" * 70)
print("三、健壮性测试")
print("=" * 70)

# 9. 空文本
print("\n[17] 空文本测试")
st, data, t9r = api("POST", "/api/structure",
    json.dumps({"text": "", "exam_type": "产科超声"}, ensure_ascii=False))
p_empty = st in (400, 422)
add_result(17, "空文本 text=\"\" → 应返回400",
    p_empty, f"{t9r:.0f}ms, status={st}", f"返回{st}" + ("" if p_empty else " 未拒绝空文本"))

# 10. 超长文本
print("\n[18] 超长文本测试")
long_text = "超" * 10000
st, data, t10r = api("POST", "/api/structure",
    json.dumps({"text": long_text, "exam_type": "腹部超声"}, ensure_ascii=False), timeout=30)
p_long = st in (200, 400, 413, 422)  # 不崩溃即可
add_result(18, "超长文本 10000个中文字 → 不崩溃",
    p_long, f"{t10r:.0f}ms, status={st}",
    f"返回{st}，未崩溃" if p_long else f"崩溃或超时")

# 11. 无效JSON
print("\n[19] 无效JSON测试")
c = http.client.HTTPSConnection(HOST, PORT, context=ctx(), timeout=15)
t0 = time.time()
c.request("POST", "/api/structure", body=b"this is not valid json {", headers={"Content-Type": "application/json"})
r = c.getresponse()
raw = r.read()
t_invalid = (time.time() - t0) * 1000
c.close()
p_json = r.status in (400, 422)
add_result(19, "无效JSON body → 应返回400",
    p_json, f"{t_invalid:.0f}ms, status={r.status}",
    f"返回{r.status}" + ("" if p_json else f" 未正确拒绝"))

# 12. 缺失必填字段
print("\n[20] 缺失必填字段测试")
st, data, t12r = api("POST", "/api/patients/quick-add", json.dumps({}))
p_missing = st in (400, 422)
add_result(20, "POST /api/patients/quick-add body={} → 应返回422/400",
    p_missing, f"{t12r:.0f}ms, status={st}",
    f"返回{st}" + ("" if p_missing else f" 未拒绝空body, resp={str(data)[:80]}"))

# 13. XSS防护
print("\n[21] XSS防护测试")
st, data, t13r = api("POST", "/api/structure",
    json.dumps({"text": "<script>alert(1)</script>", "exam_type": "产科超声"}, ensure_ascii=False))
# 检查返回中是否直接包含未转义的 script 标签
resp_str = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
xss_safe = "<script>alert(1)</script>" not in resp_str or st in (400, 422)
p_xss = xss_safe
add_result(21, "XSS防护 <script>alert(1)</script>",
    p_xss, f"{t13r:.0f}ms, status={st}",
    "未直接回显原始script标签" if xss_safe else "原始script标签被回显")

# 14. 路径遍历
print("\n[22] 路径遍历测试")
st, data, t14r = api("GET", "/../../../etc/passwd")
p_path = st == 404
add_result(22, "路径遍历 GET /../../../etc/passwd → 应返回404",
    p_path, f"{t14r:.0f}ms, status={st}",
    "正确返回404" if p_path else f"返回{st}")

# 15. SQL注入
print("\n[23] SQL注入测试")
st, data, t15r = api("POST", "/api/structure",
    json.dumps({"text": "'; DROP TABLE patients;--", "exam_type": "腹部超声"}, ensure_ascii=False))
p_sql = st in (200, 400, 422)  # 正常处理不崩溃
add_result(23, "SQL注入 text=\"'; DROP TABLE patients;--\"",
    p_sql, f"{t15r:.0f}ms, status={st}",
    f"正常处理，status={st}" if p_sql else f"异常 status={st}")

# ============================================================
# 汇总输出
# ============================================================
print("\n\n" + "=" * 70)
print("最终测试结果汇总")
print("=" * 70)
print(f"{'#':<5} {'Test Item':<48} {'Result':<6} {'Time/Data':<30} {'Note'}")
print("-" * 135)

summary_pass = 0
summary_fail = 0

for num, name, passed, dat, note in results:
    r = ok(passed)
    if passed:
        summary_pass += 1
    else:
        summary_fail += 0
    # 截断以便显示
    name_s = name[:46]
    dat_s = str(dat)[:28]
    note_s = str(note)[:30]
    print(f"{num:<5} {name_s:<48} {r:<6} {dat_s:<30} {note_s}")

print("-" * 135)

# stats
total = len(results)
passed_count = sum(1 for _, _, p, _, _ in results if p)
failed_count = total - passed_count
print(f"\nTotal: {total} | Passed: {passed_count} | Failed: {failed_count} | Rate: {passed_count/total*100:.1f}%")

# perf summary
print(f"\n--- Performance Test Details ---")
print(f"{'Endpoint':<40} {'Min(ms)':>8} {'Max(ms)':>8} {'Avg(ms)':>8} {'P50(ms)':>8} {'P95(ms)':>8}")
print("-" * 85)
for name, mn, mx, avg, times in perf_results:
    sorted_t = sorted(times)
    p50 = sorted_t[len(sorted_t)//2]
    p95 = sorted_t[int(len(sorted_t)*0.95)]
    print(f"{name:<40} {mn:>8.0f} {mx:>8.0f} {avg:>8.0f} {p50:>8.0f} {p95:>8.0f}")

print(f"\nConcurrency: 20 threads, total {t_total:.0f}ms, success rate {rate:.0f}%")

if patient_id:
    print(f"\nTest patient ID: {patient_id} (manual cleanup needed)")
if WAV_PATH:
    os.remove(WAV_PATH)

print("\nTest complete.")
