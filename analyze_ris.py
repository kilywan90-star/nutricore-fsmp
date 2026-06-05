#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RIS ultrasound report analysis - v4 final.
Fixes: cm-based measurements with context classification, broader abnormal detection.
"""
import csv, re, json
from collections import Counter, defaultdict

CSV_PATH = r"C:\Users\Administrator\Desktop\HIS数据\ris_report.csv"
OUTPUT_PATH = r"E:\claude\ris_analysis_output.json"

def sanitize(text):
    text = re.sub(r'[-]', ' ', text)
    text = text.replace('　', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

# Load
reports = []
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) < 5 or not row[4].strip(): continue
        reports.append({
            'tjxh': row[0], 'hzxm': row[1],
            'ris_xmmc': row[2].strip() if len(row) > 2 else '',
            'jcsj': sanitize(row[4]),
        })

def classify_exam(m):
    if 'CT' in m or 'HRCT' in m: return 'CT检查'
    if '腹部' in m: return '腹部彩超'
    if '前列腺' in m or '膀胱' in m: return '前列腺膀胱彩超'
    if '甲状腺' in m: return '甲状腺彩超'
    if '妇科' in m or '阴道' in m: return '妇科彩超'
    if '乳腺' in m: return '乳腺彩超'
    if '心脏' in m: return '心脏彩超'
    if '脑血管' in m: return '脑血管彩超'
    if '颈部' in m: return '颈部动脉彩超'
    if '体表包块' in m: return '体表包块彩超'
    return '其他'

for r in reports:
    r['category'] = classify_exam(r['ris_xmmc'])

cat_counts = Counter(r['category'] for r in reports)
us = [r for r in reports if 'CT' not in r['category'] and r['category'] != '其他']
all_text = '\n'.join(r['jcsj'] for r in us)

output = {
    "meta": {
        "total_reports": len(reports),
        "ultrasound_reports": len(us),
        "exam_type_distribution": dict(cat_counts.most_common()),
        "analysis_date": "2026-06-04"
    },
    "rules": []
}

# ============================================================
# 1. NORMAL VALUE PATTERNS
# ============================================================
normal_patterns = {
    # 肝脏
    '肝脏-大小形态正常': r'肝脏大小形态正常',
    '肝脏-包膜光滑': r'肝(?:脏)?包膜光滑',
    '肝脏-形态规整': r'形态规整',
    '肝脏-边缘锐利': r'边缘锐利',
    '肝脏-实质回声均匀': r'肝(?:实质)?回声(?:均匀|正常|尚均匀)',
    '肝脏-血管走行正常': r'肝内血管走行正常',
    '肝脏-纹理清晰': r'纹理清晰',
    '肝脏-肝静脉门静脉无扩张': r'肝静脉[、，]?门静脉无扩张|肝静脉无扩张',
    '肝脏-门静脉不扩张': r'门静脉(?:不|未见)扩张',
    # 胆囊
    '胆囊-正常大小': r'胆囊(?:大小形态)*正常大小|胆囊大小形态正常|胆囊正常大小',
    '胆囊-囊壁光滑': r'囊壁光滑',
    '胆囊-囊壁不厚': r'囊壁不厚',
    '胆囊-内清晰': r'囊内(?:无回声|液性暗区)?清晰',
    '胆囊-肝内外胆管不扩张': r'肝[内]*[外]*胆管(?:不|无|未见)扩张',
    '胆囊-胆总管不扩张': r'胆总管(?:不|未)扩张',
    # 脾脏
    '脾脏-大小形态正常': r'脾(?:脏)?(?:位置及)?大小形态正常',
    '脾脏-包膜光滑': r'脾(?:脏)?包膜(?:\S)*光滑',
    '脾脏-实质回声均匀': r'脾(?:实质)?回声均匀',
    '脾脏-脾静脉不扩张': r'脾静脉不扩张',
    # 胰腺
    '胰腺-大小正常': r'胰腺大小(?:形态)?正常',
    '胰腺-回声均匀': r'胰(?:腺|实质)?回声均匀',
    '胰腺-胰管不扩张': r'胰管不扩张',
    '胰腺-未见占位': r'胰腺(?:周围)?未见(?:明显)?占位',
    # 肾脏
    '肾脏-双肾大小形态正常': r'双肾大小(?:形态)?正常',
    '肾脏-肾实质回声正常': r'肾(?:实质)?回声(?:均匀|正常)',
    '肾脏-肾盂无扩张': r'肾(?:盂|窦)(?:无|未)(?:分离|扩张)',
    '肾脏-集合系统未见分离': r'集合系统(?:无|未)(?:见)*(?:分离|扩张)',
    '肾脏-输尿管不扩张': r'输尿管(?:不|无|未)扩张',
    # 前列腺
    '前列腺-大小形态正常': r'前列腺大小(?:形态)?正常',
    '前列腺-包膜完整': r'前列腺包膜(?:\S)*完整',
    '前列腺-回声均匀': r'前列腺(?:实质)?回声(?:均匀|尚均匀)',
    '前列腺-残余尿量阴性': r'残余尿(?:量)?(?:阴性|未见|无)',
    # 膀胱
    '膀胱-壁光滑': r'膀胱壁光滑',
    '膀胱-未见异常': r'膀胱(?:内)?未见(?:明显)?异常',
    # 甲状腺
    '甲状腺-大小形态正常': r'甲状腺大小(?:形态)?正常',
    '甲状腺-回声均匀': r'甲状腺(?:实质)?回声均匀',
    '甲状腺-峡部不厚': r'峡部不厚',
    '甲状腺-未见结节': r'甲状腺(?:内)?未见(?:明显)?结节',
    '甲状腺-未见占位': r'甲状腺(?:内)?未见(?:明显)?占位',
    # 乳腺
    '乳腺-腺体回声均匀': r'乳腺(?:腺体)?回声(?:均匀|正常)',
    '乳腺-导管不扩张': r'乳腺导管(?:不|无|未)扩张',
    '乳腺-未见占位': r'乳腺(?:内)?未见(?:明显)?占位',
    '乳腺-腋窝淋巴结正常': r'腋(?:窝)?淋巴结(?:未见|不肿大|正常)',
    # 心脏
    '心脏-大小正常': r'心脏(?:各房室)?大小(?:形态)?正常',
    '心脏-室壁运动正常': r'室壁(?:运动|厚度)(?:正常|协调|尚可)',
    '心脏-瓣膜未见异常': r'(?:二尖瓣|三尖瓣|主动脉瓣|肺动脉瓣)(?:形态|活动)?(?:未见(?:明显)?异常|正常|良好|尚可)',
    '心脏-心包未见积液': r'心包(?:腔)?(?:内)?(?:未见|无)(?:明显)?(?:液性暗区|积液|液性分离)',
    '心脏-心功能正常': r'(?:左)?心(?:室)?(?:收缩|舒张)?功能(?:正常|未见异常|尚可|大致正常)',
    # 血管
    '血管-内径正常': r'(?:血管|颈总|颈内)(?:动脉)?内径(?:正常|未见异常|在正常范围)',
    '血管-壁光滑': r'(?:血管|管)壁光滑',
    '血管-未见斑块': r'未见(?:明显)?(?:粥样)?斑块',
    '血管-未见狭窄': r'(?:血管|管腔)?未见(?:明显)?狭窄',
    # 子宫附件
    '子宫-大小形态正常': r'子宫(?:大小)?(?:形态)?正常',
    '子宫-回声均匀': r'子宫(?:肌层|实质)?回声均匀',
    '子宫-内膜正常': r'(?:子宫)?内膜(?:线)?(?:清晰|正常|无异常)',
    '子宫-双侧附件未见异常': r'(?:双|两|单|右)?(?:侧)?附件(?:区)?(?:未见|无)(?:明显)?异常',
    '子宫-卵巢大小正常': r'(?:双|左|右|单)?(?:侧)?卵巢大小(?:形态)?正常',
    # 通用
    '通用-未见明显异常': r'未见明显异常',
    '通用-未见占位性病变': r'未见(?:明显)?占位性病变',
    '通用-CDFI未见异常血流': r'CDFI(?:显示|检查|:)?(?:未见|无)异常血流(?:信号)?',
    '通用-未见异常回声': r'未见(?:明显)?异常回声',
    '通用-余未见异常': r'余(?:[—\-])*(?:未见|无)(?:明显)?异常',
}

for name, pattern in normal_patterns.items():
    count = 0
    examples = []
    for r in us:
        m = re.search(pattern, r['jcsj'])
        if m:
            count += 1
            if len(examples) < 3:
                start = max(0, m.start()-8)
                end = min(len(r['jcsj']), m.end()+25)
                examples.append(r['jcsj'][start:end].replace('\n',' ').strip())
    if count >= 10:
        ratio = round(count/len(us), 4)
        output["rules"].append({
            "rule_type": "normal_range",
            "category": "正常值",
            "pattern": name,
            "frequency": count,
            "ratio": ratio,
            "confidence": "high" if count > 200 else ("medium" if count > 50 else "low"),
            "examples": examples[:3],
            "suggestion": "质控规则：当报告中缺失此描述或出现矛盾措辞时标记为待复核"
        })

# ============================================================
# 2. ABNORMAL PATTERNS - keyword-based for reliability
# ============================================================
abnormal_kw_groups = {
    # Liver
    '脂肪肝': ['脂肪肝'],
    '肝囊肿': ['肝囊肿', '肝脏囊肿', '肝多发囊肿'],
    '肝血管瘤': ['肝血管瘤', '肝脏血管瘤'],
    '肝实质回声异常': ['回声增强', '回声增粗', '回声增密'],
    '肝硬化': ['肝硬化'],
    '肝内钙化灶': ['钙化灶', '钙化斑'],
    '肝内胆管结石': ['肝内胆管结石'],
    '肝大': ['肝增大', '肝脏增大', '肝肿大', '肝脏肿大'],
    # Gallbladder
    '胆囊息肉': ['胆囊息肉', '息肉样病变', '息肉样'],
    '胆囊结石': ['结石'],
    '胆囊壁毛糙': ['毛糙', '不光滑', '粗糙'],
    '胆囊壁增厚': ['增厚'],
    '胆囊胆固醇结晶': ['胆固醇结晶'],
    # Spleen
    '脾大': ['脾增大', '脾脏增大', '脾肿大', '脾脏肿大', '脾大'],
    '副脾': ['副脾'],
    # Pancreas
    '胰腺回声异常': ['胰腺回声增强', '胰腺回声增粗', '胰腺回声不均'],
    # Kidney
    '肾囊肿': ['肾囊肿', '肾脏囊肿'],
    '肾结石': ['肾结石', '肾脏结石'],
    '肾积水': ['肾积水', '肾盂积水', '肾盂积液', '肾盂分离'],
    '肾回声异常': ['肾实质回声增强', '肾皮质回声增强'],
    '肾萎缩': ['肾萎缩', '肾脏萎缩'],
    # Prostate
    '前列腺增生': ['前列腺增生', '前列腺增大'],
    '前列腺钙化': ['钙化'],
    '前列腺囊肿': ['前列腺囊肿'],
    '前列腺回声不均': ['前列腺回声不均', '前列腺回声不均匀'],
    # Bladder
    '膀胱壁增厚': ['膀胱壁增厚', '膀胱壁毛糙'],
    '膀胱残余尿增多': ['残余尿阳性', '残余尿量增多', '残余尿量多'],
    # Thyroid
    '甲状腺结节': ['甲状腺结节', '甲状腺多发结节', '结节'],
    '甲状腺囊肿': ['甲状腺囊肿'],
    '甲状腺回声不均': ['甲状腺回声不均', '甲状腺回声不均匀'],
    # Breast
    '乳腺增生': ['增生'],
    '乳腺结节': ['乳腺结节'],
    '乳腺囊肿': ['乳腺囊肿'],
    # Gynecology
    '子宫肌瘤': ['子宫肌瘤'],
    '子宫腺肌症': ['子宫腺肌症', '子宫腺肌病'],
    '卵巢囊肿': ['卵巢囊肿'],
    '宫颈纳囊': ['宫颈纳囊', '宫颈囊肿', '纳氏囊肿'],
    '盆腔积液': ['盆腔积液'],
    '子宫内膜增厚': ['内膜增厚', '子宫内膜增厚'],
    '子宫内膜息肉': ['内膜息肉', '子宫内膜息肉'],
    # Heart
    '心脏瓣膜反流': ['关闭不全', '反流', '返流'],
    '心脏扩大': ['增大'],
    '心包积液': ['心包积液'],
    # Vessels
    '斑块': ['斑块', '粥样硬化'],
    '血管狭窄': ['狭窄'],
    # General
    '占位性病变': ['占位'],
    '淋巴结肿大': ['淋巴结肿大', '淋巴结增大'],
    '囊肿(泛指)': ['囊肿'],
}

for name, keywords in abnormal_kw_groups.items():
    count = 0
    examples = []
    for r in us:
        found = False
        for kw in keywords:
            if kw in r['jcsj']:
                found = True
                if len(examples) < 3:
                    idx = r['jcsj'].find(kw)
                    start = max(0, idx-10)
                    end = min(len(r['jcsj']), idx+len(kw)+30)
                    examples.append(r['jcsj'][start:end].replace('\n',' ').strip())
                break
        if found:
            count += 1
    if count >= 5:
        ratio = round(count/len(us), 4)
        output["rules"].append({
            "rule_type": "abnormal_pattern",
            "category": "异常",
            "pattern": name,
            "frequency": count,
            "ratio": ratio,
            "confidence": "high" if count > 100 else ("medium" if count > 20 else "low"),
            "examples": examples[:3],
            "suggestion": f"ASR识别到'{name}'类描述时触发异常标记，提示医生复核"
        })

# ============================================================
# 3. MEASUREMENT RANGES (cm-based, context-classified)
# ============================================================
# Broadly capture ALL AxB cm patterns, then classify by preceding context
all_dim_values = []  # flat list for overall stats
dim_by_context = defaultdict(list)  # classified by preceding chars

for r in us:
    text = r['jcsj']
    for m in re.finditer(r'(\d+\.?\d*)\s*[xX×\*]\s*(\d+\.?\d*)\s*(?:cm|CM|mm|MM)', text):
        v1 = float(m.group(1))
        v2 = float(m.group(2))
        unit = m.group(0)[-2:].lower()
        # Convert mm to cm for consistency
        if unit == 'mm':
            v1, v2 = v1/10, v2/10

        if 0.01 < v1 < 30 and 0.01 < v2 < 30:
            val1, val2 = round(v1, 3), round(v2, 3)
            # Get context (up to 10 chars before)
            ctx_start = max(0, m.start()-12)
            ctx = text[ctx_start:m.start()].strip()
            # Keep last 2-4 meaningful chars
            ctx_short = ctx[-6:] if len(ctx) > 6 else ctx

            all_dim_values.extend([val1, val2])
            dim_by_context['_all_'].append((val1, val2))
            dim_by_context[ctx_short].append((val1, val2))

# Classify contexts into measurement types
context_map = {
    '结节大小': ['结节', '团块', '肿物', '占位', '包块', '回声团', '低回声', '高回声', '等回声', '混合回声', '无回声', '囊实性'],
    '囊肿大小': ['囊肿', '囊性'],
    '结石大小': ['结石', '强回声团'],
    '胆囊病变大小': ['胆囊', '囊壁', '胆'],
    '肾脏大小': ['肾'],
    '子宫大小': ['子宫'],
    '卵巢大小': ['卵巢'],
    '前列腺大小': ['前列腺'],
    '内膜厚度': ['内膜'],
    '息肉大小': ['息肉'],
    '肌瘤大小': ['肌瘤'],
    '淋巴结大小': ['淋巴结', '淋巴'],
    '甲状腺大小': ['甲状'],
}

measurement_rules = {}
for label, triggers in context_map.items():
    vals = []
    for ctx_key, pairs in dim_by_context.items():
        if ctx_key == '_all_': continue
        if any(t in ctx_key for t in triggers):
            for v1, v2 in pairs:
                vals.extend([v1, v2])
    if len(vals) >= 30:
        s = sorted(vals)
        n = len(s)
        measurement_rules[label] = {
            'n': n, 'values': s,
            'stats': {
                'n': n, 'min': round(s[0], 3),
                'p25': round(s[n//4], 3), 'p50': round(s[n//2], 3),
                'p75': round(s[3*n//4], 3), 'p95': round(s[int(0.95*n)], 3),
                'max': round(s[-1], 3), 'mean': round(sum(s)/n, 3),
                'std': round((sum((x-sum(s)/n)**2 for x in s)/n)**0.5, 3),
            }
        }

# Also add overall dimension stats
if len(all_dim_values) >= 100:
    s = sorted(all_dim_values)
    n = len(s)
    measurement_rules['所有测量值汇总'] = {
        'n': n, 'values': s,
        'stats': {
            'n': n, 'min': round(s[0], 3),
            'p25': round(s[n//4], 3), 'p50': round(s[n//2], 3),
            'p75': round(s[3*n//4], 3), 'p95': round(s[int(0.95*n)], 3),
            'max': round(s[-1], 3), 'mean': round(sum(s)/n, 3),
            'std': round((sum((x-sum(s)/n)**2 for x in s)/n)**0.5, 3),
        }
    }

for label, info in measurement_rules.items():
    s = info['stats']
    output["rules"].append({
        "rule_type": "measurement_range",
        "category": "正常值",
        "pattern": f"{label}(cm)",
        "frequency": s['n'],
        "ratio": round(s['n']/len(us), 4),
        "confidence": "high" if s['n'] > 100 else "medium",
        "stats": s,
        "examples": [],
        "suggestion": f"参考范围: P25={s['p25']}-P75={s['p75']}cm, P50={s['p50']}cm, P95={s['p95']}cm。超出P95的值需复核"
    })

# ============================================================
# 4. SYNONYM & ANTONYM PAIRS
# ============================================================
normal_phrases_list = [
    '未见明显异常', '未见异常', '未见异常回声', '未见异常声像', '未见异常信号',
    '未见异常表现', '未见异常改变', '未见异常发现', '形态正常', '大小正常',
    '大小形态正常', '结构正常', '实质回声均匀', '回声均匀', '回声正常',
    '未见扩张', '未见明显扩张', '未见占位', '未见占位性病变', '未见肿物',
    '未见肿块', '未探及异常', '无异常', '无明显异常', '正常范围', '阴性',
    '正常声像图', '未见明显异常回声', '未见异常血流信号', '未见异常血流',
    '未见明确占位', '余未见异常',
]
synonym_inv = {}
for phrase in normal_phrases_list:
    cnt = all_text.count(phrase)
    if cnt >= 3:
        synonym_inv[phrase] = cnt

output["rules"].append({
    "rule_type": "synonym_inventory",
    "category": "模板",
    "pattern": "正常描述同义词集合",
    "frequency": sum(synonym_inv.values()),
    "confidence": "high",
    "examples": [f"'{p}': {c}次" for p, c in sorted(synonym_inv.items(), key=lambda x: -x[1])],
    "suggestion": "所有'未见异常'同义表述覆盖大多数正常报告，ASR/Rules引擎应归一化为'正常'标签"
})

synonym_pairs = [
    ('回声均匀', '实质回声均匀'), ('大小正常', '大小形态正常'),
    ('未见异常', '未见明显异常'), ('未见扩张', '未见明显扩张'),
    ('未见积液', '未见明显积液'), ('未见占位', '未见占位性病变'),
    ('囊壁光滑', '囊壁光滑完整'), ('包膜光滑', '包膜完整光滑'),
    ('回声尚均匀', '回声均匀'), ('未见明显异常回声', '未见异常回声'),
]
for a, b in synonym_pairs:
    cnt_a = all_text.count(a)
    cnt_b = all_text.count(b)
    if cnt_a >= 5 and cnt_b >= 5:
        output["rules"].append({
            "rule_type": "synonym_pair",
            "category": "模板",
            "pattern": f"'{a}' <=> '{b}'",
            "frequency": cnt_a + cnt_b,
            "ratio": round((cnt_a+cnt_b)/len(us), 4),
            "confidence": "high" if cnt_a > 50 else "medium",
            "examples": [f"'{a}': {cnt_a}次", f"'{b}': {cnt_b}次"],
            "suggestion": "同义对，语义等同，规则引擎应归一化处理"
        })

antonym_pairs = {
    '回声均匀': ['回声不均匀', '回声增粗', '回声增强', '回声减低', '回声欠均匀'],
    '形态规整': ['形态不规整', '形态失常'],
    '边缘锐利': ['边缘变钝', '边缘圆钝'],
    '包膜光滑': ['包膜不光滑', '包膜毛糙'],
    '未见扩张': ['扩张', '明显扩张'],
    '未见积液': ['积液', '可见积液', '少量积液'],
    '未见占位': ['占位性病变', '占位'],
    '未见异常': ['异常回声', '异常信号'],
    '未见狭窄': ['狭窄', '明显狭窄'],
    '壁光滑': ['壁毛糙', '壁粗糙', '壁不光滑'],
    '回声正常': ['回声增强', '回声减低', '回声不均'],
}
for normal_term, abnormal_terms in antonym_pairs.items():
    normal_count = all_text.count(normal_term)
    for abn in abnormal_terms:
        abnormal_count = all_text.count(abn)
        if normal_count >= 10 and abnormal_count >= 5:
            output["rules"].append({
                "rule_type": "antonym_pair",
                "category": "异常",
                "pattern": f"'{normal_term}' vs '{abn}'",
                "frequency": normal_count + abnormal_count,
                "ratio": round((normal_count+abnormal_count)/len(us), 4),
                "confidence": "high" if normal_count > 50 else "medium",
                "examples": [f"正常: '{normal_term}' ({normal_count}次)", f"异常: '{abn}' ({abnormal_count}次)"],
                "suggestion": f"对立措辞对。ASR易将'{abn}'误识别为'{normal_term}'造成假阴性"
            })

# ============================================================
# 5. ASR ERROR-PRONE MEDICAL TERMS
# ============================================================
char_count = Counter()
for c in all_text:
    if '一' <= c <= '鿿':
        char_count[c] += 1

top_chars = char_count.most_common(80)
rare_chars = [(c, cnt) for c, cnt in char_count.items() if cnt <= 5]
rare_chars.sort(key=lambda x: x[1])

output["rules"].append({
    "rule_type": "asr_char_freq",
    "category": "ASR",
    "pattern": "医学报告高频汉字(TOP40)",
    "frequency": len(char_count),
    "confidence": "high",
    "examples": [f"'{c}': {cnt}次" for c, cnt in top_chars[:40]],
    "suggestion": "高频字符应优先优化声学模型；低频字符加入热词表。基于此分布可估算ASR字符级WER下限"
})

output["rules"].append({
    "rule_type": "asr_rare_char",
    "category": "ASR",
    "pattern": "罕见字符识别风险(<=5次出现)",
    "frequency": len(rare_chars),
    "confidence": "medium",
    "examples": [f"'{c}' (U+{ord(c):04X}): {cnt}次" for c, cnt in rare_chars[:30]],
    "suggestion": f"共{len(rare_chars)}个罕见字在通用ASR训练不足。核心高风险字: {','.join(c for c,_ in rare_chars[:15])}。建议加入自定义热词表"
})

# Polyphone
polyphone_map = {
    '间': 'jian1/jian4', '重': 'zhong4/chong2', '强': 'qiang2/jiang4',
    '血': 'xue4/xie3', '量': 'liang4/liang2', '脏': 'zang4/zang1',
    '藏': 'cang2/zang4', '调': 'tiao2/diao4', '长': 'chang2/zhang3',
    '数': 'shu4/shu3', '便': 'bian4/pian2', '度': 'du4/duo2',
}
poly_entries = []
for char, readings in polyphone_map.items():
    cnt = char_count.get(char, 0)
    if cnt > 0:
        contexts = set()
        for r in us:
            for m in re.finditer(re.escape(char), r['jcsj']):
                s = max(0, m.start()-2)
                e = min(len(r['jcsj']), m.end()+3)
                ctx = r['jcsj'][s:e].replace('\n',' ').strip()
                if len(ctx) >= 3:
                    contexts.add(ctx)
        poly_entries.append({"char": char, "readings": readings, "count": cnt,
            "contexts": sorted(list(contexts))[:6]})

output["rules"].append({
    "rule_type": "asr_polyphone",
    "category": "ASR",
    "pattern": "多音字歧义风险",
    "frequency": sum(e['count'] for e in poly_entries),
    "confidence": "medium",
    "examples": [f"'{e['char']}'({e['readings']}): {e['count']}次, ctx={e['contexts'][:3]}" for e in poly_entries],
    "suggestion": "多音字在医学语境有约定读音。'血'(xue4)在'血管/血流'中统一读xue4。通过N-gram语言模型权重约束"
})

# Long terms
long_terms_re = re.findall(r'[一-鿿]{4,18}', all_text)
long_term_freq = Counter(long_terms_re)
common_long = [(t, c) for t, c in long_term_freq.most_common(80) if c >= 10]

output["rules"].append({
    "rule_type": "asr_long_term",
    "category": "ASR",
    "pattern": "长医学术语ASR热词表(>=10次)",
    "frequency": len(common_long),
    "confidence": "high",
    "examples": [f"'{t}' ({c}次)" for t, c in common_long[:50]],
    "suggestion": "4字以上高频长术语加入ASR热词表，降低碎词率10-30%。后处理可用此做拼写纠错词典"
})

# Homophone risks
homophone_risks = [
    ("炎/延", "yan2", "肺炎 vs 延缓"),
    ("瘤/流", "liu2", "血管瘤 vs 血流"),
    ("腺/线", "xian4", "甲状腺 vs 甲状线"),
    ("胰/移", "yi2", "胰腺 vs 移位"),
    ("脾/皮", "pi2", "脾脏 vs 皮肤"),
    ("囊/囔", "nang2", "胆囊 vs 胆囔"),
    ("灶/造", "zao4", "钙化灶 vs 钙化造"),
    ("窦/豆", "dou4", "肾窦 vs 肾豆"),
    ("膈/隔", "ge2", "膈肌 vs 隔肌"),
    ("盂/鱼", "yu2", "肾盂 vs 肾鱼"),
    ("髂/恰", "qia4", "髂动脉 vs 恰动脉"),
    ("骶/底", "di3", "骶骨 vs 底骨"),
    ("泌/密", "mi4", "泌尿 vs 密尿"),
    ("棘/急", "ji2", "棘突 vs 急突"),
    ("肋/类", "lei4", "肋骨 vs 类骨"),
]
output["rules"].append({
    "rule_type": "asr_homophone",
    "category": "ASR",
    "pattern": "同音字医学混淆对",
    "frequency": 0,
    "confidence": "medium",
    "examples": [f"{pair[0]}({pair[1]}): {pair[2]}" for pair in homophone_risks],
    "suggestion": "同音字是ASR主要错误源。解决方案: 1)医学N-gram LM训练 2)领域词典权重10x 3)后处理规则纠错(如'胆囔'→'胆囊')"
})

# ============================================================
# 6. REPORT STRUCTURE TEMPLATES
# ============================================================
for cat in ['腹部彩超', '妇科彩超', '甲状腺彩超', '乳腺彩超', '心脏彩超', '前列腺膀胱彩超', '脑血管彩超', '颈部动脉彩超']:
    cat_r = [r for r in us if r['category'] == cat]
    if len(cat_r) < 10: continue

    # Section headers (patterns like "肝 脏：" or "胆 囊：")
    section_counter = Counter()
    for r in cat_r:
        # Match "XX XX：" organ-header patterns after PUA sanitization leaves spaces
        headers1 = re.findall(r'(?:^|\n)\s*(\S{2,3}\s+\S{1,2})\s*[：:]', r['jcsj'])
        # Also match single-word headers
        headers2 = re.findall(r'(?:^|\n)\s*([一-鿿]{2,6}(?:脏|器|官|腺|脉|区|囊|管|叶|壁|室|瓣|骨|房|尖|膜))[\s：:]*', r['jcsj'])
        for h in headers1 + headers2:
            h_clean = re.sub(r'\s+', '', h)
            if h_clean:
                section_counter[h_clean] += 1
    top_secs = section_counter.most_common(8)

    lengths = sorted([len(r['jcsj']) for r in cat_r])
    plens = sorted([len([l for l in r['jcsj'].split('\n') if l.strip()]) for r in cat_r])

    # Representative sample
    sample = ""
    for r in cat_r:
        if 150 < len(r['jcsj']) < 500:
            sample = r['jcsj'][:450]
            break
    if not sample:
        for r in cat_r:
            if len(r['jcsj']) > 80:
                sample = r['jcsj'][:450]
                break

    output["rules"].append({
        "rule_type": "report_structure",
        "category": "模板",
        "pattern": f"{cat}报告结构模板",
        "frequency": len(cat_r),
        "ratio": round(len(cat_r)/len(us), 4),
        "confidence": "high",
        "examples": [
            f"报告数: {len(cat_r)}",
            f"报告长度: P50={lengths[len(lengths)//2]}字, 均值={sum(lengths)//len(lengths)}字",
            f"段落数: P50={plens[len(plens)//2]}段, 均值={sum(plens)//len(plens)}段",
            f"标准段落标题: {'; '.join(f'{h}({c}次/{c/len(cat_r):.0%})' for h,c in top_secs)}",
            f"典型报告: {sample.replace(chr(10),' | ')[:300]}",
        ],
        "suggestion": f"{cat}标准结构。用途: ASR后处理段落分割、缺失段落检测、结构化字段抽取"
    })

# Final summary
output["meta"]["rules_summary"] = {
    "total_rules": len(output["rules"]),
    "by_category": dict(Counter(r["category"] for r in output["rules"])),
    "by_rule_type": dict(Counter(r["rule_type"] for r in output["rules"])),
    "by_confidence": dict(Counter(r["confidence"] for r in output["rules"])),
}

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# Write a human-readable summary
with open(r'E:\claude\ris_analysis_summary.txt', 'w', encoding='utf-8') as f:
    f.write(f"RIS超声报告分析摘要 (2026-06-04)\n")
    f.write(f"{'='*60}\n")
    f.write(f"总报告数: {len(reports)}\n")
    f.write(f"超声报告数: {len(us)}\n")
    f.write(f"总规则数: {len(output['rules'])}\n\n")

    f.write(f"一、检查类型分布\n")
    for exam, cnt in cat_counts.most_common():
        f.write(f"  {exam}: {cnt} ({cnt/len(reports):.1%})\n")

    f.write(f"\n二、正常值描述规则 (Top 15)\n")
    nr = [r for r in output['rules'] if r['rule_type']=='normal_range']
    for r in sorted(nr, key=lambda x: -x['frequency'])[:15]:
        f.write(f"  [{r['frequency']:5d}  {r['ratio']:.0%}] {r['pattern']}  conf={r['confidence']}\n")

    f.write(f"\n三、异常发现模式\n")
    ar = [r for r in output['rules'] if r['rule_type']=='abnormal_pattern']
    for r in sorted(ar, key=lambda x: -x['frequency']):
        f.write(f"  [{r['frequency']:5d}  {r['ratio']:.1%}] {r['pattern']}  conf={r['confidence']}\n")
        if r['examples']:
            f.write(f"    e.g. {r['examples'][0]}\n")

    f.write(f"\n四、测量数值范围\n")
    mr = [r for r in output['rules'] if r['rule_type']=='measurement_range']
    for r in mr:
        s = r['stats']
        f.write(f"  {r['pattern']}: n={s['n']} P50={s['p50']} P75={s['p75']} P95={s['p95']} mean={s['mean']} std={s['std']}\n")

    f.write(f"\n五、报告结构模板\n")
    rs = [r for r in output['rules'] if r['rule_type']=='report_structure']
    for r in rs:
        f.write(f"  [{r['pattern']}]\n")
        for e in r['examples']:
            f.write(f"    {e}\n")
        f.write(f"\n")

    f.write(f"\n注: 完整JSON格式结果见 ris_analysis_output.json\n")

print("Done")
