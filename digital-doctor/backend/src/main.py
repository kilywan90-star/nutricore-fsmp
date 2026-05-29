# digital-doctor/backend/src/main.py
from fastapi import FastAPI
from src.config import settings

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}
