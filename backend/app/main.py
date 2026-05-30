"""
FSMP Clinical Nutrition Knowledge Base — Application Entry Point

Usage:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api import screening, plan, products, interactions


app = FastAPI(
    title="FSMP Clinical Nutrition KB",
    description="Clinical nutrition intelligent decision engine — disease→nutrition needs→FSMP product matching",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screening.router, prefix="/api/v1/screening", tags=["screening"])
app.include_router(plan.router, prefix="/api/v1/plan", tags=["plan"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(interactions.router, prefix="/api/v1/interactions", tags=["interactions"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
