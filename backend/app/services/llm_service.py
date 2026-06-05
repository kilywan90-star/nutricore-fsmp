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

# ──────────────────────────────────────────────
# Task A: Progressive Intent Detection
# ──────────────────────────────────────────────
async def detect_template_intent(raw_text: str) -> dict:
    """
    Progressive intent detection: given accumulated text, decide which
    template (breast / abdominal / none) to route to, with a confidence score.

    Returns: {"template": "breast", "confidence": 98}
    """
    template_names = list(TEMPLATE_REGISTRY.keys())
    template_descriptions = "\n".join(
        f"- {name}: {TEMPLATE_REGISTRY[name]['system_prompt'][:80]}"
        for name in template_names
    )

    prompt = f"""你是一个超声科室分诊路由专家。根据医生口述的开头内容，判断当前检查属于哪个超声部位。

可选模板:
{template_descriptions}

请只输出一个 JSON，包含:
- "template": 匹配的模板名(breast/abdominal/none)
- "confidence": 0-100 的信心度分数(数字)
- "reason": 简短的判断依据

当口述中没有任何明确的部位词(如"乳腺/肝脏/胆囊/BI-RADS/肝胆")时，template为"none"，confidence填0。

医生口述: {raw_text}

输出:"""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=3.0
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "template": result.get("template", "none"),
            "confidence": int(result.get("confidence", 0))
        }
    except Exception as e:
        print(f"[Intent Detection Error] {e}")
        return {"template": "none", "confidence": 0}


# ──────────────────────────────────────────────
# Task B: Streaming Slot Filling
# ──────────────────────────────────────────────
async def fill_slots_streaming(raw_text: str, exam_part: str) -> dict:
    """
    Extract structured fields from the *entire accumulated text*.
    Called repeatedly as the doctor speaks — every new text increment.
    """
    if exam_part not in TEMPLATE_REGISTRY:
        return {"other_findings": raw_text}

    config = TEMPLATE_REGISTRY[exam_part]
    schema_json = config["schema"].model_json_schema()

    prompt = f"""{config["system_prompt"]}

目标JSON格式(Schema): {json.dumps(schema_json, ensure_ascii=False)}

参考案例(Few-Shot):
{config["few_shot"]}

当前已经累计的医生口述文本:
Input: {raw_text}
Output:"""

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
        print(f"[Slot Filling Error] Fallback triggered: {e}")
        default_instance = config["schema"]()
        default_dict = default_instance.model_dump()
        default_dict["other_findings"] = f"[AI提取失收，原始转写]: {raw_text}"
        return default_dict


# ──────────────────────────────────────────────
# Task C: Final Review / Clinical Audit
# ──────────────────────────────────────────────
async def final_review(slots: dict, exam_part: str) -> str:
    """
    Final clinical logic validation — check for contradictions.
    Returns a human-readable audit note.
    """
    if exam_part not in TEMPLATE_REGISTRY:
        return ""

    config = TEMPLATE_REGISTRY[exam_part]
    prompt = f"""你是资深超声科主任。请审查以下AI生成的结构化报告，检查是否存在临床逻辑矛盾。

科室: {exam_part}
报告内容: {json.dumps(slots, ensure_ascii=False)}

常见矛盾检查项:
- 乳腺: 如果提到"结节"但BI-RADS为"1类"，可能矛盾(1类应为阴性)
- 腹部: 如果肝脏大小为"增大"但回声描述为"均匀"，不太矛盾；如果"毛糙+光整"同时出现则有矛盾
- 如果所有字段均为默认值("未见明显结节/正常/均匀/光整")但原始口述中明确提到了异常，说明AI提取遗漏

请用中文输出审查意见。如无矛盾，输出"未见明显临床矛盾"。有矛盾请具体说明。"""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            timeout=4.0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Final Review Error] {e}")
        return "最终审查暂时不可用，请人工复核。"


# ──────────────────────────────────────────────
# Legacy: one-shot extraction (kept for /analyze-voice)
# ──────────────────────────────────────────────
async def extract_structured_data(raw_text: str, exam_part: str) -> dict:
    return await fill_slots_streaming(raw_text, exam_part)
