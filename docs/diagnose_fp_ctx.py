#!/usr/bin/env python3
"""诊断C模板FP: 找"积液"/"狭窄"被触发的具体上下文"""
import csv, re

AB = ['缺损','缺如','反流','反留','返流','狭窄','关闭不全','积液','心包积液',
    '室间隔增厚','室间隔增后','左室壁增厚','左室后壁增厚','心包增厚',
    '升主动脉增宽','升主动脉增款','左心房增大','左房增大',
    '左心室增大','右心房增大','右房增大','右心室增大',
    '内中膜增厚','内中末增后','IMT增厚',
    '斑块','粥样硬化','粥样','囊肿','结石','息肉','肌瘤','增生','脂肪肝',
    '肾盂分离','肾余分离','分离','强回声','强回','钙化','绕颈','单脐动脉','单脐',
    '强回声光点','光点','肠管回声增强','脉络丛','永存左上',
    '舒张功能减退','舒张功能减','功能不全','流速偏快','流速增快','流速减低','流速降低',
    '纤细','脾大','占位','脱垂','E/A<1','E/A < 1','肾动脉狭窄']

NEG = re.compile(r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常)')
REF = re.compile(r'[反返]流[留]?\s*[流留]速')

def has_ab(s):
    for p in s.split('/'):
        if p.strip().startswith('异常='):
            return p.split('=',1)[1].strip() != '无'
    return False

print("=== C FP (积液/狭窄) 采样 ===")
fp_by_kw = {}
fp_samples = []

with open(r'e:\claude\docs\ultrasound_asr_testset\02_template_C_3000.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='|')
    next(reader)
    for row in reader:
        if len(row) < 4: continue
        asr, struct = row[1], row[3]
        if has_ab(struct): continue  # 只看正常记录中的FP
        for kw in ['积液', '心包积液', '狭窄']:
            idx = asr.find(kw)
            if idx < 0: continue
            pfx = asr[max(0,idx-20):idx]
            if NEG.search(pfx): continue
            after_ctx = asr[idx+len(kw):idx+len(kw)+8]
            if re.search(r'(未见|无|排除)', after_ctx): continue
            ctx = asr[max(0,idx-40):idx+len(kw)+40]
            fp_by_kw[kw] = fp_by_kw.get(kw, 0) + 1
            if len(fp_samples) < 6:
                fp_samples.append((row[0], kw, ctx))

print(f"FP触发: 积液={fp_by_kw.get('积液',0)} 心包积液={fp_by_kw.get('心包积液',0)} 狭窄={fp_by_kw.get('狭窄',0)}")
for i, kw, ctx in fp_samples:
    print(f"\n#{i} kw={kw}")
    print(f"  ctx: ...{ctx}...")
