# digital-doctor/backend/src/services/health_coach.py
from dataclasses import dataclass, field
from typing import Any
from src.services.llm_client import llm_client


@dataclass
class CoachContext:
    patient_id: str
    recent_fpg: list[float] = field(default_factory=list)
    recent_ppg: list[float] = field(default_factory=list)
    hba1c: float | None = None
    medications: list[str] = field(default_factory=list)
    diet_adherence: str = "未知"
    exercise_adherence: str = "未知"

    @classmethod
    def from_patient_data(cls, patient_id: str, glucose_records: list[dict], hba1c: float | None, medications: list[str]) -> "CoachContext":
        fpg = [r["value_mmol_l"] for r in glucose_records if r.get("measure_type") == "fasting"]
        ppg = [r["value_mmol_l"] for r in glucose_records if r.get("measure_type") == "post_prandial"]
        return cls(patient_id=patient_id, recent_fpg=fpg[-7:], recent_ppg=ppg[-7:], hba1c=hba1c, medications=medications)


class HealthCoach:
    URGENT_KEYWORDS = [
        "心慌", "出冷汗", "头晕", "看不清", "昏迷", "晕倒", "测不出",
        "很高", "30", "低血糖", "发抖", "面色苍白",
    ]

    def _has_urgent_keywords(self, text: str) -> bool:
        return any(kw in text for kw in self.URGENT_KEYWORDS)

    def _build_system_prompt(self, ctx: CoachContext) -> str:
        fpg_str = f"最近空腹血糖：{ctx.recent_fpg}" if ctx.recent_fpg else "暂无空腹血糖数据"
        ppg_str = f"最近餐后血糖：{ctx.recent_ppg}" if ctx.recent_ppg else "暂无餐后血糖数据"
        hba1c_str = f"最近HbA1c：{ctx.hba1c}%" if ctx.hba1c else "暂无HbA1c数据"
        meds = "、".join(ctx.medications) if ctx.medications else "未记录"

        return f"""你是一位专业的糖尿病健康管理教练，基于《中国2型糖尿病防治指南(2024版)》为患者提供日常管理建议。

当前患者数据：
- {fpg_str}
- {ppg_str}
- {hba1c_str}
- 当前用药：{meds}
- 饮食依从性：{ctx.diet_adherence}
- 运动依从性：{ctx.exercise_adherence}

规则：
1. 提供具体、可执行的建议（不是笼统的"注意饮食"）
2. 出现低血糖症状或严重高血糖时，优先建议就医
3. 回答简洁，不超过150字
4. 不替代医生诊断，必要时建议到内分泌科就诊"""

    def _mock_reply(self, ctx: CoachContext, user_message: str) -> str:
        if self._has_urgent_keywords(user_message):
            return "您的症状需要立即引起重视。请立即测量血糖，如血糖<3.9mmol/L请立即补充15g速效碳水（如半杯果汁/3块方糖）；如症状持续不缓解，请立即拨打120或前往急诊。"
        if "血糖高" in user_message or "控制不好" in user_message:
            return f"理解您的担忧。近期空腹血糖平均{sum(ctx.recent_fpg)/len(ctx.recent_fpg):.1f}mmol/L（目标<7.0），建议：① 减少晚餐主食量至平时2/3 ② 餐后散步20分钟 ③ 避免含糖饮料和甜点。持续记录血糖，下周复诊时带上记录给医生看。"
        if "吃什么" in user_message:
            return "建议选择低GI食物：全麦面包、燕麦、荞麦面、杂豆饭作为主食；蔬菜每日500g以上；蛋白质优选鱼虾去皮禽肉；水果选苹果、柚子、草莓，每次不超过100g，两餐之间食用。每日主食总量控制在250-400g。"
        return "记录得很好！继续坚持规律的血糖监测、合理饮食和适度运动。如果有任何不适或疑问，随时告诉我。"

    async def get_reply(self, ctx: CoachContext, user_message: str) -> str:
        system = self._build_system_prompt(ctx)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        try:
            return await llm_client.chat(messages)
        except Exception:
            return self._mock_reply(ctx, user_message)
