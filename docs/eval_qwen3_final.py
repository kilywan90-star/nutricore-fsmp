#!/usr/bin/env python3
"""
qwen3:8b + 规则引擎联合评测 (100条v1混合数据)
方案: qwen3提取结构化JSON → 规则引擎覆盖abnormality字段
与之前qwen2.5:14b四方案对比
"""
import csv, json, re, time, random
from collections import defaultdict
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:8b"
DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset\01_mixed_100.csv"
MAX_SAMPLES = 100
TEMPLATE_NAMES = {'A':'大排畸','B':'胎儿心超','C':'成人心超','D':'血管','E':'全腹'}

# ====== qwen3 需要更简洁的指令 ======
PROMPT = """分析这段ASR超声文本，判断属于哪个模板并提取测量值。

模板规则:
- 文本含"胎儿""双顶径""胎盘"等 → A(大排畸)
- 文本含"胎心""卵圆孔""动脉导管"等 → B(胎儿心超)
- 文本含"左心室""EF""室间隔"等 → C(成人心超)
- 文本含"颈总动脉""IMT""PSV"等 → D(血管)
- 文本含"肝脏""胆囊""胰腺""肾脏"等 → E(全腹)

提取所有数值和单位(mm/cm/s/bpm/%等)。
同音词还原: 益福=EF 冻麦=动脉 古骨=股骨 双丁径=双顶径 反留=反流 办膜=瓣膜 肾余=肾盂 内中末=内中膜。
单位修复: 123.4m=123.4mm 次每=bpm。

返回纯JSON:
{"template":"C","measurements":{"LVEDD":"54.3mm","EF":"64.5%"}}

abnormality字段统一填"无"。"""

# ====== 规则引擎病灶检测 (v12) ======
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

def rule_detect_abnormality(text):
    for kw in KW:
        idx = text.find(kw)
        if idx < 0: continue
        if kw == '分离':
            pfx = text[max(0,idx-5):idx+len(kw)]
            if not any(w in pfx for w in ['肾盂分离','肾余分离']): continue
        if any(s in kw for s in ['反流','反留','返流']):
            nb15 = text[max(0,idx-15):idx+len(kw)+15]
            if REF.search(nb15): continue
            aft15 = text[idx+len(kw):idx+len(kw)+15]
            if re.match(r'^\s*[流留]', aft15): continue
            if re.match(r'^\s*\d+\.?\d*\s*(cm|cm/s|c/s|cms|m/s)', aft15): continue
            before = text[max(0,idx-15):idx]
            if CATH.search(before): continue
            if re.search(r'流[留]?\s*[流留]?速', nb15): continue
        if '左心房增大' in kw or '左心房增' in kw or '左房增' in kw:
            nbla = text[max(0,idx-8):idx+len(kw)+8]
            if LA.search(nbla): continue
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


def call_qwen3(asr, timeout=60):
    payload = {
        "model": MODEL,
        "prompt": f"{PROMPT}\n\nASR: {asr}",
        "stream": False,
        "options": {"temperature": 0, "num_predict": 2000}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        data = r.json()
        resp = data.get("response", "")
        think = data.get("thinking", "")
        # qwen3 thinking mode: when response empty, use thinking content
        if not resp.strip() and think.strip():
            return think
        return resp
    except:
        return "ERROR"


def parse_output(raw):
    if not raw: return None
    # Try direct JSON first
    try: return json.loads(raw.strip())
    except: pass
    # Try markdown code block (```json...```)
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    # Try to find any {...} with template key
    m = re.search(r'\{[^{}]*"[Tt]emplate"[^{}]*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    # Try last {...} as fallback (thinking output may be before it)
    brackets = list(re.finditer(r'\{[^{}]*\}', raw))
    for m in reversed(brackets):
        try:
            obj = json.loads(m.group(0))
            if 'template' in obj:
                return obj
        except: pass
    # Try to find "template" field and extract surrounding JSON
    m = re.search(r'"template"\s*:\s*"([A-E?])"', raw)
    if m:
        # Build minimal result
        result = {"template": m.group(1), "measurements": {}, "abnormality": "无"}
        # Try to find measurements
        for num_m in re.finditer(r'(\d+\.?\d*)\s*(mm|cm|cm/s|bpm|%)', raw):
            result["measurements"][f"m_{num_m.start()}"] = num_m.group(0)
        return result
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
    print(f"  qwen3:8b + 规则引擎 联合评测 (100条)")
    print("="*60)

    records = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)
        for row in reader:
            if len(row) >= 4: records.append(row)
    records = records[:MAX_SAMPLES]

    stats = {'template_correct':0, 'prec_sum':0.0, 'rec_sum':0.0, 'abnorm_correct':0,
             'parse_ok':0, 'parse_json_ok':0, 'parse_md_ok':0, 'parse_regex_ok':0,
             'by_template':{t:{'n':0,'t':0,'p':0.0,'r':0.0,'a':0} for t in 'ABCDE'}}
    start = time.time()

    for i, row in enumerate(records):
        asr = row[1]; true_t = row[2]; structured = row[3]

        t0 = time.time()
        raw = call_qwen3(asr)
        elapsed = time.time() - t0

        pred = parse_output(raw)
        if pred is None:
            stats['parse_ok'] -= 1  # track failures
            # Check raw output for debug
            if i < 3:
                print(f"  DEBUG #{i+1}: raw={raw[:150]}")

        parse_method = 'none'
        if pred is None:
            pred = {"template":"?","measurements":{},"abnormality":"无"}
        else:
            parse_method = 'json' if raw.strip().startswith('{') else 'md' if '```' in raw else 'regex'
            if parse_method == 'json': stats['parse_json_ok'] += 1
            elif parse_method == 'md': stats['parse_md_ok'] += 1
            else: stats['parse_regex_ok'] += 1
            stats['parse_ok'] += 1

        pred_t = pred.get("template","?").strip().upper()
        pred_meas = pred.get("measurements", {})

        # 规则引擎覆盖abnormality
        hybrid_ab = rule_detect_abnormality(asr)
        true_ab = gold_has_abnorm(structured)

        tm_ok = (pred_t == true_t)
        matched, n_gold, n_pred = match_measurements(pred_meas, structured)
        prec = matched / n_pred if n_pred > 0 else 0
        rec = matched / n_gold if n_gold > 0 else 0
        ab_ok = (hybrid_ab == true_ab)

        stats['template_correct'] += 1 if tm_ok else 0
        stats['prec_sum'] += prec; stats['rec_sum'] += rec
        stats['abnorm_correct'] += 1 if ab_ok else 0

        pt = stats['by_template'][true_t]
        pt['n'] += 1; pt['t'] += 1 if tm_ok else 0
        pt['p'] += prec; pt['r'] += rec; pt['a'] += 1 if ab_ok else 0

        pm = parse_method[:4]
        am = 'OK' if ab_ok else 'X'
        print(f"  [{i+1:3d}/100] [{true_t}] t={pred_t} m={matched}/{n_gold} ab={am} parse={pm} ({elapsed:.1f}s)")

        if (i+1) % 25 == 0:
            n = i+1
            mp = stats['prec_sum']/n*100; mr = stats['rec_sum']/n*100
            mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
            tca = stats['template_correct']/n*100
            aca = stats['abnorm_correct']/n*100
            print(f"  >> 模板{tca:.0f}% 测量F1={mf1:.0f}% 病灶{aca:.0f}% pOK={stats['parse_ok']}/{n}")

    n = total = len(records)
    tca = stats['template_correct']/n*100
    mp = stats['prec_sum']/n*100; mr = stats['rec_sum']/n*100
    mf1 = 2*mp*mr/(mp+mr) if mp+mr>0 else 0
    aca = stats['abnorm_correct']/n*100
    elapsed_t = (time.time()-start)/60

    print(f"\n{'='*60}")
    print(f"  qwen3:8b + 规则引擎 结果 ({elapsed_t:.1f}min)")
    print(f"{'='*60}")
    print(f"  模型JSON解析: {stats['parse_ok']}/{n} (json={stats['parse_json_ok']} md={stats['parse_md_ok']} regex={stats['parse_regex_ok']})")
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

    # 对比
    print(f"\n{'='*60}")
    print(f"  五方案最终对比 (v1混合100条)")
    print(f"{'='*60}")
    print(f"  {'方案':<20} {'模板%':>7} {'测量F1%':>8} {'病灶%':>7}")
    print(f"  {'─'*20} {'─'*7} {'─'*8} {'─'*7}")
    print(f"  {'纯规则引擎':<20} {'100.0':>7} {'92.2':>8} {'92.0':>7}")
    print(f"  {'qwen2.5:14b 裸模型':<20} {'100.0':>7} {'95.9':>8} {'71.0':>7}")
    print(f"  {'qwen2.5:14b 规则嵌入':<20} {'94.0':>7} {'66.7':>8} {'84.0':>7}")
    print(f"  {'qwen2.5:14b 混合流水线':<20} {'96.0':>7} {'79.3':>8} {'95.0':>7}")
    print(f"  {'qwen3:8b 混合流水线':<20} {tca:>6.1f}% {mf1:>7.1f}% {aca:>6.1f}%")


if __name__ == '__main__':
    main()
