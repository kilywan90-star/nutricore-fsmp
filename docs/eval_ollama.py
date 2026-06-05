#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 Ollama qwen2.5:14b 模型评测脚本
对比规则引擎 vs 模型推理在三项指标上的表现
"""
import csv, json, re, time, sys
from collections import defaultdict, Counter
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:14b-instruct"

DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset\01_mixed_100.csv"
MAX_SAMPLES = 100  # 评测100条

TEMPLATE_NAMES = {'A': '大排畸', 'B': '胎儿心超', 'C': '成人心超', 'D': '血管', 'E': '全腹'}

# ====== PROMPT ======
SYSTEM_PROMPT = """你是一个超声医学报告结构化提取系统。用户会给你一条超声ASR语音识别后的乱文本（包含同音错字、缺字、口语冗余等噪声），你需要提取以下JSON：

{
  "template": "A/B/C/D/E",
  "measurements": {"字段名": "数值+单位", ...},
  "abnormality": "异常描述或无"
}

模板分类规则：
- A(中孕期大排畸): 胎儿双顶径、头围、腹围、股骨长、胎盘、羊水
- B(胎儿心超): 胎心、心胸面积比、二尖瓣/三尖瓣血流、主动脉/肺动脉瓣上流速
- C(成人心超): 左心室舒张末径、室间隔厚度、EF射血分数、二尖瓣E/A
- D(全身血管): 颈总动脉IMT、颈内动脉PSV/EDV、椎动脉内径、股总动脉PSV
- E(全腹彩超): 肝右叶斜径、胆囊大小、胰腺、脾、双肾、门静脉

measurements提取规则：
- 从ASR乱文本中提取所有测量数值和单位(mm, cm/s, %, bpm, cm²等)
- 同音词需还原：双丁径=双顶径, 古骨=股骨, 冻麦=动脉, 净麦=静脉, 益福=EF, 内中末=内中膜, 反留=反流, 办膜=瓣膜
- 单位残缺需补全：123.4m → 123.4mm, 46.8cm在速度语境 → 46.8cm/s

abnormality提取规则：
- 如果文本中有异常发现（缺损/反流/狭窄/囊肿/结石/斑块/积液/增厚/脂肪肝等），提取具体描述
- "XX反流流速"是正常测量项，不算异常
- 如果无异常，填"无"

只返回JSON，不要解释。"""


def call_ollama(asr_text, timeout=120):
    """调用本地Ollama模型"""
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nASR文本: {asr_text}",
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 1024,
        }
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        return f"ERROR: {e}"


def parse_model_output(raw_text):
    """从模型输出中提取JSON"""
    # 尝试直接解析
    try:
        return json.loads(raw_text)
    except:
        pass
    # 尝试从```json```块提取
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    # 尝试找 {...}
    m = re.search(r'\{[^{}]*"template"[^{}]*\}', raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except:
            pass
    return None


def extract_gold_from_row(row):
    """从v1格式（template|structured）提取标准答案"""
    # row: [idx, asr_text, template_letter, structured]
    structured = row[3]
    gold = {"template": row[2], "measurements": {}, "abnormality": "无"}

    parts = re.split(r'[/|]', structured)
    for part in parts:
        part = part.strip()
        if '=' not in part:
            continue
        key, val = part.split('=', 1)
        key, val = key.strip(), val.strip()

        if key == '异常':
            gold["abnormality"] = val
        elif key == '结构':
            pass  # skip
        elif key in ('性别', '肝回声'):
            pass
        elif val not in ('无', '均匀', '稍增粗'):
            gold["measurements"][key] = val

    return gold


def evaluate_model_output(pred_json, gold):
    """对比模型输出与标准答案"""
    results = {}

    # 1. 模板分类
    pred_t = pred_json.get("template", "?").strip().upper() if pred_json else "?"
    gold_t = gold["template"]
    results["template_match"] = pred_t == gold_t
    results["template_pred"] = pred_t

    # 2. 测量数值（简化比较：看字段名是否大致匹配 + 数值相近）
    pred_meas = pred_json.get("measurements", {}) if pred_json else {}
    gold_meas = gold["measurements"]

    # 计数
    matched_fields = 0
    for gk, gv in gold_meas.items():
        # 在模型输出中找匹配
        gv_num = re.findall(r'(\d+\.?\d*)', str(gv))
        for pk, pv in pred_meas.items():
            pv_num = re.findall(r'(\d+\.?\d*)', str(pv))
            if gv_num and pv_num:
                if abs(float(gv_num[0]) - float(pv_num[0])) < max(float(gv_num[0]) * 0.06, 0.5):
                    matched_fields += 1
                    break

    total_gold = len(gold_meas)
    total_pred = len(pred_meas)
    results["measurement_precision"] = matched_fields / total_pred if total_pred > 0 else 0
    results["measurement_recall"] = matched_fields / total_gold if total_gold > 0 else 0
    results["gold_meas_count"] = total_gold
    results["pred_meas_count"] = total_pred

    # 3. 病灶
    pred_ab = pred_json.get("abnormality", "无") if pred_json else "无"
    gold_ab = gold["abnormality"]
    # 简单判断
    pred_has_ab = pred_ab not in ("无", "", None) and pred_ab != "无"
    gold_has_ab = gold_ab not in ("无", "", None) and gold_ab != "无"
    results["abnormality_match"] = (pred_has_ab == gold_has_ab)
    results["pred_abnormality"] = str(pred_ab)[:100]
    results["gold_abnormality"] = str(gold_ab)[:100]

    return results


def main():
    print("=" * 60)
    print(f"  本地模型评测: Ollama {MODEL}")
    print(f"  数据集: {DATA_FILE}")
    print("=" * 60)

    # 加载数据
    records = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)
        for row in reader:
            if len(row) >= 4:
                records.append(row)
    records = records[:MAX_SAMPLES]

    print(f"\n开始评测 {len(records)} 条样本...")
    print(f"每条预计耗时 2-5 秒，总计约 {len(records)*3//60} 分钟\n")

    all_results = []
    stats = {
        'total': len(records),
        'template_correct': 0,
        'prec_sum': 0.0, 'rec_sum': 0.0,
        'abnorm_correct': 0,
        'errors': 0,  # 模型输出解析失败
        'by_template': defaultdict(lambda: {'n': 0, 't': 0, 'p': 0.0, 'r': 0.0, 'a': 0}),
    }

    for i, row in enumerate(records):
        asr_text = row[1]
        gold = extract_gold_from_row(row)
        true_t = gold["template"]

        # 调用模型
        print(f"  [{i+1}/{len(records)}] [{true_t}] {asr_text[:60]}...", end=" ", flush=True)
        start_time = time.time()
        raw = call_ollama(asr_text)
        elapsed = time.time() - start_time

        pred_json = parse_model_output(raw)
        if pred_json is None:
            print(f"PARSE_ERROR ({elapsed:.1f}s)")
            stats['errors'] += 1
            # 使用默认值继续统计
            pred_json = {"template": "?", "measurements": {}, "abnormality": "无"}
        else:
            print(f"OK ({elapsed:.1f}s)")

        results = evaluate_model_output(pred_json, gold)
        all_results.append({
            'idx': row[0],
            'template': true_t,
            'asr_preview': asr_text[:80],
            'model_raw': raw[:200],
            'results': results,
        })

        # 汇总
        stats['template_correct'] += 1 if results['template_match'] else 0
        stats['prec_sum'] += results['measurement_precision']
        stats['rec_sum'] += results['measurement_recall']
        stats['abnorm_correct'] += 1 if results['abnormality_match'] else 0

        pt = stats['by_template'][true_t]
        pt['n'] += 1
        pt['t'] += 1 if results['template_match'] else 0
        pt['p'] += results['measurement_precision']
        pt['r'] += results['measurement_recall']
        pt['a'] += 1 if results['abnormality_match'] else 0

        # 每20条输出一次中间统计
        if (i + 1) % 20 == 0:
            tca = stats['template_correct'] / (i + 1) * 100
            mp = stats['prec_sum'] / (i + 1) * 100
            mr = stats['rec_sum'] / (i + 1) * 100
            mf1 = 2 * mp * mr / (mp + mr) if mp + mr > 0 else 0
            aca = stats['abnorm_correct'] / (i + 1) * 100
            print(f"  >> 中间: 模板{tca:.0f}% 测量F1={mf1:.0f}% 病灶{aca:.0f}% 耗时{elapsed:.1f}s")

    # ====== 最终报告 ======
    n = stats['total']
    tca = stats['template_correct'] / n * 100
    mp = stats['prec_sum'] / n * 100
    mr = stats['rec_sum'] / n * 100
    mf1 = 2 * mp * mr / (mp + mr) if mp + mr > 0 else 0
    aca = stats['abnorm_correct'] / n * 100

    print(f"\n{'='*60}")
    print(f"  模型评测结果: {MODEL}")
    print(f"{'='*60}")
    print(f"  总样本: {n}  |  解析失败: {stats['errors']}")
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

    # 对比规则引擎
    print(f"\n{'='*60}")
    print(f"  模型 vs 规则引擎 对比")
    print(f"{'='*60}")
    print(f"  {'指标':<16} {'规则引擎':>10} {'模型':>10}")
    print(f"  {'─'*16} {'─'*10} {'─'*10}")
    # 规则引擎v12数据（从上次运行获取）
    rule_tca, rule_mf1, rule_aca = 100.0, 92.2, 92.0
    print(f"  {'模板分类':<16} {rule_tca:>9.1f}% {tca:>9.1f}%")
    print(f"  {'测量F1':<16} {rule_mf1:>9.1f}% {mf1:>9.1f}%")
    print(f"  {'病灶检测':<16} {rule_aca:>9.1f}% {aca:>9.1f}%")

    # 保存详细结果
    output_file = r"e:\claude\docs\model_eval_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'model': MODEL,
                'total': n,
                'template_acc': tca,
                'measurement_f1': mf1,
                'abnormality_acc': aca,
                'parse_errors': stats['errors'],
            },
            'by_template': {t: {
                'n': stats['by_template'][t]['n'],
                'template_acc': stats['by_template'][t]['t']/stats['by_template'][t]['n']*100 if stats['by_template'][t]['n']>0 else 0,
                'meas_prec': stats['by_template'][t]['p']/stats['by_template'][t]['n']*100 if stats['by_template'][t]['n']>0 else 0,
                'meas_recall': stats['by_template'][t]['r']/stats['by_template'][t]['n']*100 if stats['by_template'][t]['n']>0 else 0,
                'abnorm_acc': stats['by_template'][t]['a']/stats['by_template'][t]['n']*100 if stats['by_template'][t]['n']>0 else 0,
            } for t in 'ABCDE'},
            'details': all_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_file}")


if __name__ == '__main__':
    main()
