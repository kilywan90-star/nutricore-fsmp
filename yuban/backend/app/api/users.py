"""用户 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_db
from app.models import User
from app.schemas import UserProfile

router = APIRouter()


@router.get("/profile", response_model=UserProfile)
async def get_profile(db: AsyncSession = Depends(get_db)):
    """获取当前用户信息（MVP阶段固定返回dev用户）"""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            openid="dev_user",
            nickname="测试钓友",
            avatar="",
            level=1,
            total_catches=0,
            max_record=0.0,
            favorite_methods=["台钓"],
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return UserProfile.model_validate(user)


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    nickname: str = None,
    favorite_methods: list[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if nickname:
        user.nickname = nickname
    if favorite_methods is not None:
        user.favorite_methods = favorite_methods

    await db.commit()
    await db.refresh(user)
    return UserProfile.model_validate(user)
