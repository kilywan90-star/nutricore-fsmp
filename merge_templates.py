#!/usr/bin/env python3
"""去重合并相似模板，输出最终精选模板库"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open("E:/claude/section_templates.json", encoding='utf-8') as f:
    tpl = json.load(f)
with open("E:/claude/matching_rules.json", encoding='utf-8') as f:
    rules = json.load(f)

# 保留完整原文（未归一化）做比较
def bigrams(s):
    return set(s[i:i+2] for i in range(len(s)-1))
def jaccard(a, b):
    ba, bb = bigrams(a), bigrams(b)
    return len(ba & bb) / max(1, len(ba | bb))

# 归一化文本
def strip_tokens(text):
    """只保留医学内容，删除标点/前缀/数字"""
    t = text
    t = re.sub(r'^[M2DdCDFI]*(：|:)?\s*', '', t)
    t = re.sub(r'[，。；;：:、\s]+', '', t)
    t = re.sub(r'\d+\.?\d*', '#', t)
    return t

# 聚类
parent = {}
ids = list(tpl.keys())
for tid in ids:
    parent[tid] = tid
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(x, y):
    parent[find(x)] = find(y)

# 只合并 Jaccard >= 0.85 的真冗余(排除 E>/<)
for i in range(len(ids)):
    for j in range(i+1, len(ids)):
        a, b = ids[i], ids[j]
        ta = strip_tokens(tpl[a]['text'])
        tb = strip_tokens(tpl[b]['text'])
        # 检查是否是 E>A / E<A 这种语义对立
        if ('E>A' in tpl[a]['text'] and 'E<A' in tpl[b]['text']) or \
           ('E<A' in tpl[a]['text'] and 'E>A' in tpl[b]['text']):
            continue
        # 检查是否饱满/稍饱满这种程度差异
        if ('饱满' in tpl[a]['text'] and '稍饱满' in tpl[b]['text']) or \
           ('稍饱满' in tpl[a]['text'] and '饱满' in tpl[b]['text']):
            continue
        if jaccard(ta, tb) >= 0.85:
            union(a, b)

# 分组
clusters = {}
for tid in parent:
    root = find(tid)
    if root not in clusters:
        clusters[root] = []
    clusters[root].append(tid)

# 每个聚类选代表: 选频次最高的(即原始写法中最主流的那种)
merged_templates = {}
merged_rules = {}
merge_log = []

for root, members in clusters.items():
    # 按频次排序
    sorted_members = sorted(members, key=lambda tid: tpl[tid]['frequency'], reverse=True)
    winner = sorted_members[0]
    merged_templates[winner] = tpl[winner]
    merged_rules[winner] = rules[winner]

    if len(members) > 1:
        total_freq = sum(tpl[t]['frequency'] for t in members)
        merged_templates[winner]['original_frequency'] = tpl[winner]['frequency']
        merged_templates[winner]['merged_count'] = len(members)
        merged_templates[winner]['merged_ids'] = sorted_members[1:]
        merged_templates[winner]['frequency_after_merge'] = total_freq
        merged_rules[winner]['merged_from'] = sorted_members[1:]
        merge_log.append({
            'kept': winner,
            'kept_text': tpl[winner]['text'][:100],
            'merged': sorted_members[1:],
            'merged_texts': [tpl[t]['text'][:80] for t in sorted_members[1:]],
            'total_frequency': total_freq,
        })

# 保存
with open("section_templates_merged.json", 'w', encoding='utf-8') as f:
    json.dump(merged_templates, f, ensure_ascii=False, indent=2)
with open("matching_rules_merged.json", 'w', encoding='utf-8') as f:
    json.dump(merged_rules, f, ensure_ascii=False, indent=2)

# 统计
from collections import Counter
cats = Counter(info['category'] for info in merged_templates.values())

print(f"54 张 -> {len(merged_templates)} 张 (消除 {54 - len(merged_templates)} 张冗余)")
print(f"\n按部位:")
for cat, cnt in cats.most_common():
    print(f"  {cat}: {cnt} 张")

print(f"\n合并明细:")
for item in merge_log:
    print(f"  保留: {item['kept']} ({item['total_frequency']:,}次)")
    print(f"    正文: {item['kept_text']}...")
    for mid, mtxt in zip(item['merged'], item['merged_texts']):
        print(f"    合并 {mid}: {mtxt}...")
