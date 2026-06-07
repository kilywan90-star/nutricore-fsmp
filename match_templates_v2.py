"""
智能匹配长沙超声报告到模板（v2）
策略：
1. 使用模板的INFO2（诊断结论）去匹配报告的StudyHint（提示）——诊断名是最可靠的匹配信号
2. 使用模板的INFO1去匹配StudySee的文本内容
3. 一个报告可能匹配多个模板（组合诊断）
"""

import csv
import re
import json
from collections import OrderedDict


def sg(val):
    """Safe str get"""
    return (val or '').strip()


def clean_for_match(text):
    """清洗文本用于匹配"""
    if not text:
        return ''
    # 统一标点
    text = text.replace('：', ':').replace('，', ',').replace('；', ';').replace('。', '.')
    text = re.sub(r'\s+', '', text)
    return text


# ========== 1. 读取模板 ==========
def read_templates(template_path):
    with open(template_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    templates = OrderedDict()
    current_rid = None

    for row in rows:
        rid = sg(row.get('RID'))
        discname = sg(row.get('DISCNAME'))

        if rid and discname:
            current_rid = rid
            templates[current_rid] = {
                'rid': rid,
                'discname': discname,
                'viscname': sg(row.get('VISCNAME')),
                'info1_parts': [],
                'info2': sg(row.get('INFO2')),
                'modulename': sg(row.get('MODULENAME')),
                'discgroup': sg(row.get('DISCGROUP')),
                'idx_viscgroup': sg(row.get('IDX_VISCGROUP')),
            }

        if current_rid and current_rid in templates:
            info1 = sg(row.get('INFO1'))
            if info1:
                templates[current_rid]['info1_parts'].append(info1)
            info2 = sg(row.get('INFO2'))
            if info2:
                templates[current_rid]['info2'] = info2

    for tpl in templates.values():
        tpl['full_info1'] = '\n'.join(tpl['info1_parts'])
        tpl['match_info1'] = clean_for_match(tpl['full_info1'])
        tpl['match_info2'] = clean_for_match(tpl['info2'])
        # 提取关键诊断词（去掉"。"和空格等）
        tpl['diagnosis_keywords'] = extract_keywords(tpl['info2'])
        # 提取检查部位关键词
        tpl['site_keywords'] = extract_keywords(tpl['discgroup'] + tpl['modulename'])

    return templates


def extract_keywords(text):
    """提取关键词：按句号/分号分割，去除非中文内容"""
    if not text:
        return []
    # 按标点分割
    parts = re.split(r'[，。；、：\n]', text)
    keywords = []
    for p in parts:
        p = p.strip()
        # 只保留包含中文且有意义的短句（2-20字）
        cn_chars = re.findall(r'[一-鿿]+', p)
        cn_text = ''.join(cn_chars)
        if len(cn_text) >= 2 and len(cn_text) <= 30:
            keywords.append(cn_text)
    return keywords


# ========== 2. 读取报告 ==========
def read_reports(report_path):
    with open(report_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    reports = []
    current_report = None

    for row in rows:
        study_identity = sg(row.get('StudyIdentity'))

        if study_identity:
            if current_report:
                reports.append(current_report)

            current_report = {
                'study_identity': study_identity,
                'disease_code': sg(row.get('DiseaseCode')),
                'last_update': sg(row.get('LastUpdate')),
                'last_study_doctor': sg(row.get('LastStudyDoctor')),
                'study_see_parts': [],
                'study_hint': sg(row.get('StudyHint')),
            }

        if current_report:
            study_see = sg(row.get('StudySee'))
            if study_see:
                current_report['study_see_parts'].append(study_see)

            study_hint = sg(row.get('StudyHint'))
            if study_hint:
                if current_report['study_hint']:
                    if study_hint not in current_report['study_hint']:
                        current_report['study_hint'] += study_hint
                else:
                    current_report['study_hint'] = study_hint

    if current_report:
        reports.append(current_report)

    for r in reports:
        r['full_study_see'] = '\n'.join(r['study_see_parts'])
        r['match_see'] = clean_for_match(r['full_study_see'])
        r['match_hint'] = clean_for_match(r['study_hint'])
        r['hint_keywords'] = extract_keywords(r['study_hint'])

    return reports


# ========== 3. 匹配算法 ==========
def match_report(report, templates):
    """
    多策略匹配：
    1. INFO2 → StudyHint 关键词匹配（加权）
    2. INFO1 → StudySee 文本相似度
    3. 综合评分
    """
    if not report.get('match_hint') and not report.get('match_see'):
        return [], {}

    matches = []

    for rid, tpl in templates.items():
        hint_score = 0.0
        see_score = 0.0
        keyword_hits = []

        # --- 策略1: INFO2 → StudyHint 诊断名匹配 ---
        if tpl['diagnosis_keywords'] and report['hint_keywords']:
            # 计算模板诊断关键词中有多少出现在报告提示中
            tpl_diag = tpl['match_info2']
            report_hint = report['match_hint']

            # 精确子串匹配：如果模板的info2是报告hint的子串
            if tpl_diag and report_hint:
                if tpl_diag in report_hint:
                    hint_score = 1.0
                    keyword_hits.append(f"hint_exact:{tpl['info2'][:30]}")
                else:
                    # 模糊：关键词命中率
                    hits = 0
                    for kw in tpl['diagnosis_keywords']:
                        if kw in report_hint:
                            hits += 1
                            keyword_hits.append(f"hint_kw:{kw}")
                    if tpl['diagnosis_keywords']:
                        hint_score = hits / len(tpl['diagnosis_keywords'])

        # --- 策略2: INFO1 → StudySee 文本匹配 ---
        if tpl['match_info1'] and report['match_see']:
            tpl_info1 = tpl['match_info1']
            report_see = report['match_see']

            # 长公共子串匹配（模板内容在报告中出现）
            # 模板信息通常由多个段落组成，检查每个段落
            info1_sentences = re.split(r'[。\n]', tpl['full_info1'])
            info1_sentences = [clean_for_match(s) for s in info1_sentences if len(clean_for_match(s)) > 10]

            if info1_sentences:
                hits = sum(1 for s in info1_sentences if s in report_see)
                see_score = hits / len(info1_sentences) if info1_sentences else 0
                if see_score > 0.3:
                    keyword_hits.append(f"see_matches:{hits}/{len(info1_sentences)}")

                # 如果句子级匹配不够好，试试关键词级
                if see_score < 0.3:
                    info1_kws = extract_keywords(tpl['full_info1'])
                    if info1_kws:
                        kw_hits = sum(1 for kw in info1_kws if kw in report_see)
                        kw_score = kw_hits / len(info1_kws) if info1_kws else 0
                        see_score = max(see_score, kw_score * 0.8)

        # 综合评分
        combined_score = hint_score * 0.6 + see_score * 0.4

        if combined_score >= 0.15:
            matches.append({
                'rid': tpl['rid'],
                'discname': tpl['discname'],
                'viscname': tpl['viscname'],
                'modulename': tpl['modulename'],
                'discgroup': tpl['discgroup'],
                'match_score': round(combined_score, 4),
                'hint_score': round(hint_score, 4),
                'see_score': round(see_score, 4),
                'keyword_hits': keyword_hits,
                'info1_excerpt': tpl['full_info1'][:200],
                'info2_excerpt': tpl['info2'][:200],
            })

    # 排序，取最匹配的前3个
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches[:5], {'hint_keywords': report['hint_keywords']}


# ========== Main ==========
def main():
    template_path = r'C:\Users\Administrator\Desktop\超声结构化报告\1长沙范本.csv'
    report_path = r'C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W - 副本.csv'
    output_path = r'C:\Users\Administrator\Desktop\超声结构化报告\matched_reports_v2.json'
    summary_path = r'C:\Users\Administrator\Desktop\超声结构化报告\matching_summary_v2.csv'
    detail_path = r'C:\Users\Administrator\Desktop\超声结构化报告\matching_detail_v2.csv'

    print("正在读取模板...")
    templates = read_templates(template_path)
    print(f"  共 {len(templates)} 个模板")

    print("正在读取报告...")
    reports = read_reports(report_path)
    print(f"  共 {len(reports)} 条报告")

    # 测试前 N 条
    test_limit = min(2000, len(reports))
    # 或者全量
    # test_limit = len(reports)

    print(f"\n开始匹配前 {test_limit} 条报告...")

    all_results = []
    stats = {
        'total': 0,
        'matched': 0,     # 至少有一个匹配
        'high_conf': 0,   # 匹配度 > 0.5
        'medium': 0,      # 0.3-0.5
        'low': 0,         # 0.15-0.3
        'none': 0,         # 无匹配
    }

    for i, report in enumerate(reports[:test_limit]):
        matches, _ = match_report(report, templates)

        stats['total'] += 1

        result = {
            'study_identity': report['study_identity'],
            'doctor': report['last_study_doctor'],
            'date': report['last_update'],
            'report_hint': report['study_hint'][:300],
            'report_see_excerpt': report['full_study_see'][:300],
            'match_count': len(matches),
            'best_score': matches[0]['match_score'] if matches else 0,
        }

        if matches:
            result['best_match'] = matches[0]
            result['all_matches'] = matches
            stats['matched'] += 1
            best = matches[0]['match_score']
            if best >= 0.5:
                stats['high_conf'] += 1
            elif best >= 0.3:
                stats['medium'] += 1
            else:
                stats['low'] += 1
        else:
            stats['none'] += 1
            result['best_match'] = None
            result['all_matches'] = []

        all_results.append(result)

        if (i + 1) % 500 == 0:
            print(f"  已处理 {i+1}/{test_limit} 条...")

    # Save JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Save summary CSV
    with open(summary_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['报告ID', '医生', '日期', '匹配模板数', '最佳匹配度',
                        '最佳模板编号', '最佳模板名称', '检查类型', '检查部位'])
        for r in all_results:
            bm = r.get('best_match') or {}
            writer.writerow([
                r['study_identity'], r['doctor'], r['date'],
                r['match_count'], r['best_score'],
                bm.get('rid'), bm.get('discname'),
                bm.get('viscname'), bm.get('modulename')
            ])

    # Save detail CSV
    with open(detail_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['报告ID', '医生', '匹配度', '匹配类型',
                        '模板编号', '模板名称', '检查类型', '检查部位',
                        '诊断关键词', '报告提示摘要'])
        for r in all_results:
            if r.get('all_matches'):
                for m in r['all_matches']:
                    writer.writerow([
                        r['study_identity'], r['doctor'], m['match_score'],
                        f"hint={m['hint_score']}/see={m['see_score']}",
                        m['rid'], m['discname'], m['viscname'], m['modulename'],
                        '; '.join(m['keyword_hits']),
                        r['report_hint'][:100]
                    ])

    # Print stats
    print(f"\n====== 匹配结果统计 ======")
    print(f"总报告数:     {stats['total']}")
    print(f"有匹配:       {stats['matched']} ({stats['matched']/stats['total']*100:.1f}%)")
    print(f"  └ 高置信度: {stats['high_conf']} (≥50%)")
    print(f"  └ 中等:     {stats['medium']} (30%-50%)")
    print(f"  └ 低:       {stats['low']} (15%-30%)")
    print(f"无匹配:       {stats['none']} ({stats['none']/stats['total']*100:.1f}%)")
    print(f"\n文件已保存:")
    print(f"  JSON: {output_path}")
    print(f"  CSV总结: {summary_path}")
    print(f"  CSV详情: {detail_path}")

    # Show examples
    print(f"\n====== 高匹配示例 ======")
    high = [r for r in all_results if r.get('best_match') and r['best_match']['match_score'] >= 0.5][:5]
    for r in high:
        bm = r['best_match']
        print(f"\n  报告: {r['study_identity']} | 医生: {r['doctor']}")
        print(f"  报告提示: {r['report_hint'][:100]}")
        print(f"  → 模板 #{bm['rid']}: {bm['discname']}")
        print(f"  匹配度: {bm['match_score']:.1%} (hint={bm['hint_score']:.1%}, see={bm['see_score']:.1%})")
        print(f"  检查类型: {bm['viscname']} | 部位: {bm['modulename']}")

    print(f"\n====== 未匹配示例 ======")
    no_match = [r for r in all_results if not r.get('all_matches')][:3]
    for r in no_match:
        print(f"\n  报告: {r['study_identity']} | 医生: {r['doctor']}")
        print(f"  提示: {r['report_hint'][:150]}")


if __name__ == '__main__':
    main()
