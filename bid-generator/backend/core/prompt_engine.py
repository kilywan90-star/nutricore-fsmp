"""
专业提示词工程系统
管理分行业、分标书类型的提示词模板，支持变量注入、版本管理
"""
import os
import re
import yaml
from dataclasses import dataclass, field
from typing import Optional

# ── 提示词模板目录 ──────────────────────────────

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


# ── 数据结构 ────────────────────────────────────

@dataclass
class BidContext:
    """标书生成上下文"""
    bidding_announcement: str = ""       # 招标公告全文
    project_requirements: str = ""       # 项目需求描述
    company_name: str = ""               # 投标公司名称
    company_info: str = ""               # 公司资质、业绩等信息
    industry: str = "政府采购"            # 行业分类
    bid_type: str = "货物采购"            # 标书类型
    key_points: str = ""                 # 重点突出内容
    budget: str = ""                     # 预算金额
    deadline: str = ""                   # 截止日期
    contact_info: str = ""               # 联系方式
    additional_requirements: str = ""    # 补充要求


# ── 系统提示词（所有行业共用） ────────────────────

SYSTEM_PROMPT_BASE = """## 角色定位
你是一位拥有15年以上招投标经验的资深标书撰写专家，精通政府采购、工程建设、服务外包、设备采购等各类招投标项目的标书撰写规范和评分标准。你熟悉《中华人民共和国招标投标法》及其实施条例，了解各行业的技术要求和商务条款。

## 核心能力
1. 精准解读招标文件，快速识别实质性要求、评分标准、资质门槛、废标风险点
2. 撰写结构完整、逻辑清晰、亮点突出的专业标书
3. 技术方案针对性强，能解决项目中的关键问题和难点
4. 商务条款完全响应，语言严谨规范
5. 能够突出投标方优势，规避潜在风险

## 工作原则
- 严格响应招标文件的所有实质性要求，不得出现负偏离
- 技术方案必须具体、可落地，禁止泛泛而谈
- 商务条款逐条响应，不得遗漏
- 公司资质和业绩展示与项目需求高度匹配
- 语言规范专业，杜绝口语化、错别字
- 对于需要用户填写的内容，用【待填写：具体内容】标注并给出填写建议
- 对于重要的评分点和加分项，在内容中重点突出

## 标书结构规范
根据标书类型，生成完整的标书结构，包括但不限于：
1. 投标函及投标函附录
2. 法定代表人身份证明及授权委托书
3. 投标保证金（如有）
4. 报价一览表及分项报价表
5. 技术方案/服务方案/施工组织设计
6. 项目管理机构及人员配置
7. 资格审查资料（营业执照、资质证书、财务报表等）
8. 类似项目业绩证明
9. 商务条款偏离表
10. 技术条款偏离表
11. 售后服务承诺及培训计划
12. 其他有利于中标的附加材料

## 输出格式
使用 Markdown 格式输出，层级分明，表格规范，重要内容加粗标注。
对于评分关键点，用 **【评分要点】** 标注。
每个章节之间用 `---` 分隔。"""


class PromptEngine:
    """提示词引擎：加载模板、注入变量、生成最终 prompt"""

    def __init__(self, prompts_dir: str = PROMPTS_DIR):
        self._prompts_dir = prompts_dir
        self._cache: dict[str, dict] = {}

    # ── 模板加载 ────────────────────────────────

    def load_template(self, industry: str, bid_type: str) -> dict:
        """加载指定行业和标书类型的提示词模板"""
        cache_key = f"{industry}:{bid_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        file_name = f"{industry}_{bid_type}.yaml"
        file_path = os.path.join(self._prompts_dir, file_name)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                template = yaml.safe_load(f)
        else:
            # Fallback to generic template
            generic_path = os.path.join(self._prompts_dir, "通用_通用.yaml")
            if os.path.exists(generic_path):
                with open(generic_path, "r", encoding="utf-8") as f:
                    template = yaml.safe_load(f)
            else:
                template = self._get_hardcoded_generic()

        self._cache[cache_key] = template
        return template

    def list_industries(self) -> list[str]:
        """列出所有可用的行业分类"""
        industries = set()
        for fname in os.listdir(self._prompts_dir):
            if fname.endswith(".yaml"):
                parts = fname.replace(".yaml", "").split("_")
                if parts:
                    industries.add(parts[0])
        return sorted(industries)

    def list_bid_types(self, industry: str) -> list[str]:
        """列出指定行业下的标书类型"""
        types = []
        prefix = f"{industry}_"
        for fname in os.listdir(self._prompts_dir):
            if fname.startswith(prefix) and fname.endswith(".yaml"):
                name = fname[len(prefix):-5]
                types.append(name)
        return sorted(types)

    # ── 核心方法：构建完整提示词 ──────────────────

    def build_messages(self, ctx: BidContext) -> list[dict]:
        """根据上下文构建发送给 LLM 的完整 messages 列表"""
        template = self.load_template(ctx.industry, ctx.bid_type)
        user_prompt = self._build_user_prompt(template, ctx)

        return [
            {"role": "user", "content": user_prompt}
        ]

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT_BASE

    def build_full_messages(self, ctx: BidContext) -> list[dict]:
        """构建包含 system + user 的完整 messages"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT_BASE},
            {"role": "user", "content": self._build_user_prompt(
                self.load_template(ctx.industry, ctx.bid_type), ctx
            )}
        ]

    # ── 章节重新生成 ──────────────────────────────

    def build_section_messages(
        self, ctx: BidContext, section_name: str, existing_content: str, feedback: str = ""
    ) -> list[dict]:
        """构建单章节重新生成的 messages"""
        prompt = f"""请重新撰写标书的【{section_name}】章节。

## 项目背景
行业：{ctx.industry}
标书类型：{ctx.bid_type}
公司名称：{ctx.company_name}

## 当前内容
{existing_content}

## 修改要求
{feedback or "请优化该章节的内容，使其更加专业、完整、有说服力。"}

请只输出【{section_name}】章节的完整内容，使用 Markdown 格式。"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT_BASE},
            {"role": "user", "content": prompt},
        ]

    # ── 内部方法 ──────────────────────────────────

    def _build_user_prompt(self, template: dict, ctx: BidContext) -> str:
        """用上下文变量填充提示词模板"""
        raw = template.get("prompt", "")

        # 变量映射
        variables = {
            "bidding_announcement": ctx.bidding_announcement or "（由用户提供）",
            "project_requirements": ctx.project_requirements or "（由用户提供）",
            "company_name": ctx.company_name or "【请填写公司名称】",
            "company_info": ctx.company_info or "（由用户提供企业资质、业绩、人员等信息）",
            "industry": ctx.industry,
            "bid_type": ctx.bid_type,
            "key_points": ctx.key_points or "（无特别要求）",
            "budget": ctx.budget or "（见招标文件）",
            "deadline": ctx.deadline or "（见招标文件）",
            "contact_info": ctx.contact_info or "【请填写联系方式】",
            "additional_requirements": ctx.additional_requirements or "（无）",
            "bid_structure": template.get("structure", self._default_structure()),
            "industry_notes": template.get("industry_notes", ""),
            "scoring_emphasis": template.get("scoring_emphasis", ""),
        }

        # 模板变量替换 {{ variable_name }}
        def replacer(match):
            key = match.group(1)
            return str(variables.get(key, match.group(0)))

        return re.sub(r"\{\{\s*(\w+)\s*\}\}", replacer, raw)

    def _default_structure(self) -> str:
        return """1. 投标函及投标函附录
2. 法定代表人身份证明及授权委托书
3. 投标保证金
4. 报价一览表及分项报价表
5. 技术方案/服务方案
6. 项目管理机构及人员配置
7. 资格审查资料
8. 类似项目业绩
9. 商务条款偏离表
10. 技术条款偏离表
11. 售后服务承诺
12. 其他材料"""

    def _get_hardcoded_generic(self) -> dict:
        return {
            "name": "通用标书模板",
            "industry": "通用",
            "bid_type": "通用",
            "version": 1,
            "prompt": """请根据以下信息，生成一份完整、专业、高中标率的投标文件。

## 项目信息
- 行业分类：{{ industry }}
- 标书类型：{{ bid_type }}
- 截止日期：{{ deadline }}
- 预算金额：{{ budget }}

## 招标公告/招标文件内容
{{ bidding_announcement }}

## 项目需求
{{ project_requirements }}

## 投标方信息
- 公司名称：{{ company_name }}
- 公司资质与业绩：{{ company_info }}

## 重点突出
{{ key_points }}

## 补充要求
{{ additional_requirements }}

## 标书结构要求
{{ bid_structure }}

## 行业注意事项
{{ industry_notes }}

## 评分侧重点
{{ scoring_emphasis }}

请严格按照上述结构生成完整的标书内容。每个章节独立成段，用 `---` 分隔。
对于需要进一步填写的内容，用【待填写：xxx】标注并给出填写建议。
对于评分关键点，用 **【评分要点】** 标注。""",
            "structure": "",
            "industry_notes": "严格按照招标文件要求逐条响应，不得出现负偏离。",
            "scoring_emphasis": "技术方案的针对性和可实施性、类似项目业绩的数量和质量、报价的合理性。",
        }
