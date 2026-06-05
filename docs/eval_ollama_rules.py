#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则增强模型评测：将同音词表、异常关键词、否定规则嵌入 prompt，
让模型"知道"我们的规则，测试准确率变化。
对比：裸模型 vs 规则增强模型 vs 纯规则引擎
"""
import csv, json, re, time, random, sys
from collections import defaultdict, Counter
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:14b-instruct"
DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset\01_mixed_100.csv"
MAX_SAMPLES = 100

TEMPLATE_NAMES = {'A':'大排畸','B':'胎儿心超','C':'成人心超','D':'血管','E':'全腹'}

# ====== 规则增强 SYSTEM PROMPT ======
RULES_PROMPT = """你是一个超声医学报告结构化提取系统。

## 同音词/错字还原表（必须遵守）
双丁径/双丁→双顶径  古骨→股骨  冻麦→动脉  净麦→静脉  益福→EF
内中末→内中膜  反留→反流  办膜→瓣膜  肾余→肾盂  阿菲指数→AFI
匹斯维→PSV  阿瑞→RI  后度→厚度  经→径  仓→腔  时→室  款→宽

## 异常关键词（任一出现即判为异常，除非有否定词）
- 结构异常：缺损、缺如、狭窄、关闭不全、骑跨、下移、早闭
- 反流类：反流、反留、返流 —— 但 "三尖瓣反流流速" "XX反流流速" 是正常测量，不算异常！
- 积: 心包积液 —— 但 "未见心包积液" "心包未见积液" 不算异常
- 增厚/增大/增宽：室间隔增厚、左室后壁增厚、心包增厚、升主动脉增宽、左心房增大、左心室增大、右心房增大、右心室增大、内中膜增厚、IMT增厚
- 肿块/结石：斑块、粥样硬化、囊肿、结石、息肉、肌瘤、占位
- 弥漫病变：脂肪肝、增生、钙化、纤维化
- 胎儿：单脐动脉、脐带绕颈、强回声光点、肠管回声增强、脉络丛囊肿、肾盂分离、NF增厚、羊水偏少、胃泡未显示
- 心功能：舒张功能减退、收缩功能减低、E/A<1
- 血管：血栓、曲张、瓣膜功能不全、动脉狭窄、肾动脉狭窄
- 流速异常：流速偏快、流速增快、流速减低、流速降低
- 其他：脾大、纤细、腹水、胰管扩张、脱垂

## 否定词（出现时排除异常）
未见、无明显、无异常、无明显、未增宽、未增厚、正常

## 模板分类
A(大排畸): 胎儿双顶径/头围/腹围/股骨/胎盘/羊水
B(胎儿心超): 胎心/心胸面积比/二尖瓣血流/三尖瓣血流/主动脉瓣上/肺动脉瓣上
C(成人心超): 左心室舒张末径/室间隔/EF射血分数/二尖瓣E/A
D(血管): 颈总动脉IMT/颈内动脉PSV/EDV/椎动脉内径/股总动脉
E(全腹): 肝右叶/胆囊/胰腺/脾/双肾/门静脉

## 输出格式
{"template":"A","measurements":{"BPD":"55.2mm","HC":"195.9mm"}, "abnormality":"无"}
只返回JSON。"""


def call_ollama(asr_text, timeout=120):
    payload = {
        "model": MODEL,
        "prompt": f"{RULES_PROMPT}\n\nASR: {asr_text}",
        "stream": False,
        "options": {"temperature": 0, "num_predict": 800}
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        return resp.json().get("response", "")
    except Exception as e:
        return f"ERROR:{e}"


def parse_output(raw):
    try: return json.loads(raw)
    except: pass
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    m = re.search(r'\{[^{}]*"template"[^{}]*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return None


def match_measurement_values(pred_meas, gold_raw):
    """gold_raw: extracted from v1 structured string"""
    gold_vals = []
    for part in re.split(r'[/|]', gold_raw):
        if '=' not in part: continue
        k, v = part.split('=', 1)
        k, v = k.strip(), v.strip()
        if k in ('异常','结构','性别','肝回声'): continue
        if v in ('无','均匀','稍增粗'): continue
        nums = re.findall(r'(\d+\.?\d*)', v)
        if nums:
            gold_vals.append((k, float(nums[0])))
    pred_vals = []
    for k, v in pred_meas.items():
        nums = re.findall(r'(\d+\.?\d*)', str(v))
        if nums:
            pred_vals.append((k, float(nums[0])))
    matched, used = 0, set()
    for gk, gv in gold_vals:
        for i, (pk, pv) in enumerate(pred_vals):
            if i in used: continue
            if abs(gv - pv) < max(gv * 0.06, 0.5):
                matched += 1; used.add(i); break
    return matched, len(gold_vals), len(pred_vals)


def gold_has_abnorm(structured):
    for p in re.split(r'[/|]', structured):
        if p.strip().startswith('异常='):
            return p.split('=',1)[1].strip() != '无'
    return False


def main():
    print("="*60)
    print(f"  规则增强模型评测: {MODEL}")
    print("="*60)

    records = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)
        for row in reader:
            if len(row) >= 4:
                records.append(row)
    records = records[:MAX_SAMPLES]
    total = len(records)

    print(f"\n评测 {total} 条...\n")

    stats = {
        'template_correct': 0, 'prec_sum': 0.0, 'rec_sum': 0.0, 'abnorm_correct': 0,
        'by_template': {t: {'n':0,'t':0,'p':0.0,'r':0.0,'a':0} for t in 'ABCDE'},
    }

    start_time = time.time()

    for i, row in enumerate(records):
        asr_text = row[1]
        true_t = row[2]
        structured = row[3]

        t0 = time.time()
        raw = call_ollama(asr_text)
        elapsed = time.time() - t0

        pred_json = parse_output(raw)
        if pred_json is None:
            pred_json = {"template":"?","measurements":{},"abnormality":"无"}

        pred_t = pred_json.get("template","?").strip().upper()
        pred_meas = pred_json.get("measurements", {})
        pred_ab = pred_json.get("abnormality", "无")

        tm_ok = (pred_t == true_t)
        matched, n_gold, n_pred = match_measurement_values(pred_meas, structured)
        prec = matched / n_pred if n_pred > 0 else 0
        rec = matched / n_gold if n_gold > 0 else 0

        true_ab = gold_has_abnorm(structured)
        pred_has_ab = pred_ab not in ("无","",None) and str(pred_ab) != "无"
        ab_ok = (true_ab == pred_has_ab)

        stats['template_correct'] += 1 if tm_ok else 0
        stats['prec_sum'] += prec; stats['rec_sum'] += rec
        stats['abnorm_correct'] += 1 if ab_ok else 0

        pt = stats['by_template'][true_t]
        pt['n'] += 1; pt['t'] += 1 if tm_ok else 0
        pt['p'] += prec; pt['r'] += rec; pt['a'] += 1 if ab_ok else 0

        ab_mark = 'OK' if ab_ok else 'X'
        print(f"  [{i+1}/{total}] [{true_t}] t={pred_t} m={matched}/{n_gold} ab={ab_mark} ({elapsed:.1f}s)")

        if (i+1) % 25 == 0:
            n = i+1
            tca = stats['template_correct']/n*100
            mp = stats['prec_sum']/n*100; mr = stats['rec_sum']/n*100
            mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
            aca = stats['abnorm_correct']/n*100
            elapsed_t = (time.time()-start_time)/60
            print(f"  >> [{n}/{total}] 模板{tca:.0f}% 测量F1={mf1:.0f}% 病灶{aca:.0f}% ({elapsed_t:.1f}min)\n")

    # Final
    n = len(records)
    tca = stats['template_correct']/n*100
    mp = stats['prec_sum']/n*100; mr = stats['rec_sum']/n*100
    mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
    aca = stats['abnorm_correct']/n*100
    elapsed_t = (time.time()-start_time)/60

    print(f"\n{'='*60}")
    print(f"  规则增强模型结果: {MODEL}")
    print(f"  总耗时: {elapsed_t:.1f}分钟")
    print(f"{'='*60}")
    print(f"  模板分类: {tca:.1f}%")
    print(f"  测量值 F1: {mf1:.1f}% (P={mp:.1f}% R={mr:.1f}%)")
    print(f"  病灶检测: {aca:.1f}%")

    print(f"\n  分模板:")
    print(f"  {'模板':<16} {'N':>4} {'分类%':>7} {'精确%':>7} {'召回%':>7} {'病灶%':>7}")
    for t in 'ABCDE':
        pt = stats['by_template'][t]
        if pt['n']>0:
            print(f"  {TEMPLATE_NAMES[t]:<16} {pt['n']:>4} {pt['t']/pt['n']*100:>6.1f}% "
                  f"{pt['p']/pt['n']*100:>6.1f}% {pt['r']/pt['n']*100:>6.1f}% "
                  f"{pt['a']/pt['n']*100:>6.1f}%")

    # 三方对比
    print(f"\n{'='*60}")
    print(f"  三方对比: 规则引擎 vs 裸模型 vs 规则增强模型")
    print(f"{'='*60}")
    print(f"  {'指标':<16} {'规则引擎':>10} {'裸模型':>10} {'规则+模型':>11}")
    print(f"  {'─'*16} {'─'*10} {'─'*10} {'─'*11}")
    print(f"  {'模板分类':<16} {'100.0%':>10} {'100.0%':>10} {tca:>10.1f}%")
    print(f"  {'测量F1':<16} {'92.2%':>10} {'95.9%':>10} {mf1:>10.1f}%")
    print(f"  {'病灶检测':<16} {'92.0%':>10} {'71.0%':>10} {aca:>10.1f}%")


if __name__ == '__main__':
    main()
