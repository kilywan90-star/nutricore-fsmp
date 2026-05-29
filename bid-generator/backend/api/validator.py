"""
标书智能校验 API
检查完整性、格式规范、评分覆盖、风险条款
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.sqlite import get_db, Project, Config
from core.llm_client import DeepSeekClient, LLMConfig, get_client as get_llm_client

logger = logging.getLogger(__name__)
router = APIRouter()


class ValidateRequest(BaseModel):
    project_id: int
    check_types: list[str] = ["completeness", "scoring", "format", "risk"]


def _get_config_from_db(db: Session) -> LLMConfig:
    config = LLMConfig()
    db_configs = db.query(Config).all()
    config_map = {c.key: c.value for c in db_configs}
    if "llm_api_key" in config_map:
        config.api_key = config_map["llm_api_key"]
    if "llm_api_base" in config_map:
        config.api_base = config_map["llm_api_base"]
    if "llm_model" in config_map:
        config.model = config_map["llm_model"]
    return config


# ── 规则引擎（非 AI，直接跑） ─────────────────────

def _check_format(bid_content: str, requirements: dict) -> list[dict]:
    """基于规则的格式检查"""
    issues = []

    if not bid_content or len(bid_content.strip()) < 500:
        issues.append({
            "type": "format",
            "severity": "high",
            "message": "标书内容过短，可能未生成或生成不完整",
            "section": "全文",
            "suggestion": "请重新生成完整标书"
        })
        return issues

    # 检查是否有章节结构
    if "## " not in bid_content and "# " not in bid_content:
        issues.append({
            "type": "format",
            "severity": "medium",
            "message": "缺少 Markdown 标题层级，标书结构不清晰",
            "section": "全文",
            "suggestion": "确保标书使用 # 和 ## 标题建立清晰的层级结构"
        })

    # 检查必要章节
    required_sections = ["投标函", "报价", "方案", "资格"]
    for section in required_sections:
        if section not in bid_content:
            issues.append({
                "type": "format",
                "severity": "medium",
                "message": f'可能缺少"{section}"相关章节',
                "section": "全文",
                "suggestion": f'请确认标书包含了"{section}"相关内容'
            })

    # 检查错别字（简单规则）
    common_typos = {
        "在来一份": "再来一份",
        "投标保证经": "投标保证金",
    }
    for wrong, correct in common_typos.items():
        if wrong in bid_content:
            issues.append({
                "type": "typo",
                "severity": "low",
                "message": f'疑似错别字："{wrong}" 应为 "{correct}"',
                "section": "全文",
                "suggestion": f"将 {wrong} 替换为 {correct}"
            })

    return issues


def _check_completeness(bid_content: str, requirements: dict) -> list[dict]:
    """基于规则的完整性检查"""
    issues = []

    if isinstance(requirements, dict):
        mandatory_docs = requirements.get("mandatory_documents", [])
        if mandatory_docs:
            for doc in mandatory_docs:
                if doc not in bid_content:
                    issues.append({
                        "type": "missing",
                        "severity": "high",
                        "message": f'招标文件要求的"{doc}"未在标书中找到',
                        "section": "资格审查",
                        "suggestion": f"请添加{doc}，否则可能导致废标"
                    })

        # 检查风险点
        risk_points = requirements.get("risk_points", [])
        for risk in risk_points:
            issues.append({
                "type": "risk_reminder",
                "severity": "high",
                "message": f"招标文件风险提示：{risk}",
                "section": "全文",
                "suggestion": "请在标书中正面回应上述风险点，避免被判定为未响应"
            })

    return issues


@router.post("/validate")
async def validate_bid(req: ValidateRequest, db: Session = Depends(get_db)):
    """智能校验标书 — 规则引擎 + AI 审核"""
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not project.bid_content:
        raise HTTPException(status_code=400, detail="项目标书内容为空，请先生成标书")

    bid_content = project.bid_content
    requirements = project.requirements or {}

    all_issues = []

    # 1. 规则引擎检查
    if "format" in req.check_types or not req.check_types:
        all_issues.extend(_check_format(bid_content, requirements))

    if "completeness" in req.check_types or not req.check_types:
        all_issues.extend(_check_completeness(bid_content, requirements))

    # 2. AI 深度审核
    if "scoring" in req.check_types or "risk" in req.check_types:
        try:
            llm_config = _get_config_from_db(db)
            client = get_llm_client(llm_config)

            ai_prompt = f"""你是一位资深标书审核专家。请对以下标书进行全面审核。

## 招标要求
{json.dumps(requirements, ensure_ascii=False, indent=2)}

## 标书内容
{bid_content[:8000]}

## 请从以下维度审核（JSON 格式返回）：
```json
{{
  "overall_score": 85,
  "scoring_analysis": [
    {{"item": "评分项名称", "current_score": "预计得分", "max_score": "满分", "improvement": "改进建议"}}
  ],
  "risk_warnings": [
    {{"level": "high/medium/low", "description": "风险描述", "impact": "可能导致废标/扣分/印象分降低", "fix": "修改建议"}}
  ],
  "format_issues": [
    {{"location": "位置", "issue": "问题描述", "fix": "修改建议"}}
  ],
  "missing_items": ["投标函缺少法人签字栏", "..."],
  "improvement_summary": "整体改进建议摘要"
}}
```

请严格基于标书内容进行分析，不要凭空猜测。"""

            result = await client.chat(
                messages=[{"role": "user", "content": ai_prompt}],
                system="你是一位拥有20年经验的招投标审核专家。请严格、专业地审核标书。",
                temperature=0.2,
            )
            content = result["choices"][0]["message"]["content"]
            usage = client.get_total_usage()
            await client.close()

            # 解析 AI 审核结果
            try:
                import re
                json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                ai_result = json.loads(json_match.group(1)) if json_match else json.loads(content)
            except (json.JSONDecodeError, AttributeError):
                ai_result = {"raw_analysis": content}

            # 将 AI 发现的问题合并到 all_issues
            for risk in ai_result.get("risk_warnings", []):
                all_issues.append({
                    "type": "risk",
                    "severity": risk.get("level", "medium"),
                    "message": risk.get("description", ""),
                    "section": "全文",
                    "suggestion": risk.get("fix", ""),
                    "impact": risk.get("impact", "")
                })

            for item in ai_result.get("missing_items", []):
                all_issues.append({
                    "type": "missing",
                    "severity": "high",
                    "message": item,
                    "section": "全文",
                    "suggestion": "请补充上述缺失内容"
                })

            overall_score = ai_result.get("overall_score", 0)
            scoring_analysis = ai_result.get("scoring_analysis", [])
            improvement_summary = ai_result.get("improvement_summary", "")

        except Exception as e:
            logger.error(f"AI validation failed: {e}")
            overall_score = 0
            scoring_analysis = []
            improvement_summary = f"AI审核暂时不可用: {str(e)}"
            usage = None

    else:
        overall_score = 0
        scoring_analysis = []
        improvement_summary = ""
        usage = None

    # 分类汇总
    errors = [i for i in all_issues if i["severity"] == "high"]
    warnings = [i for i in all_issues if i["severity"] == "medium"]
    suggestions = [i for i in all_issues if i["severity"] == "low"]

    return {
        "status": "success",
        "data": {
            "project_id": req.project_id,
            "overall_score": overall_score,
            "total_issues": len(all_issues),
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "scoring_analysis": scoring_analysis,
            "improvement_summary": improvement_summary,
            "usage": {
                "total_tokens": usage.total_tokens if usage else 0,
                "estimated_cost_rmb": round(usage.cost, 4) if usage else 0,
            } if usage else None
        }
    }


@router.post("/quick-check")
async def quick_check(project_id: int, db: Session = Depends(get_db)):
    """快速格式检查（仅规则引擎，不消耗 AI token）"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not project.bid_content:
        return {"status": "success", "data": {"issues": [], "message": "标书内容为空"}}

    issues = _check_format(project.bid_content, project.requirements or {})
    return {
        "status": "success",
        "data": {
            "project_id": project_id,
            "issue_count": len(issues),
            "issues": issues,
            "message": "快速检查完成（仅格式检查，未消耗AI token）"
        }
    }
