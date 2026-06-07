"""
构建超声模板规则库
输出: 结构化的JSON规则文件，供语音录入系统使用
"""
import csv, re, json, os
from collections import Counter, defaultdict, OrderedDict

OUT = r'C:\Users\Administrator\Desktop\超声规则库_rulebase.json'
TEMPLATE_CSV = r'C:\Users\Administrator\Desktop\超声结构化报告\模板表.csv'
MATCH_RESULT = r'C:\Users\Administrator\Desktop\全字段40万-matching_result_clean.csv'

print('=== 1. 读取模板表 ===')
templates = OrderedDict()
current_rid = None

with open(TEMPLATE_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = (row.get('RID') or '').strip()
        discname = (row.get('DISCNAME') or '').strip()
        if rid and discname:
            current_rid = rid
            t = OrderedDict()
            for k, v in row.items():
                t[k] = (v or '').strip()
            t['_info1_parts'] = []
            templates[current_rid] = t
        if current_rid and current_rid in templates:
            info1 = (row.get('INFO1') or '').strip()
            if info1:
                templates[current_rid]['_info1_parts'].append(info1)
            info2 = (row.get('INFO2') or '').strip()
            if info2:
                templates[current_rid]['INFO2'] = info2

print(f'  模板数: {len(templates)}')

# ========== 构建规则库 ==========
rulebase = OrderedDict()

# --- 1. 部位关键词映射 ---
rulebase['site_keywords'] = {
    "肝脏": ["肝", "门静脉", "肝脏", "肝内", "胆囊", "胆总管", "脾厚", "胰头", "胰体"],
    "胆囊": ["胆囊", "胆总管", "胆泥", "胆囊壁"],
    "脾": ["脾厚", "脾内", "脾大", "脾"],
    "双肾": ["肾", "输尿管", "肾上腺", "肾集合", "肾实质", "肾盂"],
    "心脏": ["心脏", "心房", "心室", "瓣膜", "室间隔", "主动脉", "肺动脉",
              "二尖瓣", "三尖瓣", "EF", "FS", "CDFI", "心功能", "TDI", "左室", "右房"],
    "甲状腺": ["甲状腺", "甲状旁腺", "颈部淋巴结", "甲状腺双侧叶", "峡部"],
    "乳腺": ["乳腺", "乳", "腋窝", "BI-RADS", "腺体", "豹纹征"],
    "颈动脉": ["颈动脉", "颈总", "颈内", "颈外", "椎动脉", "锁骨下动脉", "斑块", "内中膜"],
    "前列腺": ["前列腺", "膀胱", "精囊"],
    "子宫附件": ["子宫", "附件", "卵巢", "宫腔", "宫颈", "内膜", "盆腔"],
    "睾丸": ["睾丸", "附睾", "精索", "阴囊", "鞘膜"],
    "四肢血管": ["肱", "股", "腘", "动脉", "静脉", "血管"],
    "胎儿": ["胎儿", "胎", "羊水", "胎盘", "双顶径", "头围", "腹围", "股骨"],
    "腹主动脉": ["腹主动脉"],
    "ABUS": ["ABUS", "乳腺容积"],
}

# --- 2. 变量提取规则 ---
rulebase['variable_rules'] = {
    "尺寸_长x宽mm": {
        "pattern": r"(?:约)?(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*mm",
        "description": "二维尺寸，如 3x2mm",
        "examples": ["大小约3x2mm", "3×2mm", "大小约 5x4mm"]
    },
    "尺寸_三维mm": {
        "pattern": r"(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*mm",
        "description": "三维尺寸，如 10x8x6mm",
        "examples": ["10x8x6mm", "5×4×3mm"]
    },
    "尺寸_mm": {
        "pattern": r"(\d+\.?\d*)\s*mm",
        "description": "单值尺寸，如 45mm",
        "examples": ["厚约45mm", "内径8mm", "宽度约5mm"]
    },
    "尺寸_cm": {
        "pattern": r"(\d+\.?\d*)\s*cm",
        "description": "厘米尺寸，如 1.5cm",
        "examples": ["1.5cm", "长约3cm"]
    },
    "百分比": {
        "pattern": r"(EF|FS)?\s*[：:]?\s*(\d+\.?\d*)\s*%",
        "description": "百分比值，如 EF:72%",
        "examples": ["EF:72%", "FS:41%", "72%"]
    },
    "血流速度": {
        "pattern": r"(Vmax|流速|速度)?\s*[：:]?\s*(\d+\.?\d*)\s*(cm/s|m/s)",
        "description": "血流速度，如 Vmax:120cm/s",
        "examples": ["Vmax:120cm/s", "流速 80cm/s"]
    },
    "程度描述": {
        "pattern": r"(轻|中|重)(度)?",
        "description": "程度：轻/中/重度",
        "examples": ["轻度返流", "中度狭窄", "重度"],
        "values": {"轻": "轻度", "中": "中度", "重": "重度"}
    },
    "左右侧": {
        "pattern": r"(左|右|双侧)(侧)?",
        "description": "左右侧位置",
        "examples": ["左侧", "右侧", "双侧"],
        "values": {"左": "左", "右": "右", "双侧": "双侧"}
    },
    "解剖位置": {
        "pattern": r"(前壁|后壁|侧壁|前叶|后叶|上段|下段|上极|下极|中部|上部|下部|远端|近端)",
        "description": "解剖方位描述",
        "examples": ["前壁", "后叶", "上段"]
    },
    "钟点位置": {
        "pattern": r"(\d+)\s*(点|点钟)",
        "description": "乳腺钟点位，如 2点",
        "examples": ["2点", "10点钟"]
    },
    "分级分类": {
        "pattern": r"(BI-RADS|TI-RADS)\s*(\d+)\s*(级|类)?",
        "description": "分级标准，如 BI-RADS 3类",
        "examples": ["BI-RADS 3类", "TI-RADS 2类"]
    },
}

# --- 3. 阴性指标（正常标志）---
rulebase['normal_indicators'] = [
    "未见明显异常", "未见异常", "大小正常", "形态规则",
    "回声均匀", "表面光滑", "边界清晰", "清晰", "光滑",
    "内透声可", "透声可", "未见明显", "正常",
    "未见明显异常血流信号",
]

# --- 4. 异常指标 ---
rulebase['abnormal_indicators'] = {
    "结石": ["强回声团", "强回声斑", "伴声影", "后伴声影", "结石"],
    "囊肿": ["无回声区", "囊性", "壁薄", "后壁回声增强"],
    "增生": ["增厚", "增大", "增生", "饱满", "体积增大"],
    "斑块": ["斑块", "附壁光团", "内中膜增厚", "毛糙"],
    "返流": ["返流", "返流血彩", "五彩镶嵌"],
    "钙化": ["钙化", "强回声点", "强回声斑", "彗尾征"],
    "积液": ["液暗区", "积液", "分离"],
    "结节": ["结节", "低回声", "混合回声", "稍高回声"],
}

# --- 5. 模板变量提取函数 ---
rulebase['template_variable_extractors'] = {
    "尺寸": r"(?:约)?(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)(?:\s*mm)?",
    "单值": r"(\d+\.?\d*)\s*mm",
    "百分比": r"(\d+\.?\d*)\s*%",
    "速度": r"(\d+\.?\d*)\s*cm/s",
}

# ========== 处理模板 ==========
print('\n=== 2. 提取模板变量占位符 ===')
rulebase['templates'] = []

for rid, t in templates.items():
    discname = t.get('DISCNAME', '')
    info2 = t.get('INFO2', '')
    info1_full = '\n'.join(t['_info1_parts'])
    modulename = t.get('MODULENAME', '')
    discgroup = t.get('DISCGROUP', '')
    viscname = t.get('VISCNAME', '')

    # 从INFO1中提取变量占位符标记(x mm等)
    variables = []
    for var_name, pat in rulebase['template_variable_extractors'].items():
        if re.search(pat, info1_full):
            variables.append(var_name)

    # 判断检查部位
    matched_sites = []
    for site, kws in rulebase['site_keywords'].items():
        for kw in kws:
            if kw in info1_full or kw in discname or kw in discgroup:
                matched_sites.append(site)
                break
    if not matched_sites:
        matched_sites = ['其他']

    # 判断是否正常模板
    is_normal = any(ind in discname for ind in ['正常', '未见异常'])
    if not is_normal:
        is_normal = any(ind in info2 for ind in ['未见明显异常', '未见异常', '正常声像'])

    entry = OrderedDict([
        ('id', rid),
        ('name', discname),
        ('site', matched_sites[0] if matched_sites else '其他'),
        ('sites', matched_sites),
        ('discgroup', discgroup),
        ('modulename', modulename),
        ('viscname', viscname),
        ('is_normal', is_normal),
        ('has_variables', len(variables) > 0),
        ('variables', variables),
        ('description', info1_full[:300]),
        ('diagnosis', info2[:200]),
        ('keywords', extract_keywords(discname + info2)),
        ('frequency', 0),  # 由匹配数据填充
    ])
    rulebase['templates'].append(entry)

print(f'  共处理 {len(rulebase["templates"])} 个模板')

# ========== 6. 统计频率（从匹配结果）==========
print('\n=== 3. 统计模板使用频率 ===')
if os.path.exists(MATCH_RESULT):
    with open(MATCH_RESULT, 'r', encoding='gb18030') as f:
        reader = csv.DictReader(f)
        freq = Counter()
        for r in reader:
            name = ''
            for k in r.keys():
                if 'discname' in k:
                    name = (r[k] or '').strip()
                    break
            if name:
                freq[name] += 1

    freq_by_id = {}
    for t in rulebase['templates']:
        tname = t['name']
        f = freq.get(tname, 0)
        t['frequency'] = f
        freq_by_id[t['id']] = f

    print(f'  已填充 {len(freq)} 个模板的频率数据')
    top5 = sorted(rulebase['templates'], key=lambda x: -x['frequency'])[:5]
    for t in top5:
        print(f'    #{t["id"]} {t["name"]}: {t["frequency"]}次')
else:
    print('  (匹配结果文件不存在，跳过频率统计)')

# ========== 辅助函数 ==========
def extract_keywords(text):
    """提取中文字词作为关键词"""
    if not text:
        return []
    parts = re.split(r'[，。；：、／\s]', text)
    kws = []
    for p in parts:
        p = p.strip()
        p = re.sub(r'[（(][^）)]*[）)]', '', p)
        if len(p) >= 2:
            kws.append(p)
    return kws[:10]


def extract_variables_from_text(text, rules):
    """从语音文本中提取变量值"""
    result = {}
    for var_name, rule in rules.items():
        matches = re.findall(rule['pattern'], text, re.IGNORECASE)
        if matches:
            result[var_name] = matches
    return result

# ========== 7. 匹配策略配置 ==========
rulebase['match_strategy'] = {
    "priorities": [
        {"name": "diagnosis_exact", "weight": 0.5, "desc": "诊断结论精确匹配"},
        {"name": "site_match", "weight": 0.3, "desc": "检查部位匹配"},
        {"name": "text_similarity", "weight": 0.3, "desc": "文本内容相似度"},
        {"name": "name_match", "weight": 0.2, "desc": "模板名称关键词匹配"},
    ],
    "scoring": {
        "has_hint": {"diagnosis": 0.5, "text": 0.3, "site": 0.1, "name": 0.1},
        "no_hint":  {"diagnosis": 0.0, "text": 0.5, "site": 0.3, "name": 0.2},
    },
    "thresholds": {
        "high_confidence": 0.5,
        "medium_confidence": 0.3,
        "low_confidence": 0.2,
    },
    "max_candidates": 5,
}

# ========== 写入规则库 ==========
print('\n=== 4. 写入规则库 ===')
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(rulebase, f, ensure_ascii=False, indent=2)

size = os.path.getsize(OUT)
print(f'  输出: {OUT}')
print(f'  大小: {size/1024:.0f} KB')
print(f'  结构:')
print(f'    site_keywords: {len(rulebase["site_keywords"])}个部位')
print(f'    variable_rules: {len(rulebase["variable_rules"])}条')
print(f'    normal_indicators: {len(rulebase["normal_indicators"])}条')
print(f'    abnormal_indicators: {len(rulebase["abnormal_indicators"])}类')
print(f'    templates: {len(rulebase["templates"])}个')
print(f'    match_strategy: 已配置')

# ========== 辅助函数 ==========
def extract_keywords(text):
    """提取中文字词作为关键词"""
    if not text:
        return []
    # 按标点分割
    parts = re.split(r'[，。；：、／\s]', text)
    kws = []
    for p in parts:
        p = p.strip()
        # 去掉括号备注
        p = re.sub(r'[（(][^）)]*[）)]', '', p)
        if len(p) >= 2:
            kws.append(p)
    return kws[:10]


def extract_variables_from_text(text, rules):
    """从语音文本中提取变量值"""
    result = {}
    for var_name, rule in rules.items():
        matches = re.findall(rule['pattern'], text, re.IGNORECASE)
        if matches:
            result[var_name] = matches
    return result


print('\n=== 5. 验证样例 ===')
# 测试一条语音输入
sample_voice = "肝脏大小正常，表面光滑，实质回声分布均匀，肝内管系尚清，大小约3乘2毫米"
test_vars = extract_variables_from_text(sample_voice, rulebase['variable_rules'])
print(f'  语音输入: {sample_voice}')
print(f'  提取变量: {json.dumps(test_vars, ensure_ascii=False)}')

print('\n✅ 规则库构建完成！')
print(f'文件路径: {OUT}')
