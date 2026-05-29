"""
LLM 客户端 —— 兼容 OpenAI 接口，支持 DeepSeek / 通义千问 / 智谱等。
"""

import json
import re
import time

import openai

from app.config import settings


class LLMClient:
    """统一 LLM 调用客户端（延迟初始化，无 API key 也能 import）"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
        return self._client

    def chat(self, prompt: str, model: str = None, temperature: float = None,
             max_tokens: int = None, max_retries: int = 3) -> str:
        """调用 LLM 返回文本响应，自动重试"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model or settings.llm_model,
                    temperature=temperature if temperature is not None else settings.llm_temperature,
                    max_tokens=max_tokens or settings.llm_max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                else:
                    raise
            except openai.APIError as e:
                if attempt < max_retries - 1 and e.status_code and e.status_code >= 500:
                    time.sleep(2 ** (attempt + 1))
                else:
                    raise

    def chat_json(self, prompt: str, model: str = None, max_retries: int = 2) -> dict | list:
        """调用 LLM 并解析 JSON 响应"""
        response = self.chat(prompt, model=model, temperature=0.05, max_retries=max_retries)
        return self._extract_json(response)

    def _extract_json(self, text: str) -> dict | list:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

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

        raise ValueError(f"无法从响应解析 JSON: {text[:300]}")


llm_client = LLMClient()
