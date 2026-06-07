#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
voice_matcher.py 使用示例 — 直接运行即可看到效果
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ===== 方式1: 直接命令行测试 =====
print("="*60)
print("语音匹配引擎 v4.2 — 使用示例")
print("="*60)
print()

# 导入引擎
from voice_matcher import match, generate

# ===== 基础用法 =====
print("【基础用法】")
print()

# 模拟医生说话
text = "肝脏形态规则，大小正常，表面光滑，实质回声分布均匀，肝内管系尚清"

# 匹配
top5, locked = match(text)

# 查看TOP5
print("医生说:", text)
print()
print("TOP5匹配结果:")
for i, m in enumerate(top5, 1):
    print(f"  #{i}  置信度={m['score']*100:.0f}%  rid={m['rid']}  {m['discname']}")
    print(f"     诊断分组: {m['discgroup']}")
    print(f"     诊断提示: {m['tpl_hint'][:40]}")
    print()

# 自动锁定
if locked:
    print(">>> 自动锁定! <<<")
    report = generate(locked)
    print(f"  疾病名称: {report['discname']}")
    print(f"  诊断分组: {report['discgroup']}")
    print(f"  诊断提示: {report['tpl_hint']}")
    print(f"  随访建议: {report['suggestion']}")
    print(f"  置信度: {report['confidence']*100:.0f}%")
    print(f"  完整报告: {report['full_report'][:60]}...")
else:
    print("(未达到85%锁定阈值，需说更多内容)")

print()
print("="*60)
print()

# ===== 批量测试 =====
print("【批量测试 — 11个标准用例全部自动锁定】")
print()

tests = [
    ("肝脏脂肪沉积", "肝脏形态规则，大小正常，表面光滑，实质回声分布均匀，肝内管系尚清"),
    ("前列腺增大", "膀胱充盈可，壁光滑，内未见明显包块回声。前列腺形态稍饱满"),
    ("双乳小叶增生", "双乳组织增厚、增粗，回声分布不均，见多个粗大点片状低回声区"),
    ("甲状腺回声不均匀", "甲状腺双侧叶形态规则，大小正常，表面光滑，实质回声不均匀"),
    ("颈动脉斑块", "双侧颈动脉走行正常，内膜面毛糙，内中膜不厚"),
    ("脂肪肝", "肝脏形态大小正常，表面光滑，实质回声分布欠均匀，近场回声增强"),
    ("肝囊肿", "肝内可见无回声区，壁薄，后壁回声增强，内透声可"),
    ("甲状腺结节", "甲状腺左侧叶内可见低回声结节，大小约3.5x4.0mm"),
    ("胆囊结石", "胆囊大小形态正常，壁光滑，内可见多个强回声团"),
    ("心脏", "2D：各房室内径正常，房室间隔未见明显连续中断"),
    ("肾囊肿", "左肾可见无回声区，壁薄，后壁回声增强，内透声可"),
]

for name, txt in tests:
    top5, locked = match(txt)
    if locked:
        report = generate(locked)
        print(f"  ✓ {name}: 锁定 → {report['discname'][:20]} ({report['confidence']*100:.0f}%)")
    else:
        top1 = top5[0]['discname'] if top5 else "无匹配"
        print(f"  · {name}: 未锁定 → 最高={top5[0]['score']*100:.0f}% {top1}")

print()
print("="*60)
print()

# ===== 不同输入长度的效果 =====
print("【说多长才能锁定？— 渐进演示】")
print()

steps = ["肝脏", "肝脏形态", "肝脏形态规则",
         "肝脏形态规则，大小正常",
         "肝脏形态规则，大小正常，表面光滑",
         "肝脏形态规则，大小正常，表面光滑，实质回声",
         "肝脏形态规则，大小正常，表面光滑，实质回声分布均匀",
         "肝脏形态规则，大小正常，表面光滑，实质回声分布均匀，肝内管系尚清"]

for txt in steps:
    top5, locked = match(txt)
    if top5:
        status = "→ 锁定!" if locked else f"({top5[0]['score']*100:.0f}%)"
        print(f"  \"{txt[:18]:20s}\"  {status:>8}  {top5[0]['discname'][:15]}")

print()
print("="*60)
print()

# ===== 接口说明 =====
print("【接口说明】")
print()
print("  from voice_matcher import match, generate")
print()
print("  1. top5, locked = match(医生说的话)")
print("     - top5:  TOP5匹配列表，每项含 rid/score/discname/discgroup/tpl_hint")
print("     - locked: 锁定结果(score>=85%)，None=未锁定")
print()
print("  2. report = generate(locked)")
print("     - report['discname']     — 疾病名称")
print("     - report['discgroup']    — 诊断分组")
print("     - report['tpl_hint']     — 诊断提示")
print("     - report['tpl_see']      — 通用模板")
print("     - report['full_report']  — 完整报告")
print("     - report['suggestion']   — 随访建议")
print("     - report['confidence']   — 置信度")
print()
print("  3. TIPS:")
print("     - 说3-4个短句(20-40字)即可锁定")
print("     - 支持183个超声模板")
print("     - 器官自动识别，跨部位不误匹配")
