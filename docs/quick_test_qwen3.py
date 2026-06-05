#!/usr/bin/env python3
"""Quick 50-sample test for qwen3:8b with detailed logging"""
import csv, json, re, time, random, sys
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:8b"
DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset_v2.csv"

PROMPT = """你是超声ASR结构化提取系统。返回JSON:{"template":"A/B/C/D/E","measurements":{},"abnormality":"异常或无"}

模板:A大排畸(胎儿双顶径/头围) B胎儿心超(胎心/瓣膜血流) C成人心超(左室/EF) D血管(颈动脉IMT/PSV/EDV) E全腹(肝/胆囊/脾/肾)
同音还原:双丁径=双顶径 古骨=股骨 冻麦=动脉 净麦=静脉 益福=EF 反留=反流 办膜=瓣膜 肾余=肾盂
单位修复:123.4m→123.4mm 次每→bpm
病灶:"XX反流流速"是测量不算异常。只返回JSON。"""

def call(asr_text):
    payload = {"model":MODEL,"prompt":f"{PROMPT}\n\nASR:{asr_text}","stream":False,"options":{"temperature":0,"num_predict":400}}
    try:
        r = requests.post(OLLAMA_URL,json=payload,timeout=45)
        return r.json().get("response","")
    except Exception as e:
        return f"ERR:{e}"

def parse(raw):
    try: return json.loads(raw)
    except: pass
    m = re.search(r'\{[^{}]*"template"[^{}]*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return None

random.seed(42)
all_rec = {t:[] for t in 'ABCDE'}
with open(DATA_FILE,'r',encoding='utf-8-sig') as f:
    reader = csv.reader(f); next(reader)
    for row in reader:
        if len(row)<5: continue
        t = row[2]
        if t in all_rec: all_rec[t].append(row)

samples = []
for t in 'ABCDE':
    samples.extend(random.sample(all_rec[t], 10))
random.shuffle(samples)

print(f"qwen3:8b 快速测试 ({len(samples)}条)")
ok_t, ok_ab = 0, 0
total = len(samples)
start = time.time()

for i, row in enumerate(samples):
    asr = row[1]; true_t = row[2]
    ans = json.loads(row[4])
    true_ab = ans.get('abnormality','无') not in ('无','',None) and ans.get('abnormality','') != '无'

    t0 = time.time()
    raw = call(asr)
    elapsed = time.time()-t0
    pred = parse(raw)
    if pred is None:
        pred = {"template":"?","abnormality":"无"}

    pred_t = pred.get("template","?").strip().upper()
    pred_ab = pred.get("abnormality","无")
    pred_has_ab = pred_ab not in ('无','',None) and str(pred_ab) != '无'

    t_ok = pred_t == true_t
    ab_ok = pred_has_ab == true_ab
    if t_ok: ok_t += 1
    if ab_ok: ok_ab += 1

    print(f"[{i+1}/{total}] [{true_t}] pred={pred_t} t={'OK' if t_ok else 'X'} ab={'OK' if ab_ok else 'X'} ({elapsed:.1f}s)")

elapsed_t = (time.time()-start)/60
print(f"\n{'='*40}")
print(f"qwen3:8b 快速测试完成 ({elapsed_t:.1f}min)")
print(f"模板分类: {ok_t}/{total} = {ok_t/total*100:.1f}%")
print(f"病灶检测: {ok_ab}/{total} = {ok_ab/total*100:.1f}%")
print(f"平均速度: {elapsed_t*60/total:.1f}s/条")
