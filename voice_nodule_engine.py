#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""多病灶模板组合引擎 v2.1 - 提取+分级+匹配+合并"""
import json, re

BASE = 'E:/claude'
with open(BASE+'/ultrasound_report_templates.json', encoding='utf-8') as f:
    TPL_LIB = json.load(f)

FOLLOWUP = {"2": "定期复查1年", "3": "短期复查6-12月", "4a": "建议穿刺活检", "4b": "建议专科就诊", "5": "立即专科就诊"}
ECHO_TYPES = ["囊实混合回声", "极低回声", "无回声", "低回声", "等回声", "高回声", "混合回声", "强回声", "中等回声"]


def extract_nodules(text):
    """从报告文本中提取所有结节"""
    text = text.replace('较大约', '大小约')
    sents = re.split(r'[。；;]', text)
    nodules = []
    for sent in sents:
        sent = sent.strip()
        if not sent or '大小约' not in sent:
            continue
        # 侧别
        side = '-'
        for s in ['左侧叶', '右侧叶', '双侧叶', '峡部', '左侧', '右侧']:
            if s in sent: side = s; break
        # 回声
        echo = '-'
        for e in ECHO_TYPES:
            if e in sent: echo = e; break
        # 尺寸
        sizes = re.findall(r'大小约\s*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*mm', sent)
        if not sizes:
            sizes = re.findall(r'大小约\s*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*mm?\s*', sent)
        if not sizes:
            continue
        # 特征
        has_asp = bool(re.search(r'纵横比[大于>\s]*1', sent))
        has_micro = bool(re.search(r'微小钙化|点状强回声', sent))
        has_macro = bool(re.search(r'粗大钙化|强回声斑', sent))
        margin = '-'
        for m in ['毛糙成角', '毛糙', '模糊', '欠清晰', '清晰', '稍毛糙', '成角']:
            if m in sent: margin = m; break
        morph = '-'
        for m in ['不规则', '欠规则', '规则']:
            if m in sent: morph = m; break
        multi = '多个' in sent or '多发' in sent
        for w, h in sizes:
            nodules.append({
                '侧': side, '回声': echo, '尺寸': w + 'x' + h + 'mm',
                '形态': morph, '边界': margin,
                '纵横比>1': has_asp,
                '钙化': '微小钙化' if has_micro else ('粗大钙化' if has_macro else '无'),
                '多发': multi
            })
    return nodules


def calc_tirads(n):
    """计算TI-RADS分级"""
    s = 0
    e = n.get('回声', '')
    if '无回声' in e: s += 0
    elif '囊实混合' in e: s += 1
    elif '低回声' in e: s += 2
    elif '极低回声' in e: s += 3
    else: s += 1

    m = n.get('边界', '')
    if '清晰' in m: s += 0
    elif '模糊' in m or '毛糙' in m: s += 2
    else: s += 1

    if n.get('纵横比>1'): s += 1
    c = n.get('钙化', '无')
    if '微小' in c: s += 3
    elif '粗大' in c: s += 1

    grade_map = {0: '2', 1: '3', 2: '4a', 3: '4a', 4: '4b', 5: '5', 6: '5', 7: '5', 8: '5'}
    return grade_map.get(min(s, 8), '3'), s


def match_tpl(text):
    """匹配模板"""
    best = []
    for g in TPL_LIB.get('疾病分组', []):
        if '甲状腺' not in g.get('疾病分组', ''):
            continue
        for t in g.get('模板列表', []):
            see = t.get('模板-所见段', '') or ''
            dn = t.get('疾病名称', '')
            rid = t.get('rid', 0)
            s = 0
            if '多个' in text and '多个' in see: s += 3
            if '多发' in text and '多发' in see: s += 3
            if any(e in text and e in see for e in ['低回声', '混合回声']): s += 3
            if '纵横比' in text and '纵横比' in see: s += 2
            if s > 0: best.append((s, rid, dn))
    best.sort(key=lambda x: -x[0])
    return best[:3]


def process(text):
    """主入口"""
    nodes = extract_nodules(text)
    if not nodes:
        return {"error": "未检测到结节(需包含'大小约')"}

    for n in nodes:
        g, sc = calc_tirads(n)
        n['TI-RADS'] = g
        n['评分'] = sc
        n['建议'] = FOLLOWUP.get(g, '复查')

    tpls = match_tpl(text)

    # 综合诊断
    gs = [int(n['TI-RADS'].replace('a', '').replace('b', '')) for n in nodes
          if n['TI-RADS'].replace('a', '').replace('b', '').isdigit()]
    mx = max(gs) if gs else 3
    mn = min(gs) if gs else 3
    if mx >= 4:
        summary = "甲状腺多发病灶(TI-RADS " + str(mn) + "-" + str(mx) + "类)，建议专科就诊"
    else:
        summary = "甲状腺结节(TI-RADS " + str(mx) + "类)，定期复查"

    out = {
        "结节数": len(nodes),
        "病灶": [],
        "综合诊断": summary,
        "匹配模板": [{"rid": r, "名称": d, "得分": s} for s, r, d in tpls[:3] if s >= 2]
    }

    for n in nodes:
        d = {"侧": n['侧'], "回声": n['回声'], "尺寸": n['尺寸'],
             "评分": n['评分'], "TI-RADS": n['TI-RADS'], "建议": n['建议']}
        if n['边界'] != '-': d['边界'] = n['边界']
        if n['形态'] != '-': d['形态'] = n['形态']
        if n['纵横比>1']: d['纵横比>1'] = True
        out['病灶'].append(d)

    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        txt = "".join(sys.argv[1:])
    else:
        txt = """甲状腺双侧叶形态规则，大小正常,表面欠光滑,包膜完整,内部回声均匀,左侧叶内可见多个低回声结节,其一位于左侧叶近峡部大小约 4.4x7.0 mm，另一位于左侧叶中部大小约4x5mm，纵横比大于1，形态欠规则，边缘毛糙，内部回声欠均匀。右侧叶内可见混合回声结节,其一大小约 10x10 mm，纵横比相等，形态尚规则，边缘稍毛糙、成角，内部回声欠均匀。右侧叶内可见低回声结节,形态规则，边界清晰，内部回声欠均匀，大小约 5.2x4.5 mm。"""
    print(json.dumps(process(txt), ensure_ascii=False, indent=2))
