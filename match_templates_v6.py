"""
长沙超声报告模板匹配 v6 - 完整输出所有字段
"""

import csv
import re
import sys
from collections import OrderedDict, Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')


# ========== 1. 读取模板 ==========
def read_templates(filepath):
    """读取模板并保留所有原始字段"""
    templates = OrderedDict()
    current_rid = None
    raw_headers = []

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        raw_headers = reader.fieldnames

        for row in reader:
            rid = (row.get('RID') or '').strip()
            discname = (row.get('DISCNAME') or '').strip()

            if rid and discname:
                current_rid = rid
                # 保留所有原始字段
                tpl = dict(row)
                for k, v in tpl.items():
                    tpl[k] = (v or '').strip()
                tpl['info1_parts'] = []
                tpl['site_kw'] = set()
                tpl['name_site_kw'] = set()
                templates[current_rid] = tpl

            if current_rid and current_rid in templates:
                info1 = (row.get('INFO1') or '').strip()
                if info1:
                    templates[current_rid]['info1_parts'].append(info1)
                info2 = (row.get('INFO2') or '').strip()
                if info2:
                    templates[current_rid]['INFO2'] = info2

    # 构建全文
    for rid, tpl in templates.items():
        tpl['rid'] = rid  # lowercase alias
        tpl['full_info1'] = re.sub(r'\s+', '', ''.join(tpl['info1_parts']))
        tpl['full_info2'] = re.sub(r'\s+', '', tpl.get('INFO2', ''))
        tpl['clean_name'] = re.sub(r'\s+', '', tpl.get('DISCNAME', ''))

        site_text = (tpl.get('DISCGROUP') or '') + (tpl.get('MODULENAME') or '')
        tpl['site_kw'] = extract_site_keywords(site_text)
        tpl['name_site_kw'] = extract_site_keywords(tpl['clean_name'])

    return templates, raw_headers


# 部位关键词库
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

NEGATIVE_PATTERNS = [
    '未见明显异常', '未见异常', '未见明显', '正常', '大小正常',
    '形态规则', '回声均匀', '光滑', '清晰',
]


def extract_site_keywords(text):
    found = set()
    for site_name, keywords in BODY_SITES.items():
        for kw in keywords:
            if kw in text:
                found.add(site_name)
                break
    return found


def diagnose_site_from_text(see_text):
    if not see_text:
        return set()
    found_sites = set()
    for site_name, keywords in BODY_SITES.items():
        for kw in keywords:
            if kw in see_text:
                found_sites.add(site_name)
                break
    return found_sites


def is_normal_report(see_text, hint_text=''):
    if hint_text:
        if any(kw in hint_text for kw in ['未见明显异常', '未见异常', '正常声像']):
            return True
    if see_text:
        total_neg = sum(1 for kw in NEGATIVE_PATTERNS if kw in see_text)
        if total_neg >= 3:
            return True
    return False


# ========== 2. 流式解析报告 ==========
REPORT_HEADERS = [
    'StudyIdentity', 'DiseaseCode', 'LastUpdate', 'LastStudyDoctor',
    'ResultComments', 'F_ReportHintInfo', 'F_ControlValue', 'StudySee',
    'StudyHint', 'SurgeryProcess', 'PathologyDiagnose',
    'StudySeeXml', 'StudyHindXml', 'StudySeeRtf', 'StudyHintRtf'
]


def parse_reports(filepath, limit=0):
    """流式解析报告，保留所有15个字段"""
    reports = []
    current = None
    total = 0

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        f.readline()  # skip header

        for line in f:
            total += 1
            first_comma = line.index(',') if ',' in line else -1
            if first_comma > 0:
                col0 = line[:first_comma].strip('"')
                if len(col0) >= 15 and col0.isdigit():
                    if current:
                        reports.append(current)
                        if limit and len(reports) >= limit:
                            return reports, REPORT_HEADERS

                    cols = smart_split(line)
                    current = {h: '' for h in REPORT_HEADERS}
                    for i, h in enumerate(REPORT_HEADERS):
                        if i < len(cols):
                            current[h] = cols[i].strip('" ')

                    # 段落收集
                    current['_see_parts'] = []
                    current['_hint_parts'] = []
                    s = current.get('StudySee', '')
                    if s: current['_see_parts'].append(s)
                    h = current.get('StudyHint', '')
                    if h: current['_hint_parts'].append(h)

                elif current is not None:
                    cols = smart_split(line)
                    if len(cols) > 7:
                        s = cols[7].strip('" ')
                        if s and not s.startswith('{\\rtf'):
                            current['_see_parts'].append(s)
                    if len(cols) > 8:
                        h = cols[8].strip('" ')
                        if h and not h.startswith('{\\rtf'):
                            current['_hint_parts'].append(h)

            if total % 1000000 == 0:
                print(f'  已扫描 {total} 行... {len(reports)} 报告')

    if current:
        reports.append(current)
    return reports, REPORT_HEADERS


def smart_split(line):
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


# ========== 3. 匹配引擎 ==========
class Matcher:
    def __init__(self, templates):
        self.templates = templates
        self.site_index = defaultdict(list)
        for rid, tpl in templates.items():
            for site in tpl['site_kw']:
                self.site_index[site].append(tpl)
            for site in tpl['name_site_kw']:
                self.site_index[site].append(tpl)
        self.all_templates = list(templates.values())

    def match(self, report):
        see = re.sub(r'\s+', '', ''.join(report.get('_see_parts', [])))
        hint = re.sub(r'\s+', '', ''.join(report.get('_hint_parts', [])))
        report_sites = diagnose_site_from_text(see)

        candidates = []
        if report_sites:
            seen_ids = set()
            for site in report_sites:
                for tpl in self.site_index.get(site, []):
                    if tpl['rid'] not in seen_ids:
                        seen_ids.add(tpl['rid'])
                        candidates.append(tpl)

        if not candidates:
            candidates = self.all_templates

        scored = []
        for tpl in candidates:
            s = self._calc_score(tpl, see, hint, report_sites)
            if s['score'] >= 0.15:
                scored.append(s)

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:3]

    def _calc_score(self, tpl, see, hint, report_sites):
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
                site = 0.2

        # B: 诊断匹配
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
        if name_m == 0 and name_core and see:
            if name_core in see:
                name_m = 0.5

        # D: 文本内容匹配
        tpl_i1 = tpl['full_info1']
        if tpl_i1 and see:
            sents = [s for s in re.split(r'[。\n]', tpl_i1) if len(s) >= 10]
            if sents:
                hits = sum(1 for s in sents if s in see)
                text = hits / len(sents)
            if text < 0.3:
                tpl_kws = set(re.findall(r'[一-鿿]{4,}', tpl_i1))
                see_kws = set(re.findall(r'[一-鿿]{4,}', see))
                if tpl_kws and see_kws:
                    kw_hits = len(tpl_kws & see_kws)
                    kw_total = len(tpl_kws)
                    text = max(text, kw_hits / kw_total * 0.6)

        if hint:
            combined = diag * 0.5 + text * 0.3 + site * 0.1 + name_m * 0.1
        else:
            combined = text * 0.5 + site * 0.3 + name_m * 0.2

        return {
            'rid': tpl.get('RID', ''), 'discname': tpl.get('DISCNAME', ''),
            'viscname': tpl.get('VISCNAME', ''), 'modulename': tpl.get('MODULENAME', ''),
            'discgroup': tpl.get('DISCGROUP', ''),
            'tpl_INFO1': tpl.get('full_info1', ''),
            'tpl_INFO2': tpl.get('full_info2', ''),
            'tpl_IDX': tpl.get('IDX', ''), 'tpl_VISCIDX': tpl.get('VISCIDX', ''),
            'tpl_IDX_VISCGROUP': tpl.get('IDX_VISCGROUP', ''),
            'tpl_Buf1': tpl.get('Buf1', ''), 'tpl_Buf2': tpl.get('Buf2', ''),
            'tpl_Buf3': tpl.get('Buf3', ''), 'tpl_Buf4': tpl.get('Buf4', ''),
            'score': round(combined, 4),
            'site_score': round(site, 4), 'text_score': round(text, 4),
            'diag_score': round(diag, 4), 'name_score': round(name_m, 4),
        }


# ========== Main ==========
def main():
    tp = r'C:\Users\Administrator\Desktop\超声结构化报告\模板表.csv'
    rp = r'C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W - 副本.csv'
    out = r'C:\Users\Administrator\Desktop\超声结构化报告\matching_result_full.csv'

    print('=== 读取模板 ===')
    templates, tpl_headers = read_templates(tp)
    print(f'  共 {len(templates)} 个模板')
    print(f'  模板字段: {tpl_headers}')

    print('\n=== 构建索引 ===')
    matcher = Matcher(templates)

    print('\n=== 解析报告(流式) ===')
    reports, rpt_headers = parse_reports(rp, limit=0)
    print(f'  共 {len(reports)} 条报告')
    print(f'  报告字段: {rpt_headers}')

    print('\n=== 匹配中... ===')
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

        # 合并：报告所有字段 + 最佳模板所有字段 + 评分
        row = {}
        # 报告原始字段
        for h in rpt_headers:
            if h in ('_see_parts', '_hint_parts'):
                continue
            row[f'rpt_{h}'] = rep.get(h, '')

        # 报告全文
        row['rpt_StudySee_Full'] = rep.get('StudySee', '') + '\n'.join(rep.get('_see_parts', []))[1:] if rep.get('StudySee', '') else '\n'.join(rep.get('_see_parts', []))
        row['rpt_StudyHint_Full'] = rep.get('StudyHint', '') + '\n'.join(rep.get('_hint_parts', []))[1:] if rep.get('StudyHint', '') else '\n'.join(rep.get('_hint_parts', []))

        # 匹配结果
        row['match_score'] = best_score
        row['match_rank'] = 1
        row['match_detail'] = f"site={best['site_score']:.2f}|text={best['text_score']:.2f}|diag={best['diag_score']:.2f}|name={best['name_score']:.2f}" if best else ''

        # 模板字段
        if best:
            for k, v in best.items():
                if k not in ('score', 'site_score', 'text_score', 'diag_score', 'name_score'):
                    row[k] = v
        else:
            for k in ['rid', 'discname', 'viscname', 'modulename', 'discgroup',
                       'tpl_INFO1', 'tpl_INFO2', 'tpl_IDX', 'tpl_VISCIDX',
                       'tpl_IDX_VISCGROUP', 'tpl_Buf1', 'tpl_Buf2', 'tpl_Buf3', 'tpl_Buf4']:
                row[k] = ''

        results.append(row)

        if (i+1) % 10000 == 0:
            print(f'  {i+1}/{len(reports)} 高:{stats["高(≥50%)"]} 中:{stats["中(30-50%)"]} 无:{stats["无(<20%)"]}')

    # 写CSV
    print('\n=== 写入CSV ===')
    if not results:
        print('无结果可输出')
        return

    fieldnames = list(results[0].keys())
    with open(out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in results:
            w.writerow(row)

    print(f'\n{"="*50}')
    print('匹配统计:')
    for k, v in stats.most_common():
        print(f'  {k}: {v} ({v/len(results)*100:.1f}%)')
    print(f'{"="*50}')
    print(f'输出文件: {out}')
    print(f'总列数: {len(fieldnames)} 列')
    print(f'包含: 报告字段({len(rpt_headers)}) + 模板字段 + 匹配评分')


if __name__ == '__main__':
    main()
