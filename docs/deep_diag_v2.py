#!/usr/bin/env python3
"""Deep diagnostic script v2"""
import csv, json, re
from collections import Counter, defaultdict

# === exact keyword detection from v13 ===
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
            for w in ws: vs.add(kw.replace(c,w))
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

def detect_abnormality(text):
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

# === measure extraction diagnostic ===
def extract_all_measures(text):
    measures, seen = [], set()
    patterns = [
        (r'(\d+\.?\d*)\s*(cm\s*/\s*s|cm/s)','cm/s'),
        (r'(\d+\.?\d*)\s*(cm)','cm'),
        (r'(\d+\.?\d*)\s*(mm)','mm'),
        (r'(\d+\.?\d*)\s*(%|％)','%'),
        (r'(\d+\.?\d*)\s*(bpm)','bpm'),
        (r'(\d+\.?\d*)\s*(ms)','ms'),
        (r'(\d+\.?\d*)\s*cm(?=\s*[,;，；。\s]|$)','cm_maybe_vel'),
        (r'(\d+\.?\d*)\s*m(?=\s*[,;，；。\s]|$)','mm_trunc'),
        (r'(\d+)\s*次\s*每\s*分','bpm'),
        (r'(\d+)\s*次\s*每','bpm_trunc'),
        (r'[Ee]/[Aa]\s*[比值]?\s*(\d+\.?\d*)','ratio'),
        (r'RI\s*(\d+\.?\d*)','ratio'),
        (r'CTR\s*(\d+\.?\d*)','ratio'),
        (r'心胸面积比\s*(\d+\.?\d*)','ratio'),
        (r'孕\s*(\d+)\s*周\s*(\d*)\s*天?','周'),
        (r'(\d+)\s*天','天'),
        (r'(\d+)\s*岁','岁'),
    ]
    for pat, unit in patterns:
        for m in re.finditer(pat, text):
            s, e = m.start(), m.end()
            if any(s0<e and e0>s for s0,e0 in seen): continue
            if unit == '周':
                try: measures.append((float(m.group(1)),'周'))
                except ValueError: pass
                if m.lastindex>=2 and m.group(2):
                    try: measures.append((float(m.group(2)),'天'))
                    except ValueError: pass
                seen.add((s,e)); continue
            try: val = float(m.group(1) if m.lastindex>=1 else m.group(0))
            except ValueError: continue
            if unit in ('天','岁') and val>120: continue
            if unit=='周' and val>45: continue
            if val<=0: continue
            unit_orig = unit
            if unit=='cm_maybe_vel':
                unit = 'cm/s' if 20<=val<=500 else 'cm'
            if unit=='mm_trunc': unit='mm'
            if unit=='bpm_trunc':
                if 40<=val<=250: unit='bpm'
                else: continue
            measures.append((val,unit,unit_orig))
            seen.add((s,e))
    return measures

# ======== MAIN DIAGNOSTIC ========
print("=== V2 数据集深度诊断 ===\n")

total = 0
by_template = defaultdict(lambda: {'n':0, 'abnorm_true':0, 'abnorm_pred':0, 'abnorm_fp':0, 'abnorm_fn':0,
                                     'asr_measures_total':0, 'gold_measures_total':0,
                                     'matched_vals':0, 'missing_gold_vals':Counter()})

with open(r'e:\claude\docs\ultrasound_asr_testset_v2.csv','r',encoding='utf-8-sig') as f:
    reader = csv.reader(f); next(reader)
    for row in reader:
        if len(row) < 5: continue
        asr = row[1]; tmpl = row[2]
        ans = json.loads(row[4])
        total += 1

        # Abnormality
        true_ab = ans.get('abnormality','无') != '无' and ans.get('abnormality','') != ''
        pred_ab = detect_abnormality(asr)
        st = by_template[tmpl]
        st['n'] += 1
        if true_ab: st['abnorm_true'] += 1
        if pred_ab: st['abnorm_pred'] += 1
        if pred_ab and not true_ab: st['abnorm_fp'] += 1
        if not pred_ab and true_ab: st['abnorm_fn'] += 1

        # Measures
        am = extract_all_measures(asr)
        gm_raw = ans.get('measurements', {})
        # Gold values from JSON — extract numeric parts
        gold_vals = []
        for k, v in gm_raw.items():
            for m in re.finditer(r'(\d+\.?\d*)', str(v)):
                try: gold_vals.append(float(m.group(1)))
                except: pass
        st['asr_measures_total'] += len(am)
        st['gold_measures_total'] += len(gold_vals)

for tmpl in 'ABCDE':
    st = by_template[tmpl]
    n = st['n']
    print(f"[{tmpl}] N={n}")
    print(f"  异常真实={st['abnorm_true']} 异常预测={st['abnorm_pred']} FP={st['abnorm_fp']} FN={st['abnorm_fn']}")
    prec = st['abnorm_true']/max(st['abnorm_pred'],1)*100
    rec = (st['abnorm_true']-st['abnorm_fn'])/max(st['abnorm_true'],1)*100
    print(f"  病灶Precision={prec:.1f}% Recall={rec:.1f}%")
    print(f"  ASR数值提取数={st['asr_measures_total']} 标准答案数值数={st['gold_measures_total']}")
    print(f"  平均ASR数值/条={st['asr_measures_total']/n:.1f}  平均Gold数值/条={st['gold_measures_total']/n:.1f}")

# Show 3 B template records to understand measurement format
print("\n=== B模板前3条数据样本 ===")
count = 0
with open(r'e:\claude\docs\ultrasound_asr_testset_v2.csv','r',encoding='utf-8-sig') as f:
    reader = csv.reader(f); next(reader)
    for row in reader:
        if len(row) < 5 or row[2] != 'B': continue
        ans = json.loads(row[4])
        print(f"\n#{row[0]} ASR: {row[1][:150]}...")
        print(f"  Measurements JSON: {json.dumps(ans.get('measurements',{}), ensure_ascii=False)[:200]}")
        print(f"  Abnormality: {ans.get('abnormality','无')}")
        count += 1
        if count >= 3: break

# Show D template records for similar diagnosis
print("\n=== D模板前3条数据样本 ===")
count = 0
with open(r'e:\claude\docs\ultrasound_asr_testset_v2.csv','r',encoding='utf-8-sig') as f:
    reader = csv.reader(f); next(reader)
    for row in reader:
        if len(row) < 5 or row[2] != 'D': continue
        ans = json.loads(row[4])
        print(f"\n#{row[0]} ASR: {row[1][:180]}...")
        print(f"  Measurements JSON: {json.dumps(ans.get('measurements',{}), ensure_ascii=False)[:200]}")
        count += 1
        if count >= 3: break
