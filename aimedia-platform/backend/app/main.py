"""AI融媒体平台 —— FastAPI 入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, content, review, publish, aigc
from app.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AI融媒体平台",
    description="医疗行业AI融媒体内容管理平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(content.router)
app.include_router(review.router)
app.include_router(publish.router)
app.include_router(aigc.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "env": settings.env}
