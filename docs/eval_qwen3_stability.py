#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen3:8b 稳定性评测 — 10次独立运行，每次1000条分层抽样
评测模板分类和病灶检测两项（数值提取已有充分数据）
输出: 10次运行的平均值和标准差
"""
import csv, json, re, time, random
from collections import defaultdict, Counter
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:8b"
DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset_v2.csv"
SAMPLES_PER_TEMPLATE = 200
RUNS = 10

TEMPLATE_NAMES = {'A':'大排畸','B':'胎儿心超','C':'成人心超','D':'血管','E':'全腹'}

SYSTEM_PROMPT = """你是超声医学报告结构化提取系统。按JSON返回：{"template":"A/B/C/D/E","measurements":{},"abnormality":"异常描述"}

模板: A大排畸(胎儿双顶径/头围/股骨/胎盘羊水) B胎儿心超(胎心/瓣膜血流) C成人心超(左室/EF/二尖瓣E/A) D血管(颈动脉IMT/PSV/EDV) E全腹(肝/胆囊/胰腺/肾)

同音还原:双丁径=双顶径 古骨=股骨 冻麦=动脉 净麦=静脉 益福=EF 反留=反流 内中末=内中膜 办膜=瓣膜 肾余=肾盂 匹斯维=PSV

单位修复:123.4m→123.4mm 46.8cm速度→46.8cm/s 次每→bpm

病灶:提取缺损/反流/狭窄/囊肿/结石/斑块/积液/增厚/脂肪肝/血栓/曲张等异常,"XX反流流速"是正常测量不算异常。无异常填"无"。只返回JSON。"""


def call_ollama(asr_text, timeout=60):
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nASR: {asr_text}",
        "stream": False,
        "options": {"temperature": 0, "num_predict": 600}
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        return resp.json().get("response", "")
    except:
        return "ERROR"

def parse_output(raw):
    try: return json.loads(raw)
    except: pass
    m = re.search(r'\{[^{}]*"template"[^{}]*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return None


def main():
    random.seed(42)

    # 加载全部数据
    all_records = {t: [] for t in 'ABCDE'}
    with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f); next(reader)
        for row in reader:
            if len(row) < 5: continue
            t = row[2]
            if t in all_records: all_records[t].append(row)

    run_results = []

    for run_idx in range(RUNS):
        # 每轮独立抽样
        samples = []
        for t in 'ABCDE':
            picks = random.sample(all_records[t], SAMPLES_PER_TEMPLATE)
            samples.extend(picks)
        random.shuffle(samples)

        print(f"\n{'='*50}")
        print(f"  第 {run_idx+1}/{RUNS} 轮")
        print(f"{'='*50}")

        stats = {'template_correct': 0, 'abnorm_correct': 0, 'total': len(samples)}
        t0 = time.time()

        for i, row in enumerate(samples):
            asr = row[1]; true_t = row[2]
            ans = json.loads(row[4])
            true_ab = ans.get('abnormality','无') not in ('无','',None) and ans.get('abnormality','') != '无'

            raw = call_ollama(asr)
            pred = parse_output(raw)
            if pred is None:
                pred = {"template":"?","measurements":{},"abnormality":"无"}

            pred_t = pred.get("template","?").strip().upper()
            pred_ab = pred.get("abnormality","无")
            pred_has_ab = pred_ab not in ('无','',None) and str(pred_ab) != '无'

            stats['template_correct'] += 1 if pred_t == true_t else 0
            stats['abnorm_correct'] += 1 if (pred_has_ab == true_ab) else 0

            if (i+1) % 200 == 0:
                n = i+1
                tca = stats['template_correct']/n*100
                aca = stats['abnorm_correct']/n*100
                elapsed = (time.time()-t0)/60
                eta = elapsed/n*(len(samples)-n)
                print(f"  [{n}/{len(samples)}] 模板{tca:.1f}% 病灶{aca:.1f}% ({elapsed:.1f}min, 剩余~{eta:.0f}min)")

        elapsed = (time.time()-t0)/60
        tca = stats['template_correct']/stats['total']*100
        aca = stats['abnorm_correct']/stats['total']*100
        run_results.append((tca, aca, elapsed))
        print(f"  第{run_idx+1}轮完成: 模板{tca:.1f}% 病灶{aca:.1f}% 耗时{elapsed:.1f}min")

    # 统计
    tcas = [r[0] for r in run_results]
    acas = [r[1] for r in run_results]
    times = [r[2] for r in run_results]

    print(f"\n{'='*60}")
    print(f"  qwen3:8b 稳定性评测 ({RUNS}轮 × 1000条)")
    print(f"{'='*60}")
    print(f"  {'指标':<16} {'均值':>8} {'标准差':>8} {'最低':>8} {'最高':>8}")
    print(f"  {'─'*16} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    print(f"  {'模板分类':<16} {sum(tcas)/RUNS:>7.1f}% {__import__('statistics').stdev(tcas):>7.1f}% {min(tcas):>7.1f}% {max(tcas):>7.1f}%")
    print(f"  {'病灶检测':<16} {sum(acas)/RUNS:>7.1f}% {__import__('statistics').stdev(acas):>7.1f}% {min(acas):>7.1f}% {max(acas):>7.1f}%")
    print(f"  {'耗时(min)':<16} {sum(times)/RUNS:>7.1f} {__import__('statistics').stdev(times):>7.1f} {min(times):>7.1f} {max(times):>7.1f}")
    print(f"{'='*60}")

    # 对比
    print(f"\n  对比:")
    print(f"  {'方案':<22} {'模板%':>7} {'病灶%':>7}")
    print(f"  {'─'*22} {'─'*7} {'─'*7}")
    print(f"  {'规则引擎(v2)':<22} {'99.2':>7} {'98.2':>7}")
    print(f"  {'qwen2.5:14b(100条)':<22} {'100.0':>7} {'71.0':>7}")
    print(f"  {'qwen3:8b(10×1000)':<22} {sum(tcas)/RUNS:>6.1f}% {sum(acas)/RUNS:>6.1f}%")

if __name__ == '__main__':
    main()
