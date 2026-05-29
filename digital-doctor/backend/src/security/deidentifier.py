import re

# 手机号：1开头的11位数字
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
# 身份证：18位或15位
ID_CARD_PATTERN = re.compile(r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]")
ID_CARD_PATTERN_OLD = re.compile(r"\d{15}")
# 中文姓名：2-4个中文字符
CN_NAME_PATTERN = re.compile(r"(患者|姓名|联系人|家属)[：:]*\s*[一-龥]{2,4}")
CN_NAME_SIMPLE = re.compile(r"[一-龥]{2,4}(?=(，|。|,|\.|;|；|\s|男|女|先生|女士))")
# 地址关键词
ADDRESS_KEYWORDS = re.compile(r"(地址|住址|现住址|户籍地)[：:]*\s*.{5,50}(?=[，。,\.;；\s]|$)")


def mask_phi(text: str) -> str:
    if not text:
        return ""
    text = PHONE_PATTERN.sub("PHONE***", text)
    text = ID_CARD_PATTERN.sub("ID***", text)
    text = ID_CARD_PATTERN_OLD.sub("ID***", text)
    text = CN_NAME_PATTERN.sub(lambda m: m.group(1) + "***", text)
    text = ADDRESS_KEYWORDS.sub(lambda m: m.group(1) + "***", text)
    return text


def deidentify_clinical_text(text: str | None) -> str:
    if not text:
        return ""
    return mask_phi(text)
