"""
政策文档智能处理 PoC 管线
串联：文档解析 → 结构化提取 → 自动分类 → 待办提取

用法:
  python pipeline.py <样本目录或单文件>

示例:
  python pipeline.py samples/长诚Q2返利政策.pdf
  python pipeline.py samples/        # 处理整个目录
"""

import os
import sys
import json
import time
from pathlib import Path

# 将当前目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from parse import parse_file
from llm_client import run_step


def process_one(filepath: str, output_dir: str, config: dict = None) -> dict:
    """处理单个文件：解析 → 提取 → 分类 → 待办。返回完整结果。"""
    filename = Path(filepath).name
    print(f"\n{'='*60}")
    print(f"📄 处理文件: {filename}")
    print(f"{'='*60}")

    # Step 1: 文档解析
    print("\n[1/4] 文档解析...")
    start = time.time()
    parsed = parse_file(filepath)
    elapsed = time.time() - start
    print(f"  ✓ 解析完成 ({elapsed:.1f}s) | {parsed['char_count']} 字符 | 类型: {parsed['file_type']}")

    full_text = parsed["text"]
    if len(full_text) < 50:
        print(f"  ⚠ 警告: 提取文本过短，请检查文件内容或 OCR 环境")

    # 保存解析结果
    base_name = Path(filepath).stem
    os.makedirs(output_dir, exist_ok=True)
    _save_output(output_dir, f"{base_name}_01_parsed.md", full_text)

    # Step 2: 结构化提取
    print("\n[2/4] 结构化提取...")
    extract_result = run_step("结构化提取", "extract", full_text, config)
    _save_output(output_dir, f"{base_name}_02_extract.json", extract_result)
    print(f"  主题: {extract_result.get('主题', 'N/A')}")

    # Step 3: 自动分类（输入为提取的摘要，而非全文）
    print("\n[3/4] 自动分类...")
    summary = json.dumps(extract_result, ensure_ascii=False, indent=2)
    classify_result = run_step("自动分类", "classify", f"## 文档基本信息\n- 文件名: {filename}\n\n## 结构化摘要\n{summary}", config)
    _save_output(output_dir, f"{base_name}_03_classify.json", classify_result)
    print(f"  业务类型: {classify_result.get('业务类型', 'N/A')}")
    print(f"  业务域: {', '.join(classify_result.get('业务域', []))}")

    # Step 4: 待办提取（输入为全文 + 结构化摘要）
    print("\n[4/4] 待办提取...")
    doc_for_todo = f"## 文档文件名\n{filename}\n\n## 结构化摘要\n{summary}\n\n## 文档全文\n{full_text}"
    todo_result = run_step("待办提取", "todo", doc_for_todo, config)
    _save_output(output_dir, f"{base_name}_04_todos.json", todo_result)
    print(f"  提取待办: {len(todo_result)} 项")

    result = {
        "file": filename,
        "parsed": {"char_count": parsed["char_count"], "file_type": parsed["file_type"]},
        "extract": extract_result,
        "classify": classify_result,
        "todos": todo_result,
    }

    # 保存完整结果
    _save_output(output_dir, f"{base_name}_full_result.json", result)

    return result


def _save_output(output_dir: str, filename: str, data):
    """保存中间结果到文件。"""
    path = os.path.join(output_dir, filename)
    if isinstance(data, str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def print_summary(results: list):
    """打印所有文件的处理摘要。"""
    print(f"\n\n{'='*60}")
    print(f"📊 处理完毕 - 共 {len(results)} 个文件")
    print(f"{'='*60}")

    for r in results:
        print(f"\n📄 {r['file']}")
        print(f"   主题: {r['extract'].get('主题', 'N/A')}")
        print(f"   分类: {r['classify'].get('业务类型', 'N/A')} | {', '.join(r['classify'].get('业务域', []))}")
        print(f"   待办: {len(r['todos'])} 项")
        for todo in r["todos"]:
            print(f"     - [{todo.get('优先级', '中')}] {todo.get('待办标题', '')} | 截止: {todo.get('截止时间', '')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = sys.argv[1]
    output_dir = os.path.join(os.path.dirname(__file__), "output")

    # 收集文件列表
    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        supported = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
        files = sorted([
            os.path.join(target, f) for f in os.listdir(target)
            if Path(f).suffix.lower() in supported
        ])
        if not files:
            print(f"错误: {target} 目录下未找到支持的文件（PDF/DOCX/图片）")
            sys.exit(1)
    else:
        print(f"错误: {target} 不存在")
        sys.exit(1)

    print(f"找到 {len(files)} 个文件待处理")
    _ = input("按 Enter 开始处理...")

    # 可选配置（可切换模型）
    config = {
        # "model": "deepseek-chat",  # 默认
        # "base_url": "https://api.deepseek.com/v1",
    }

    results = []
    for filepath in files:
        try:
            result = process_one(filepath, output_dir, config)
            results.append(result)
        except Exception as e:
            print(f"\n❌ 处理失败: {filepath}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()

    if results:
        print_summary(results)
        print(f"\n📁 完整结果已保存至: {output_dir}")
