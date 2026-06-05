#!/usr/bin/env python3
"""Final FP diagnosis: print exactly which keywords fire in C normal records"""
import csv, re
from collections import Counter

# build keyword list identically to v10 eval
CORRUPTION = {
    '动脉': ['冻麦'], '静脉': ['净麦'], '内中膜': ['内中末'],
    '反流': ['反留'], '肾盂': ['肾余'], '瓣膜': ['办膜'],
    '瓣': ['办'], '腔': ['仓'], '室': ['时'],
    '径': ['经'], '厚': ['后'], '流': ['留'], '宽': ['款'],
}

BASE = [
    '缺损', '狭窄', '关闭不全', '心包积液', '室间隔增厚',
    '左室壁增厚', '左室后壁增厚', '心包增厚', '升主动脉增宽',
    '左心房增大', '左心室增大', '右心房增大', '右心室增大',
    '内中膜增厚', 'IMT增厚', '斑块', '粥样硬化', '囊肿', '结石',
    '息肉', '肌瘤', '增生', '脂肪肝', '肾盂分离', '强回声', '钙化',
    '绕颈', '单脐动脉', '强回声光点', '肠管回声增强', '脉络丛',
    '永存左上', '舒张功能减退', '流速偏快', '流速增快', '流速减低',
    '纤细', '脾大', '占位', '脱垂', 'E/A<1', '肾动脉狭窄',
]

def expand(kw):
    vs = [kw]
    for c, ws in CORRUPTION.items():
        if c in kw:
            for w in ws:
                vs.append(kw.replace(c, w))
    return list(set(vs))

KEYWORDS = []
for kw in BASE:
    KEYWORDS.extend(expand(kw))
KEYWORDS.extend([
    '缺如', '粥样', '反流', '反留', '返流', '强回', '光点', '单脐',
    '舒张功能减', '室间隔增后', '内中末增后', '内中末增厚',
    '左房增大', '右房增大', '升主动脉增款', '分离', '流速降低',
])
KEYWORDS = list(set(KEYWORDS))

NEG_PREFIX = re.compile(
    r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常的|正常|无\s*积|无\s*狭)'
)
REF_VEL = re.compile(r'[反返]流[留]?\s*[流留]速')
LA_SAFE = re.compile(r'左心房?\s*前后')

def detect(text):
    for kw in KEYWORDS:
        idx = text.find(kw)
        if idx < 0:
            continue
        # Check all filter rules
        if kw == '分离':
            pfx = text[max(0, idx-5):idx+len(kw)]
            if not any(w in pfx for w in ['肾盂分离', '肾余分离']):
                continue
        if kw in ('反流', '反留', '返流'):
            nb = text[max(0, idx-15):idx+len(kw)+15]
            if REF_VEL.search(nb):
                continue
            aft = text[idx+len(kw):idx+len(kw)+15]
            if re.match(r'^\s*[流留]', aft):
                continue
            if re.match(r'^\s*\d+\.?\d*\s*(cm|cm/s|c/s|cms|m/s)', aft):
                continue
            bef10 = text[max(0, idx-10):idx]
            if re.search(r'[办瓣]\s*\d+\.?\d*\s*$', bef10):
                continue
        if kw == '左心房增大':
            nbla = text[max(0, idx-8):idx+len(kw)+8]
            if LA_SAFE.search(nbla):
                continue
        if kw in ('室间隔增厚', '室间隔增后'):
            bef = text[max(0, idx-15):idx]
            aft = text[idx+len(kw):idx+len(kw)+10]
            if re.search(r'厚度\s*\d', bef):
                continue
            if re.search(r'^\s*\d+\.?\d*\s*mm', aft):
                continue
        pfx = text[max(0, idx-20):idx]
        if NEG_PREFIX.search(pfx):
            continue
        if kw in ('积液', '心包积液', '狭窄'):
            aftc = text[idx+len(kw):idx+len(kw)+8]
            if re.search(r'(未见|无|排除)', aftc):
                continue
        return kw, idx
    return '', -1

def has_abnorm(structured):
    for part in structured.split('/'):
        if part.strip().startswith('异常='):
            return part.split('=', 1)[1].strip() != '无'
    return False

# Main
fp_raw = Counter()
fp_samples = []
with open(r'e:\claude\docs\ultrasound_asr_testset\02_template_C_3000.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='|')
    next(reader)
    for row in reader:
        if len(row) < 4:
            continue
        asr_text = row[1]
        gold = row[3]
        if has_abnorm(gold):
            continue  # skip truly abnormal
        kw, idx = detect(asr_text)
        if kw:
            fp_raw[kw] += 1
            if len(fp_samples) < 6:
                ctx = asr_text[max(0, idx-35):idx+len(kw)+35]
                fp_samples.append((row[0], kw, ctx, gold))

print(f"Total FP records: {sum(fp_raw.values())}")
print(f"\nFP keywords (top 10):")
for kw, cnt in fp_raw.most_common(10):
    print(f"  '{kw}': {cnt}")

print(f"\nFP samples:")
for sid, kw, ctx, gold in fp_samples:
    print(f"\n  #{sid} kw='{kw}'")
    print(f"    ctx: ...{ctx}...")
    # Show gold abnormality field
    for part in gold.split('/'):
        if part.startswith('异常='):
            print(f"    gold: {part}")
            break
