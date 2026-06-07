"""长沙客户数据转换工具 v2
将 1长沙范本.csv + 2报告内容.csv → 模板表.csv + 规则JSON

用法:
  python convert_changsha.py --preview   # 预览模式
  python convert_changsha.py --execute   # 执行转换，输出到 output/
"""
import csv
import re
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SRC_DIR = Path(r"C:\Users\Administrator\Desktop\超声结构化报告")
OUT_DIR = SRC_DIR / "output"


# ============================================================
# 1. 多行CSV解析器
# ============================================================
def parse_multiline_csv(filepath: str) -> list[dict]:
    """解析多行字段未引号包裹的CSV (长沙范本格式)"""
    with open(filepath, encoding='utf-8-sig') as f:
        raw = f.read()

    lines = raw.split('\n')
    records = []
    current = None
    for line in lines[1:]:
        line = line.rstrip('\r')
        if not line:
            continue
        m = re.match(r'^(\d{1,5}),(?=\D)', line)
        if m:
            if current:
                records.append(current)
            rid = m.group(1)
            rest = line[len(rid) + 1:]
            current = {'_rid': rid, '_lines': [rest]}
        else:
            if current:
                current['_lines'].append(line)
    if current:
        records.append(current)

    parsed = []
    for rec in records:
        full = '\n'.join(rec['_lines'])
        tail_match = re.search(
            r',(\d+),(\d+),([^,]*),(?:UIS|RTF),(\d+),([^,]*)(?:,NULL)*\s*$',
            full
        )
        if not tail_match:
            continue

        before_tail = full[:tail_match.start()]
        tail = {
            'IDX': tail_match.group(1),
            'VISCIDX': tail_match.group(2),
            'DISCGROUP': tail_match.group(3),
            'MODULENAME': 'UIS',
            'IDX_VISCGROUP': tail_match.group(4),
            'Buf1': tail_match.group(5),
            'Buf2': 'NULL', 'Buf3': 'NULL', 'Buf4': 'NULL',
        }

        parts = before_tail.split(',', 2)
        discname = parts[0].strip()
        viscname = parts[1] if len(parts) > 1 else ''
        info_content = parts[2] if len(parts) > 2 else ''

        row = {
            'RID': rec['_rid'],
            'DISCNAME': discname,
            'VISCNAME': viscname.strip(),
            'INFO1': info_content,
            'INFO2': '',
        }
        row.update(tail)
        parsed.append(row)

    return parsed


def parse_existing_template(filepath: str) -> list[dict]:
    """解析现有模板表 (带引号的多行CSV)"""
    with open(filepath, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)

    records = []
    with open(filepath, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 5:
                rid = row[0].strip()
                name = row[1].strip()
                if rid.isdigit() and name:
                    records.append({
                        'RID': rid,
                        'DISCNAME': name,
                        'VISCNAME': row[2].strip() if len(row) > 2 else '',
                        'INFO1': row[3] if len(row) > 3 else '',
                        'INFO2': row[4] if len(row) > 4 else '',
                        'IDX': row[5] if len(row) > 5 else '0',
                        'VISCIDX': row[6] if len(row) > 6 else '0',
                        'DISCGROUP': row[7] if len(row) > 7 else '',
                        'MODULENAME': row[8] if len(row) > 8 else 'UIS',
                        'IDX_VISCGROUP': row[9] if len(row) > 9 else '0',
                        'Buf1': row[10] if len(row) > 10 else 'NULL',
                        'Buf2': 'NULL', 'Buf3': 'NULL', 'Buf4': 'NULL',
                    })
    return records


# ============================================================
# 2. 合并模板
# ============================================================
def merge_templates(existing: list[dict], new: list[dict]) -> list[dict]:
    seen = {}
    merged = []
    max_rid = 0

    # 新范本优先
    for t in new:
        name = t['DISCNAME']
        if name and name not in seen:
            seen[name] = True
            merged.append(t)
            try:
                max_rid = max(max_rid, int(t['RID']))
            except ValueError:
                pass

    # 补充现有独有
    added = 0
    for t in existing:
        name = t.get('DISCNAME', '')
        if name and name not in seen:
            seen[name] = True
            max_rid += 1
            t['RID'] = str(max_rid)
            merged.append(t)
            added += 1

    return merged, added


def write_template_csv(templates: list[dict], filepath: str):
    """写入模板表CSV"""
    headers = ['RID', 'DISCNAME', 'VISCNAME', 'INFO1', 'INFO2',
               'IDX', 'VISCIDX', 'DISCGROUP', 'MODULENAME', 'IDX_VISCGROUP',
               'Buf1', 'Buf2', 'Buf3', 'Buf4']
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for t in templates:
            writer.writerow(t)


# ============================================================
# 3. 从真实报告提取规则
# ============================================================
def extract_rules(report_path: str) -> dict:
    """从2报告内容.csv提取规则数据"""
    # 报告CSV的DESCRIBES字段有引号包裹，用csv模块正确解析
    with open(report_path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # --- normal_kw: 阴性报告高频短语 ---
    normal_kw = Counter()
    abnormal_kw = Counter()

    # 已知的异常关键词种子
    abnormal_seeds = {'结石', '囊肿', '肌瘤', '息肉', '增生', '钙化', '结节',
                      '占位', '积液', '血栓', '狭窄', '扩张', '反流', '关闭不全',
                      '畸形', '肿瘤', '斑块', '团块', '肿物'}
    # 否定词 — 含这些的短语是正常发现，不应归入异常
    negation_words = ('未见', '未见明显', '无明显', '未探及', '未闻及', '未及')
    # 注意: "无" 和 "不" 太短，容易误匹配 (如 "无回声结节" 是异常不是正常)
    # 单独处理: 只有当 "无"/"不" 后面跟的是异常种子词时才视为否定
    # 轻微异常词 — 不应归入正常
    mild_abnormal = ('欠均匀', '欠光滑', '不均匀', '不光滑', '欠清晰', '欠完整', '不均匀')

    for r in rows:
        desc = (r.get('DESCRIBES') or '') + ' ' + (r.get('DIAGNOSIS') or '')
        result = (r.get('RESULTISPLUS') or '').strip()

        # 提取医学短语: 以异常种子词为核心，向前抓取上下文
        for seed in abnormal_seeds:
            for m in re.finditer(rf'([\u4e00-\u9fffa-zA-Z]{{0,6}}{re.escape(seed)})', desc):
                phrase = m.group(1)
                # 长否定词 (任意位置) → 正常发现
                has_negation = any(neg in phrase for neg in negation_words)
                # 短否定词: "不X"/"无X" — 但 "无回声*" 是超声术语(anechoic)，不算否定
                if not has_negation:
                    for short_neg in ('无', '不'):
                        idx = phrase.find(short_neg)
                        if idx >= 0:
                            after = phrase[idx + len(short_neg):]
                            if after.startswith('回声'):
                                continue  # "无回声结节" = 异常，不是正常
                            if after:
                                has_negation = True
                                break
                if has_negation:
                    normal_kw[phrase] += 1
                else:
                    abnormal_kw[phrase] += 1

        # 正常描述短语 (独立提取)
        for m in re.finditer(r'([\u4e00-\u9fff]{2,4}(?:正常|光滑|均匀|清晰|完整|不扩张|未见异常))', desc):
            phrase = m.group(1)
            # 排除轻微异常短语
            if not any(ma in phrase for ma in mild_abnormal):
                normal_kw[phrase] += 1

    # 过滤: 至少出现5次
    normal_kw_filtered = {k: v for k, v in normal_kw.most_common(50) if v >= 5}
    abnormal_kw_filtered = {k: v for k, v in abnormal_kw.most_common(50) if v >= 5}

    # --- cross_validation: 按检查类型统计正常模式 ---
    cv_data = defaultdict(list)
    normal_pattern_counter = defaultdict(Counter)

    # 检查类型映射
    viscera_map = {
        '腹部': ['肝胆', '腹部', '胰腺', '脾脏', '输尿管', '肝胰'],
        '心脏': ['心脏'],
        '甲状腺': ['甲状腺'],
        '乳腺': ['乳腺'],
        '前列腺': ['前列腺'],
        '膀胱': ['膀胱'],
        '颈动脉': ['颈动脉'],
        '子宫附件': ['子宫', '附件'],
    }

    for r in rows:
        desc = r.get('DESCRIBES') or ''
        visc = (r.get('VISCERAS') or '').strip()
        result = (r.get('RESULTISPLUS') or '').strip()

        if result != '阴性':
            continue

        # 确定检查类型
        exam_type = ''
        for et, keywords in viscera_map.items():
            if any(kw in visc for kw in keywords):
                exam_type = et
                break

        # 提取正常模式 (短句)
        patterns = re.findall(r'[一-鿿]{4,12}(?:正常|未见异常|未见明显异常|光滑|均匀|不扩张)', desc)
        for p in patterns:
            normal_pattern_counter[exam_type][p] += 1
            normal_pattern_counter[''][p] += 1  # 通用

    # 构建cross_validation结构
    for exam_type, counter in normal_pattern_counter.items():
        for pattern, count in counter.most_common(10):
            if count >= 3:
                cv_data[exam_type].append({'pattern': pattern, 'count': count})

    # --- site_disease: 从诊断短语提取 ---
    site_disease = defaultdict(dict)
    site_keywords = ['胆', '肝', '肾', '子宫', '卵巢', '膀胱', '前列腺', '胰', '脾',
                     '甲状', '乳腺', '颈动', '心']
    disease_keywords = ['结石', '囊肿', '肌瘤', '息肉', '增生', '钙化', '血管瘤',
                        '脂肪肝', '硬化', '积水', '畸胎瘤', '狭窄', '斑块', '血栓',
                        '结节', '积液', '腺肌', '炎', '大', '癌']

    for r in rows:
        diag = (r.get('DIAGNOSIS') or '').strip()
        for line in diag.split('\n'):
            line = line.strip().rstrip('。，,')
            if not (2 < len(line) < 25):
                continue
            for site in site_keywords:
                if site in line:
                    for dis in disease_keywords:
                        if dis in line:
                            site_disease[site][dis] = line
                            break
                    break

    # --- field_asr_hints: 从测量值提取 ---
    measurements_by_context = defaultdict(list)
    for r in rows:
        desc = r.get('DESCRIBES') or ''
        for m in re.finditer(r'([\u4e00-\u9fff]{2,6})(?:约|约\s*)(\d+(?:\.\d+)?)\s*(mm|cm)', desc):
            context = m.group(1)
            value = float(m.group(2))
            unit = m.group(3)
            measurements_by_context[context].append({'value': value, 'unit': unit})

    return {
        'normal_kw': sorted(normal_kw_filtered.keys()),
        'abnormal_kw': sorted(abnormal_kw_filtered.keys()),
        'cross_validation': dict(cv_data),
        'site_disease': {k: dict(v) for k, v in site_disease.items()},
        'measurement_stats': {
            'total': sum(len(v) for v in measurements_by_context.values()),
            'top_contexts': sorted(
                [(k, len(v)) for k, v in measurements_by_context.items()],
                key=lambda x: -x[1]
            )[:20],
        },
    }


# ============================================================
# 4. 主流程
# ============================================================
def main():
    execute = '--execute' in sys.argv

    print("=" * 70)
    print("  长沙客户数据转换工具 v2")
    print(f"  模式: {'执行' if execute else '预览'}")
    print("=" * 70)

    # 1. 解析长沙范本
    print("\n[1/4] 解析 1长沙范本.csv ...")
    new_templates = parse_multiline_csv(str(SRC_DIR / '1长沙范本.csv'))
    print(f"      → {len(new_templates)} 条模板")

    # 2. 解析现有模板
    print("\n[2/4] 解析现有模板表.csv ...")
    existing = parse_existing_template(str(SRC_DIR / '模板表.csv'))
    print(f"      → {len(existing)} 条模板")

    # 3. 合并
    print("\n[3/4] 合并模板 ...")
    merged, added = merge_templates(existing, new_templates)
    print(f"      新范本: {len(new_templates)} + 现有独有: {added} = 合并: {len(merged)}")

    # 分组统计
    groups = Counter(t['DISCGROUP'] for t in merged)
    print(f"      分组数: {len(groups)}")
    for g, c in groups.most_common(15):
        print(f"        {g or '(空)'}: {c}")

    # 4. 提取规则
    print("\n[4/4] 从 2报告内容.csv 提取规则 ...")
    rules = extract_rules(str(SRC_DIR / '2报告内容.csv'))
    print(f"      normal_kw: {len(rules['normal_kw'])} 个")
    print(f"      abnormal_kw: {len(rules['abnormal_kw'])} 个")
    print(f"      cross_validation: {len(rules['cross_validation'])} 类")
    print(f"      site_disease: {len(rules['site_disease'])} 部位")
    print(f"      测量值: {rules['measurement_stats']['total']} 个")

    if not execute:
        print("\n" + "=" * 70)
        print("  预览完成。加 --execute 参数执行实际文件生成")
        print("=" * 70)
        return

    # 写入文件
    OUT_DIR.mkdir(exist_ok=True)

    # 模板表
    out_template = OUT_DIR / '模板表_merged.csv'
    write_template_csv(merged, str(out_template))
    print(f"\n[OUTPUT] 模板表: {out_template} ({len(merged)} 条)")

    # normal_report_detection 规则
    norm_rule = {
        'normal_kw': rules['normal_kw'],
        'abnormal_kw': rules['abnormal_kw'],
    }
    out_norm = OUT_DIR / 'normal_report_detection.json'
    with open(out_norm, 'w', encoding='utf-8') as f:
        json.dump(norm_rule, f, ensure_ascii=False, indent=2)
    print(f"[OUTPUT] 正常报告检测: {out_norm}")

    # cross_validation
    out_cv = OUT_DIR / 'cross_validation_new.json'
    with open(out_cv, 'w', encoding='utf-8') as f:
        json.dump(rules['cross_validation'], f, ensure_ascii=False, indent=2)
    print(f"[OUTPUT] 交叉验证模式: {out_cv}")

    # site_disease
    out_sd = OUT_DIR / 'site_disease_new.json'
    with open(out_sd, 'w', encoding='utf-8') as f:
        json.dump(rules['site_disease'], f, ensure_ascii=False, indent=2)
    print(f"[OUTPUT] 部位-病变映射: {out_sd}")

    print(f"\n{'=' * 70}")
    print(f"  全部输出到: {OUT_DIR}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
