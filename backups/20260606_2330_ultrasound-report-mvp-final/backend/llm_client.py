"""阿里云百炼 qwen-plus 结构化提取 — v3 ABCDEF流水线 + 长沙医院模板"""

import json
import os
import re
import time
import logging
from openai import OpenAI
from openai import APIError, APITimeoutError

from templates import match_template as match_tpl_key, TEMPLATES
from template_loader import (
    match_template as match_formal_template,
    match_templates_multi,
    format_template_for_prompt,
    load_templates,
)

from knowledge.loader import get_kb

MAX_RETRIES = 2

# ICD-10 编码表：优先从知识库加载，回退到硬编码
def _load_icd10_map() -> dict:
    try:
        kb = get_kb()
        if hasattr(kb, 'normal_ranges') and kb.normal_ranges:
            icd10_section = kb.normal_ranges.get('icd10_codes', {})
            if icd10_section:
                return icd10_section
    except Exception:
        pass
    return {
    "K76.0": "脂肪肝", "K74.6": "肝硬化", "K80.0": "胆囊结石伴急性胆囊炎",
    "K80.1": "胆囊结石伴慢性胆囊炎", "K80.2": "胆囊结石", "K80.3": "胆管结石",
    "K80.5": "胆总管结石", "K81.0": "急性胆囊炎", "K81.1": "慢性胆囊炎",
    "K85.9": "急性胰腺炎", "K35.9": "急性阑尾炎", "K40.9": "腹股沟疝",
    "K82.8": "胆囊息肉", "Q44.6": "肝囊肿", "Q44.7": "多囊肝",
    "D18.0": "肝血管瘤", "C22.9": "肝癌", "N28.1": "肾囊肿",
    "N20.0": "肾结石", "N20.9": "泌尿系结石", "N13.3": "肾积水",
    "N40": "前列腺增生", "N40.0": "前列腺增生", "C64": "肾细胞癌",
    "D30.0": "肾错构瘤", "Q61.2": "多囊肾", "N18.9": "慢性肾病",
    "C67.9": "膀胱肿瘤", "D25.9": "子宫肌瘤", "D25.0": "子宫粘膜下肌瘤",
    "N80.0": "子宫腺肌症", "N84.0": "子宫内膜息肉", "N83.2": "卵巢囊肿",
    "D27.9": "卵巢畸胎瘤", "N70.1": "输卵管积水", "O20.9": "妊娠期出血",
    "O34.2": "子宫切口憩室", "O44.0": "胎盘低置", "O00.9": "异位妊娠",
    "O01.9": "葡萄胎", "O44.9": "前置胎盘", "O45.9": "胎盘早剥",
    "I05.0": "二尖瓣狭窄", "I34.0": "二尖瓣关闭不全", "I34.1": "二尖瓣脱垂",
    "I35.0": "主动脉瓣狭窄", "I35.1": "主动脉瓣关闭不全",
    "I07.1": "三尖瓣关闭不全", "I42.0": "扩张型心肌病",
    "I42.1": "肥厚型心肌病", "I25.1": "冠心病",
    "I50.9": "心力衰竭", "I31.3": "心包积液", "I27.0": "肺动脉高压",
    "I71.9": "主动脉瘤", "I71.4": "腹主动脉瘤",
    "Q21.0": "室间隔缺损", "Q21.1": "房间隔缺损", "Q25.0": "动脉导管未闭",
    "Q21.3": "法洛四联症", "D15.1": "左心房粘液瘤",
    "I70.0": "动脉粥样硬化", "I65.2": "颈动脉狭窄", "I74.3": "下肢动脉闭塞",
    "I80.2": "深静脉血栓", "E05.0": "甲亢", "E04.1": "甲状腺结节",
    "C73": "甲状腺癌", "N60.9": "乳腺纤维腺瘤", "N60.1": "乳腺增生",
    "C50.9": "乳腺癌", "R16.1": "脾大", "R18": "腹水",
    "R59.9": "淋巴结肿大", "Q89.2": "甲状舌管囊肿", "E21.0": "甲状旁腺腺瘤",
    "R33": "尿潴留", "K11.2": "腮腺炎", "C62.9": "睾丸肿瘤",
    "C54.9": "子宫体癌", "C56": "卵巢癌", "E06.3": "桥本氏甲状腺炎",
    "I51.7": "心脏扩大", "I51.8": "其他心脏疾病", "I33.0": "感染性心内膜炎",
    "I30.1": "缩窄性心包炎", "I81": "门静脉血栓", "I83.9": "下肢静脉曲张",
}

ICD10_MAP = _load_icd10_map()

# 确保模板已加载
load_templates()


_client: OpenAI | None = None


# 模型选择: 可通过环境变量 MODEL_PROFILE 控制
# - "fast": qwen-turbo (快速, ~3-10s)
# - "balanced": qwen-plus (默认, 平衡, ~8-30s)  
# - "quality": qwen-max (高质量, ~15-45s)
# - "deepseek": deepseek-v4-flash (超快, ~2-8s, 需DEEPSEEK_API_KEY)
MODEL_PROFILE = os.getenv("MODEL_PROFILE", "balanced")

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

MODEL_MAP = {
    "fast": {"b": "qwen-turbo", "ef": "qwen-turbo"},
    "balanced": {"b": "qwen-plus", "ef": "qwen-plus"},
    "quality": {"b": "qwen-max", "ef": "qwen-vl-max"},
    "deepseek": {"b": "deepseek-v4-flash", "ef": "deepseek-v4-flash"},
}
MODELS = MODEL_MAP.get(MODEL_PROFILE, MODEL_MAP["balanced"])

def _get_client(provider="dashscope") -> OpenAI:
    """复用单例 OpenAI 客户端（支持阿里云百炼和DeepSeek）"""
    global _client
    
    if provider == "deepseek" and DEEPSEEK_API_KEY:
        # 使用DeepSeek API
        return OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=60,
        )
    
    # 默认使用阿里云百炼
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            timeout=60,
        )
    return _client


def _system_prompt(exam_type: str, formal_tpl: dict | None = None) -> str:
    tpl_key = match_tpl_key(exam_type)
    tpl = TEMPLATES.get(tpl_key, TEMPLATES["abdomen"])

    # 正式模板参考
    formal_ref = ""
    if formal_tpl:
        formal_ref = f"""
## 正式模板参考（请按此格式输出）

{format_template_for_prompt(formal_tpl)}
"""

    return f"""你是一位资深超声科主任医师。将口语化的超声检查口述转换为规范化超声报告。

当前检查类型: {tpl["name"]}
覆盖脏器: {"、".join(tpl["organs"])}
{formal_ref}
## 规则
1. 口述中缺失的测量值填"___mm"占位，绝不编造数值
2. 口语转标准术语（"肝有点大"→"肝脏形态饱满"，"胆囊没有"→"胆囊未见异常"）
3. study_see 按脏器分段，每段格式: "脏器名: 描述。"
4. study_hint 每条一行，按临床重要性排序
5. study_hint 标注 ICD-10（格式 "K76.0 脂肪肝"）
6. 口述中提及的每一个脏器都在 study_see 中出现（包括正常脏器）
7. patient_info 全部填 null
8. 只输出 JSON

## 输出 JSON Schema
{{
  "patient_info": {{ "name": null, "gender": null, "age": null, "exam_id": null }},
  "exam_info": {{ "modality": "{tpl["name"]}", "device": null, "exam_date": null }},
  "study_see": "脏器分段描述的完整所见文本。每段格式: 脏器名: 描述。\\n例如: 肝脏: 形态大小正常，实质回声均匀。\\n胆囊: 大小正常，囊壁光滑，腔内未见异常回声。",
  "study_hint": [
    {{ "rank": 1, "diagnosis": "疾病名", "icd10": "K76.0 脂肪肝" }}
  ],
  "recommendation": "建议文字"
}}"""


def _extract_json(content: str) -> str:
    content = content.strip()
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
    if m:
        return m.group(1).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return content[start: end + 1]
    return content


def _parse_json(content: str) -> dict:
    json_str = _extract_json(content)
    errors = []

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        errors.append(f"直接解析: {e}")

    try:
        fixed = json_str.rstrip()
        open_braces = fixed.count("{") - fixed.count("}")
        open_brackets = fixed.count("[") - fixed.count("]")
        in_string = fixed.count('"') % 2 != 0
        if in_string:
            fixed += '"'
        fixed += "]" * open_brackets + "}" * open_braces
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        errors.append(f"补全括号: {e}")

    lines = json_str.split("\n")
    for cut in range(1, min(5, len(lines))):
        try:
            return _parse_json("\n".join(lines[:-cut]))
        except Exception:
            pass

    raise ValueError(f"JSON 解析失败: {'; '.join(errors)}")


def _enrich_icd10(report: dict) -> dict:
    for imp in report.get("study_hint", []):
        icd10 = imp.get("icd10", "") or ""
        if not icd10.strip():
            continue
        code_only = icd10.strip().split()[0]
        name = ICD10_MAP.get(code_only, "")
        if name and name not in icd10:
            imp["icd10"] = f"{code_only} {name}"
    return report


def structure_report(raw_text: str, exam_type: str = "腹部超声") -> dict:
    """结构化提取：输出 study_see + study_hint 双层格式"""
    client = _get_client()

    # P0-2: 匹配正式模板
    formal_tpl = match_formal_template(raw_text, exam_type)

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": _system_prompt(exam_type, formal_tpl)},
                    {"role": "user", "content": (
                        f"请将以下{exam_type}检查口述转换为规范化超声报告"
                        f"（注意：study_see 必须包含口述中提到的每一个脏器）：\n\n{raw_text}"
                    )},
                ],
                temperature=0.1,
                max_tokens=4096,
                timeout=30,
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("LLM 返回空内容")

            report = _parse_json(content)
            report = _enrich_icd10(report)
            return report

        except (APIError, APITimeoutError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                import time
                time.sleep(1.5 ** attempt)
                continue
            raise RuntimeError(f"LLM API 调用失败(已重试{MAX_RETRIES}次): {e}") from e

        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"结构化输出解析失败: {e}") from e

    raise RuntimeError(f"结构化失败: {last_error}")


def _extract_plain_text(html_or_text: str) -> str:
    text = re.sub(r'<[^>]+>', '', html_or_text or "")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


_log = logging.getLogger(__name__)


def generate_free_report(asr_text: str, exam_type: str = "腹部超声") -> dict:
    """B路: 自由生成报告 (使用配置的模型)"""
    # 根据模型名称选择provider
    provider = "deepseek" if MODELS["b"].startswith("deepseek") else "dashscope"
    client = _get_client(provider)
    model = MODELS["b"]  # 根据配置选择模型
    system = f"""一位资深超声科主任医师，将口语化口述转为规范化超声报告。
检查类型: {exam_type}
规则: 缺失值填___mm占位，口语转术语，按脏器分段，只输出JSON。
输出格式: {{"study_see": "...", "study_hint": [...], "recommendation": "..."}}"""

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model, messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"请将以下口述转为规范化报告:\n\n{asr_text}"},
                ], temperature=0.1, max_tokens=4096, timeout=30)
            content = response.choices[0].message.content
            if not content: raise RuntimeError("empty")
            r = _parse_json(content)
            r["_method"] = "b_free_gen"
            return r
        except Exception as e:
            if attempt < 1: time.sleep(1.0); continue
            _log.warning(f"B fail: {e}")
    return {"study_see": f"<div class='rpt-html'>{asr_text}</div>", "study_hint": [], "recommendation": "", "_method": "b_fallback"}


def generate_lightweight_report(asr_text: str, exam_type: str = "腹部超声") -> dict:
    """快速通道: 单次轻量LLM生成报告 (固定qwen-turbo, 精简prompt)

    用于ASR高置信度场景，跳过ABCDEF多路流水线，直接一次调用生成结构化报告。
    """
    from rule_engine import get_rule
    routing_cfg = get_rule("pipeline.dynamic_routing", {})
    model = routing_cfg.get("fast_path_model", "qwen-turbo")
    max_tokens = routing_cfg.get("fast_path_max_tokens", 2048)
    temperature = routing_cfg.get("fast_path_temperature", 0.05)

    client = _get_client("dashscope")
    system = f"""超声科主任医师，将口述转为规范化报告。检查类型:{exam_type}
规则:缺失值填___mm,口语转术语,按脏器分段,只输出JSON
格式:{{"study_see":"...","study_hint":[...],"recommendation":"..."}}"""

    for attempt in range(1):
        try:
            response = client.chat.completions.create(
                model=model, messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"口述转报告:\n{asr_text}"},
                ], temperature=temperature, max_tokens=max_tokens, timeout=20)
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("empty")
            r = _parse_json(content)
            r["_method"] = "lightweight"
            return r
        except Exception as e:
            _log.warning(f"lightweight LLM fail: {e}")
    return {"study_see": f"<div class='rpt-html'>{asr_text}</div>",
            "study_hint": [], "recommendation": "", "_method": "lightweight_fallback"}


# ── EF合并: v4-flash 一次完成模板选择+填充+交叉验证 ──

def _ef_combined_system_prompt(exam_type: str) -> str:
    return f"""资深超声科主任医师，完成超声报告的模板选择、变量填充和最终审核。检查类型: {exam_type}

## 你的5项任务 (按顺序)

### 1. 选模板
从候选模板列表中选出最匹配ASR原文的一条。如果ASR原文过短或与所有候选模板都不匹配，选择最接近的模板并在reasoning中说明。

### 2. 数值保全 (最高优先级 — 违反此项视为严重错误)
**硬性规则: ASR原文中出现的每一个数值和测量结果，必须在输出中原样保留，不得遗漏、换算或修改。**
- 禁止单位换算: ASR说"5.4×4.8cm"就必须输出"5.4×4.8cm"，绝不允许转成"54mm"或"54×48mm"
- 禁止数值合并: ASR说"1.2×0.8"就必须完整保留两个维度，不允许只写一个
- 保留修饰词: ASR说"约28.5cm"就输出"约28.5cm"，不要丢掉"约"字
- 保留原始单位: ASR用cm就输出cm，ASR用mm就输出mm，不要自行换算
- 如果模板没有合适的位置放某个数值，将该数值追加到study_see末尾，格式为: "<b class=\\"voice\\">补充测量: 数值内容</b>"

### 3. 填变量
- 模板中的占位符(如 __mm, ___cm, x mm 等)用ASR原文中的对应数值填充
- **只填写ASR原文中明确提到的内容, ASR未提及的占位符保留原样(写 __)**
- **绝对不要删除含有占位符的整句或整段** — 模板是骨架, 医生会在系统上手动补充未填的内容
- **绝对不要编造ASR原文中没有的数值** — 没有就留 __
- "[选项A;选项B;选项C]" → 只保留一个正确选项
- 用 <b class="voice">值</b> 标记AI填充值(绿色), 未填写保留 __ 即可(系统会自动标橙色)
- [选项A;选项B;选项C] → 语音命中的选项用 <b class="voice">选项</b> 绿色标记

### 4. 交叉验证
对比所有来源(B自由生成/C规则引擎/D规则增强)，标记冲突并选择最可靠的值。
**当ASR原文有明确数值时，ASR原文优先级最高，高于任何模板默认值或推断值。**

### 5. 不改变模板结构
段落、标题、标点、顺序一律不动。**含有 __ 占位符的句子必须保留, 不得删除。** 模板是给医生用的半成品框架, 未填写的部分由医生在系统中手动补充。

## 输出JSON
{{"template_name":"...", "filled_study_see_html":"...", "study_hint":[...], "recommendation":"...", "confidence":0.9, "conflicts":[{{"field":"...", "sources":{{}}, "resolution":"..."}}], "reasoning":"..."}}"""


def select_fill_and_validate(
    asr_text: str, b_result: dict | None, c_result: dict | None,
    d_result: dict | None, exam_type: str, candidates: list[dict],
) -> dict:
    """EF合并: 一次v4-flash调用完成模板选择+填充+交叉验证"""
    from template_loader import get_template_by_name
    from rule_engine import get_rule
    client = _get_client()

    # 加载字段ASR提示词，注入到system prompt中帮助v4-flash精准匹配
    field_hints = get_rule("extraction.field_asr_hints", {})
    hints_text = ""
    if field_hints:
        hint_parts = []
        for field_id, info in list(field_hints.items())[:20]:
            kwds = "、".join(info.get("keywords", [])[:4])
            unit = info.get("unit", "")
            rng = info.get("range", [])
            
            # P0-2: 增加数值范围校验提示
            range_hint = f" (合理范围:{rng[0]}-{rng[1]})" if len(rng) == 2 else ""
            hint_parts.append(f"- {field_id}: 搜索\"{kwds}\" 单位{unit}{range_hint}")
        
        hints_text = "\n## 字段ASR搜索提示\n" + "\n".join(hint_parts)
        hints_text += "\n\n### 重要提醒\n- 如果提取的数值超出合理范围,请标记为冲突并在conflicts中说明\n- 优先使用C路(规则引擎)提取的数值,因为它们经过正则精确匹配"

    cand_parts = []
    for c in candidates[:8]:
        tpl = get_template_by_name(c["name"])
        if tpl:
            cand_parts.append(f"### {c['name']} (模块:{c.get('module','')})\n{tpl.get('info1','')[:500]}")
    cand_text = "\n\n".join(cand_parts)

    b_see = _extract_plain_text(b_result.get("study_see", ""))[:400] if b_result else "(无)"
    b_hint = json.dumps(b_result.get("study_hint", []), ensure_ascii=False)[:200] if b_result else "[]"
    c_see = _extract_plain_text(c_result.get("study_see", ""))[:400] if c_result else "(无)"
    c_hint = json.dumps(c_result.get("study_hint", []), ensure_ascii=False)[:200] if c_result else "[]"
    d_see = _extract_plain_text(d_result.get("study_see", ""))[:400] if d_result else "(无)"
    d_hint = json.dumps(d_result.get("study_hint", []), ensure_ascii=False)[:200] if d_result else "[]"

    user_msg = f"""## ASR(A路)\n{asr_text[:500]}\n## B路(自由生成)\nsee: {b_see}\nhint: {b_hint}\n## C路(规则引擎)\nsee: {c_see}\nhint: {c_hint}\n## D路(规则增强)\nsee: {d_see}\nhint: {d_hint}\n## 候选模板\n{cand_text}{hints_text}"""

    # 根据EF模型名称选择provider
    ef_provider = "deepseek" if MODELS["ef"].startswith("deepseek") else "dashscope"
    client = _get_client(ef_provider)
    
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODELS["ef"], messages=[  # 根据配置选择EF模型
                    {"role": "system", "content": _ef_combined_system_prompt(exam_type)},
                    {"role": "user", "content": user_msg},
                ], temperature=0.1, max_tokens=4096, timeout=30)
            content = response.choices[0].message.content
            if not content: raise RuntimeError("empty")
            r = _parse_json(content)
            r["_method"] = "ef_combined"
            return r
        except Exception as e:
            if attempt < 1: time.sleep(1.0); continue
            _log.warning(f"EF combined fail: {e}")

    # Fallback to C result
    return {
        "template_name": candidates[0]["name"] if candidates else "未知",
        "filled_study_see_html": c_result.get("study_see", "") if c_result else f"<div class='rpt-html'>{asr_text}</div>",
        "study_hint": c_result.get("study_hint", []) if c_result else [],
        "recommendation": "", "confidence": 0.3, "conflicts": [],
        "reasoning": "EF回退到规则引擎", "_method": "ef_fallback",
    }
