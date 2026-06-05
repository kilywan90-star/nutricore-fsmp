#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合流水线评测:
ASR文本 → 模型提取JSON (template + measurements) → 规则引擎修正病灶 → 最终结果
对比: 纯规则 / 裸模型 / 规则嵌入模型 / 混合流水线
"""
import csv, json, re, time
from collections import defaultdict
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:14b-instruct"
DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset\01_mixed_100.csv"
MAX_SAMPLES = 100

TEMPLATE_NAMES = {'A':'大排畸','B':'胎儿心超','C':'成人心超','D':'血管','E':'全腹'}

# ====== 完整模型prompt (保留数值提取能力) ======
FULL_PROMPT = """你是超声医学报告结构化提取系统。请提取模板分类和所有测量数值，异常判断请忽略（我会用其他工具）。

同音还原: 双丁径=双顶径 古骨=股骨 冻麦=动脉 净麦=静脉 益福=EF 内中末=内中膜 反留=反流 办膜=瓣膜 肾余=肾盂 阿菲指数=AFI 匹斯维=PSV 后度=厚度

单位修复: 123.4m→123.4mm  46.8cm在速度语境→46.8cm/s  次每→bpm

模板分类: A大排畸(胎儿双顶径/头围/股骨/胎盘羊水) B胎儿心超(胎心/瓣膜血流/主动脉/肺动脉) C成人心超(左心室/EF/二尖瓣E/A) D血管(颈动脉IMT/PSV/EDV/椎动脉/股总动脉) E全腹(肝/胆囊/胰腺/脾/肾/门静脉)

只返回JSON: {"template":"A","measurements":{"BPD":"55.2mm","HC":"195.9mm"}, "abnormality":"无"}
注意: abnormality统一填"无", 是否正确无关紧要。"""

# ====== 规则引擎病灶检测 (复用v12最优版) ======
CORRUPTION_MAP = {
    '双顶径':['双丁径'],'股骨':['古骨'],'动脉':['冻麦'],'静脉':['净麦'],
    '内中膜':['内中末'],'反流':['反留'],'肾盂':['肾余'],'瓣膜':['办膜'],
    '瓣':['办'],'腔':['仓'],'室':['时'],'径':['经'],'厚':['后'],
    '流':['留'],'宽':['款'],'EF':['益福'],'AFI':['阿菲指数'],
}
def corrupt_variants(kw):
    vs = {kw}
    for c, ws in CORRUPTION_MAP.items():
        if c in kw:
            for w in ws: vs.add(kw.replace(c, w))
    return list(vs)

BASE_KEYWORDS = [
    '缺损','狭窄','关闭不全','心包积液','室间隔增厚',
    '左室壁增厚','左室后壁增厚','心包增厚','升主动脉增宽',
    '左心房增大','左心室增大','右心房增大','右心室增大',
    '内中膜增厚','IMT增厚','斑块','粥样硬化','囊肿','结石',
    '息肉','肌瘤','增生','脂肪肝','肾盂分离','强回声','钙化',
    '绕颈','单脐动脉','强回声光点','肠管回声增强','脉络丛',
    '永存左上','舒张功能减退','流速偏快','流速增快','流速减低',
    '纤细','脾大','占位','脱垂','E/A<1','肾动脉狭窄',
]
KEYWORDS = set()
for kw in BASE_KEYWORDS: KEYWORDS.update(corrupt_variants(kw))
KEYWORDS.update([
    '缺如','粥样','反流','反留','返流','强回','光点','单脐',
    '舒张功能减','室间隔增后','内中末增后','内中末增厚',
    '左房增大','右房增大','升主动脉增款','分离','流速降低',
    '二尖办反流','二尖反流','尖瓣反流','尖办反流','尖瓣反留',
    '主冻麦反流','主动脉反留','三尖办反流','三尖反流',
    '心包积','心包积掖','心包积夜',
    '室间隔基底部增厚','室间隔基底部增后','室间隔基底增厚',
    '左心房增','左室增大','左时增大',
    '血栓','曲张','腹水','胰管扩张',
])
KEYWORDS = sorted(KEYWORDS, key=len, reverse=True)

NEG = re.compile(r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常的|正常|无\s*积|无\s*狭)')
REF_VEL = re.compile(r'[反返]流[留]?\s*[流留]速')
LA_SAFE = re.compile(r'左心房?\s*前后')
CATH_INFO = re.compile(r'(尖瓣|尖办|三尖|二尖)[^，。；]{0,6}$')

def rule_detect_abnormality(text):
    """规则引擎独立判定病灶(从v12移植)"""
    for kw in KEYWORDS:
        idx = text.find(kw)
        if idx < 0: continue
        if kw == '分离':
            pfx = text[max(0,idx-5):idx+len(kw)]
            if not any(w in pfx for w in ['肾盂分离','肾余分离']): continue
        if any(s in kw for s in ['反流','反留','返流']):
            nb15 = text[max(0,idx-15):idx+len(kw)+15]
            if REF_VEL.search(nb15): continue
            aft15 = text[idx+len(kw):idx+len(kw)+15]
            if re.match(r'^\s*[流留]', aft15): continue
            if re.match(r'^\s*\d+\.?\d*\s*(cm|cm/s|c/s|cms|m/s)', aft15): continue
            before = text[max(0,idx-15):idx]
            if CATH_INFO.search(before): continue
            if re.search(r'流[留]?\s*[流留]?速', nb15): continue
        if '左心房增大' in kw or '左心房增' in kw or '左房增' in kw:
            nbla = text[max(0,idx-8):idx+len(kw)+8]
            if LA_SAFE.search(nbla): continue
        if '室间隔' in kw and any(s in kw for s in ['增厚','增后']):
            bef = text[max(0,idx-15):idx]
            aft = text[idx+len(kw):idx+len(kw)+10]
            if re.search(r'厚度\s*\d', bef): continue
            if re.search(r'^\s*\d+\.?\d*\s*mm', aft): continue
        pfx = text[max(0,idx-20):idx]
        if NEG.search(pfx): continue
        if any(s in kw for s in ['积液','心包积液','积','狭窄','积掖','积夜']):
            afc = text[idx+len(kw):idx+len(kw)+8]
            if re.search(r'(未见|无|排除)', afc): continue
        return True
    return False


# ====== 工具函数 ======
def call_ollama(prompt, asr_text, timeout=120):
    payload = {
        "model": MODEL,
        "prompt": f"{prompt}\n\nASR: {asr_text}",
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
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    m = re.search(r'\{[^{}]*"template"[^{}]*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return None

def match_measurements(pred_meas, structured):
    gold_vals = []
    for part in re.split(r'[/|]', structured):
        if '=' not in part: continue
        k, v = part.split('=', 1)
        k, v = k.strip(), v.strip()
        if k in ('异常','结构','性别','肝回声'): continue
        if v in ('无','均匀','稍增粗'): continue
        nums = re.findall(r'(\d+\.?\d*)', v)
        if nums: gold_vals.append((k, float(nums[0])))
    pred_vals = []
    for k, v in pred_meas.items():
        nums = re.findall(r'(\d+\.?\d*)', str(v))
        if nums: pred_vals.append((k, float(nums[0])))
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
    print(f"  混合流水线评测: 模型提取 + 规则修正病灶")
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

    # 四种方案的统计
    stats_hybrid = {'template_correct':0, 'prec_sum':0.0, 'rec_sum':0.0, 'abnorm_correct':0}
    stats_rule_only = {'template_correct':0, 'prec_sum':0.0, 'rec_sum':0.0, 'abnorm_correct':0}  # v12 numbers pre-loaded

    start = time.time()

    for i, row in enumerate(records):
        asr_text = row[1]; true_t = row[2]; structured = row[3]

        t0 = time.time()
        raw = call_ollama(FULL_PROMPT, asr_text)
        elapsed = time.time() - t0

        pred_json = parse_output(raw)
        if pred_json is None:
            pred_json = {"template":"?", "measurements":{}, "abnormality":"无"}

        pred_t = pred_json.get("template","?").strip().upper()
        pred_meas = pred_json.get("measurements", {})

        # 混合流水线: 模型提取template+measurements, 规则修正abnormality
        hybrid_ab = rule_detect_abnormality(asr_text)

        # 评估
        tm_ok = (pred_t == true_t)
        matched, n_gold, n_pred = match_measurements(pred_meas, structured)
        prec = matched / n_pred if n_pred > 0 else 0
        rec = matched / n_gold if n_gold > 0 else 0

        true_ab = gold_has_abnorm(structured)
        ab_ok = (hybrid_ab == true_ab)

        stats_hybrid['template_correct'] += 1 if tm_ok else 0
        stats_hybrid['prec_sum'] += prec
        stats_hybrid['rec_sum'] += rec
        stats_hybrid['abnorm_correct'] += 1 if ab_ok else 0

        ab_mark = 'OK' if ab_ok else 'X'
        print(f"  [{i+1}/{total}] [{true_t}] t={pred_t} m={matched}/{n_gold} ab={ab_mark} ({elapsed:.1f}s)")

        if (i+1) % 25 == 0:
            n = i+1
            mp = stats_hybrid['prec_sum']/n*100; mr = stats_hybrid['rec_sum']/n*100
            mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
            tca = stats_hybrid['template_correct']/n*100
            aca = stats_hybrid['abnorm_correct']/n*100
            et = (time.time()-start)/60
            print(f"  >> [{n}/{total}] 模板{tca:.0f}% 测量F1={mf1:.0f}% 病灶{aca:.0f}% ({et:.1f}min)\n")

    # 输出四方案对比
    n = total
    h_tca = stats_hybrid['template_correct']/n*100
    h_mp = stats_hybrid['prec_sum']/n*100; h_mr = stats_hybrid['rec_sum']/n*100
    h_mf1 = 2*h_mp*h_mr/(h_mp+h_mr) if h_mp+h_mr>0 else 0
    h_aca = stats_hybrid['abnorm_correct']/n*100

    print(f"\n{'='*60}")
    print(f"  四方案对比 (v1混合100条)")
    print(f"{'='*60}")
    print(f"  {'方案':<18} {'模板%':>8} {'测量F1%':>9} {'病灶%':>8}")
    print(f"  {'─'*18} {'─'*8} {'─'*9} {'─'*8}")
    print(f"  {'纯规则引擎':<18} {'100.0':>8} {'92.2':>9} {'92.0':>8}")
    print(f"  {'裸模型(14b)':<18} {'100.0':>8} {'95.9':>9} {'71.0':>8}")
    print(f"  {'规则嵌入模型':<18} {'94.0':>8} {'66.7':>9} {'84.0':>8}")
    print(f"  {'混合流水线':<18} {h_tca:>7.1f}% {h_mf1:>8.1f}% {h_aca:>7.1f}%")
    print(f"{'='*60}")

    # 判断最优方案
    print(f"\n  结论:")
    best_tca = max(100.0, 100.0, 94.0, h_tca)
    best_mf1 = max(92.2, 95.9, 66.7, h_mf1)
    best_aca = max(92.0, 71.0, 84.0, h_aca)
    print(f"    模板分类最优: 裸模型/规则引擎 (100.0%)")
    print(f"    测量F1最优:   {'裸模型' if best_mf1==95.9 else ('混合流水线' if best_mf1==h_mf1 else '规则引擎')} ({best_mf1:.1f}%)")
    print(f"    病灶检测最优: {'规则引擎' if best_aca==92.0 else ('混合流水线' if best_aca==h_aca else '规则嵌入模型')} ({best_aca:.1f}%)")

    if h_mf1 > 92.2 and h_aca > 92.0:
        print(f"\n    ★ 混合流水线全面超越规则引擎! ★")
    elif h_mf1 > 90 and h_aca > 85:
        print(f"\n    混合流水线接近最优, 推荐使用")
    else:
        print(f"\n    当前最优方案仍是纯规则引擎")


if __name__ == '__main__':
    main()
