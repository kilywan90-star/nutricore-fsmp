#!/usr/bin/env python3
"""All-in-one: run detect on all 5 templates, output precise FP/FN matrices"""
import csv, re
from collections import Counter

ABNORMAL = [
    '缺损','缺如','反流','反留','返流','狭窄','关闭不全','心包积液',
    '室间隔增厚','室间隔增后','左室壁增厚','左室后壁增厚','心包增厚',
    '升主动脉增宽','升主动脉增款','左心房增大',
    '左心室增大','右心房增大','右心室增大',
    '内中膜增厚','内中末增后','IMT增厚',
    '斑块','粥样硬化','粥样','囊肿','结石','息肉','肌瘤','增生','脂肪肝',
    '肾盂分离','肾余分离','分离','强回声','强回','钙化','绕颈','单脐动脉','单脐',
    '强回声光点','光点','肠管回声增强','脉络丛','永存左上',
    '舒张功能减退','舒张功能减',
    '流速偏快','流速增快','流速减低','流速降低',
    '纤细','脾大','占位','脱垂','E/A<1','E/A < 1','肾动脉狭窄',
]

NEG = re.compile(r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常的|正常|无\s*积|无\s*狭)')
REFLUX = re.compile(r'[反返]流[留]?\s*[流留]速')
LA_NORMAL = re.compile(r'左心房?\s*前后径')

def detect(text):
    for kw in ABNORMAL:
        idx = text.find(kw)
        if idx < 0: continue
        if kw == '分离':
            pfx = text[max(0,idx-5):idx+len(kw)]
            if not any(w in pfx for w in ['肾盂分离','肾余分离']): continue
        if kw in ('反流','反留','返流'):
            nearby = text[max(0,idx-10):idx+len(kw)+10]
            if REFLUX.search(nearby): continue
            after = text[idx+len(kw):idx+len(kw)+12]
            if re.match(r'^\s*[流留]', after): continue
            if re.match(r'^\s*\d+', after): continue
        if kw == '左心房增大':
            nearby_la = text[max(0,idx-5):idx+len(kw)+5]
            if LA_NORMAL.search(nearby_la): continue
        if kw in ('室间隔增厚','室间隔增后'):
            before = text[max(0,idx-15):idx]
            after = text[idx+len(kw):idx+len(kw)+10]
            if re.search(r'厚度\s*\d', before): continue
            if re.search(r'\d+\.?\d*\s*mm', after): continue
        pfx = text[max(0,idx-20):idx]
        if NEG.search(pfx): continue
        if kw in ('积液','心包积液','狭窄'):
            after_ctx = text[idx+len(kw):idx+len(kw)+8]
            if re.search(r'(未见|无|排除)', after_ctx): continue
        return kw, True
    return '', False

def has_ab(gold):
    for p in gold.split('/'):
        if p.strip().startswith('异常='):
            return p.split('=',1)[1].strip() != '无'
    return False

TEMPLATES = {
    'A': r'e:\claude\docs\ultrasound_asr_testset\02_template_A_3000.csv',
    'B': r'e:\claude\docs\ultrasound_asr_testset\02_template_B_3000.csv',
    'C': r'e:\claude\docs\ultrasound_asr_testset\02_template_C_3000.csv',
    'D': r'e:\claude\docs\ultrasound_asr_testset\02_template_D_3000.csv',
    'E': r'e:\claude\docs\ultrasound_asr_testset\02_template_E_3000.csv',
}

print("=== 全模板FP/FN诊断 ===")
for tc, fp in TEMPLATES.items():
    tp = tn = fp_c = fn_c = 0
    fp_kws = Counter()
    fn_samples = []
    with open(fp, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)
        for row in reader:
            if len(row) < 4: continue
            asr, gold = row[1], row[3]
            true_ab = has_ab(gold)
            kw, pred_ab = detect(asr)
            if pred_ab and true_ab: tp += 1
            elif pred_ab and not true_ab: fp_c += 1; fp_kws[kw] += 1
            elif not pred_ab and true_ab: fn_c += 1
            else: tn += 1
    total = tp+tn+fp_c+fn_c
    acc = (tp+tn)/total*100
    print(f"\n  [{tc}] Acc={acc:.1f}% TP={tp} TN={tn} FP={fp_c} FN={fn_c}")
    if fp_c > 0:
        print(f"    FP keywords: {fp_kws.most_common(8)}")
