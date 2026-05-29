"""钓点 API"""
from math import radians, cos, sin, asin, sqrt

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_db
from app.models import Spot, SpotType
from app.schemas import SpotListQuery, SpotOut, SpotDetailOut

router = APIRouter()


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间距离(米)"""
    r = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return r * 2 * asin(sqrt(a))


@router.get("/list", response_model=list[SpotOut])
async def list_spots(
    lat: float = Query(None),
    lng: float = Query(None),
    city: str = Query(None),
    type: str = Query(None),
    keyword: str = Query(None),
    radius: int = Query(50000),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("distance"),
    db: AsyncSession = Depends(get_db),
):
    """搜索钓点列表"""
    stmt = select(Spot)

    if city:
        stmt = stmt.where(Spot.city == city)
    if type:
        try:
            spot_type = SpotType(type)
            stmt = stmt.where(Spot.type == spot_type)
        except ValueError:
            pass
    if keyword:
        stmt = stmt.where(
            Spot.name.contains(keyword) | Spot.address.contains(keyword)
        )

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    spots = result.scalars().all()

    out = []
    for s in spots:
        d = SpotOut.model_validate(s)
        if lat and lng:
            d.distance = round(haversine(lat, lng, s.lat, s.lng))
        else:
            d.distance = None
        out.append(d)

    # 过滤超出范围的
    if lat and lng:
        out = [s for s in out if s.distance is not None and s.distance <= radius]

    # 排序
    if sort_by == "distance" and lat and lng:
        out.sort(key=lambda x: x.distance or 999999)
    elif sort_by == "rating":
        out.sort(key=lambda x: x.rating or 0, reverse=True)

    return out[:page_size]


@router.get("/{spot_id}", response_model=SpotDetailOut)
async def get_spot_detail(
    spot_id: int,
    lat: float = Query(None),
    lng: float = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """钓点详情"""
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(status_code=404, detail="钓点不存在")

    out = SpotDetailOut.model_validate(spot)
    if lat and lng:
        out.distance = round(haversine(lat, lng, spot.lat, spot.lng))

    return out


@router.get("/nearby/map-markers")
async def map_markers(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: int = Query(20000),
    db: AsyncSession = Depends(get_db),
):
    """获取地图标注点（轻量数据）"""
    stmt = select(Spot.id, Spot.name, Spot.lat, Spot.lng, Spot.type).limit(500)
    result = await db.execute(stmt)
    rows = result.all()

    markers = []
    for row in rows:
        d = haversine(lat, lng, row.lat, row.lng)
        if d <= radius:
            markers.append({
                "id": row.id,
                "name": row.name,
                "lat": row.lat,
                "lng": row.lng,
                "type": row.type.value if row.type else "其他",
                "distance": round(d),
            })

    markers.sort(key=lambda x: x["distance"])
    return markers
