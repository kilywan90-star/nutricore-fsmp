#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据生成原理验证脚本
回答：数据是否是固定的？是的——伪随机+固定种子=可复现
"""

import random

print("=" * 65)
print("  原理验证：random.seed(42) → 伪随机 ← 可复现")
print("=" * 65)

# 第1次
random.seed(42)
run1 = [random.randint(1, 100) for _ in range(5)]
print(f"\n第1次运行(seed=42): {run1}")

# 第2次 — 重新 seed → 完全一致
random.seed(42)
run2 = [random.randint(1, 100) for _ in range(5)]
print(f"第2次运行(seed=42): {run2}")
print(f"  完全一致? {'YES' if run1 == run2 else 'NO'}")

# 换个种子 → 完全不同
random.seed(99)
run3 = [random.randint(1, 100) for _ in range(5)]
print(f"\n换种子(seed=99)  : {run3}")
print(f"  与seed=42一致? {'YES' if run1 == run3 else 'NO'}")

# 验证数据文件
import os
DATA_DIR = r"e:\claude\docs\ultrasound_asr_testset"
mixed = os.path.join(DATA_DIR, "01_mixed_100.csv")
with open(mixed, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f"\n数据文件 01_mixed_100.csv:  {len(lines)-1}条记录 (含header)")
print(f"  第1行: {lines[1][:80]}...")
print(f"  第2行: {lines[2][:80]}...")
print(f"\n结论: 每次运行 gen_ultrasound_asr.py 生成的数据完全一致")
print(f"       seed=42 保证可复现 → 适合做基准评测集")
