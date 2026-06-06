#!/usr/bin/env python3
"""
超声报告段落级模板自动提取 v2
数据范围: 仅完整记录 (StudyIdentity + StudySee + StudyHint 都有)
策略: 段落级聚合 + 数值归一化 + StudyHint分组归类 + TF-IDF锚点词
"""
import csv, re, json, time
from collections import Counter, defaultdict

t0 = time.time()

CSV_PATH = r"C:\Users\Administrator\Desktop\超声结构化报告\长沙报告40W.csv"
OUT_TEMPLATES = "section_templates.json"
OUT_RULES = "matching_rules.json"
OUT_STATS = "extraction_stats.json"

# ==========================================
# 1. 读取完整记录 + 段落归一化
# ==========================================
print("[1/5] 读取完整记录并拆分段落...")

section_counter = Counter()
hint_counter = Counter()
hint_to_sections = defaultdict(set)
section_to_hints = defaultdict(set)
full_reports = {}  # StudyIdentity -> {see, hint}

seen_ids = set()
total_rows = 0
complete = 0

with open(CSV_PATH, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1
        sid = (row.get('StudyIdentity') or '').strip()
        see = (row.get('StudySee') or '').strip()
        hint = (row.get('StudyHint') or '').strip()

        if not sid:
            continue
        if sid in seen_ids:
            continue  # 去重: 同一ID取第一条
        seen_ids.add(sid)

        if not see or not hint or see == 'NULL' or hint == 'NULL':
            continue
        complete += 1
        full_reports[sid] = {'see': see, 'hint': hint}
        hint_counter[hint] += 1

        # 段落拆分 + 归一化
        for para in see.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
            para = para.strip()
            if len(para) < 6:
                continue
            zh = sum(1 for c in para if '一' <= c <= '鿿')
            if zh < 3:
                continue

            # 数值归一化
            t = para
            t = re.sub(r'\s+', '', t)
            t = t.replace(',', '，').replace(';', '；').replace(':', '：')
            t = re.sub(r'\d+\.?\d*\s*[xX\xd7]\s*\d+\.?\d*\s*(?:[xX\xd7]\s*\d+\.?\d*)?', '#x#', t)
            t = re.sub(r'\d+\.?\d+\s*mm', '#mm', t)
            t = re.sub(r'\d+\.?\d+\s*cm', '#cm', t)
            t = re.sub(r'\d+\.?\d+\s*%', '#%', t)
            t = re.sub(r'\d+\.?\d+', '#', t)

            section_counter[t] += 1
            hint_to_sections[hint].add(t)
            section_to_hints[t].add(hint)

print(f"  总行数: {total_rows:,}")
print(f"  完整记录(去重): {complete:,}")
print(f"  段落总数(归一化后): {sum(section_counter.values()):,}")
print(f"  唯一种类: {len(section_counter):,}")

# ==========================================
# 2. 覆盖度分析
# ==========================================
print("\n[2/5] 覆盖度分析...")

total_sec = sum(section_counter.values())
cover_stats = {}
cum = 0
for pct_target in [50, 60, 70, 80, 85, 90, 95, 99]:
    cum = 0; count = 0
    for _, freq in section_counter.most_common():
        cum += freq; count += 1
        if cum / total_sec * 100 >= pct_target:
            cover_stats[pct_target] = count
            print(f"  {pct_target:>3}%: {count:>6} 张段落模板")
            break

# ==========================================
# 3. 按检查部位分组
# ==========================================
print("\n[3/5] 按检查部位分组归类...")

CATEGORIES = [
    ('腹部综合', ['脂肪肝', '肝囊肿', '肝内钙化灶', '肝、胆、脾', '胆囊息肉', '胆囊多发',
                  '未见明显异常声像', '肝多发囊肿', '右肾', '左肾', '双肾', '输尿管',
                  '门静脉', '胆总管', '肝内管', '肝脏', '胆囊', '脾', '胰', '肾结石']),
    ('心脏', ['心内结构', '左室', '右室', '二尖瓣', '三尖瓣', '主动脉瓣', '肺动脉',
              '返流', '心包', '房室间隔', '室间隔', '心功能', 'EF', '各房室']),
    ('甲状腺', ['甲状腺', 'TI-RADS', '甲状']),
    ('乳腺', ['乳腺', 'BI-RADS', '双乳', '左乳', '右乳']),
    ('前列腺', ['前列腺']),
    ('颈动脉', ['颈动脉', '颈总', '颈内']),
    ('妇科', ['子宫', '附件', '卵巢', '盆腔', '宫腔', '内膜']),
    ('颈动脉', ['颈动脉', '颈总', '颈内']),
    ('其他', []),
]

# 先对10526个StudyHint归类
hint_category = {}
for hint in hint_counter:
    matched = False
    for cat, keywords in CATEGORIES:
        if cat == '其他':
            continue
        for kw in keywords:
            if kw in hint:
                hint_category[hint] = cat
                matched = True
                break
        if matched:
            break
    if not matched:
        hint_category[hint] = '其他'

# 每个段落归到主要类别
section_category = {}
for text in section_counter:
    hints = section_to_hints.get(text, set())
    if not hints:
        section_category[text] = '其他'
        continue
    # 取最高频hint的类别
    best_hint = max(hints, key=lambda h: hint_counter.get(h, 0))
    section_category[text] = hint_category.get(best_hint, '其他')

# 按类别统计
cat_templates = defaultdict(list)
cat_sections = defaultdict(list)
for text, freq in section_counter.most_common():
    cat = section_category[text]
    cat_sections[cat].append((text, freq))

print(f"\n  各部位段落分布:")
for cat in ['腹部综合', '心脏', '甲状腺', '乳腺', '前列腺', '妇科', '颈动脉', '其他']:
    items = cat_sections.get(cat, [])
    if items:
        total_f = sum(f for _, f in items)
        print(f"    {cat}: {len(items):>5} 种段落, {total_f:>8,} 次出现")

# ==========================================
# 4. TF-IDF 提取特征词
# ==========================================
print("\n[4/5] TF-IDF 提取各模板特征词...")

try:
    import jieba
    jieba.setLogLevel(20)
    _has_jieba = True
except ImportError:
    _has_jieba = False
    print("  jieba不可用, 用字符级n-gram替代")

def segment_for_tfidf(text):
    text = re.sub(r'[^一-鿿\w]', ' ', text)
    if _has_jieba:
        words = [w.strip() for w in jieba.cut(text) if len(w.strip()) >= 2]
        return ' '.join(words)
    else:
        chars = [c for c in text if '一' <= c <= '鿿']
        bigrams = [''.join(chars[i:i+2]) for i in range(len(chars)-1)]
        trigrams = [''.join(chars[i:i+3]) for i in range(len(chars)-2)]
        return ' '.join(bigrams + trigrams)

from sklearn.feature_extraction.text import TfidfVectorizer

# 取覆盖80%的段落数
target_80_count = cover_stats.get(80, 0)
print(f"  提取 Top{target_80_count} 张模板的特征词...")

top_texts = [t for t, _ in section_counter.most_common(target_80_count)]
seg_texts = [segment_for_tfidf(t) for t in top_texts]

vectorizer = TfidfVectorizer(max_features=2000)
tfidf_matrix = vectorizer.fit_transform(seg_texts)
feature_names = vectorizer.get_feature_names_out()

matching_rules = {}
templates_output = {}
template_id = 0

for idx, text in enumerate(top_texts):
    template_id += 1
    tid = f"T{str(template_id).zfill(4)}"
    freq = section_counter[text]
    cat = section_category[text]
    hints = sorted(section_to_hints.get(text, set()),
                   key=lambda h: hint_counter.get(h, 0), reverse=True)[:3]

    # TF-IDF特征词
    row_data = tfidf_matrix.getrow(idx).toarray()[0]
    top_indices = row_data.argsort()[-6:][::-1]
    keywords = []
    for i in top_indices:
        if row_data[i] > 0.05:
            keywords.append(feature_names[i])
        if len(keywords) >= 5:
            break

    matching_rules[tid] = {
        "keywords": keywords,
        "category": cat,
        "threshold": len(keywords) * 40,
    }
    templates_output[tid] = {
        "text": text,
        "frequency": freq,
        "category": cat,
        "keywords": keywords,
        "top_hints": hints,
    }

# ==========================================
# 5. 统计与保存
# ==========================================
print("\n[5/5] 保存输出...")

with open(OUT_TEMPLATES, 'w', encoding='utf-8') as f:
    json.dump(templates_output, f, ensure_ascii=False, indent=2)

with open(OUT_RULES, 'w', encoding='utf-8') as f:
    json.dump(matching_rules, f, ensure_ascii=False, indent=2)

# 按类别汇总
cat_summary = {}
for cat in sorted(set(section_category.values())):
    items_in_cat = [(tid, info) for tid, info in templates_output.items() if info['category'] == cat]
    cat_summary[cat] = {
        "count": len(items_in_cat),
        "total_frequency": sum(info['frequency'] for _, info in items_in_cat),
        "sample_ids": [tid for tid, _ in items_in_cat[:5]],
    }

stats = {
    "total_complete_records": complete,
    "total_sections_normalized": total_sec,
    "unique_sections": len(section_counter),
    "coverage": {str(k): v for k, v in cover_stats.items()},
    "templates_extracted": template_id,
    "categories": cat_summary,
}

with open(OUT_STATS, 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

elapsed = time.time() - t0
print(f"\n{'='*60}")
print(f"DONE. {elapsed:.1f}s")
print(f"  完整记录: {complete:,}")
print(f"  段落种类: {len(section_counter):,}")
print(f"  80%覆盖需: {cover_stats.get(80,0)} 张段落模板")
print(f"  95%覆盖需: {cover_stats.get(95,0)} 张段落模板")
print(f"\n输出文件:")
print(f"  {OUT_TEMPLATES} - {template_id} 张段落模板 + 特征词")
print(f"  {OUT_RULES}     - {template_id} 条匹配规则")
print(f"  {OUT_STATS}     - 统计摘要")
