"""
高效匹配长沙超声报告到模板 v4
- 逐行流式解析（不用csv模块，更快）
- 准确的报告分割
- 多策略匹配
"""

import re
import json
from collections import OrderedDict

# ========== 1. 流式解析报告CSV ==========
def parse_reports_fast(filepath):
    """
    流式解析：根据StudyIdentity分割报告
    每行用 | 分割（实际查看数据发现用TAB不一致，这里用逗号分割）
    """
    # 先读表头
    reports = []
    current_report = None
    total_lines = 0
    report_count = 0

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        header_line = f.readline().strip()
        # 简单解析表头（按逗号，处理引号）
        headers = parse_csv_line(header_line)
        # 确定关键列索引
        see_idx = -1
        hint_idx = -1
        id_idx = -1
        doctor_idx = -1
        date_idx = -1

        for i, h in enumerate(headers):
            h = h.strip().strip('"')
            if h == 'StudySee':
                see_idx = i
            elif h == 'StudyHint':
                hint_idx = i
            elif h == 'StudyIdentity':
                id_idx = i
            elif h == 'LastStudyDoctor':
                doctor_idx = i
            elif h == 'LastUpdate':
                date_idx = i

        print(f"  列索引: ID={id_idx}, See={see_idx}, Hint={hint_idx}, Doctor={doctor_idx}")

        # 逐行处理
        for line in f:
            total_lines += 1
            line = line.rstrip('\n\r')

            if not line:
                continue

            # 简单按逗号分割（处理7M行，不用csv模块）
            cols = parse_csv_line(line)
            col0 = cols[0].strip('" ') if cols else ''

            # 新报告判定：第一列是纯数字（StudyIdentity）
            # 长度至少10位的数字
            if re.match(r'^\d{15,}$', col0):
                if current_report:
                    reports.append(finalize_report(current_report))
                    report_count += 1

                current_report = {
                    'study_id': col0,
                    'doctor': get_col(cols, doctor_idx).strip('" '),
                    'date': get_col(cols, date_idx).strip('" '),
                    'see_parts': [],
                    'hint_parts': [],
                }

                # 添加当前行的数据
                see_val = get_col(cols, see_idx).strip('" ')
                if see_val and not see_val.startswith('{\\rtf'):
                    current_report['see_parts'].append(see_val)
                hint_val = get_col(cols, hint_idx).strip('" ')
                if hint_val and not hint_val.startswith('{\\rtf'):
                    current_report['hint_parts'].append(hint_val)

            elif current_report is not None:
                # 续行：追加See和Hint
                see_val = get_col(cols, see_idx).strip('" ')
                if see_val and not see_val.startswith('{\\rtf') and not see_val.startswith('\\rtf'):
                    current_report['see_parts'].append(see_val)
                hint_val = get_col(cols, hint_idx).strip('" ')
                if hint_val and not hint_val.startswith('{\\rtf') and not hint_val.startswith('\\rtf'):
                    current_report['hint_parts'].append(hint_val)

            if total_lines % 500000 == 0:
                print(f"  扫描 {total_lines} 行... 已找到 {report_count} 条报告")

    # 最后一条
    if current_report:
        reports.append(finalize_report(current_report))
        report_count += 1

    print(f"  总行数: {total_lines}, 报告数: {report_count}")
    return reports


def parse_csv_line(line):
    """简化CSV行分割 - 处理引号内的逗号"""
    cols = []
    current = ''
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            current += ch
        elif ch == ',' and not in_quotes:
            cols.append(current)
            current = ''
        else:
            current += ch
    cols.append(current)
    return cols


def get_col(cols, idx):
    """安全获取列"""
    if 0 <= idx < len(cols):
        return cols[idx]
    return ''


def finalize_report(rep):
    """完成报告数据整理"""
    see_text = '\n'.join(rep['see_parts'])
    hint_text = '\n'.join(rep['hint_parts'])

    # 清理
    see_text = re.sub(r'\s+', '', see_text)
    hint_text = re.sub(r'\s+', '', hint_text)

    rep['full_see'] = see_text
    rep['full_hint'] = hint_text
    return rep


# ========== 2. 读取模板 ==========
def read_templates(filepath):
    """读取范本CSV - 简单解析"""
    templates = OrderedDict()
    current_rid = None

    # 读字段名
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        header_line = f.readline().strip()
        headers = parse_csv_line(header_line)
        headers = [h.strip().strip('"') for h in headers]

        # 找列索引
        rid_idx = next(i for i, h in enumerate(headers) if h == 'RID')
        name_idx = next(i for i, h in enumerate(headers) if h == 'DISCNAME')
        visc_idx = next(i for i, h in enumerate(headers) if h == 'VISCNAME')
        info1_idx = next(i for i, h in enumerate(headers) if h == 'INFO1')
        info2_idx = next(i for i, h in enumerate(headers) if h == 'INFO2')
        mod_idx = next(i for i, h in enumerate(headers) if h == 'MODULENAME')
        dg_idx = next(i for i, h in enumerate(headers) if h == 'DISCGROUP')

        # 逐行处理
        for line in f:
            line = line.rstrip('\n\r')
            if not line:
                continue
            cols = parse_csv_line(line)
            rid = get_col(cols, rid_idx).strip('" ')
            discname = get_col(cols, name_idx).strip('" ')

            if rid and discname:
                current_rid = rid
                templates[current_rid] = {
                    'rid': rid,
                    'discname': discname,
                    'viscname': get_col(cols, visc_idx).strip('" '),
                    'info1_parts': [],
                    'info2': get_col(cols, info2_idx).strip('" '),
                    'modulename': get_col(cols, mod_idx).strip('" '),
                    'discgroup': get_col(cols, dg_idx).strip('" '),
                }

            if current_rid and current_rid in templates:
                info1 = get_col(cols, info1_idx).strip('" ')
                if info1:
                    templates[current_rid]['info1_parts'].append(info1)
                info2 = get_col(cols, info2_idx).strip('" ')
                if info2:
                    templates[current_rid]['info2'] = info2

    # 构建全文
    for tpl in templates.values():
        full_info1 = ''.join(tpl['info1_parts'])
        full_info2 = tpl['info2']
        tpl['full_info1'] = re.sub(r'\s+', '', full_info1)
        tpl['full_info2'] = re.sub(r'\s+', '', full_info2)

    return templates


# ========== 3. 匹配策略 ==========
def match_report(report, templates):
    """匹配一条报告到模板"""
    see = report['full_see']
    hint = report['full_hint']

    matches = []

    for rid, tpl in templates.items():
        # 评分维度
        hint_match = 0.0
        see_match = 0.0
        name_match = 0.0

        # A: 诊断结论匹配 (INFO2 vs StudyHint)
        tpl_i2 = tpl['full_info2']
        if tpl_i2 and hint:
            if tpl_i2 in hint:
                hint_match = 1.0
            else:
                # 分段匹配
                parts = [p for p in re.split(r'[，。；]', tpl_i2) if len(p) >= 3]
                if parts:
                    hits = sum(1 for p in parts if p in hint)
                    hint_match = hits / len(parts)

        # B: 模板名匹配模板名 vs StudyHint
        tpl_name = re.sub(r'\s', '', tpl['discname'])
        if hint:
            # 去掉括号备注比较核心名
            core_name = re.sub(r'[（(][^）)]*[）)]', '', tpl_name)
            # 多个关键词匹配
            name_parts = [p for p in re.split(r'[、／]', core_name) if len(p) >= 2]
            if name_parts:
                hits = sum(1 for p in name_parts if p in hint)
                name_match = hits / len(name_parts) * 0.8
            elif core_name and core_name in hint:
                name_match = 0.8

        # C: 文本内容匹配 (INFO1 vs StudySee)
        tpl_i1 = tpl['full_info1']
        if tpl_i1 and see:
            # 按句子匹配
            sents = [s for s in re.split(r'[。\n]', tpl_i1) if len(s) >= 10]
            if sents:
                hits = sum(1 for s in sents if s in see)
                see_match = hits / len(sents)

            # 如果句子级匹配不够，试试分段
            if see_match < 0.3:
                para = [p for p in tpl['info1_parts'] if len(p) >= 10]
                if para:
                    # 清理后的段落
                    clean_para = [re.sub(r'\s+', '', p) for p in para]
                    hits = sum(1 for p in clean_para if p in see)
                    see_match = max(see_match, hits / len(para) * 0.9)

        # 组合分
        combined = hint_match * 0.5 + see_match * 0.3 + name_match * 0.2

        if combined >= 0.2:
            matches.append({
                'rid': rid,
                'discname': tpl['discname'],
                'viscname': tpl['viscname'],
                'modulename': tpl['modulename'],
                'discgroup': tpl['discgroup'],
                'score': round(combined, 4),
                'hint_score': round(hint_match, 4),
                'see_score': round(see_match, 4),
                'name_score': round(name_match, 4),
            })

    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:5]


# ========== Main ==========
def main():
    template_path = r'C:\Users\Administrator\Desktop\超声结构化报告\1长沙范本.csv'
    report_path = r'C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W - 副本.csv'
    output_csv = r'C:\Users\Administrator\Desktop\超声结构化报告\matching_result_v4.csv'

    print("=== 读取模板 ===")
    templates = read_templates(template_path)
    print(f"  共 {len(templates)} 个模板")

    print("\n=== 解析报告（流式）===")
    reports = parse_reports_fast(report_path)
    print(f"  共 {len(reports)} 条报告")

    print("\n=== 开始匹配 ===")
    total = len(reports)

    # 统计
    stats = {
        'total': total,
        'has_hint': 0, 'has_see': 0,
        'matched': 0, 'high': 0, 'medium': 0, 'low': 0, 'none': 0
    }

    # 输出
    f_out = open(output_csv, 'w', encoding='utf-8-sig', newline='')
    writer = csv.writer(f_out)
    writer.writerow([
        '报告ID', '医生', '日期',
        '匹配度', '模板编号', '模板名称', '检查类型', '检查部位',
        '报告提示摘要', '匹配详情'
    ])

    for i, rep in enumerate(reports):
        matches = match_report(rep, templates)
        best = matches[0] if matches else None
        best_score = best['score'] if best else 0

        # 统计
        stats['has_hint'] += 1 if rep['full_hint'] else 0
        stats['has_see'] += 1 if rep['full_see'] else 0
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

        # 写入
        detail = '; '.join([f"#{m['rid']}{m['discname'][:10]}({m['score']:.0%})" for m in matches[:3]]) if matches else ''
        writer.writerow([
            rep['study_id'], rep['doctor'], rep['date'],
            best_score,
            best['rid'] if best else '',
            best['discname'] if best else '',
            best['viscname'] if best else '',
            best['modulename'] if best else '',
            rep['full_hint'][:100],
            detail,
        ])

        if (i + 1) % 100000 == 0:
            print(f"  已处理 {i+1}/{total} 条... "
                  f"匹配:{stats['matched']}/{stats['high']}高/{stats['medium']}中/{stats['low']}低 "
                  f"未匹配:{stats['none']}")

    f_out.close()

    print(f"\n{'='*50}")
    print(f"匹配完成！统计结果：")
    print(f"{'='*50}")
    print(f"总报告数:     {stats['total']}")
    print(f"有StudyHint:  {stats['has_hint']} ({stats['has_hint']/max(1,stats['total'])*100:.1f}%)")
    print(f"有StudySee:   {stats['has_see']} ({stats['has_see']/max(1,stats['total'])*100:.1f}%)")
    print(f"有匹配(≥20%): {stats['matched']} ({stats['matched']/max(1,stats['total'])*100:.1f}%)")
    print(f"  高置信度:   {stats['high']} (≥50%)")
    print(f"  中等:       {stats['medium']} (30%-50%)")
    print(f"  低:         {stats['low']} (20%-30%)")
    print(f"无匹配:       {stats['none']} ({stats['none']/max(1,stats['total'])*100:.1f}%)")
    print(f"\n输出: {output_csv}")


if __name__ == '__main__':
    # 需要在顶部 import csv（因为上面用了csv.writer）
    import csv
    main()
