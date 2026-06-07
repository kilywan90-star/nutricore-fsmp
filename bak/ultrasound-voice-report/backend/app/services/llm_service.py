import os
import json
from openai import AsyncOpenAI
from app.templates import TEMPLATE_REGISTRY
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
except ImportError:
    pass

api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or "mock_key"
base_url = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1"

client = AsyncOpenAI(api_key=api_key, base_url=base_url)

async def extract_structured_data(raw_text: str, exam_part: str) -> dict:
    if exam_part not in TEMPLATE_REGISTRY:
        return {"other_findings": raw_text}

    config = TEMPLATE_REGISTRY[exam_part]
    schema_json = config["schema"].model_json_schema()

    prompt = f"""
    {config["system_prompt"]}

    目标JSON格式(Schema): {json.dumps(schema_json, ensure_ascii=False)}

    参考案例(Few-Shot):
    {config["few_shot"]}

    请处理以下输入口述:
    Input: {raw_text}
    Output:
    """

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=5.0
        )
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        # CIRCUIT BREAKER / FALLBACK: If LLM fails, dump raw text to other_findings
        print(f"[LLM Service Error] Fallback triggered due to: {e}")
        default_instance = config["schema"]()
        default_dict = default_instance.model_dump()
        default_dict["other_findings"] = f"[AI提取失败，原始转写]: {raw_text}"
        return default_dict
