#!/usr/bin/env python3
"""Generate comparison report between old and new ultrasound code."""
import os, difflib

OLD = "E:/claude/ultrasound-report-mvp"
NEW = "E:/claude/ultrasound-app-new/ultrasound-app"
REPORT = "E:/claude/ultrasound-report-mvp/import_diff_report.md"

def read(fpath):
    try:
        with open(fpath, encoding='utf-8') as f:
            return f.read()
    except: return None

pairs = [
    ("backend/main.py", "backend/main.py"),
    ("backend/db.py", "backend/database.py"),
    ("backend/models.py", "backend/models.py"),
    ("backend/engine.py", None),
    (None, "backend/engine.py"),
    (None, "backend/asr_service.py"),
    (None, "backend/knowledge_engine.py"),
    (None, "backend/llm_engine.py"),
    (None, "backend/pipeline.py"),
    (None, "backend/routing_rules.py"),
    ("frontend/index.html", "frontend/index.html"),
]

lines = ["# 超声报告新旧代码对比报告\n", f"生成时间: 2026-06-07\n\n"]
lines.append("## 文件结构对比\n\n")

old_files = set()
for root, dirs, files in os.walk(OLD):
    for f in files:
        rp = os.path.relpath(os.path.join(root, f), OLD)
        if '.git' not in rp and '__pycache__' not in rp:
            old_files.add(rp)

new_files = set()
for root, dirs, files in os.walk(NEW):
    for f in files:
        rp = os.path.relpath(os.path.join(root, f), NEW)
        new_files.add(rp)

lines.append(f"- 旧项目文件数: {len(old_files)}\n")
lines.append(f"- 新版文件数: {len(new_files)}\n\n")

lines.append("### 新版新增文件\n\n")
for f in sorted(new_files - old_files):
    lines.append(f"- `{f}`\n")
lines.append("\n### 旧版有但新版无的文件\n\n")
for f in sorted(old_files - new_files):
    if f.startswith('backend/') and not any(x in f for x in ['__pycache__', '.db', '.pyc']):
        lines.append(f"- `{f}`\n")

lines.append("\n## 相同路径文件差异\n\n")
for old_p, new_p in pairs:
    if not old_p or not new_p:
        continue
    old_c = read(os.path.join(OLD, old_p))
    new_c = read(os.path.join(NEW, new_p))
    if old_c and new_c and old_c != new_c:
        diff = difflib.unified_diff(
            old_c.splitlines(), new_c.splitlines(),
            fromfile=f'old/{old_p}', tofile=f'new/{new_p}',
            lineterm=''
        )
        dlines = list(diff)
        if dlines:
            lines.append(f"### {old_p}\n")
            lines.append(f"```diff\n")
            lines.extend(f"{l}\n" for l in dlines[:80])
            if len(dlines) > 80:
                lines.append(f"... (truncated, {len(dlines)} lines total)\n")
            lines.append("```\n\n")

with open(REPORT, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print(f"Report written to {REPORT}")
print(f"Old files: {len(old_files)}, New files: {len(new_files)}")
