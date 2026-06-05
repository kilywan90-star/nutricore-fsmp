#!/usr/bin/env python3
"""诊断成人心超(C)剩余FP — 统计每个异常关键词的触发频率"""
import csv, re
from collections import Counter

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

def has_abnorm(structured):
    for p in structured.split('/'):
        if p.strip().startswith('异常='):
            return p.split('=',1)[1].strip() != '无'
    return False

fps_by_kw = Counter()
total_normal = 0
total_fp = 0

with open(r'e:\claude\docs\ultrasound_asr_testset\02_template_C_3000.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='|')
    next(reader)
    for row in reader:
        if len(row) < 4: continue
        asr = row[1]; struct = row[3]
        if has_abnorm(struct): continue  # skip truly abnormal
        total_normal += 1
        triggered = []
        for kw in ABNORMAL_POSITIVE:
            idx = asr.find(kw)
            if idx < 0: continue
            if kw == '分离':
                pfx = asr[max(0,idx-5):idx+len(kw)]
                if not any(w in pfx for w in ['肾盂分离','肾余分离']): continue
            if kw in ('反流','反留','返流'):
                nearby = asr[max(0,idx-3):idx+len(kw)+3]
                if re.search(r'[反返]流[留]?\s*[流留]速', nearby): continue
                after = asr[idx+len(kw):idx+len(kw)+10]
                if re.match(r'\s*\d+', after): continue
            pfx = asr[max(0,idx-15):idx]
            if NEG.search(pfx): continue
            triggered.append(kw)
        if triggered:
            total_fp += 1
            for kw in triggered:
                fps_by_kw[kw] += 1

print(f"Total normal: {total_normal}, Total FP: {total_fp} ({total_fp/total_normal*100:.1f}%)")
print(f"\nTop FP keywords:")
for kw, cnt in fps_by_kw.most_common(20):
    print(f"  {kw}: {cnt}")
