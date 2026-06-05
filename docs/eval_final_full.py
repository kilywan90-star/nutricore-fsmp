#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen2.5:14b + 规则引擎 混合流水线 — 17500条v2数据集全量评测
方案: qwen2.5提取template+measurements → 规则引擎覆盖abnormality
"""
import csv, json, re, time, random
from collections import defaultdict, Counter
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:14b"
DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset_v2.csv"
TEMPLATE_NAMES = {'A':'大排畸','B':'胎儿心超','C':'成人心超','D':'血管','E':'全腹'}

PROMPT = """你是超声医学报告结构化提取系统。提取模板分类和所有测量数值。
同音还原: 双丁径=双顶径 古骨=股骨 冻麦=动脉 净麦=静脉 益福=EF 内中末=内中膜 反留=反流 办膜=瓣膜 肾余=肾盂。
单位修复: 123.4m→123.4mm  次每→bpm。
模板: A大排畸(胎儿双顶径/头围/股骨/胎盘) B胎儿心超(胎心/瓣膜血流) C成人心超(左心室/EF/二尖瓣E/A) D血管(颈动脉IMT/PSV/EDV) E全腹(肝/胆囊/胰腺/肾)。
返回JSON: {"template":"A","measurements":{"BPD":"55.2mm","HC":"195.9mm"},"abnormality":"无"}"""

# ====== 规则引擎 ======
CORRUPTION_MAP = {
    '双顶径':['双丁径'],'股骨':['古骨'],'动脉':['冻麦'],'静脉':['净麦'],
    '内中膜':['内中末'],'反流':['反留'],'肾盂':['肾余'],'瓣膜':['办膜'],
    '瓣':['办'],'腔':['仓'],'室':['时'],'径':['经'],'厚':['后'],
    '流':['留'],'宽':['款'],'EF':['益福'],'AFI':['阿菲指数'],
}
def cv(kw):
    vs = {kw}
    for c, ws in CORRUPTION_MAP.items():
        if c in kw:
            for w in ws: vs.add(kw.replace(c, w))
    return list(vs)

BASE = ['缺损','狭窄','关闭不全','心包积液','室间隔增厚','左室壁增厚','左室后壁增厚',
    '心包增厚','升主动脉增宽','左心房增大','左心室增大','右心房增大','右心室增大',
    '内中膜增厚','IMT增厚','斑块','粥样硬化','囊肿','结石','息肉','肌瘤','增生',
    '脂肪肝','肾盂分离','强回声','钙化','绕颈','单脐动脉','强回声光点','肠管回声增强',
    '脉络丛','永存左上','舒张功能减退','流速偏快','流速增快','流速减低','纤细','脾大',
    '占位','脱垂','E/A<1','肾动脉狭窄']
KW = set()
for kw in BASE: KW.update(cv(kw))
KW.update(['缺如','粥样','反流','反留','返流','强回','光点','单脐','舒张功能减',
    '室间隔增后','内中末增后','内中末增厚','左房增大','右房增大','升主动脉增款',
    '分离','流速降低','二尖办反流','二尖反流','尖瓣反流','尖办反流','尖瓣反留',
    '主冻麦反流','主动脉反留','三尖办反流','三尖反流','心包积','心包积掖','心包积夜',
    '室间隔基底部增厚','室间隔基底部增后','室间隔基底增厚','左心房增','左室增大',
    '左时增大','血栓','曲张','腹水','胰管扩张'])
KW = sorted(KW, key=len, reverse=True)
NEG = re.compile(r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常的|正常|无\s*积|无\s*狭)')
REF = re.compile(r'[反返]流[留]?\s*[流留]速')
LA = re.compile(r'左心房?\s*前后')
CATH = re.compile(r'(尖瓣|尖办|三尖|二尖)[^，。；]{0,6}$')

def rule_detect(text):
    for kw in KW:
        idx = text.find(kw)
        if idx < 0: continue
        if kw == '分离':
            if not any(w in text[max(0,idx-5):idx+len(kw)] for w in ['肾盂分离','肾余分离']): continue
        if any(s in kw for s in ['反流','反留','返流']):
            nb15 = text[max(0,idx-15):idx+len(kw)+15]
            if REF.search(nb15): continue
            aft15 = text[idx+len(kw):idx+len(kw)+15]
            if re.match(r'^\s*[流留]', aft15): continue
            if re.match(r'^\s*\d+\.?\d*\s*(cm|cm/s|c/s|cms|m/s)', aft15): continue
            if CATH.search(text[max(0,idx-15):idx]): continue
            if re.search(r'流[留]?\s*[流留]?速', nb15): continue
        if '左心房增大' in kw or '左心房增' in kw or '左房增' in kw:
            if LA.search(text[max(0,idx-8):idx+len(kw)+8]): continue
        if '室间隔' in kw and any(s in kw for s in ['增厚','增后']):
            bef = text[max(0,idx-15):idx]
            if re.search(r'厚度\s*\d', bef): continue
            if re.search(r'^\s*\d+\.?\d*\s*mm', text[idx+len(kw):idx+len(kw)+10]): continue
        if NEG.search(text[max(0,idx-20):idx]): continue
        if any(s in kw for s in ['积液','心包积液','积','狭窄','积掖','积夜']):
            if re.search(r'(未见|无|排除)', text[idx+len(kw):idx+len(kw)+8]): continue
        return True
    return False

def call_model(asr):
    payload = {
        "model": MODEL,
        "prompt": f"{PROMPT}\n\nASR: {asr}",
        "stream": False,
        "options": {"temperature": 0, "num_predict": 800}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=45)
        return r.json().get("response", "")
    except:
        return "ERROR"

def parse(raw):
    try: return json.loads(raw)
    except: pass
    m = re.search(r'\{[^{}]*"template"[^{}]*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return None

def match_meas(pred_meas, gold_json):
    gold_vals = []
    for k, v in gold_json.get("measurements", {}).items():
        nums = re.findall(r'(\d+\.?\d*)', str(v))
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

random.seed(42)

# 加载全部17500条
all_records = []
with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f); header = next(reader)
    for row in reader:
        if len(row) < 5: continue
        all_records.append(row)

# 分层抽样: 每模板500条, 共2500条 (需约 2500*12s ≈ 8h, 实际5-8h)
SAMPLES_PER = 500
samples = []
for t in 'ABCDE':
    t_records = [r for r in all_records if r[2] == t]
    picks = random.sample(t_records, min(SAMPLES_PER, len(t_records)))
    samples.extend(picks)
random.shuffle(samples)

total = len(samples)
print(f"qwen2.5:14b + 规则引擎 混合评测")
print(f"样本: {total}条 ({SAMPLES_PER}/模板)")
print(f"预计: {total*10//60}~{total*15//60}分钟\n")

stats = {'template_correct':0, 'prec_sum':0.0, 'rec_sum':0.0, 'abnorm_correct':0,
         'parse_ok':0, 'by_template':{t:{'n':0,'t':0,'p':0.0,'r':0.0,'a':0} for t in 'ABCDE'}}
start_time = time.time()

for i, row in enumerate(samples):
    asr = row[1]; true_t = row[2]
    ans = json.loads(row[4])
    true_ab = ans.get('abnormality','无') not in ('无','',None) and ans.get('abnormality','') != '无'

    t0 = time.time()
    raw = call_model(asr)
    elapsed = time.time() - t0

    pred = parse(raw)
    parse_ok = pred is not None
    if pred is None:
        pred = {"template":"?","measurements":{},"abnormality":"无"}
    else:
        stats['parse_ok'] += 1

    pred_t = pred.get("template","?").strip().upper()
    pred_meas = pred.get("measurements", {})

    # 规则覆盖abnormality
    hybrid_ab = rule_detect(asr)
    ab_ok = (hybrid_ab == true_ab)

    tm_ok = (pred_t == true_t)
    matched, n_gold, n_pred = match_meas(pred_meas, ans)
    prec = matched / n_pred if n_pred > 0 else 0
    rec = matched / n_gold if n_gold > 0 else 0

    stats['template_correct'] += 1 if tm_ok else 0
    stats['prec_sum'] += prec; stats['rec_sum'] += rec
    stats['abnorm_correct'] += 1 if ab_ok else 0

    pt = stats['by_template'][true_t]
    pt['n'] += 1; pt['t'] += 1 if tm_ok else 0
    pt['p'] += prec; pt['r'] += rec; pt['a'] += 1 if ab_ok else 0

    ok_mark = 'OK' if tm_ok else 'X'
    ab_mark = 'OK' if ab_ok else 'X'
    print(f"[{i+1:4d}/{total}] [{true_t}] t={pred_t} {ok_mark} m={matched}/{n_gold} ab={ab_mark} p={'Y' if parse_ok else 'N'} ({elapsed:.1f}s)")

    if (i+1) % 100 == 0:
        n = i+1
        mp = stats['prec_sum']/n*100; mr = stats['rec_sum']/n*100
        mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
        tca = stats['template_correct']/n*100
        aca = stats['abnorm_correct']/n*100
        pct = stats['parse_ok']/n*100
        et = (time.time()-start_time)/60
        eta = et/n*(total-n)
        print(f">> [{n}/{total}] 模板{tca:.1f}% 测量F1={mf1:.1f}% 病灶{aca:.1f}% 解析{pct:.0f}% 耗时{et:.0f}m 剩余~{eta:.0f}m")

# 最终报告
n = total
tca = stats['template_correct']/n*100
mp = stats['prec_sum']/n*100; mr = stats['rec_sum']/n*100
mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
aca = stats['abnorm_correct']/n*100
et = (time.time()-start_time)/60

print(f"\n{'='*60}")
print(f"  qwen2.5:14b + 规则引擎 混合流水线 (n={n})")
print(f"  总耗时: {et:.0f}分钟  JSON解析: {stats['parse_ok']}/{n} ({stats['parse_ok']/n*100:.1f}%)")
print(f"{'='*60}")
print(f"  模板分类: {tca:.1f}%")
print(f"  测量F1:   {mf1:.1f}%  (P={mp:.1f}% R={mr:.1f}%)")
print(f"  病灶检测: {aca:.1f}%")

print(f"\n  分模板:")
print(f"  {'模板':<16} {'N':>4} {'分类%':>7} {'精确%':>7} {'召回%':>7} {'病灶%':>7}")
for t in 'ABCDE':
    pt = stats['by_template'][t]
    if pt['n']>0:
        print(f"  {TEMPLATE_NAMES[t]:<16} {pt['n']:>4} {pt['t']/pt['n']*100:>6.1f}% "
              f"{pt['p']/pt['n']*100:>6.1f}% {pt['r']/pt['n']*100:>6.1f}% "
              f"{pt['a']/pt['n']*100:>6.1f}%")

# 最终对比
print(f"\n{'='*60}")
print(f"  最终方案对比")
print(f"{'='*60}")
print(f"  {'方案':<22} {'模板%':>7} {'测量F1%':>8} {'病灶%':>7}")
print(f"  {'─'*22} {'─'*7} {'─'*8} {'─'*7}")
print(f"  {'纯规则引擎(v2)':<22} {'99.2':>7} {'88.8':>8} {'98.2':>7}")
print(f"  {'纯规则引擎(v1混合100)':<22} {'100.0':>7} {'92.2':>8} {'92.0':>7}")
print(f"  {'qwen2.5:14b裸模型':<22} {'100.0':>7} {'95.9':>8} {'71.0':>7}")
print(f"  {'混合流水线(v2)':<22} {tca:>6.1f}% {mf1:>7.1f}% {aca:>6.1f}%")
