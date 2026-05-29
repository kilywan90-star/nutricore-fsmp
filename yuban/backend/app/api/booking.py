"""约钓 & 陪钓 API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_db
from app.models import (
    YuediaoSession, YuediaoStatus,
    Companion, CompanionType, CompanionOrder, OrderStatus,
    User, Spot,
)
from app.schemas import (
    YuediaoCreate, YuediaoOut,
    CompanionCreate, CompanionOut,
    OrderCreate, OrderOut,
)

router = APIRouter()


# ===== 约钓 =====
@router.get("/yuediao", response_model=list[YuediaoOut])
async def list_yuediao(
    status: str = Query("招募中"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(YuediaoSession)
        .where(YuediaoSession.status == YuediaoStatus(status))
        .order_by(desc(YuediaoSession.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    out = []
    for s in sessions:
        d = YuediaoOut.model_validate(s)
        if s.creator:
            d.creator = {"id": s.creator.id, "nickname": s.creator.nickname, "avatar": s.creator.avatar}
        if s.spot:
            d.spot = {"id": s.spot.id, "name": s.spot.name}
        out.append(d)
    return out


@router.post("/yuediao", response_model=YuediaoOut)
async def create_yuediao(data: YuediaoCreate, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(openid="dev_user", nickname="测试钓友", avatar="")
        db.add(user)
        await db.flush()

    session = YuediaoSession(
        creator_id=user.id,
        spot_id=data.spot_id,
        target_date=data.target_date,
        max_participants=data.max_participants,
        current_count=1,
        requirements=data.requirements,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    d = YuediaoOut.model_validate(session)
    d.creator = {"id": user.id, "nickname": user.nickname, "avatar": user.avatar}
    return d


# ===== 陪钓服务者 =====
@router.get("/companions", response_model=list[CompanionOut])
async def list_companions(
    companion_type: str = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Companion).where(Companion.available == True)

    if companion_type:
        try:
            stmt = stmt.where(Companion.type == CompanionType(companion_type))
        except ValueError:
            pass

    stmt = stmt.order_by(desc(Companion.verified), desc(Companion.rating))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    companions = result.scalars().all()

    out = []
    for c in companions:
        d = CompanionOut.model_validate(c)
        if c.user:
            d.user = {"id": c.user.id, "nickname": c.user.nickname, "avatar": c.user.avatar}
        out.append(d)
    return out


@router.post("/companions", response_model=CompanionOut)
async def register_companion(data: CompanionCreate, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(openid="dev_user", nickname="测试钓友", avatar="")
        db.add(user)
        await db.flush()

    companion = Companion(
        user_id=user.id,
        type=CompanionType(data.type),
        price_per_hour=data.price_per_hour,
        services=data.services,
        bio=data.bio,
        photos=data.photos,
        verified=False,
    )
    db.add(companion)
    await db.commit()
    await db.refresh(companion)

    d = CompanionOut.model_validate(companion)
    d.user = {"id": user.id, "nickname": user.nickname, "avatar": user.avatar}
    return d


# ===== 陪钓订单 =====
@router.post("/orders", response_model=OrderOut)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(openid="dev_user", nickname="测试钓友", avatar="")
        db.add(user)
        await db.flush()

    comp_result = await db.execute(select(Companion).where(Companion.id == data.companion_id))
    companion = comp_result.scalar_one_or_none()
    if not companion:
        raise HTTPException(status_code=404, detail="服务者不存在")

    total_price = round(companion.price_per_hour * data.duration, 2)

    order = CompanionOrder(
        companion_id=data.companion_id,
        user_id=user.id,
        spot_id=data.spot_id,
        service_date=data.service_date,
        duration=data.duration,
        total_price=total_price,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    d = OrderOut.model_validate(order)
    d.companion = {"id": companion.id, "type": companion.type.value if companion.type else "陪钓", "rating": companion.rating}
    return d


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CompanionOrder).order_by(desc(CompanionOrder.created_at))

    if status:
        try:
            stmt = stmt.where(CompanionOrder.status == OrderStatus(status))
        except ValueError:
            pass

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    orders = result.scalars().all()

    out = []
    for o in orders:
        d = OrderOut.model_validate(o)
        if o.companion:
            d.companion = {"id": o.companion.id, "type": o.companion.type.value if o.companion.type else "陪钓", "rating": o.companion.rating}
        out.append(d)
    return out
