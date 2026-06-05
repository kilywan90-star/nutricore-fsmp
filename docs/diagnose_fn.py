#!/usr/bin/env python3
"""诊断FN: 检查被漏检的异常记录中的异常描述词"""
import csv, re

AB = {'缺损','缺如','反流','反留','返流','狭窄','关闭不全','积液','心包积液',
    '室间隔增厚','室间隔增后','左室壁增厚','左室后壁增厚','心包增厚',
    '升主动脉增宽','升主动脉增款','左心房增大','左房增大',
    '左心室增大','右心房增大','右房增大','右心室增大',
    '内中膜增厚','内中末增后','IMT增厚',
    '斑块','粥样硬化','粥样','囊肿','结石','息肉','肌瘤','增生','脂肪肝',
    '肾盂分离','肾余分离','分离','强回声','强回','钙化','绕颈','单脐动脉','单脐',
    '强回声光点','光点','肠管回声增强','脉络丛','永存左上',
    '舒张功能减退','舒张功能减','功能不全','流速偏快','流速增快','流速减低','流速降低',
    '纤细','脾大','占位','脱垂','E/A<1','E/A < 1','肾动脉狭窄'}

def has_ab(gold):
    for p in gold.split('/'):
        if p.strip().startswith('异常='):
            return p.split('=',1)[1].strip() != '无'
    return False

def get_true_abnorm_desc(gold):
    for p in gold.split('/'):
        if p.strip().startswith('异常='):
            val = p.split('=',1)[1].strip()
            return val if val != '无' else ''

for tmpl_code, tmpl_file in [
    ('C', r'e:\claude\docs\ultrasound_asr_testset\02_template_C_3000.csv'),
    ('D', r'e:\claude\docs\ultrasound_asr_testset\02_template_D_3000.csv'),
    ('E', r'e:\claude\docs\ultrasound_asr_testset\02_template_E_3000.csv'),
]:
    print(f"\n=== {tmpl_code} FN分析 ===")
    fn_count = 0
    fn_descs = []
    with open(tmpl_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)
        for row in reader:
            if len(row) < 4: continue
            asr, gold = row[1], row[3]
            if not has_ab(gold): continue
            # 检查是否命中
            found = False
            for kw in AB:
                idx = asr.find(kw)
                if idx < 0: continue
                # same detect logic as eval
                if kw == '分离':
                    pfx = asr[max(0,idx-5):idx+len(kw)]
                    if not any(w in pfx for w in ['肾盂分离','肾余分离']): continue
                if kw in ('反流','反留','返流'):
                    nearby = asr[max(0,idx-10):idx+len(kw)+10]
                    if re.search(r'[反返]流[留]?\s*[流留]速', nearby): continue
                    after = asr[idx+len(kw):idx+len(kw)+12]
                    if re.match(r'^\s*[流留]', after): continue
                    if re.match(r'^\s*\d+', after): continue
                pfx = asr[max(0,idx-15):idx]
                if re.search(r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常)', pfx): continue
                found = True
                break
            if not found:
                fn_count += 1
                desc = get_true_abnorm_desc(gold)
                if len(fn_descs) < 5:
                    fn_descs.append((row[0], desc, asr[:250]))

    print(f"  FN总数: {fn_count}")
    for i, d, a in fn_descs:
        print(f"  #{i} 真异常={d[:120]}")
        print(f"      asr={a[:180]}")
