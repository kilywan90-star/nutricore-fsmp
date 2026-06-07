"""
清洗全字段40万数据
"""
import csv, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

SRC = r'C:\Users\Administrator\Desktop\全字段40万-matching_result_full.csv'
DST = r'C:\Users\Administrator\Desktop\全字段40万-matching_result_clean.csv'

print('=== 1. 读数据 ===')
with open(SRC, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    rows = list(reader)

N = len(rows)
print(f'行: {N}, 列: {len(cols)}')

# === 2. 识别要删除的冗余列（空值>=99%）===
DROP = []
for c in cols:
    empty = sum(1 for r in rows if not (r.get(c, '') or '').strip())
    if empty / N >= 0.99:
        DROP.append(c)
print(f'\n删除 {len(DROP)} 个冗余列(99%+空): {DROP}')

keep_cols = [c for c in cols if c not in DROP]
print(f'保留 {len(keep_cols)} 列')

# === 3. 逐行清洗 ===
print(f'\n=== 2. 清洗数据 ===')
fix_quote = 0
fix_null_to_empty = 0
has_see = 0
has_hint = 0

cleaned = []
for r in rows:
    row = {}
    for c in keep_cols:
        v = r.get(c, '') or ''

        # NULL字符串 → 空
        if v.strip() in ('NULL', 'null', 'Null'):
            v = ''
            fix_null_to_empty += 1

        # tpl_INFO1 去掉CSV包裹的引号
        if c == 'tpl_INFO1' and v:
            v = v.strip('"')
            if v != (r.get(c, '') or '').strip():
                fix_quote += 1

        row[c] = v.strip()

        # 统计有文本的
        if c == 'rpt_StudySee_Full' and v: has_see += 1
        if c == 'rpt_StudyHint_Full' and v: has_hint += 1

    cleaned.append(row)

print(f'  修正NULL→空: {fix_null_to_empty}')
print(f'  去除tpl_INFO1引号: {fix_quote}')
print(f'  有StudySee_Full: {has_see}, 有StudyHint_Full: {has_hint}')

# === 4. 写清洗后文件 ===
print(f'\n=== 3. 写入 ===')
with open(DST, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keep_cols)
    w.writeheader()
    w.writerows(cleaned)

print(f'输出: {DST}')
print(f'大小: {os.path.getsize(DST)/1024/1024:.1f} MB')

# === 5. 验证 ===
print(f'\n=== 4. 验证 ===')
with open(DST, 'r', encoding='utf-8-sig') as f:
    check = list(csv.DictReader(f))
print(f'行数: {len(check)}, 列数: {len(check[0])}')
print(f'字段:')
for i, c in enumerate(check[0].keys()):
    print(f'  [{i:>2}] {c}')
