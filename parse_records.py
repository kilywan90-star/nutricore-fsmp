"""按原始文本解析：StudyIdentity开头 → }结尾为一条记录"""
import re, sys, json
sys.stdout.reconfigure(encoding='utf-8')

path = r"C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W.csv"

with open(path, encoding='utf-8-sig') as f:
    raw = f.read()

lines = raw.split('\n')
total = len(lines)
print(f"总行数: {total:,}")

records = []
i = 0
# 跳过表头 (第一行是列名)
while i < total:
    line = lines[i].strip()
    if re.match(r'^\d{15,20},', line):
        record_lines = [line]
        i += 1
        while i < total:
            nl = lines[i].rstrip('\r')
            record_lines.append(nl)
            # 判断是否是记录结尾: 行以 } 结尾且下一行是新的数字ID(或文件末尾)
            stripped_nl = nl.strip()
            ends_with_brace = stripped_nl.endswith('}')
            # 排除 RTF 转义: 不以反斜杠开头(如 \\viewkind)
            if ends_with_brace and not stripped_nl.startswith('\\'):
                # 看下一行
                if i + 1 >= total:
                    i += 1
                    break
                next_line = lines[i + 1].strip()
                if re.match(r'^\d{15,20},', next_line):
                    i += 1
                    break
                # 下一行也是 RTF 内容(以反斜杠开头), 继续收集
                # 但如果下一行不是RTF也不是数字, 应该是分隔结束
            i += 1
        records.append(record_lines)
    else:
        i += 1

print(f"解析出的记录数: {len(records):,}")

# 统计行数分布
lens = [len(r) for r in records]
print(f"记录行数: min={min(lens)}, max={max(lens)}, avg={sum(lens)/len(lens):.1f}, median={sorted(lens)[len(lens)//2]}")

# 检查完整性
has_see = 0
has_hint = 0
with open(path, encoding='utf-8-sig') as f:
    content = f.read()

print(f"\n前3条记录:")
for j, rec in enumerate(records[:3]):
    print(f"\n--- 记录{j+1} ({len(rec)}行) ---")
    for k, line in enumerate(rec):
        print(f"  [{k}] {line[:150]}")
