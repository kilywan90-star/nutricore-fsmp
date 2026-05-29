"""
智能标书生成工具 — 主入口
"""
import os
import logging
from pathlib import Path

# 加载 .env 文件（必须在其他导入之前）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装时跳过，直接读系统环境变量

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from db.sqlite import init_db, engine, Base
from db.models import init_extended_tables, seed_default_plans, User, Order
from api import project, knowledge, parser, generator, validator, export, auth, payment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    logger.info("Initializing database...")
    init_db()
    init_extended_tables()
    seed_default_plans()
    logger.info("Database initialized successfully.")

    # 检查 DeepSeek 配置
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if api_key:
        logger.info(f"DeepSeek API configured (key: ...{api_key[-8:]})")
    else:
        logger.warning("DeepSeek API Key 未配置！请在 .env 中设置 DEEPSEEK_API_KEY")

    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="智能标书生成工具 API",
    description="AI-powered bid document generation service",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──────────────────────────────────────

app.include_router(project.router, prefix="/api/project", tags=["项目管理"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库管理"])
app.include_router(parser.router, prefix="/api/parser", tags=["文件解析"])
app.include_router(generator.router, prefix="/api/generator", tags=["AI生成"])
app.include_router(validator.router, prefix="/api/validator", tags=["智能校验"])
app.include_router(export.router, prefix="/api/export", tags=["导出功能"])
app.include_router(auth.router, prefix="/api/auth", tags=["用户认证"])
app.include_router(payment.router, prefix="/api/payment", tags=["订单支付"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0", "message": "服务运行正常"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
