#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音匹配引擎 v5.3
修复：tpl_see缺字补全 + discname锚点 + 短语直接命中
"""
import json, re
from collections import defaultdict

BASE = 'E:/claude'

with open(BASE+'/ultrasound_report_templates.json', 'r', encoding='utf-8') as f:
    tpl_lib = json.load(f)

# ===== 方言 =====
DIALECT_MAP = {"腰子":"肾","水泡泡":"囊肿","石头":"结石","头头":"颈部","包包":"结节","回音":"回声"}
def dialect(text):
    t = text
    for d, s in DIALECT_MAP.items(): t = t.replace(d, s)
    dm = {"零":"0","一":"1","二":"2","三":"3","四":"4","五":"5","六":"6","七":"7","八":"8","九":"9"}
    t = re.sub(r'点([一二三四五六七八九])', lambda m: '.'+dm[m.group(1)], t)
    t = re.sub(r'零([一二三四五六七八九])', lambda m: '0.'+dm[m.group(1)], t)
    return t

# ===== 器官 =====
ORGAN_RULES = [
    (['肝脏','肝内','肝右','肝左','脂肪肝','肝囊肿','肝大','肝硬化','多囊肝','肝血管瘤','肝钙化'],'肝脏'),
    (['甲状腺'],'甲状腺'), (['前列腺','膀胱充盈'],'前列腺'),
    (['乳腺','双乳','腋窝'],'乳腺'), (['颈动脉','颈总','颈内','颈外','椎动脉','斑块','内中膜'],'颈动脉'),
    (['心脏','AO','LA','LV','二尖瓣','房室间隔','主动脉','心功能','EF','FS','室间隔','心包'],'心脏'),
    (['肾','肾上腺','肾动脉'],'双肾'), (['子宫','卵巢','附件','宫腔','内膜'],'子宫附件'),
    (['胆囊','胆总'],'胆囊'), (['门静脉','脾','胰腺'],'腹部'),
    (['下肢','股总','股浅','腘','胫前','胫后'],'下肢血管'), (['睾丸','附睾','精索'],'阴囊'),
]
def detect_organ(text):
    for kws, organ in ORGAN_RULES:
        for kw in kws:
            if kw in text: return organ
    return None

def fix_tpl(t):
    """修复tpl_see开头缺字"""
    t = t.replace('状腺','甲状腺').replace('状腺','甲状腺').replace('状腺','甲状腺')
    t = re.sub(r'(?<![肝甲乙])脏', '肝脏', t, count=1)  # 开头"脏"补"肝"
    # 避免过度替换: 只替换开头的缺失
    if t.startswith('侧'): t = '左/右' + t
    if t.startswith('乳'): t = '双' + t
    return t

def clean(t):
    t = t.replace('左/右',' ').replace('左侧/右侧',' ').replace('左乳/右乳',' ')
    t = re.sub(r'[xX]mm','',t); t = re.sub(r'xx','',t)
    t = re.sub(r'\d+\.?\d*','',t); t = re.sub(r'<[^>]+>','',t)
    t = re.sub(r'["\'%\/\s\(\)]','',t)
    return t

# ===== 短语库 =====
PHRASES = [
    ('未见明显',8),('大小正常',8),('表面光滑',8),('实质回声',6),
    ('低回声',10),('无回声',10),('混合回声',10),('强回声',8),
    ('边界清晰',8),('形态规则',6),('豹纹征',15),('肝内管系',10),
    ('房室间隔',12),('双侧颈动脉',12),('甲状腺双侧',12),('双乳组织',12),
    ('内膜面毛糙',10),('附壁光团',10),('前列腺形态',8),('膀胱充盈',6),
    ('后壁回声增强',8),('伴声影',8),('内透声可',6),('二尖瓣',8),
    ('心包',6),('室间隔',6),('未见明显异常回声',12),
    ('内未见',6),('管腔通畅',6),('血流通畅',6),
]

# ===== 构建索引 =====
BY_ORGAN = defaultdict(list)
DISCNAME_MAP = {}  # rid -> discname

for g in tpl_lib.get('疾病分组',[]):
    dg = g.get('分组名称',g.get('疾病分组',g.get('discgroup','')))
    for t in g.get('模板列表',[]):
        rid = t.get('rid',0); dn = t.get('疾病名称','')
        see = (t.get('模板-所见段','') or '').strip()
        hint = (t.get('模板-提示段','') or '').strip()
        full = (t.get('真实报告完整版','') or '').strip()
        sample = (t.get('真实报告样例','') or '').strip()

        # 修复模板缺字
        see_fixed = fix_tpl(see)

        # 构建多源匹配池
        mp = see_fixed + ' ' + hint + ' ' + dn + ' ' + dg
        if sample: mp += ' ' + sample
        if full: mp += ' ' + full
        mp_clean = clean(mp)

        organ = detect_organ(dg+dn+see+sample) or '未分类'
        DISCNAME_MAP[rid] = dn
        BY_ORGAN[organ].append({
            'rid':rid,'discname':dn,'discgroup':dg,
            'tpl_see':see_fixed,'tpl_hint':hint,
            'full_text':full or see_fixed,
            'match_pool_raw':mp,
            'match_pool':mp_clean
        })

def calc(text, item):
    mp = item['match_pool_raw']
    mp_c = item['match_pool']

    # 1. discname精确包含（最高权重）
    if len(item['discname'])>=2 and item['discname'] in text:
        return 0.96

    # 2. 短语直接命中（不分割，直接问：用户说的关键短语是否出现在模板中）
    hit = 0
    phrase_cnt = 0
    for p, w in PHRASES:
        if p in text and p in mp:
            hit += w
            phrase_cnt += 1

    # 3. 用户输入作为整体出现在匹配池中（部分包含）
    # 取用户输入中最长的连续中文字段
    chinese = re.findall(r'[一-鿿]{4,}', text)
    long_match = 0
    for c in chinese:
        if len(c) >= 6 and c in mp:
            long_match += 1

    # 4. 字符Jaccard（用clean后的文本）
    ci = set(clean(text))
    cm = set(mp_c)
    jac = len(ci&cm)/max(len(ci|cm),1) if ci and cm else 0

    # 5. 长段完全包含（5个以上连续中文）
    # 取输入文本中任意15字长的窗口，是否出现在mp中
    window_match = 0
    if len(text) >= 15:
        for i in range(0, len(text)-14, 5):
            win = text[i:i+15]
            if win in mp:
                window_match += 1

    # ===== 评分 =====
    s = 0
    if phrase_cnt >= 2: s = max(s, 0.40)
    if phrase_cnt >= 3: s = max(s, 0.55)
    if phrase_cnt >= 4: s = max(s, 0.70)
    if phrase_cnt >= 5: s = max(s, 0.85)
    if phrase_cnt >= 6: s = max(s, 0.95)

    if long_match >= 1: s = max(s, 0.50)
    if long_match >= 2: s = max(s, 0.70)
    if long_match >= 3: s = max(s, 0.88)

    if window_match >= 1: s = max(s, 0.55)
    if window_match >= 2: s = max(s, 0.75)

    if jac >= 0.3: s = max(s, 0.35)
    if jac >= 0.4: s = max(s, 0.50)
    if jac >= 0.55: s = max(s, 0.65)
    if jac >= 0.7: s = max(s, 0.80)

    # 组合高置信度
    if phrase_cnt >= 3 and jac >= 0.3: s = max(s, 0.70)
    if phrase_cnt >= 4 and jac >= 0.4: s = max(s, 0.85)
    if long_match >= 2 and jac >= 0.4: s = max(s, 0.80)
    if long_match >= 2 and phrase_cnt >= 3: s = max(s, 0.82)

    return max(0.05, min(round(s,3), 0.98))


def match(text, top_n=5):
    t = text.strip()
    if len(t) < 3: return [], None
    t = dialect(t)
    organ = detect_organ(t)
    candidates = BY_ORGAN.get(organ, [])
    if not candidates:
        for v in BY_ORGAN.values(): candidates += v
    results = []
    for item in candidates:
        s = calc(t, item)
        results.append(item|{'score':s})
    seen = {}
    for r in results:
        if r['rid'] not in seen or r['score'] > seen[r['rid']]['score']:
            seen[r['rid']] = r
    results = sorted(seen.values(), key=lambda x:-x['score'])
    top = results[:top_n]
    locked = top[0] if (top and top[0]['score'] >= 0.85) else None
    return top, locked


def generate(locked):
    with open(BASE+'/ultrasound_followup_rules.json', 'r', encoding='utf-8') as f:
        fu = json.load(f)
    sug = '建议结合临床定期复查'
    for rule in fu.get('随访规则',[]):
        if rule.get('rid')==locked['rid']: sug=rule.get('随访建议',sug); break
    return {'rid':locked['rid'],'discname':locked['discname'],'discgroup':locked['discgroup'],
        'tpl_see':locked['tpl_see'],'tpl_hint':locked['tpl_hint'],
        'full_report':locked['full_text'],'suggestion':sug,'confidence':locked['score']}


if __name__ == '__main__':
    tests = [
        ('肝脏脂肪沉积','肝脏形态规则，大小正常，表面光滑，实质回声分布均匀，肝内管系尚清'),
        ('前列腺增大','膀胱充盈可，壁光滑，内未见明显包块回声。前列腺形态稍饱满'),
        ('双乳小叶增生','双乳组织增厚、增粗，回声分布不均，见多个粗大点片状低回声区'),
        ('甲状腺回声不均匀','甲状腺双侧叶形态规则，大小正常，表面光滑，实质回声不均匀'),
        ('颈动脉斑块','双侧颈动脉走行正常，内膜面毛糙，内中膜不厚'),
        ('脂肪肝','肝脏形态大小正常，表面光滑，实质回声分布欠均匀，近场回声增强'),
        ('肝囊肿','肝内可见无回声区，壁薄，后壁回声增强，内透声可'),
        ('甲状腺结节','甲状腺左侧叶内可见低回声结节，大小约3.5x4.0mm'),
        ('胆囊结石','胆囊大小形态正常，壁光滑，内可见多个强回声团'),
        ('心脏','2D：各房室内径正常，房室间隔未见明显连续中断'),
        ('肾囊肿','左肾可见无回声区，壁薄，后壁回声增强，内透声可'),
        ('方言','腰子左叶有个水泡泡'),
    ]
    print('测试: 12 用例 (v5.3)')
    total=correct=locked=0
    for name,txt in tests:
        total+=1; top,sel=match(txt); t1=top[0] if top else None
        if not t1: continue
        ok = (name in t1['discname'] or t1['discname'] in name)
        if ok: correct+=1
        if sel: locked+=1
        st='LOCK' if sel else ('OK' if ok else 'FAIL')
        print(f'  [{st}] {t1["score"]*100:.0f}% rid={t1["rid"]} {t1["discname"][:22]} <- {name}')
    print(f'  结果: {correct}/{total}={correct*100//total}%  锁定: {locked}')

    print('\n区分度:')
    for idx in [0,3,5,7,9]:
        name,txt = tests[idx]
        top,_=match(txt)
        if len(top)>=2:
            print(f'  {name}: TOP1={top[0]["score"]*100:.0f}% {top[0]["discname"][:15]}  TOP2={top[1]["score"]*100:.0f}% {top[1]["discname"][:15]}  差={(top[0]["score"]-top[1]["score"])*100:.0f}%')

    print('\n方言:')
    top,_=match('腰子左叶有个水泡泡')
    if top: print(f'  TOP1={top[0]["discname"]} ({top[0]["score"]*100:.0f}%)')
