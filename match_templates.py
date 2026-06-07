"""
匹配长沙超声报告到模板
- 模板文件: 1长沙范本.csv (多行聚合一个模板)
- 报告文件: 长沙报告40W - 副本.csv (每条报告占5行)
- 输出: 匹配结果，包含模板编号、模板名称、模板内容、检查类型、检查部位
"""

import csv
import re
import json
from collections import OrderedDict

# ========== 1. 读取模板 ==========
def sg(val):
    """Safe str get - returns empty string if None"""
    return (val or '').strip()


def read_templates(template_path):
    """读取模板CSV，每个模板可能跨多行"""
    with open(template_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    templates = OrderedDict()
    current_rid = None

    for row in rows:
        rid = sg(row.get('RID'))
        discname = sg(row.get('DISCNAME'))

        # Detect if this is a new template (has RID + DISCNAME)
        if rid and discname:
            current_rid = rid
            templates[current_rid] = {
                'rid': rid,
                'discname': discname,
                'viscname': sg(row.get('VISCNAME')),
                'info1_parts': [],
                'info2': sg(row.get('INFO2')),
                'idx': sg(row.get('IDX')),
                'viscidx': sg(row.get('VISCIDX')),
                'discgroup': sg(row.get('DISCGROUP')),
                'modulename': sg(row.get('MODULENAME')),
                'idx_viscgroup': sg(row.get('IDX_VISCGROUP')),
            }

        # Add INFO1 text to current template
        if current_rid and current_rid in templates:
            info1 = sg(row.get('INFO1'))
            if info1:
                templates[current_rid]['info1_parts'].append(info1)

            # Update INFO2 if present (last row of template usually has it)
            info2 = sg(row.get('INFO2'))
            if info2:
                templates[current_rid]['info2'] = info2

            # Update other fields from the last row
            for field in ['IDX', 'VISCIDX', 'DISCGROUP', 'MODULENAME', 'IDX_VISCGROUP']:
                val = sg(row.get(field))
                if val:
                    templates[current_rid][field.lower()] = val

    # Build full text for each template
    for rid, tpl in templates.items():
        tpl['full_info1'] = '\n'.join(tpl['info1_parts'])
        # Clean RTF placeholders
        tpl['full_info1'] = clean_text(tpl['full_info1'])
        tpl['full_info2'] = clean_text(tpl['info2'])

    return templates


def clean_text(text):
    """清理文本 - 去除多余空白"""
    text = re.sub(r'\s+', '', text)
    return text


def normalize_for_match(text):
    """规范化文本用于匹配 - 移除数值、空格、特殊字符，保留中文和关键字"""
    if not text:
        return ''
    # 替换占位符和数值为统一标记
    text = re.sub(r'\d+\.?\d*\s*x\s*\d+\.?\d*\s*mm', ' __SIZE__ ', text)
    text = re.sub(r'\d+\.?\d*\s*x\s*\d+', ' __SIZE__ ', text)
    text = re.sub(r'\d+\.?\d*%', ' __PCT__ ', text)
    text = re.sub(r'\d+\.?\d*\s*mm', ' __MM__ ', text)
    text = re.sub(r'\d+\.?\d*\s*cm', ' __CM__ ', text)
    text = re.sub(r'\d+\.?\d*', ' __NUM__ ', text)
    # 只保留中文字符和关键标点
    text = re.sub(r'[^一-鿿，。：；！？、]', '', text)
    return text


def calculate_similarity(template_text, report_text):
    """计算两个文本的相似度 - 基于共同子串/字符重合度"""
    if not template_text or not report_text:
        return 0.0

    # 提取关键医学词组
    t_set = set()
    r_set = set()

    # 按句号分割
    t_sents = [s.strip() for s in re.split(r'[，。；]', template_text) if len(s.strip()) > 3]
    r_sents = [s.strip() for s in re.split(r'[，。；]', report_text) if len(s.strip()) > 3]

    if not t_sents or not r_sents:
        return 0.0

    # Jaccard相似度基于句子
    t_set = set(t_sents)
    r_set = set(r_sents)

    intersection = len(t_set & r_set)
    union = len(t_set | r_set)

    if union == 0:
        return 0.0

    return intersection / union


def calculate_char_similarity(template_text, report_text):
    """基于字符级重合度的相似度"""
    if not template_text or not report_text:
        return 0.0

    # 提取关键医学短语（3-gram以上）
    def extract_phrases(text, min_len=4, max_len=20):
        """提取文本中的所有连续子串"""
        text = re.sub(r'\s', '', text)
        phrases = set()
        for length in range(min_len, min_len + 5):
            for i in range(len(text) - length + 1):
                phrases.add(text[i:i+length])
        return phrases

    norm_t = normalize_for_match(template_text)
    norm_r = normalize_for_match(report_text)

    # 简单方法：最长公共子序列比例
    # 使用字符集合交集
    t_chars = set(norm_t)
    r_chars = set(norm_r)

    if not t_chars or not r_chars:
        return 0.0

    # 关键短语匹配
    t_phrases = extract_phrases(template_text)
    r_phrases = extract_phrases(report_text)

    if not t_phrases or not r_phrases:
        common_chars = len(t_chars & r_chars)
        return common_chars / max(len(t_chars), len(r_chars))

    common_phrases = t_phrases & r_phrases
    phrase_score = len(common_phrases) / max(len(t_phrases), len(r_phrases))

    return phrase_score


# ========== 2. 读取报告数据 ==========
def read_reports(report_path):
    """读取报告CSV，合并跨行的一条报告"""
    with open(report_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    reports = []
    current_report = None
    fieldnames = reader.fieldnames

    for row in rows:
        study_identity = sg(row.get('StudyIdentity'))

        # New report starts with StudyIdentity
        if study_identity:
            if current_report:
                reports.append(current_report)

            current_report = {
                'study_identity': study_identity,
                'disease_code': sg(row.get('DiseaseCode')),
                'last_update': sg(row.get('LastUpdate')),
                'last_study_doctor': sg(row.get('LastStudyDoctor')),
                'result_comments': sg(row.get('ResultComments')),
                'f_ReportHintInfo': sg(row.get('F_ReportHintInfo')),
                'f_ControlValue': sg(row.get('F_ControlValue')),
                'study_see_parts': [],
                'study_hint': sg(row.get('StudyHint')),
                'surgery_process': sg(row.get('SurgeryProcess')),
                'pathology_diagnose': sg(row.get('PathologyDiagnose')),
                'study_see_xml': sg(row.get('StudySeeXml')),
                'study_hind_xml': sg(row.get('StudyHindXml')),
                'study_see_rtf': sg(row.get('StudySeeRtf')),
                'study_hint_rtf': sg(row.get('StudyHintRtf')),
            }

        # Add StudySee parts
        if current_report:
            study_see = sg(row.get('StudySee'))
            if study_see:
                current_report['study_see_parts'].append(study_see)

            study_hint = sg(row.get('StudyHint'))
            if study_hint and study_hint != current_report['study_hint']:
                current_report['study_hint'] += '\n' + study_hint if current_report['study_hint'] else study_hint

    if current_report:
        reports.append(current_report)

    # Build full text for each report
    for r in reports:
        r['full_study_see'] = '\n'.join(r['study_see_parts'])
        r['full_study_see_clean'] = clean_text(r['full_study_see'])
        r['full_study_hint_clean'] = clean_text(r['study_hint'])

    return reports


# ========== 3. 匹配报告到模板 ==========
def match_report_to_template(report, templates, threshold=0.1):
    """将一条报告匹配到最相似的模板"""
    report_see = report.get('full_study_see_clean', '')
    report_hint = report.get('full_study_hint_clean', '')

    if not report_see:
        return None, 0.0

    best_match = None
    best_score = 0.0

    for rid, tpl in templates.items():
        # Combined score: INFO1 text match + INFO2 hint match
        see_sim = calculate_similarity(tpl['full_info1'], report_see)

        hint_sim = 0.0
        if tpl['full_info2'] and report_hint:
            hint_sim = calculate_similarity(tpl['full_info2'], report_hint)

        # Weighted score: 70% from study see text, 30% from study hint
        score = see_sim * 0.7 + hint_sim * 0.3

        if score > best_score:
            best_score = score
            best_match = tpl

    if best_score < threshold:
        return None, best_score

    return best_match, best_score


# ========== Main ==========
def main():
    template_path = r'C:\Users\Administrator\Desktop\超声结构化报告\1长沙范本.csv'
    report_path = r'C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W - 副本.csv'
    output_path = r'C:\Users\Administrator\Desktop\超声结构化报告\matched_reports.json'
    summary_path = r'C:\Users\Administrator\Desktop\超声结构化报告\matching_summary.csv'

    print("读取模板...")
    templates = read_templates(template_path)
    print(f"  共读取 {len(templates)} 个模板")

    print("读取报告...")
    reports = read_reports(report_path)
    print(f"  共读取 {len(reports)} 条报告")

    # Limit for testing
    test_limit = min(500, len(reports))

    print(f"\n开始匹配前 {test_limit} 条报告...")
    results = []
    match_stats = {
        'total': 0,
        'matched': 0,
        'unmatched': 0,
        'score_distribution': {f'{i/10:.1f}-{(i+1)/10:.1f}': 0 for i in range(10)}
    }

    for i, report in enumerate(reports[:test_limit]):
        matched_tpl, score = match_report_to_template(report, templates)

        match_stats['total'] += 1

        result = {
            'study_identity': report['study_identity'],
            'doctor': report['last_study_doctor'],
            'date': report['last_update'],
            'match_score': round(score, 4),
            'matched_template_id': matched_tpl['rid'] if matched_tpl else None,
            'matched_template_name': matched_tpl['discname'] if matched_tpl else None,
            'matched_template_viscname': matched_tpl['viscname'] if matched_tpl else None,
            'matched_template_modulename': matched_tpl['modulename'] if matched_tpl else None,
            'matched_template_info1': matched_tpl['full_info1'][:200] if matched_tpl else '',
            'matched_template_info2': matched_tpl['full_info2'][:200] if matched_tpl else '',
            'report_study_see': report['full_study_see_clean'][:300],
            'report_study_hint': report['full_study_hint_clean'][:300],
        }
        results.append(result)

        if matched_tpl and score > 0.15:
            match_stats['matched'] += 1
            for j in range(10):
                if j/10 <= score < (j+1)/10:
                    match_stats['score_distribution'][f'{j/10:.1f}-{(j+1)/10:.1f}'] += 1
                    break
        else:
            match_stats['unmatched'] += 1

        if (i + 1) % 100 == 0:
            print(f"  已处理 {i+1}/{test_limit} 条...")

    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Save summary CSV
    with open(summary_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['报告ID', '医生', '日期', '匹配度', '模板编号', '模板名称', '检查类型', '检查部位'])
        for r in results:
            writer.writerow([
                r['study_identity'], r['doctor'], r['date'],
                r['match_score'], r['matched_template_id'],
                r['matched_template_name'], r['matched_template_viscname'],
                r['matched_template_modulename']
            ])

    # Print stats
    print(f"\n===== 匹配完成 =====")
    print(f"总报告数: {match_stats['total']}")
    print(f"成功匹配: {match_stats['matched']}")
    print(f"未匹配: {match_stats['unmatched']}")
    print(f"匹配率: {match_stats['matched']/match_stats['total']*100:.1f}%")
    print(f"\n得分分布:")
    for k, v in sorted(match_stats['score_distribution'].items()):
        if v > 0:
            print(f"  {k}: {v}条")

    print(f"\n结果已保存:")
    print(f"  JSON: {output_path}")
    print(f"  CSV:  {summary_path}")

    # Show some examples
    print(f"\n===== 匹配示例 =====")
    high_score = [r for r in results if r['match_score'] > 0.5][:5]
    for r in high_score:
        print(f"\n  报告ID: {r['study_identity']}")
        print(f"  医生: {r['doctor']}")
        print(f"  匹配模板: [{r['matched_template_id']}] {r['matched_template_name']}")
        print(f"  匹配度: {r['match_score']:.2%}")
        print(f"  检查类型: {r['matched_template_viscname']}")
        print(f"  检查部位: {r['matched_template_modulename']}")


if __name__ == '__main__':
    main()
