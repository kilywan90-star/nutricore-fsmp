"""
LLM 客户端：统一封装 DeepSeek API 调用。
支持 OpenAI 兼容接口，可切换为通义千问、智谱等。
"""

import os
import json
import re
import time
from pathlib import Path

import openai

# DeepSeek 兼容 OpenAI 接口
DEFAULT_CONFIG = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
    "api_key": os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
    "model": os.getenv("LLM_MODEL", "deepseek-chat"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
}


def load_prompt(name: str) -> str:
    """加载 prompts/ 目录下的 Prompt 模板。"""
    prompt_dir = Path(__file__).parent / "prompts"
    path = prompt_dir / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def call_llm(prompt: str, config: dict = None) -> str:
    """
    调用 LLM，返回文本响应。
    支持自动重试（最多 3 次），处理 rate limit 和 server error。
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    if not cfg["api_key"]:
        raise ValueError(
            "请设置环境变量 DEEPSEEK_API_KEY 或 LLM_API_KEY"
        )

    client = openai.OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=cfg["model"],
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except openai.RateLimitError:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  ⏳ Rate limited, {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise
        except openai.APIError as e:
            if attempt < max_retries - 1 and e.status_code and e.status_code >= 500:
                wait = 2 ** (attempt + 1)
                print(f"  ⏳ Server error, {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise


def extract_json(text: str) -> dict | list:
    """从 LLM 响应中提取 JSON。容忍 markdown 代码块包裹。"""
    text = text.strip()

    # 移除 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首行 ```json 和末行 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 正则提取第一个 JSON 对象或数组
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从响应中解析 JSON:\n{text[:500]}")


def run_step(step_name: str, prompt_name: str, doc_text: str, config: dict = None) -> dict | list:
    """
    执行一个完整的 LLM 步骤：加载 Prompt → 拼接文档 → 调用 LLM → 解析 JSON
    返回解析后的 JSON 对象（dict 或 list）。
    """
    prompt = load_prompt(prompt_name)
    full_prompt = f"{prompt}\n\n{doc_text}"

    # 截断超长文本（DeepSeek 上下文 64K，留够余量）
    max_input = 50000
    if len(full_prompt) > max_input:
        full_prompt = full_prompt[:max_input]
        print(f"  ⚠ 文档过长，已截断至 {max_input} 字符")

    print(f"  → 调用 LLM ({prompt_name})...")
    start = time.time()
    response = call_llm(full_prompt, config)
    elapsed = time.time() - start

    result = extract_json(response)
    print(f"  ✓ {step_name} 完成 ({elapsed:.1f}s)")
    return result
