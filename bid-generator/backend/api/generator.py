"""
标书 AI 生成 API
支持一键生成、流式生成、章节重新生成、进度查询
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.sqlite import get_db, Project, Config
from core.llm_client import DeepSeekClient, LLMConfig, get_client as get_llm_client
from core.prompt_engine import PromptEngine, BidContext

logger = logging.getLogger(__name__)
router = APIRouter()

# 生成任务状态缓存（内存，生产环境应迁移到 Redis）
_generation_tasks: dict[str, dict] = {}


# ── 请求模型 ──────────────────────────────────────

class GenerateRequest(BaseModel):
    project_id: int
    industry: str = "通用"
    bid_type: str = "通用"
    company_name: str = ""
    company_info: str = ""
    key_points: str = ""
    budget: str = ""
    additional_requirements: str = ""


class RegenerateSectionRequest(BaseModel):
    project_id: int
    section_name: str
    feedback: str = ""


class ParseTenderRequest(BaseModel):
    project_id: int
    tender_content: str     # 已提取的招标文件文本


# ── 内部辅助 ──────────────────────────────────────

def _get_config_from_db(db: Session) -> LLMConfig:
    """从数据库读取 LLM 配置"""
    config = LLMConfig()
    db_configs = db.query(Config).all()
    config_map = {c.key: c.value for c in db_configs}

    if "llm_api_key" in config_map:
        config.api_key = config_map["llm_api_key"]
    if "llm_api_base" in config_map:
        config.api_base = config_map["llm_api_base"]
    if "llm_model" in config_map:
        config.model = config_map["llm_model"]
    if "llm_temperature" in config_map:
        config.temperature = float(config_map["llm_temperature"])

    return config


def _build_context(project: Project, req: GenerateRequest) -> BidContext:
    """从请求和项目数据构建 BidContext"""
    requirements_json = project.requirements or {}
    if isinstance(requirements_json, str):
        try:
            requirements_json = json.loads(requirements_json)
        except (json.JSONDecodeError, TypeError):
            requirements_json = {}

    return BidContext(
        bidding_announcement=requirements_json.get("raw_content", project.description or ""),
        project_requirements=requirements_json.get("requirements", project.description or ""),
        company_name=req.company_name,
        company_info=req.company_info,
        industry=req.industry,
        bid_type=req.bid_type,
        key_points=req.key_points,
        budget=req.budget,
        deadline=project.deadline or "",
        additional_requirements=req.additional_requirements,
    )


async def _stream_generator(client: DeepSeekClient, messages: list[dict]) -> AsyncGenerator[str, None]:
    """SSE 流式输出的异步生成器"""
    try:
        async for chunk in client.chat_stream(messages):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Stream generation error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        await client.close()


# ── API 路由 ──────────────────────────────────────

@router.post("/generate")
async def generate_bid(req: GenerateRequest, db: Session = Depends(get_db)):
    """一键生成完整标书（非流式）"""
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 更新项目状态
    project.status = "generating"
    db.commit()

    try:
        # 构建上下文和提示词
        llm_config = _get_config_from_db(db)
        engine = PromptEngine()
        ctx = _build_context(project, req)
        messages = engine.build_full_messages(ctx)
        system = engine.build_system_prompt()

        # 调用 LLM
        client = get_llm_client(llm_config)
        result = await client.chat(messages, system=system)

        content = result["choices"][0]["message"]["content"]
        usage = client.get_total_usage()
        await client.close()

        # 保存生成内容到项目
        project.bid_content = content
        project.status = "completed"
        project.updated_at = datetime.now()
        db.commit()

        return {
            "status": "success",
            "data": {
                "project_id": req.project_id,
                "content": content,
                "content_length": len(content),
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "estimated_cost_rmb": round(usage.cost, 4),
                }
            }
        }

    except Exception as e:
        project.status = "draft"
        db.commit()
        logger.error(f"Generate bid failed: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate/stream")
async def generate_bid_stream(req: GenerateRequest, db: Session = Depends(get_db)):
    """流式生成标书（SSE）"""
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.status = "generating"
    db.commit()

    try:
        llm_config = _get_config_from_db(db)
        engine = PromptEngine()
        ctx = _build_context(project, req)
        messages = engine.build_full_messages(ctx)

        client = get_llm_client(llm_config)

        async def event_stream():
            full_content = ""
            try:
                async for chunk in client.chat_stream(messages):
                    full_content += chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                # 保存完整内容
                project.bid_content = full_content
                project.status = "completed"
                project.updated_at = datetime.now()
                db.commit()

                usage = client.get_total_usage()
                yield f"data: {json.dumps({'done': True, 'usage': {'total_tokens': usage.total_tokens, 'cost': round(usage.cost, 4)}})}\n\n"

            except Exception as e:
                project.status = "draft"
                db.commit()
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                await client.close()

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            }
        )

    except Exception as e:
        project.status = "draft"
        db.commit()
        raise HTTPException(status_code=500, detail=f"流式生成启动失败: {str(e)}")


@router.post("/regenerate/{section_name}")
async def regenerate_section(
    section_name: str,
    req: RegenerateSectionRequest,
    db: Session = Depends(get_db)
):
    """重新生成指定章节"""
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not project.bid_content:
        raise HTTPException(status_code=400, detail="项目尚无标书内容，请先生成完整标书")

    try:
        llm_config = _get_config_from_db(db)
        engine = PromptEngine()

        # 尝试从现有内容中提取该章节
        existing = project.bid_content
        ctx = BidContext(
            bidding_announcement=project.description or "",
            project_requirements=project.description or "",
            company_name="",  # 从已有内容推断
            company_info="",
            industry=project.industry or "通用",
            bid_type=project.type or "通用",
        )

        messages = engine.build_section_messages(
            ctx, section_name, existing, req.feedback
        )

        client = get_llm_client(llm_config)
        result = await client.chat(messages, system=engine.build_system_prompt())
        new_section = result["choices"][0]["message"]["content"]
        usage = client.get_total_usage()
        await client.close()

        # 替换对应章节（简单实现：追加到末尾，后续可优化为精确替换）
        project.bid_content = project.bid_content + f"\n\n---\n\n## {section_name}（重新生成）\n\n{new_section}"
        project.updated_at = datetime.now()
        db.commit()

        return {
            "status": "success",
            "data": {
                "section_name": section_name,
                "content": new_section,
                "content_length": len(new_section),
                "usage": {
                    "total_tokens": usage.total_tokens,
                    "estimated_cost_rmb": round(usage.cost, 4),
                }
            }
        }

    except Exception as e:
        logger.error(f"Regenerate section failed: {e}")
        raise HTTPException(status_code=500, detail=f"章节重新生成失败: {str(e)}")


@router.post("/parse-tender")
async def parse_tender_file(req: ParseTenderRequest, db: Session = Depends(get_db)):
    """AI 智能解析招标文件 — 提取关键信息"""
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    try:
        llm_config = _get_config_from_db(db)
        parse_prompt = f"""你是一位招标文件解读专家。请仔细阅读以下招标文件内容，提取关键信息并结构化输出。

## 招标文件内容
{req.tender_content}

## 请提取以下信息（JSON 格式返回）：
```json
{{
  "project_name": "项目名称",
  "procurement_agency": "采购代理机构",
  "budget": "采购预算金额",
  "deadline": "投标截止时间",
  "bid_opening_time": "开标时间",
  "bid_bond": "投标保证金金额和形式",
  "qualification_requirements": ["资质要求1", "资质要求2"],
  "scoring_criteria": [
    {{"name": "评分项名称", "max_score": 分值, "type": "技术/商务/价格"}}
  ],
  "technical_requirements": ["核心技术要求1", "核心技术要求2"],
  "key_deliverables": ["交付物1", "交付物2"],
  "contract_terms": ["关键合同条款1", "关键合同条款2"],
  "risk_points": ["潜在风险点1", "废标风险点2"],
  "mandatory_documents": ["必须提交的文件1", "文件2"]
}}
```

请确保提取的信息准确、完整。如果某个字段在原文件中没有明确信息，请写"未在文件中明确"。"""

        client = get_llm_client(llm_config)
        result = await client.chat(
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.1,  # 低温度保证提取准确性
        )
        content = result["choices"][0]["message"]["content"]
        usage = client.get_total_usage()
        await client.close()

        # 尝试解析 JSON
        try:
            # 提取 JSON 块
            import re
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group(1))
            else:
                parsed_data = json.loads(content)
        except (json.JSONDecodeError, AttributeError):
            parsed_data = {"raw_analysis": content}

        # 保存到项目
        project.requirements = parsed_data
        project.updated_at = datetime.now()
        db.commit()

        return {
            "status": "success",
            "data": {
                "project_id": req.project_id,
                "parsed": parsed_data,
                "raw": content,
                "usage": {
                    "total_tokens": usage.total_tokens,
                    "estimated_cost_rmb": round(usage.cost, 4),
                }
            }
        }

    except Exception as e:
        logger.error(f"Parse tender failed: {e}")
        raise HTTPException(status_code=500, detail=f"招标文件解析失败: {str(e)}")


@router.get("/industries")
def list_industries():
    """获取所有可用的行业分类和标书类型"""
    engine = PromptEngine()
    industries = engine.list_industries()
    result = {}
    for ind in industries:
        result[ind] = engine.list_bid_types(ind)
    return {"status": "success", "data": result}


@router.get("/usage-stats")
def get_usage_stats(db: Session = Depends(get_db)):
    """获取全局 API 用量统计（简单实现，生产环境应从数据库统计）"""
    return {
        "status": "success",
        "data": {
            "message": "用量统计功能完善中，请通过管理后台查看详细统计"
        }
    }
