#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对v2数据集(17500条)进行分层抽样模型评测
每模板随机抽取200条，共1000条
"""
import csv, json, re, time, random
from collections import defaultdict, Counter
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:14b-instruct"
DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset_v2.csv"
SAMPLES_PER_TEMPLATE = 200

TEMPLATE_NAMES = {'A':'大排畸','B':'胎儿心超','C':'成人心超','D':'血管','E':'全腹'}

SYSTEM_PROMPT = """你是一个超声医学报告结构化提取系统。按以下JSON格式返回结果：
{"template":"A/B/C/D/E","measurements":{"字段名":"数值+单位"}, "abnormality":"异常描述"}

模板分类：A大排畸(胎儿双顶径/头围/股骨/胎盘) B胎儿心超(胎心/瓣膜血流) C成人心超(左心室/EF/二尖瓣E/A) D全身血管(颈动脉IMT/PSV/EDV) E全腹(肝/胆囊/胰腺/脾/肾)

同音词还原：双丁径=双顶径 古骨=股骨 冻麦=动脉 净麦=静脉 益福=EF 内中末=内中膜 反留=反流 办膜=瓣膜 肾余=肾盂 阿菲指数=AFI 匹斯维=PSV

单位修复：123.4m→123.4mm  46.8cm在速度语境→46.8cm/s  次每→bpm

病灶：提取缺损/反流/狭窄/囊肿/结石/斑块/积液/增厚/脂肪肝/血栓/曲张等，"XX反流流速"是正常测量不算异常。无异常填"无"。

只返回JSON。"""


def call_ollama(asr_text, timeout=120):
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nASR: {asr_text}",
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


def match_measurement_values(pred_meas, gold_meas):
    """比较测量字段：找到数值匹配的个数"""
    matched = 0
    gold_vals = []
    for k, v in gold_meas.items():
        nums = re.findall(r'(\d+\.?\d*)', str(v))
        if nums:
            gold_vals.append((k, float(nums[0])))

    pred_vals = []
    for k, v in pred_meas.items():
        nums = re.findall(r'(\d+\.?\d*)', str(v))
        if nums:
            pred_vals.append((k, float(nums[0])))

    used = set()
    for gk, gv in gold_vals:
        for i, (pk, pv) in enumerate(pred_vals):
            if i in used: continue
            if abs(gv - pv) < max(gv * 0.06, 0.5):
                matched += 1
                used.add(i)
                break

    return matched, len(gold_vals), len(pred_vals)


def main():
    random.seed(42)
    print("=" * 60)
    print(f"  模型评测 {MODEL} — v2数据集分层抽样")
    print(f"  每模板{SAMPLES_PER_TEMPLATE}条 × 5 = 1000条")
    print("=" * 60)

    # 加载并分层抽样
    all_records = {t: [] for t in 'ABCDE'}
    with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 5: continue
            t = row[2]
            if t in all_records:
                all_records[t].append(row)

    samples = []
    for t in 'ABCDE':
        n = len(all_records[t])
        k = min(SAMPLES_PER_TEMPLATE, n)
        picks = random.sample(all_records[t], k)
        samples.extend(picks)
        print(f"  {TEMPLATE_NAMES[t]}: 抽样{k}/{n}")

    random.shuffle(samples)
    total = len(samples)
    print(f"\n总评测: {total}条 (含扰动标签分布详见结果)")
    print(f"预计耗时: {total*8//60}~{total*12//60}分钟\n")

    results = []
    stats = {
        'total': total, 'errors': 0,
        'template_correct': 0, 'prec_sum': 0.0, 'rec_sum': 0.0, 'abnorm_correct': 0,
        'by_template': {t: {'n':0,'t':0,'p':0.0,'r':0.0,'a':0,'tag_n':Counter()} for t in 'ABCDE'},
        'tag_stats': defaultdict(lambda: {'n':0,'t':0,'p':0.0,'r':0.0,'a':0}),
    }

    start_time = time.time()

    for i, row in enumerate(samples):
        asr_text = row[1]; true_t = row[2]; tags = row[3].split(",") if row[3] else []
        ans_json = json.loads(row[4])
        gold_meas = ans_json.get("measurements", {})
        gold_ab = ans_json.get("abnormality", "无")

        print(f"  [{i+1}/{total}] [{true_t}] {asr_text[:50]}...", end=" ", flush=True)
        t0 = time.time()
        raw = call_ollama(asr_text)
        elapsed = time.time() - t0

        pred_json = parse_output(raw)
        if pred_json is None:
            print(f"PARSE ({elapsed:.1f}s)")
            stats['errors'] += 1
            pred_json = {"template":"?","measurements":{},"abnormality":"无"}

        pred_t = pred_json.get("template","?").strip().upper()
        pred_meas = pred_json.get("measurements", {})
        pred_ab = pred_json.get("abnormality", "无")

        # 指标计算
        tm_ok = pred_t == true_t
        matched, n_gold, n_pred = match_measurement_values(pred_meas, gold_meas)
        prec = matched / n_pred if n_pred > 0 else 0
        rec = matched / n_gold if n_gold > 0 else 0

        gold_has_ab = gold_ab not in ("无", "", None) and gold_ab != "无"
        pred_has_ab = pred_ab not in ("无", "", None) and str(pred_ab) != "无"
        ab_ok = (gold_has_ab == pred_has_ab)

        stats['template_correct'] += 1 if tm_ok else 0
        stats['prec_sum'] += prec; stats['rec_sum'] += rec
        stats['abnorm_correct'] += 1 if ab_ok else 0

        pt = stats['by_template'][true_t]
        pt['n'] += 1; pt['t'] += 1 if tm_ok else 0
        pt['p'] += prec; pt['r'] += rec; pt['a'] += 1 if ab_ok else 0

        for tag in tags:
            tag = tag.strip()
            if tag:
                ts = stats['tag_stats'][tag]
                ts['n'] += 1; ts['t'] += 1 if tm_ok else 0
                ts['p'] += prec; ts['r'] += rec; ts['a'] += 1 if ab_ok else 0

        tag_str = ",".join(tags[:2])
        print(f"OK t={pred_t} m={matched}/{n_gold} ab={'OK' if ab_ok else 'X'} ({elapsed:.1f}s)")

        if (i + 1) % 50 == 0:
            elapsed_total = (time.time() - start_time) / 60
            eta = elapsed_total / (i + 1) * (total - i - 1)
            tca = stats['template_correct'] / (i+1) * 100
            mp = stats['prec_sum'] / (i+1) * 100
            mr = stats['rec_sum'] / (i+1) * 100
            mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
            aca = stats['abnorm_correct'] / (i+1) * 100
            print(f"  >> [{i+1}/{total}] 模板{tca:.0f}% 测量F1={mf1:.0f}% 病灶{aca:.0f}% 已耗时{elapsed_total:.0f}min 剩余~{eta:.0f}min")

    elapsed_total = (time.time() - start_time) / 60

    # ====== 最终报告 ======
    n = stats['total']
    tca = stats['template_correct'] / n * 100
    mp = stats['prec_sum'] / n * 100
    mr = stats['rec_sum'] / n * 100
    mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
    aca = stats['abnorm_correct'] / n * 100

    print(f"\n{'='*60}")
    print(f"  模型评测结果: {MODEL}")
    print(f"{'='*60}")
    print(f"  总耗时: {elapsed_total:.1f}分钟  |  解析失败: {stats['errors']}")
    print(f"  模板分类: {stats['template_correct']}/{n} = {tca:.1f}%")
    print(f"  测量值 Precision: {mp:.1f}%  Recall: {mr:.1f}%  F1: {mf1:.1f}%")
    print(f"  病灶检测: {stats['abnorm_correct']}/{n} = {aca:.1f}%")

    print(f"\n  分模板:")
    print(f"  {'模板':<16} {'N':>4} {'分类%':>7} {'精确%':>7} {'召回%':>7} {'病灶%':>7}")
    for t in 'ABCDE':
        pt = stats['by_template'][t]
        if pt['n'] > 0:
            print(f"  {TEMPLATE_NAMES[t]:<16} {pt['n']:>4} {pt['t']/pt['n']*100:>6.1f}% "
                  f"{pt['p']/pt['n']*100:>6.1f}% {pt['r']/pt['n']*100:>6.1f}% "
                  f"{pt['a']/pt['n']*100:>6.1f}%")

    # 对比规则引擎v2
    print(f"\n{'='*60}")
    print(f"  模型 vs 规则引擎 对比 (v2数据集)")
    print(f"{'='*60}")
    print(f"  {'指标':<16} {'规则引擎':>10} {'模型':>10} {'差异':>10}")
    print(f"  {'─'*16} {'─'*10} {'─'*10} {'─'*10}")
    rule_tca, rule_mf1, rule_aca = 99.2, 88.8, 98.2
    print(f"  {'模板分类':<16} {rule_tca:>9.1f}% {tca:>9.1f}% {tca-rule_tca:>+9.1f}%")
    print(f"  {'测量F1':<16} {rule_mf1:>9.1f}% {mf1:>9.1f}% {mf1-rule_mf1:>+9.1f}%")
    print(f"  {'病灶检测':<16} {rule_aca:>9.1f}% {aca:>9.1f}% {aca-rule_aca:>+9.1f}%")

    # 扰动标签维度
    print(f"\n  ┌─ 扰动标签维度 (模型) ────────────────────────")
    print(f"  │ {'标签':<16} {'N':>5} {'分类%':>7} {'测量F1%':>8} {'病灶%':>7}")
    for tag in sorted(stats['tag_stats'].keys(), key=lambda t: -stats['tag_stats'][t]['n']):
        ts = stats['tag_stats'][tag]
        if ts['n'] < 5: continue
        tp = ts['p']/ts['n']*100; tr = ts['r']/ts['n']*100
        tf1 = 2*tp*tr/(tp+tr) if tp+tr>0 else 0
        print(f"  │ {tag:<16} {ts['n']:>5} {ts['t']/ts['n']*100:>6.1f}% {tf1:>7.1f}% {ts['a']/ts['n']*100:>6.1f}%")
    print(f"  └──────────────────────────────────────────────")

    # 保存
    output = {
        'model': MODEL, 'samples': n, 'time_min': elapsed_total,
        'summary': {'template_acc': tca, 'measurement_f1': mf1, 'abnormality_acc': aca},
        'by_template': {},
        'vs_rules': {'rule_tca': rule_tca, 'rule_mf1': rule_mf1, 'rule_aca': rule_aca,
                     'model_tca': tca, 'model_mf1': mf1, 'model_aca': aca},
    }
    for t in 'ABCDE':
        pt = stats['by_template'][t]
        if pt['n'] > 0:
            output['by_template'][t] = {
                'n': pt['n'], 'template_acc': pt['t']/pt['n']*100,
                'meas_prec': pt['p']/pt['n']*100, 'meas_recall': pt['r']/pt['n']*100,
                'abnorm_acc': pt['a']/pt['n']*100,
            }
    with open(r"e:\claude\docs\model_eval_v2.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果: e:\\claude\\docs\\model_eval_v2.json")


if __name__ == '__main__':
    main()
