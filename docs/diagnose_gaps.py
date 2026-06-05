#!/usr/bin/env python3
"""精确诊断脚本: D/E测量F1低 + C病灶FP残留, 输出具体失败案例"""
import csv, re, json
from collections import Counter, defaultdict

DATA_DIR = r"e:\claude\docs\ultrasound_asr_testset"

# ---- 1. 数值提取诊断 (复用v6逻辑) ----
def extract_all_measures(text):
    measures = []
    seen = set()
    patterns = [
        (r'(\d+\.?\d*)\s*(cm/s|cm\s*/\s*s|cm/s)', 'cm/s'),
        (r'(\d+\.?\d*)\s*(cm\s*²|cm\s*2)', 'cm²'),
        (r'(\d+\.?\d*)\s*(mm\s*Hg)', 'mmHg'),
        (r'(\d+\.?\d*)\s*(mm)', 'mm'),
        (r'(\d+\.?\d*)\s*(cm)(?![a-z/²])', 'cm'),
        (r'(\d+\.?\d*)\s*(%|％)', '%'),
        (r'(\d+\.?\d*)\s*(bpm)', 'bpm'),
        (r'(\d+\.?\d*)\s*(ms)', 'ms'),
        (r'(\d+\.?\d*)\s*cm(?=\s*[,;，；。\s]|$)', 'cm_maybe_vel'),
        (r'(\d+\.?\d*)\s*m(?=\s*[,;，；。\s]|$)', 'mm_trunc'),
        (r'(\d+)\s*次\s*每\s*分', 'bpm'),
        (r'(\d+)\s*次\s*每', 'bpm_trunc'),
        (r'(\d+)\s*次\s*/', 'bpm_trunc'),
        (r'[Ee]/[Aa]\s*[比值]?\s*(\d+\.?\d*)', 'ratio'),
        (r'RI\s*(\d+\.?\d*)', 'ratio'),
        (r'CTR\s*(\d+\.?\d*)', 'ratio'),
        (r'心胸面积比\s*(\d+\.?\d*)', 'ratio'),
        (r'孕\s*(\d+)\s*周\s*(\d*)\s*天?', '周'),
        (r'(\d+)\s*天', '天'),
        (r'(\d+)\s*岁', '岁'),
    ]
    for pattern, unit in patterns:
        for m in re.finditer(pattern, text):
            start, end = m.start(), m.end()
            if any(s < end and e > start for s, e in seen):
                continue
            if unit == '周':
                try:
                    measures.append((float(m.group(1)), '周'))
                except ValueError: pass
                if m.lastindex >= 2 and m.group(2):
                    try:
                        measures.append((float(m.group(2)), '天'))
                    except ValueError: pass
                seen.add((start, end))
                continue
            val_str = m.group(1) if m.lastindex >= 1 else m.group(0)
            try:
                val = float(val_str)
            except ValueError: continue
            if unit in ('天','岁') and val > 120: continue
            if unit == '周' and val > 45: continue
            if val <= 0: continue
            if unit == 'cm_maybe_vel':
                unit = 'cm/s' if 20 <= val <= 500 else 'cm'
            if unit == 'mm_trunc':
                unit = 'mm/s' if 200 <= val <= 5000 else 'mm'
            if unit == 'bpm_trunc':
                if 40 <= val <= 250: unit = 'bpm'
                else: continue
            measures.append((val, unit))
            seen.add((start, end))
    return measures

def parse_answer_measures(structured_str):
    measures = []
    parts = re.split(r'[/|]', structured_str)
    for part in parts:
        part = part.strip()
        if '=' not in part: continue
        key, val = part.split('=', 1)
        key, val = key.strip(), val.strip()
        if key in ['异常','结构','肝回声','性别','胎盘']: continue
        if val in ['无','均匀','稍增粗']: continue
        if key == 'GA':
            for m in re.finditer(r'(\d+)\s*周\s*(\d*)\s*天?', val):
                measures.append((float(m.group(1)), '周'))
                if m.group(2): measures.append((float(m.group(2)), '天'))
            continue
        if key == '年龄':
            try: measures.append((float(val), '岁'))
            except ValueError: pass
            continue
        if key in ('HR','胎心'):
            try: measures.append((float(re.sub(r'[bpm]','',val)), 'bpm'))
            except ValueError: pass
            continue
        measures.extend(extract_all_measures(val))
    return measures

def units_compatible(u1, u2):
    if u1 == u2: return True
    if {u1,u2} == {'cm/s','cm'}: return True
    if {u1,u2} == {'mm/s','mm'}: return True
    if 'ratio' in (u1,u2) and 'num' in (u1,u2): return True
    return False

def match_measures(asr_measures, gold_measures, tolerance=0.06):
    matched, used = 0, set()
    unmatched_gold = []
    for g_val, g_unit in gold_measures:
        best_dist, best_idx = float('inf'), -1
        for i, (a_val, a_unit) in enumerate(asr_measures):
            if i in used: continue
            if not units_compatible(g_unit, a_unit): continue
            if g_val == 0:
                dist = 0 if a_val == 0 else float('inf')
            else:
                dist = abs(a_val - g_val) / g_val
            if dist < best_dist and dist < tolerance:
                best_dist, best_idx = dist, i
        if best_idx >= 0:
            matched += 1
            used.add(best_idx)
        else:
            unmatched_gold.append((g_val, g_unit))
    return matched, len(asr_measures), len(gold_measures), unmatched_gold

# ---- 2. 病灶检测诊断 ----
ABNORMAL_POSITIVE = [
    '缺损','缺如','反流','反留','返流','狭窄','关闭不全','积液','心包积液',
    '室间隔增厚','室间隔增后','左室壁增厚','左室后壁增厚','心包增厚',
    '升主动脉增宽','升主动脉增款','左心房增大','左房增大',
    '左心室增大','右心房增大','右房增大','右心室增大',
    '内中膜增厚','内中末增后','IMT增厚',
    '斑块','粥样硬化','粥样','囊肿','结石','息肉','肌瘤','增生','脂肪肝',
    '肾盂分离','肾余分离','分离','强回声','强回','钙化','绕颈','单脐动脉','单脐',
    '强回声光点','光点','肠管回声增强','脉络丛','永存左上',
    '舒张功能减退','舒张功能减','功能不全','流速偏快','流速增快','流速减低','流速降低',
    '纤细','脾大','占位','脱垂','E/A<1','E/A < 1','肾动脉狭窄',
]
NEG_PREFIX = re.compile(r'(未见|无明显|无异常|无\s*明显|未\s*见|不\s*宽|不\s*厚|未\s*增|正常)')
REFLUX_VEL = re.compile(r'[反返]流[留]?\s*[流留]速')

def detect_abnormality(text):
    for keyword in ABNORMAL_POSITIVE:
        idx = text.find(keyword)
        if idx < 0: continue
        if keyword == '分离':
            pfx = text[max(0,idx-5):idx+len(keyword)]
            if not any(w in pfx for w in ['肾盂分离','肾余分离']): continue
        if keyword in ('反流','反留','返流'):
            nearby = text[max(0,idx-10):idx+len(keyword)+10]
            if REFLUX_VEL.search(nearby): continue
            after = text[idx+len(keyword):idx+len(keyword)+12]
            if re.match(r'^\s*[流留]', after): continue
            if re.match(r'^\s*\d+', after): continue
        prefix = text[max(0,idx-15):idx]
        if NEG_PREFIX.search(prefix): continue
        return True
    return False

def has_abnorm_in_gold(s):
    for p in s.split('/'):
        if p.strip().startswith('异常='):
            return p.split('=',1)[1].strip() != '无'
    return False

# ---- 主诊断 ----
def diagnose_measurement(template_code, template_file, max_samples=2000):
    """诊断数值提取: 输出未匹配的gold值分布"""
    unmatched_counter = Counter()
    prec_sum, rec_sum = 0.0, 0.0
    total = 0
    with open(template_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)
        for row in reader:
            if len(row) < 4: continue
            asr, struct = row[1], row[3]
            am = extract_all_measures(asr)
            gm = parse_answer_measures(struct)
            matched, n_asr, n_gold, unmatched = match_measures(am, gm)
            total += 1
            if n_asr > 0: prec_sum += matched / n_asr
            if n_gold > 0: rec_sum += matched / n_gold
            for v, u in unmatched:
                unmatched_counter[(u, round(v, 1))] += 1
            if total >= max_samples: break

    prec = prec_sum / total * 100
    rec = rec_sum / total * 100
    print(f"\n  数值诊断 [{template_code}]:")
    print(f"    Precision={prec:.1f}%  Recall={rec:.1f}%  (N={total})")
    print(f"    Top 10 未匹配值 (单位,近似值):")
    for (u, v), c in unmatched_counter.most_common(10):
        print(f"      {u} ~{v}: {c}次")

def diagnose_lesion(template_code, template_file, max_samples=3000):
    """诊断病灶检测: 输出FP/FN案例"""
    fp_kw = Counter()
    fn_texts = []
    total, fp, fn, tp, tn = 0, 0, 0, 0, 0
    with open(template_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)
        for row in reader:
            if len(row) < 4: continue
            asr, struct = row[1], row[3]
            true_ab = has_abnorm_in_gold(struct)
            pred_ab = detect_abnormality(asr)
            total += 1
            if pred_ab and not true_ab:
                fp += 1
                # 找触发词
                for kw in ABNORMAL_POSITIVE:
                    idx = asr.find(kw)
                    if idx >= 0:
                        # 检查是否被排除规则忽略
                        if kw == '分离':
                            pfx = asr[max(0,idx-5):idx+len(kw)]
                            if not any(w in pfx for w in ['肾盂分离','肾余分离']): continue
                        if kw in ('反流','反留','返流'):
                            nearby = asr[max(0,idx-10):idx+len(kw)+10]
                            if REFLUX_VEL.search(nearby): continue
                            after = asr[idx+len(kw):idx+len(kw)+12]
                            if re.match(r'^\s*[流留]', after): continue
                            if re.match(r'^\s*\d+', after): continue
                        pfx = asr[max(0,idx-15):idx]
                        if NEG_PREFIX.search(pfx): continue
                        fp_kw[kw] += 1
                        break
            elif not pred_ab and true_ab:
                fn += 1
                if len(fn_texts) < 3:
                    fn_texts.append((row[0], asr[:200], struct[:150]))
            elif pred_ab and true_ab:
                tp += 1
            else:
                tn += 1
            if total >= max_samples: break

    acc = (tp+tn)/total*100
    print(f"\n  病灶诊断 [{template_code}]:")
    print(f"    Acc={acc:.1f}%  TP={tp}  TN={tn}  FP={fp}  FN={fn}  (N={total})")
    if fp > 0:
        print(f"    FP触发词Top10:")
        for kw, c in fp_kw.most_common(10):
            print(f"      {kw}: {c}")
    if fn > 0:
        print(f"    FN案例:")
        for i, t, s in fn_texts:
            print(f"      #{i} asr={t[:100]}...")
            print(f"          gold={s[:100]}...")


if __name__ == '__main__':
    print("="*60)
    print("精确诊断报告")
    print("="*60)

    # D(血管) 测量诊断
    diagnose_measurement('D:血管', rf'{DATA_DIR}\02_template_D_3000.csv')

    # E(全腹) 测量诊断
    diagnose_measurement('E:全腹', rf'{DATA_DIR}\02_template_E_3000.csv')

    # C(成人心超) 病灶诊断
    diagnose_lesion('C:成人心超', rf'{DATA_DIR}\02_template_C_3000.csv')

    # D(血管) 病灶诊断
    diagnose_lesion('D:血管', rf'{DATA_DIR}\02_template_D_3000.csv')

    # E(全腹) 病灶诊断
    diagnose_lesion('E:全腹', rf'{DATA_DIR}\02_template_E_3000.csv')
