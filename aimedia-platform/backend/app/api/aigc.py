"""AIGC 辅助创作 API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.engine.aigc import generate_article, optimize_title, extract_summary, generate_script

router = APIRouter(prefix="/api/aigc", tags=["aigc"])


class GenerateArticleRequest(BaseModel):
    topic: str
    specialty: str = ""
    target_audience: str = "普通公众"
    word_count: int = Field(default=800, ge=200, le=3000)


class OptimizeTitleRequest(BaseModel):
    body: str
    style: str = "科普风"


class ExtractSummaryRequest(BaseModel):
    body: str
    max_length: int = Field(default=200, ge=50, le=500)


class GenerateScriptRequest(BaseModel):
    topic: str
    duration_minutes: int = Field(default=3, ge=1, le=10)


@router.post("/article")
async def api_generate_article(req: GenerateArticleRequest):
    try:
        text = await generate_article(req.topic, req.specialty, req.target_audience, req.word_count)
        return {"content": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/titles")
async def api_optimize_title(req: OptimizeTitleRequest):
    try:
        titles = await optimize_title(req.body, req.style)
        return {"titles": titles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summary")
async def api_extract_summary(req: ExtractSummaryRequest):
    try:
        summary = await extract_summary(req.body, req.max_length)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/script")
async def api_generate_script(req: GenerateScriptRequest):
    try:
        script = await generate_script(req.topic, req.duration_minutes)
        return {"script": script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
