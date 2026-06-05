#!/usr/bin/env python3
"""快速诊断成人心超(C)病灶检测假阳性根因"""
import csv, re

ABNORMAL_POSITIVE = [
    '缺损', '缺如', '反流', '反留', '返流', '狭窄', '关闭不全', '积液','心包积液',
    '增厚', '增宽', '增大', '斑块', '粥样硬化', '粥样', '囊肿', '结石', '息肉',
    '肌瘤', '增生', '脂肪肝', '肾盂分离', '肾余分离', '分离', '强回声','强回',
    '钙化', '绕颈', '单脐动脉', '单脐', '强回声光点','光点','肠管回声增强',
    '脉络丛', '永存左上', '舒张功能减退','舒张功能减','功能不全','流速偏快',
    '流速增快','流速减低','流速降低','纤细','脾大','占位','脱垂','E/A<1',
    'IMT增厚', '内中膜增厚','内中末增后','升主动脉增宽','左心房增大','左房增大',
    '肾动脉狭窄',
]

NEG = re.compile(r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常)')

def detect(text):
    for kw in ABNORMAL_POSITIVE:
        idx = text.find(kw)
        if idx < 0:
            continue
        prefix = text[max(0, idx-15):idx]
        if NEG.search(prefix):
            continue
        return kw, idx
    return None, -1

def has_abnorm(structured):
    for p in structured.split('/'):
        if p.strip().startswith('异常='):
            return p.split('=',1)[1].strip() != '无'
    return False

fp = 0
tn = 0
with open(r'e:\claude\docs\ultrasound_asr_testset\02_template_C_3000.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='|')
    next(reader)
    for row in reader:
        if len(row) < 4:
            continue
        asr = row[1]
        struct = row[3]
        kw, pos = detect(asr)
        true_ab = has_abnorm(struct)
        if kw and not true_ab:  # FP
            fp += 1
            if fp <= 5:
                ctx = asr[max(0,pos-30):pos+len(kw)+30]
                print(f"FP[{row[0]}]: kw='{kw}' ctx=...{ctx}...")
        elif not kw and true_ab:  # FN
            pass
        elif not kw and not true_ab:
            tn += 1

print(f"\nFP={fp}, TN={tn} (of ~2232 non-abnormal)")
