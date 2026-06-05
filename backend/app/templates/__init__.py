from .breast import BreastSchema, BREAST_FEW_SHOT
from .abdominal import AbdominalSchema, ABDOMINAL_FEW_SHOT

TEMPLATE_REGISTRY = {
    "breast": {
        "schema": BreastSchema,
        "few_shot": BREAST_FEW_SHOT,
        "system_prompt": "你是一个乳腺超声报告专家。请根据医生的口述，精确提取字段。当前文本可能由语音转写存在同音字错误，请先结合医学常识纠错再提取。必须输出纯JSON，严禁任何多余解释。"
    },
    "abdominal": {
        "schema": AbdominalSchema,
        "few_shot": ABDOMINAL_FEW_SHOT,
        "system_prompt": "你是一个腹部超声报告专家。请根据医生的口述，精确提取字段。当前文本可能由语音转写存在同音字错误，请先结合医学常识纠错再提取。必须输出纯JSON，严禁任何多意解释。"
    }
}
