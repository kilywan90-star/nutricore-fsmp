import asyncio
import json
import re
from typing import Optional

from openai import OpenAI, AsyncOpenAI

from news_agent.config import config
from news_agent.rewriter.prompt_templates import TOUTIAO_SYSTEM_PROMPT, TOUTIAO_USER_TEMPLATE
from news_agent.utils.logger import logger


def _count_cn_chars(text: str) -> int:
    return len(re.findall(r"[一-鿿]", text))


class DeepSeekRewriter:

    def __init__(self):
        self.client = OpenAI(
            api_key=config.deepseek.api_key,
            base_url=config.deepseek.base_url,
        )
        self.async_client = AsyncOpenAI(
            api_key=config.deepseek.api_key,
            base_url=config.deepseek.base_url,
        )

    def rewrite(self, title: str, content: str, published_at: str, category: str) -> Optional[dict]:
        """同步改写（保留兼容）。"""
        result = self._call_deepseek(title, content, published_at, category)
        if not result:
            return None
        return self._check_length(result, title, category)

    async def rewrite_async(self, title: str, content: str, published_at: str, category: str) -> Optional[dict]:
        """异步改写，用于并发流水线。"""
        result = await self._call_deepseek_async(title, content, published_at, category)
        if not result:
            return None
        return self._check_length(result, title, category)

    def _check_length(self, result: dict, title: str, category: str) -> Optional[dict]:
        cn_count = _count_cn_chars(result.get("body", ""))
        if cn_count < 1150:
            logger.info(f"Word count {cn_count} < 1100, expanding...")
            expanded = self._expand(result, title, category)
            if expanded:
                new_count = _count_cn_chars(expanded.get("body", ""))
                logger.info(f"Expanded: {cn_count} -> {new_count} chars")
                return expanded
        logger.info(f"Rewrote ({_count_cn_chars(result.get('body',''))} chars): '{title[:30]}...' -> '{result['title'][:30]}...'")
        return result

    # ── sync internals ──────────────────────────────────────

    def _call_deepseek(self, title: str, content: str, published_at: str, category: str) -> Optional[dict]:
        user_prompt = TOUTIAO_USER_TEMPLATE.format(
            title=title, content=content[:3000], published_at=published_at, category=category,
        )
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=config.deepseek.model,
                    messages=[
                        {"role": "system", "content": TOUTIAO_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    extra_body={"thinking": {"type": "enabled"}},
                    temperature=config.deepseek.temperature,
                    max_tokens=config.deepseek.max_tokens,
                )
                raw = response.choices[0].message.content.strip()
                result = _parse_json_response(raw)
                if result:
                    return result
                logger.warning(f"Parse failed (attempt {attempt + 1}): {title[:40]}")
            except Exception as e:
                logger.error(f"DeepSeek API error (attempt {attempt + 1}): {e}")
        return None

    # ── async internals ─────────────────────────────────────

    async def _call_deepseek_async(self, title: str, content: str, published_at: str, category: str) -> Optional[dict]:
        user_prompt = TOUTIAO_USER_TEMPLATE.format(
            title=title, content=content[:3000], published_at=published_at, category=category,
        )
        for attempt in range(2):
            try:
                response = await self.async_client.chat.completions.create(
                    model=config.deepseek.model,
                    messages=[
                        {"role": "system", "content": TOUTIAO_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    extra_body={"thinking": {"type": "enabled"}},
                    temperature=config.deepseek.temperature,
                    max_tokens=config.deepseek.max_tokens,
                )
                raw = response.choices[0].message.content.strip()
                result = _parse_json_response(raw)
                if result:
                    return result
                logger.warning(f"Parse failed (attempt {attempt + 1}): {title[:40]}")
            except Exception as e:
                logger.error(f"DeepSeek API error (attempt {attempt + 1}): {e}")
                await asyncio.sleep(1)  # brief backoff on error
        return None

    def _expand(self, original: dict, original_title: str, category: str) -> Optional[dict]:
        expand_prompt = f"""你刚才写的这篇文章字数不足1200字，请扩充到1200-1500字。保持标题不变，保持原有风格和结构，在以下位置补充内容：

1. 增加更多背景数据或历史对比
2. 补充一个具体案例或专家观点
3. 扩展"影响与展望"部分

原标题：{original['title']}
当前正文：
{original['body']}

请输出完整的扩充后JSON（标题保持不变）：
{{"title": "{original['title']}", "body": "扩充后的完整正文（1200-1500汉字）", "summary": "一句话总结"}}"""
        try:
            response = self.client.chat.completions.create(
                model=config.deepseek.model,
                messages=[
                    {"role": "system", "content": "你是今日头条财经专栏作者。严格按JSON格式输出。"},
                    {"role": "user", "content": expand_prompt},
                ],
                temperature=0.7,
                max_tokens=config.deepseek.max_tokens,
            )
            raw = response.choices[0].message.content.strip()
            return _parse_json_response(raw)
        except Exception as e:
            logger.error(f"Expand API error: {e}")
            return None


def _parse_json_response(raw: str) -> Optional[dict]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    try:
        data = json.loads(cleaned)
        if "title" in data and "body" in data:
            return data
    except json.JSONDecodeError:
        pass

    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', raw)
    body_match = re.search(r'"body"\s*:\s*"([^"]*)"', raw)
    summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', raw)
    if title_match and body_match:
        return {
            "title": title_match.group(1),
            "body": body_match.group(1),
            "summary": summary_match.group(1) if summary_match else "",
        }
    return None
