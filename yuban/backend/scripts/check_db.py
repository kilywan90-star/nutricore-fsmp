"""Quick database setup verification"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///./test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("DB tables created OK")
    await engine.dispose()

asyncio.run(main())
