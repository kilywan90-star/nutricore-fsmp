"""
长沙超声报告模板匹配 v3 - 智能匹配
关键改进：
1. 自定义CSV解析器，正确处理RTF内容
2. 多策略匹配：诊断名、模板名、文本内容
3. 支持组合诊断（一条报告可能匹配多个模板）
"""

import csv
import re
import json
from collections import OrderedDict


def sg(val):
    return (val or '').strip()


# ========== 自定义CSV解析 ==========
def smart_parse_csv(filepath):
    """
    智能解析：报告行以数字StudyIdentity开头，RTF行以{rtf或}开头
    合并多行到一条记录
    """
    fieldnames = None
    records = []
    current_record = None
    line_count = 0
    report_count = 0

    # 先读字段名
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        field_line = f.readline().strip()
        # CSV可能有BOM，清理
        field_line = field_line.lstrip('﻿')
        # 标准CSV解析字段名
        fieldnames = [sg(fn.strip('"')) for fn in field_line.split(',')]

    print(f"  字段名: {fieldnames}")
    print(f"  字段数: {len(fieldnames)}")

    # 使用Python csv模块，但处理它的输出
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # skip header

        for row in reader:
            line_count += 1
            if not row or len(row) < 2:
                continue

            col0 = sg(row[0])

            # 新报告：StudyIdentity是纯数字（不是RTF内容）
            if re.match(r'^\d{10,}$', col0) and len(col0) >= 10:
                if current_record:
                    records.append(current_record)
                report_count += 1

                current_record = {}
                for i, fn in enumerate(fieldnames):
                    if i < len(row):
                        current_record[fn] = sg(row[i])
                    else:
                        current_record[fn] = ''
                # 初始化收集器
                current_record['_see_parts'] = []
                current_record['_hint_parts'] = []
                current_record['_see_rtf_parts'] = []
                current_record['_hint_rtf_parts'] = []
                # 添加初始StudySee/StudyHint
                study_see = sg(row[min(7, len(row)-1)]) if len(row) > 7 else ''
                if study_see:
                    current_record['_see_parts'].append(study_see)
                study_hint = sg(row[min(8, len(row)-1)]) if len(row) > 8 else ''
                if study_hint:
                    current_record['_hint_parts'].append(study_hint)

            elif current_record is not None:
                # 续行 - 追加内容
                study_see = sg(row[min(7, len(row)-1)]) if len(row) > 7 else ''
                if study_see and not study_see.startswith('{\\rtf'):
                    current_record['_see_parts'].append(study_see)

                study_hint = sg(row[min(8, len(row)-1)]) if len(row) > 8 else ''
                if study_hint and not study_hint.startswith('{\\rtf'):
                    current_record['_hint_parts'].append(study_hint)

                # 收集RTF
                for i, fn in enumerate(fieldnames):
                    if i < len(row):
                        val = row[i]
                        if val.startswith('{\\rtf') or val.startswith('\\rtf'):
                            if fn == 'StudySeeXml' or fn == 'StudySeeRtf':
                                current_record['_see_rtf_parts'].append(val)
                            elif fn == 'StudyHindXml' or fn == 'StudyHintRtf':
                                current_record['_hint_rtf_parts'].append(val)

    if current_record:
        records.append(current_record)

    print(f"  总行数: {line_count}")
    print(f"  解析出报告数: {len(records)}")

    return records


def clean_report_text(parts):
    """合并并清理报告文本"""
    text = '\n'.join(parts)
    # 清理多余的空白
    text = re.sub(r'\s+', '', text)
    return text


# ========== 读取模板 ==========
def read_templates(template_path):
    with open(template_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    templates = OrderedDict()
    current_rid = None

    for row in rows:
        rid = sg(row.get('RID', ''))
        discname = sg(row.get('DISCNAME', ''))

        if rid and discname:
            current_rid = rid
            templates[current_rid] = {
                'rid': rid,
                'discname': discname,
                'viscname': sg(row.get('VISCNAME', '')),
                'info1_parts': [],
                'info2': sg(row.get('INFO2', '')),
                'modulename': sg(row.get('MODULENAME', '')),
                'discgroup': sg(row.get('DISCGROUP', '')),
            }

        if current_rid and current_rid in templates:
            info1 = sg(row.get('INFO1', ''))
            if info1:
                templates[current_rid]['info1_parts'].append(info1)
            info2 = sg(row.get('INFO2', ''))
            if info2:
                templates[current_rid]['info2'] = info2

    # 构建全文
    for tpl in templates.values():
        tpl['full_info1'] = clean_report_text(tpl['info1_parts'])
        tpl['clean_info2'] = clean_report_text([tpl['info2']])

    return templates


# ========== 匹配策略 ==========
def match_report(record, templates):
    """将一条报告匹配到模板"""
    # 解析报告数据
    study_see = clean_report_text(record.get('_see_parts', []))
    study_hint = clean_report_text(record.get('_hint_parts', []))
    doctor = sg(record.get('LastStudyDoctor', ''))

    matches = []

    for rid, tpl in templates.items():
        hint_score = 0.0
        see_score = 0.0
        name_score = 0.0
        match_detail = []

        tpl_info2 = tpl['clean_info2']
        tpl_info1 = tpl['full_info1']
        tpl_name = clean_report_text([tpl['discname']])
        tpl_viscname = tpl['viscname']

        # === 策略A: 模板诊断(INFO2)匹配报告提示(StudyHint) ===
        if tpl_info2 and study_hint:
            # 精确子串匹配
            if tpl_info2 in study_hint:
                hint_score = 1.0
                match_detail.append(f"hint_exact")
            else:
                # 关键词匹配：按标点分割比较段落
                tpl_phrases = re.split(r'[，。；：、]', tpl_info2)
                tpl_phrases = [p for p in tpl_phrases if len(p) >= 3]
                if tpl_phrases:
                    hits = sum(1 for p in tpl_phrases if p in study_hint)
                    hint_score = hits / len(tpl_phrases)

        # === 策略B: 模板名(DISCNAME)匹配报告提示 ===
        if study_hint:
            # 模板名去掉括号备注
            name_clean = re.sub(r'[（(][^）)]*[）)]', '', tpl_name)
            if name_clean and name_clean in study_hint:
                name_score = 0.8
                match_detail.append(f"name_in_hint")
            elif name_clean:
                # 模板名的关键词
                name_kws = set(re.split(r'[，。；：、／]', name_clean))
                name_kws = {k for k in name_kws if len(k) >= 2}
                if name_kws:
                    hits = sum(1 for kw in name_kws if kw in study_hint)
                    if name_kws:
                        name_score = hits / len(name_kws) * 0.8

        # === 策略C: 模板内容(INFO1)匹配报告所见(StudySee) ===
        # 将模板内容按句分割
        tpl_sents = [s.strip() for s in re.split(r'[。\n]', tpl_info1) if len(s.strip()) > 8]
        if tpl_sents and study_see:
            hits = sum(1 for s in tpl_sents if s in study_see)
            see_score = hits / len(tpl_sents)
            if see_score > 0.3:
                match_detail.append(f"see_sent:{hits}/{len(tpl_sents)}")

        # === 组合评分 ===
        combined = hint_score * 0.4 + see_score * 0.3 + name_score * 0.3

        if combined >= 0.2:
            matches.append({
                'rid': tpl['rid'],
                'discname': tpl['discname'],
                'viscname': tpl_viscname,
                'modulename': tpl['modulename'],
                'discgroup': tpl['discgroup'],
                'score': round(combined, 4),
                'hint_score': round(hint_score, 4),
                'see_score': round(see_score, 4),
                'name_score': round(name_score, 4),
                'detail': match_detail,
            })

    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:10]


# ========== Main ==========
def main():
    template_path = r'C:\Users\Administrator\Desktop\超声结构化报告\1长沙范本.csv'
    report_path = r'C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W - 副本.csv'
    output_csv = r'C:\Users\Administrator\Desktop\超声结构化报告\matching_result_v3.csv'

    print("=== 读取模板 ===")
    templates = read_templates(template_path)
    print(f"  共 {len(templates)} 个模板")

    print("\n=== 解析报告CSV ===")
    records = smart_parse_csv(report_path)
    print(f"  成功解析 {len(records)} 条报告")

    # 全量处理
    print(f"\n=== 开始匹配 ===")
    total = len(records)
    results = []
    stats = {'total': total, 'matched': 0, 'high': 0, 'medium': 0, 'low': 0, 'none': 0}

    for i, rec in enumerate(records):
        study_id = sg(rec.get('StudyIdentity', ''))
        doctor = sg(rec.get('LastStudyDoctor', ''))
        date = sg(rec.get('LastUpdate', ''))
        study_hint = clean_report_text(rec.get('_hint_parts', []))
        study_see = clean_report_text(rec.get('_see_parts', []))

        matches = match_report(rec, templates)

        best = matches[0] if matches else None
        best_score = best['score'] if best else 0

        if best and best_score >= 0.2:
            stats['matched'] += 1
            if best_score >= 0.5:
                stats['high'] += 1
            elif best_score >= 0.3:
                stats['medium'] += 1
            else:
                stats['low'] += 1
        else:
            stats['none'] += 1

        results.append({
            'study_id': study_id,
            'doctor': doctor,
            'date': date,
            'hint_excerpt': study_hint[:200],
            'see_excerpt': study_see[:200],
            'has_hint': bool(study_hint),
            'has_see': bool(study_see),
            'best_score': best_score,
            'best_rid': best['rid'] if best else '',
            'best_name': best['discname'] if best else '',
            'best_viscname': best['viscname'] if best else '',
            'best_modulename': best['modulename'] if best else '',
            'match_count': len(matches),
        })

        if (i + 1) % 50000 == 0:
            print(f"  已处理 {i+1}/{total} 条...")

    # ====== 输出CSV ======
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            '报告ID', '医生', '日期', '匹配度',
            '模板编号', '模板名称', '检查类型', '检查部位',
            '有提示', '有描述', '匹配模板数', '报告提示摘要'
        ])
        for r in results:
            writer.writerow([
                r['study_id'], r['doctor'], r['date'],
                r['best_score'],
                r['best_rid'], r['best_name'],
                r['best_viscname'], r['best_modulename'],
                r['has_hint'], r['has_see'],
                r['match_count'],
                r['hint_excerpt'][:100],
            ])

    # ====== 统计 ======
    has_hint_count = sum(1 for r in results if r['has_hint'])
    has_see_count = sum(1 for r in results if r['has_see'])

    print(f"\n{'='*50}")
    print(f"匹配完成！统计结果：")
    print(f"{'='*50}")
    print(f"总报告数:     {stats['total']}")
    print(f"有StudyHint:  {has_hint_count} ({has_hint_count/stats['total']*100:.1f}%)")
    print(f"有StudySee:   {has_see_count} ({has_see_count/stats['total']*100:.1f}%)")
    print(f"---")
    print(f"有匹配:       {stats['matched']} ({stats['matched']/stats['total']*100:.1f}%)")
    print(f"  高置信度:   {stats['high']} (≥50%)")
    print(f"  中等:       {stats['medium']} (30%-50%)")
    print(f"  低:         {stats['low']} (20%-30%)")
    print(f"无匹配:       {stats['none']} ({stats['none']/stats['total']*100:.1f}%)")
    print(f"\n输出文件: {output_csv}")

    # 部分示例
    print(f"\n{'='*50}")
    print(f"高匹配示例：")
    high = [r for r in results if r['best_score'] >= 0.5][:10]
    for r in high:
        print(f"  [ID:{r['study_id'][:8]}..] {r['doctor']} | "
              f"匹配度:{r['best_score']:.0%} → #{r['best_rid']} {r['best_name']}")

    print(f"\n{'='*50}")
    print(f"未匹配但有StudyHint的示例：")
    no_match = [r for r in results if r['best_score'] < 0.2 and r['has_hint']][:5]
    for r in no_match:
        print(f"  [ID:{r['study_id'][:8]}..] {r['doctor']} | "
              f"提示:{r['hint_excerpt'][:80]}")


if __name__ == '__main__':
    main()
