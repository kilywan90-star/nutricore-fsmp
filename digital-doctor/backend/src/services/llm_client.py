# digital-doctor/backend/src/services/llm_client.py
from httpx import AsyncClient
from src.config import settings


class LLMClient:
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    async def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        if not self.api_key:
            return self._mock_response(messages)

        async with AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _mock_response(self, messages: list[dict]) -> str:
        """无API Key时的mock响应，用于开发测试"""
        last_msg = messages[-1]["content"] if messages else ""
        if "风险评估" in last_msg:
            return '{"risk_level": "中危", "score": 12, "recommendations": ["建议生活方式干预", "3个月后复查空腹血糖"]}'
        if "报告" in last_msg:
            return "根据检查结果：空腹血糖 6.5mmol/L（轻度升高），HbA1c 7.2%（提示近3月血糖控制欠佳），总胆固醇 5.2mmol/L（正常）。建议：控制饮食碳水化合物摄入，增加有氧运动，遵医嘱服药，2周后复查空腹血糖。"
        if "血糖" in last_msg:
            return "您今日空腹血糖6.5mmol/L，在可接受范围。注意今日早餐碳水摄入量，保持午餐后散步15分钟。"
        return "分析结果：无异常。"


llm_client = LLMClient()
