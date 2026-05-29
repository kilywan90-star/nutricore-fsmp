from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine = None
_async_session = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.database_url
        if "sqlite" in db_url:
            _engine = create_async_engine(db_url, echo=False)
        else:
            _engine = create_async_engine(db_url, echo=False, pool_size=20, max_overflow=10)
    return _engine


def get_sessionmaker():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _async_session


async def get_db() -> AsyncSession:
    async with get_sessionmaker()() as session:
        yield session


async def init_db():
    """创建所有表（SQLite 开发模式用）"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
