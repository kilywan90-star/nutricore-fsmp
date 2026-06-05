#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超声ASR评测脚本 v13 — 适配v2数据进行评测
读取ultrasound_asr_testset_v2.csv (17500条)
输出三项指标 + 扰动标签分维度准确率
"""
import csv, json, re, os, sys
from collections import defaultdict, Counter

DATA_FILE = r"e:\claude\docs\ultrasound_asr_testset_v2.csv"

TEMPLATE_NAMES = {'A':'大排畸','B':'胎儿心超','C':'成人心超','D':'血管','E':'全腹'}

# =============== 腐败映射 ===============
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
            for w in ws:
                vs.add(kw.replace(c, w))
    return list(vs)

# =============== 1. 模板分类 ===============
TEMPLATE_KEYWORDS = {
    'A':['胎儿','双顶径','双丁径','头围','腹围','股骨长','古骨长','肱骨','小脑','侧脑室','侧脑时','羊水指数','阿菲指数','胎盘','羊水深度','颅骨光环','透明隔腔','透明隔仓','四肢长骨','鼻骨可见','上唇','胃泡','脐带','孕'],
    'B':['胎心','心胸面积','二尖瓣血','三尖瓣血','主动脉瓣上','肺动脉瓣上','降主动脉','卵圆孔','骑跨','动脉导管','肺静脉引流','肺净麦','上下腔静脉','永存左上腔','心轴'],
    'C':['左心室舒张','左心室收缩','室间隔厚度','左室后壁','左心房前后','主动脉根部','右心室前后','右心房左右','射血分数','缩短分数','心包积液','瓣反留','瓣反流','左心房增大','升主动脉增宽','舒张功能'],
    'D':['颈总动脉','颈内动脉','椎动脉','内中膜','内中末','股总动脉','腘动脉','胫后动脉','足背动脉','斑块','狭窄率','静脉瓣膜','反流时间','锁骨下','股浅动脉'],
    'E':['肝','胆囊','胰腺','胰头','胰体','胰尾','脾','肾','门静脉','肠系膜上动脉','腹主动脉','下腔静脉','脂肪肝','肝囊肿','胆囊结石','胆囊息肉','肾囊肿','肾结石','前列腺','子宫肌瘤','脾大','腹膜'],
}

def classify_template(text):
    scores = {k:0 for k in TEMPLATE_KEYWORDS}
    for t, kws in TEMPLATE_KEYWORDS.items():
        for kw in kws:
            if kw in text: scores[t] += 1
    # Fallback: if all scores are 0, use template-agnostic keywords
    if max(scores.values()) == 0:
        fallback_kws = {
            'A': ['孕', '周天', '胎儿', '胎盘', '羊水'],
            'B': ['胎心', '卵圆孔', '动脉导管'],
            'C': ['左心室', '射血分数', '二尖瓣', '心功能'],
            'D': ['颈动脉', 'PSV', 'EDV', 'IMT', '椎动脉', '股动脉', '腘动脉', '胫后', '足背'],
            'E': ['肝', '胆囊', '胰腺', '脾', '肾', '腹水', '脂肪'],
        }
        for t, kws in fallback_kws.items():
            for kw in kws:
                if kw in text: scores[t] += 1
    return max(scores, key=scores.get), scores

# =============== 2. 数值提取 ===============
VELOCITY_RANGE_CM_S = (20, 500)

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
            if unit=='cm_maybe_vel':
                unit = 'cm/s' if VELOCITY_RANGE_CM_S[0]<=val<=VELOCITY_RANGE_CM_S[1] else 'cm'
            if unit=='mm_trunc': unit='mm'
            if unit=='bpm_trunc':
                if 40<=val<=250: unit='bpm'
                else: continue
            measures.append((val,unit))
            seen.add((s,e))
    return measures

def parse_answer_measures(ans_json):
    """从v2标准答案JSON中提取测量值"""
    measurements = ans_json.get("measurements", {})
    all_measures = []
    for key, val in measurements.items():
        all_measures.extend(extract_all_measures(str(val)))
    return all_measures

def units_compatible(u1,u2):
    if u1==u2: return True
    if {u1,u2}<={'cm/s','cm','cm_maybe_vel'}: return True
    if {u1,u2}<={'mm/s','mm','mm_trunc'}: return True
    if 'bpm_trunc' in (u1,u2) and 'bpm' in (u1,u2): return True
    if 'ratio' in (u1,u2) and 'num' in (u1,u2): return True
    return False

def match_measures(asr_m, gold_m, tol=0.06):
    matched, used = 0, set()
    for gv, gu in gold_m:
        best_d, best_i = float('inf'), -1
        for i, (av, au) in enumerate(asr_m):
            if i in used: continue
            if not units_compatible(gu, au): continue
            d = 0 if gv==0 and av==0 else (abs(av-gv)/gv if gv!=0 else float('inf'))
            if d<best_d and d<tol: best_d, best_i = d, i
        if best_i>=0: matched+=1; used.add(best_i)
    p = matched/len(asr_m) if asr_m else 0
    r = matched/len(gold_m) if gold_m else 0
    f = 2*p*r/(p+r) if p+r>0 else 0
    return p, r, f

# =============== 3. 病灶检测 ===============
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

# =============== 4. 评估 ===============
def evaluate_single(row):
    """row = [id, text, template, tags, ans_json_str]"""
    asr_text = row[1]
    true_template = row[2]
    ans = json.loads(row[4])

    pred_t, _ = classify_template(asr_text)
    am = extract_all_measures(asr_text)
    gm = parse_answer_measures(ans)
    prec, rec, f1 = match_measures(am, gm)

    pred_ab = detect_abnormality(asr_text)
    true_ab = ans.get("abnormality", "无") != "无" and ans.get("abnormality", "无") != ""

    return {
        'template_match': pred_t == true_template,
        'template_pred': pred_t,
        'measurement_precision': prec, 'measurement_recall': rec,
        'measurement_f1': f1,
        'abnormality_match': pred_ab == true_ab,
        'tags': row[3].split(",") if row[3] else [],
    }

def evaluate_file(filepath, label=""):
    records = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 5:
                records.append(row)

    total = len(records)
    if total == 0: return None

    stats = {
        'file': label, 'total': total,
        'template_correct': 0, 'prec_sum': 0.0, 'rec_sum': 0.0,
        'abnorm_correct': 0,
        'pt': {t: {'n': 0, 't': 0, 'p': 0.0, 'r': 0.0, 'a': 0} for t in 'ABCDE'},
        'tag_stats': defaultdict(lambda: {'total': 0, 'templ_corr': 0, 'prec_sum': 0.0, 'rec_sum': 0.0, 'ab_corr': 0}),
    }

    for row in records:
        res = evaluate_single(row)
        t = row[2]

        stats['template_correct'] += 1 if res['template_match'] else 0
        stats['prec_sum'] += res['measurement_precision']
        stats['rec_sum'] += res['measurement_recall']
        stats['abnorm_correct'] += 1 if res['abnormality_match'] else 0

        pt = stats['pt'][t]
        pt['n'] += 1
        pt['t'] += 1 if res['template_match'] else 0
        pt['p'] += res['measurement_precision']
        pt['r'] += res['measurement_recall']
        pt['a'] += 1 if res['abnormality_match'] else 0

        for tag in res['tags']:
            tag = tag.strip()
            ts = stats['tag_stats'][tag]
            ts['total'] += 1
            ts['templ_corr'] += 1 if res['template_match'] else 0
            ts['prec_sum'] += res['measurement_precision']
            ts['rec_sum'] += res['measurement_recall']
            ts['ab_corr'] += 1 if res['abnormality_match'] else 0

    return stats

def print_report(stats):
    total = stats['total']
    print(f"\n{'='*70}")
    print(f"  {stats['file']} (N={total})")
    print(f"{'='*70}")
    tc = stats['template_correct'] / total * 100
    mp = stats['prec_sum'] / total * 100
    mr = stats['rec_sum'] / total * 100
    mf1 = 2 * mp * mr / (mp + mr) if mp + mr > 0 else 0
    aca = stats['abnorm_correct'] / total * 100
    print(f"  模板分类: {tc:.1f}%  |  测量F1: {mf1:.1f}%  |  病灶: {aca:.1f}%")

    print(f"\n  {'模板':<16} {'N':>5} {'分类%':>7} {'精确%':>7} {'召回%':>7} {'病灶%':>7}")
    for t in 'ABCDE':
        pt = stats['pt'][t]
        if pt['n'] > 0:
            print(f"  {TEMPLATE_NAMES[t]:<16} {pt['n']:>5} {pt['t']/pt['n']*100:>6.1f}% "
                  f"{pt['p']/pt['n']*100:>6.1f}% {pt['r']/pt['n']*100:>6.1f}% "
                  f"{pt['a']/pt['n']*100:>6.1f}%")

    # Tag breakdown
    print(f"\n  ┌─ 扰动标签维度准确率 ─────────────────────────────────────")
    print(f"  │ {'标签':<16} {'样本':>5} {'分类%':>7} {'测量F1%':>8} {'病灶%':>7}")
    for tag in sorted(stats['tag_stats'].keys()):
        ts = stats['tag_stats'][tag]
        n = ts['total']
        tacc = ts['templ_corr'] / n * 100 if n else 0
        tp = ts['prec_sum'] / n * 100 if n else 0
        tr = ts['rec_sum'] / n * 100 if n else 0
        tf1 = 2 * tp * tr / (tp + tr) if tp + tr > 0 else 0
        ta = ts['ab_corr'] / n * 100 if n else 0
        print(f"  │ {tag:<16} {n:>5} {tacc:>6.1f}% {tf1:>7.1f}% {ta:>6.1f}%")
    print(f"  └──────────────────────────────────────────────────────────")

    return tc, mf1, aca


def main():
    print("=" * 70)
    print("  超声ASR评测 v13 (v2数据集17500条)")
    print("=" * 70)

    if not os.path.exists(DATA_FILE):
        print(f"ERROR: 数据文件不存在: {DATA_FILE}")
        sys.exit(1)

    stats = evaluate_file(DATA_FILE, "v2数据集17500条")
    if stats:
        tca, mf1, aca = print_report(stats)

    print(f"\n  结论: 模板{tca:.1f}% 测量F1={mf1:.1f}% 病灶={aca:.1f}%")


if __name__ == '__main__':
    main()
