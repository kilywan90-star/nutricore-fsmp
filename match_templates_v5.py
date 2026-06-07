"""
长沙超声报告模板匹配 v5 - 基于部位+文本内容的精准匹配

核心思路：
1. 模板分为"正常模板"和"异常模板"两类
2. 对于无诊断提示的报告，通过提取StudySee中的部位关键词确定检查范围
3. 同部位内用段落级文本匹配定位具体模板
"""

import csv
import re
import sys
from collections import OrderedDict, Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')


# ========== 1. 读取模板（完整版）==========
def read_templates(filepath):
    templates = OrderedDict()
    current_rid = None

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = (row.get('RID') or '').strip()
            discname = (row.get('DISCNAME') or '').strip()

            if rid and discname:
                current_rid = rid
                templates[current_rid] = {
                    'rid': rid,
                    'discname': discname,
                    'viscname': (row.get('VISCNAME') or '').strip(),
                    'info1_parts': [],
                    'info2': (row.get('INFO2') or '').strip(),
                    'modulename': (row.get('MODULENAME') or '').strip(),
                    'discgroup': (row.get('DISCGROUP') or '').strip(),
                    'idx_viscgroup': (row.get('IDX_VISCGROUP') or '').strip(),
                }

            if current_rid and current_rid in templates:
                info1 = (row.get('INFO1') or '').strip()
                if info1:
                    templates[current_rid]['info1_parts'].append(info1)
                info2 = (row.get('INFO2') or '').strip()
                if info2:
                    templates[current_rid]['info2'] = info2

    # Build clean text
    out = {}
    for rid, tpl in templates.items():
        tpl['full_info1'] = re.sub(r'\s+', '', ''.join(tpl['info1_parts']))
        tpl['full_info2'] = re.sub(r'\s+', '', tpl['info2'])
        tpl['clean_name'] = re.sub(r'\s+', '', tpl['discname'])

        # 提取部位关键词（从discgroup/modulename）
        site_text = tpl['discgroup'] + tpl['modulename']
        tpl['site_kw'] = extract_site_keywords(site_text)
        # 也提取名中的部位
        tpl['name_site_kw'] = extract_site_keywords(tpl['clean_name'])

        out[rid] = tpl

    return out


# 部位关键词库（按层级）
BODY_SITES = {
    '腹部': ['肝', '胆', '脾', '胰', '腹腔', '腹部'],
    '肝脏': ['肝', '门静脉'],
    '胆囊': ['胆', '胆囊'],
    '脾': ['脾'],
    '双肾': ['肾', '输尿管', '肾上腺'],
    '心脏': ['心脏', '心', '房室', '瓣膜', '室间隔', '主动脉', '肺动脉', '二尖瓣', '三尖瓣'],
    '甲状腺': ['甲状腺', '甲状旁腺', '颈部淋巴结'],
    '乳腺': ['乳腺', '乳', '腋窝'],
    '颈动脉': ['颈动脉', '颈总动脉', '椎动脉', '锁骨下动脉'],
    '前列腺': ['前列腺', '膀胱'],
    '子宫附件': ['子宫', '附件', '卵巢', '宫腔', '宫颈', '盆腔'],
    '睾丸': ['睾丸', '附睾', '精索', '精囊'],
    '四肢血管': ['血管', '动脉', '静脉', '肱', '股'],
    '胎儿': ['胎儿', '胎', '羊水', '胎盘'],
    '腹主动脉': ['腹主动脉'],
    'ABUS': ['ABUS', '乳腺容积'],
}

# 常见阴性诊断关键词（表示正常/无异常）
NEGATIVE_PATTERNS = [
    '未见明显异常', '未见异常', '未见明显', '正常', '大小正常',
    '形态规则', '回声均匀', '光滑', '清晰',
]


def extract_site_keywords(text):
    """从文本中提取部位关键词"""
    found = set()
    for site_name, keywords in BODY_SITES.items():
        for kw in keywords:
            if kw in text:
                found.add(site_name)
                break
    return found


def diagnose_site_from_text(see_text):
    """从超声所见文本中判断检查部位"""
    if not see_text:
        return set()
    found_sites = set()
    for site_name, keywords in BODY_SITES.items():
        for kw in keywords:
            if kw in see_text:
                found_sites.add(site_name)
                break
    return found_sites


def is_normal_template(tpl):
    """判断模板是否是正常/阴性模板"""
    name = tpl['clean_name']
    info2 = tpl.get('full_info2', '')
    name_neg = any(kw in name for kw in ['正常', '未见异常', '未见明显异常'])
    info2_neg = any(kw in info2 for kw in ['未见明显异常', '未见异常', '正常'])
    return name_neg or info2_neg


def is_normal_report(see_text, hint_text=''):
    """判断报告是否是正常/阴性报告"""
    if hint_text:
        if any(kw in hint_text for kw in ['未见明显异常', '未见异常', '正常声像']):
            return True
    if see_text:
        total_neg = sum(1 for kw in NEGATIVE_PATTERNS if kw in see_text)
        # 如果文本中有3个以上阴性描述，可能是正常报告
        if total_neg >= 3:
            return True
    return False


def site_match_score(tpl_sites, tpl_name_sites, report_sites):
    """计算报告和模板在检查部位上的匹配度"""
    if not report_sites or not tpl_sites:
        return 0.0
    union = tpl_sites | report_sites
    inter = tpl_sites & report_sites

    if not inter:
        # 试试从模板名匹配
        inter2 = tpl_name_sites & report_sites
        if inter2:
            return 0.3
        return 0.0

    return len(inter) / len(union)


# ========== 2. 流式解析报告 ==========
def parse_reports(filepath, limit=0):
    reports = []
    current = None
    total = 0

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        header = f.readline()
        # 找到索引
        cols_h = header.strip().split(',')
        id_idx = 0
        see_idx = 7
        hint_idx = 8
        doctor_idx = 3

        for line in f:
            total += 1
            # 快速解析：找到第1个逗号前的内容
            first_comma = line.index(',') if ',' in line else -1
            if first_comma > 0:
                col0 = line[:first_comma].strip('"')
                if len(col0) >= 15 and col0.isdigit():
                    if current:
                        reports.append(current)
                        if limit and len(reports) >= limit:
                            return reports

                    # 解析这一行
                    cols = smart_split(line)
                    current = {
                        'id': col0,
                        'doctor': get_s(cols, doctor_idx),
                        'date': get_s(cols, 2),
                        'see_parts': [],
                        'hint_parts': [],
                    }
                    s = get_s(cols, see_idx)
                    if s: current['see_parts'].append(s)
                    h = get_s(cols, hint_idx)
                    if h: current['hint_parts'].append(h)
                elif current is not None:
                    cols = smart_split(line)
                    s = get_s(cols, see_idx)
                    if s and not s.startswith('{\\rtf'): current['see_parts'].append(s)
                    h = get_s(cols, hint_idx)
                    if h and not h.startswith('{\\rtf'): current['hint_parts'].append(h)

            if total % 1000000 == 0:
                print(f'  已扫描 {total} 行... {len(reports)} 报告')

    if current:
        reports.append(current)
    return reports


def smart_split(line):
    """智能CSV分割"""
    cols = []
    cur = ''
    in_q = False
    for ch in line.rstrip('\n\r'):
        if ch == '"':
            in_q = not in_q
        elif ch == ',' and not in_q:
            cols.append(cur)
            cur = ''
            continue
        cur += ch
    cols.append(cur)
    return cols


def get_s(cols, idx):
    """安全获取字符串"""
    if 0 <= idx < len(cols):
        return cols[idx].strip('" ')
    return ''


# ========== 3. 匹配引擎 ==========
class Matcher:
    def __init__(self, templates):
        self.templates = templates
        # 按部位建立模板索引
        self.site_index = defaultdict(list)
        for rid, tpl in templates.items():
            for site in tpl['site_kw']:
                self.site_index[site].append(tpl)
            for site in tpl['name_site_kw']:
                self.site_index[site].append(tpl)

        # 也建立无部位的索引
        self.all_templates = list(templates.values())

    def match(self, report):
        see = re.sub(r'\s+', '', ''.join(report.get('see_parts', [])))
        hint = re.sub(r'\s+', '', ''.join(report.get('hint_parts', [])))

        # 判断检查部位
        report_sites = diagnose_site_from_text(see)
        is_neg = is_normal_report(see, hint)

        # 缩小候选范围
        candidates = []
        if report_sites:
            # 从部位索引找候选
            seen_ids = set()
            for site in report_sites:
                for tpl in self.site_index.get(site, []):
                    if tpl['rid'] not in seen_ids:
                        seen_ids.add(tpl['rid'])
                        candidates.append(tpl)

        if not candidates:
            candidates = self.all_templates

        # 评分
        scored = []
        for tpl in candidates:
            scores = self._calc_score(tpl, see, hint, report_sites)
            if scores['score'] >= 0.15:
                scored.append(scores)

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:3]

    def _calc_score(self, tpl, see, hint, report_sites):
        s = {'rid': tpl['rid'], 'discname': tpl['discname'],
             'viscname': tpl['viscname'], 'modulename': tpl['modulename'],
             'discgroup': tpl['discgroup']}

        site = 0.0
        text = 0.0
        diag = 0.0
        name_m = 0.0

        # A: 部位匹配
        tpl_sites = tpl['site_kw']
        tpl_name_sites = tpl['name_site_kw']
        if report_sites:
            inter = tpl_sites & report_sites
            if inter:
                site = len(inter) / max(len(tpl_sites | report_sites), 1)
            elif tpl_name_sites & report_sites:
                site = 0.2  # name site partial match

        # B: 诊断匹配 (如果有提示)
        tpl_i2 = tpl.get('full_info2', '')
        if hint and tpl_i2:
            if tpl_i2 in hint:
                diag = 1.0
            else:
                d_parts = [p for p in re.split(r'[，。；]', tpl_i2) if len(p) >= 4]
                if d_parts:
                    hits = sum(1 for p in d_parts if p in hint)
                    diag = hits / len(d_parts)

        # C: 模板名匹配
        tpl_name = tpl['clean_name']
        name_core = re.sub(r'[（(][^）)]*[）)]', '', tpl_name)
        if name_core:
            name_parts = [p for p in re.split(r'[、／]', name_core) if len(p) >= 2]
            if name_parts and hint:
                hits = sum(1 for p in name_parts if p in hint)
                name_m = hits / len(name_parts) * 0.6
            elif name_parts and see:
                hits = sum(1 for p in name_parts if p in see)
                name_m = hits / len(name_parts) * 0.4

        # 如果没有hint，尝试将模板名匹配到see
        if name_m == 0 and name_core and see:
            if name_core in see:
                name_m = 0.5

        # D: 文本内容匹配
        tpl_i1 = tpl['full_info1']
        if tpl_i1 and see:
            # 句子级匹配
            sents = [s for s in re.split(r'[。\n]', tpl_i1) if len(s) >= 10]
            if sents:
                hits = sum(1 for s in sents if s in see)
                text = hits / len(sents)

            # 如果句子级不够好，试关键词
            if text < 0.3:
                tpl_kws = set(re.findall(r'[一-鿿]{4,}', tpl_i1))
                see_kws = set(re.findall(r'[一-鿿]{4,}', see))
                if tpl_kws and see_kws:
                    kw_hits = len(tpl_kws & see_kws)
                    kw_total = len(tpl_kws)
                    text = max(text, kw_hits / kw_total * 0.6)

        # 综合
        if hint:
            combined = diag * 0.5 + text * 0.3 + site * 0.1 + name_m * 0.1
        else:
            combined = text * 0.5 + site * 0.3 + name_m * 0.2

        s.update({
            'score': round(combined, 4),
            'site_score': round(site, 4),
            'text_score': round(text, 4),
            'diag_score': round(diag, 4),
            'name_score': round(name_m, 4),
        })
        return s


# ========== Main ==========
def main():
    tp = r'C:\Users\Administrator\Desktop\超声结构化报告\模板表.csv'
    rp = r'C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W - 副本.csv'
    out = r'C:\Users\Administrator\Desktop\超声结构化报告\matching_result_v5.csv'

    print('=== 读取模板 ===')
    templates = read_templates(tp)
    print(f'  共 {len(templates)} 个模板')

    print('\n=== 构建索引 ===')
    matcher = Matcher(templates)

    # 统计各部位的模板数
    site_counts = Counter()
    for t in templates.values():
        for s in t['site_kw']:
            site_counts[s] += 1
    print('  部位->模板数:', dict(site_counts.most_common()))

    print('\n=== 解析报告(小批量测试) ===')
    reports = parse_reports(rp, limit=0)  # 全量
    print(f'  共 {len(reports)} 条')

    print('\n=== 匹配 ===')
    results = []
    stats = Counter()

    for i, rep in enumerate(reports):
        matches = matcher.match(rep)
        best = matches[0] if matches else None
        best_score = best['score'] if best else 0

        if best:
            if best_score >= 0.5: stats['高(≥50%)'] += 1
            elif best_score >= 0.3: stats['中(30-50%)'] += 1
            elif best_score >= 0.2: stats['低(20-30%)'] += 1
            else: stats['无(<20%)'] += 1
        else:
            stats['无(<20%)'] += 1

        see_txt = re.sub(r'\s+', '', ''.join(rep.get('see_parts', [])))[:100]
        hint_txt = re.sub(r'\s+', '', ''.join(rep.get('hint_parts', [])))[:100]

        results.append({
            'id': rep['id'],
            'doctor': rep['doctor'],
            'date': rep['date'],
            'score': best_score,
            'rid': best['rid'] if best else '',
            'name': best['discname'] if best else '',
            'viscname': best['viscname'] if best else '',
            'modulename': best['modulename'] if best else '',
            'discgroup': best['discgroup'] if best else '',
            'hint': hint_txt,
            'see': see_txt,
            'detail': f"site={best['site_score']:.2f}/text={best['text_score']:.2f}/diag={best['diag_score']:.2f}/name={best['name_score']:.2f}" if best else '',
        })

        if (i+1) % 5000 == 0:
            print(f'  {i+1}/{len(reports)} 高:{stats["高(≥50%)"]} 中:{stats["中(30-50%)"]} 低:{stats["低(20-30%)"]} 无:{stats["无(<20%)"]}')

    # Write CSV
    with open(out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['报告ID', '医生', '日期', '匹配度', '模板编号', '模板名称',
                    '检查类型', '检查部位', '检查分组', '评分详情', '报告提示', '报告摘要'])
        for r in results:
            w.writerow([r['id'], r['doctor'], r['date'], r['score'],
                       r['rid'], r['name'], r['viscname'], r['modulename'],
                       r['discgroup'], r['detail'], r['hint'][:60], r['see'][:60]])

    print(f'\n{"="*50}')
    print('匹配统计:')
    for k, v in stats.most_common():
        print(f'  {k}: {v} ({v/len(results)*100:.1f}%)')
    print(f'{"="*50}')
    print(f'输出: {out}')


if __name__ == '__main__':
    main()
