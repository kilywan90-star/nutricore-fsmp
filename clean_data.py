"""
清洗数据：全字段40万-matching_result_full.csv
"""
import csv, os, re, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'C:\Users\Administrator\Desktop\全字段40万-matching_result_full.csv'
DST = r'C:\Users\Administrator\Desktop\全字段40万-matching_result_full_clean.csv'
LOG = r'C:\Users\Administrator\Desktop\清洗报告_全字段40万.txt'

print(f'读取文件: {SRC}')
lines_orig = sum(1 for _ in open(SRC, 'r', encoding='utf-8-sig'))
print(f'总行数(含表头): {lines_orig}')

with open(SRC, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    rows = list(reader)

print(f'数据行: {len(rows)}, 列: {len(cols)}')
print(f'字段列表:')
for i, c in enumerate(cols):
    print(f'  [{i:>2}] {c}')

# ======= 统计脏数据 =======
logs = []
logs.append(f'清洗前总行数: {len(rows)}')
logs.append(f'总列数: {len(cols)}')
logs.append('')

# 1. 统计 NULL/空值
null_log = ['=== NULL/空值统计 ===']
for c in cols:
    nulls = sum(1 for r in rows if r.get(c,'').strip() in ('NULL','null','Null',''))
    empties = sum(1 for r in rows if not r.get(c,'').strip())
    if nulls > 0 or empties > 0:
        null_log.append(f'  {c:<32} NULL值={nulls:>7}({nulls/len(rows)*100:>5.1f}%)  空值={empties:>7}')

logs.append('\n'.join(null_log))
logs.append('')

# 2. 统计 NULL > 90% 的列（冗余列）
redundant_cols = [c for c in cols if sum(1 for r in rows if not r.get(c,'').strip()) > len(rows) * 0.9]
logs.append(f'高稀疏列(空值>90%): {redundant_cols}')
logs.append('')

# 3. 检查 StudySee_Full 是否包含 StudySee
contains = sum(1 for r in rows if r.get('rpt_StudySee','').strip() and r['rpt_StudySee'].strip() in r.get('rpt_StudySee_Full',''))
logs.append(f'StudySee 包含在 StudySee_Full: {contains}/{len(rows)}')

# 4. tpl_INFO1 前引号问题
has_lead_quote = sum(1 for r in rows if r.get('tpl_INFO1','').startswith('"'))
logs.append(f'tpl_INFO1 以引号开头: {has_lead_quote}')

# 5. 评分分布
score_dist = Counter()
for r in rows:
    try:
        s = float(r.get('match_score', 0) or 0)
        if s >= 0.8: score_dist['>=0.8'] += 1
        elif s >= 0.5: score_dist['0.5-0.8'] += 1
        elif s >= 0.3: score_dist['0.3-0.5'] += 1
        elif s >= 0.2: score_dist['0.2-0.3'] += 1
        else: score_dist['<0.2'] += 1
    except:
        score_dist['parse_err'] += 1

logs.append('\n=== 匹配度分布 ===')
for k in ['>=0.8','0.5-0.8','0.3-0.5','0.2-0.3','<0.2','parse_err']:
    if k in score_dist:
        logs.append(f'  {k:<10} {score_dist[k]:>7} ({score_dist[k]/len(rows)*100:.1f}%)')

# ======= 执行清洗 =======
clean = []
stats = Counter()
for i, r in enumerate(rows):
    row = {}
    for c in cols:
        val = r.get(c, '')

        # NULL字符串 → 空
        if val.strip() in ('NULL', 'null', 'Null'):
            val = ''

        # tpl_INFO1 去前后引号
        if c == 'tpl_INFO1':
            # 去除CSV裹的引号
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                val = val[1:-1]
                stats['tpl_INFO1_unquote'] += 1

        # 去除首尾空白
        val = val.strip()

        # StudyHint_Full 如果为空且 StudyHint 有值，用 StudyHint 补
        if c == 'rpt_StudyHint_Full' and not val:
            hint = r.get('rpt_StudyHint', '').strip()
            if hint and hint not in ('NULL', 'null', 'Null'):
                val = hint
                stats['hint_fill_from_StudyHint'] += 1

        # StudySee_Full 如果为空且 StudySee 有值，用 StudySee 补
        if c == 'rpt_StudySee_Full' and not val:
            see = r.get('rpt_StudySee', '').strip()
            if see and see not in ('NULL', 'null', 'Null'):
                val = see
                stats['see_fill_from_StudySee'] += 1

        row[c] = val
    clean.append(row)

logs.append(f'\n=== 清洗动作 ===')
for k, v in stats.most_common():
    logs.append(f'  {k}: {v}')

# ======= 写清洗后CSV =======
print(f'\n写入清洗后文件: {DST}')
os.makedirs(os.path.dirname(DST) or '.', exist_ok=True)
with open(DST, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(clean)

# ======= 写清洗报告 =======
with open(LOG, 'w', encoding='utf-8') as f:
    f.write('\n'.join(logs))

# ======= 验证 =======
with open(DST, 'r', encoding='utf-8-sig') as f:
    check = list(csv.DictReader(f))

print(f'清洗后行数: {len(check)}')
print(f'清洗后列数: {len(check[0]) if check else 0}')
print(f'清洗报告: {LOG}')
print('\n=== 关键修复摘要 ===')
for k, v in stats.most_common():
    print(f'  {k}: {v}')
