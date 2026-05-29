"""天气 & 钓鱼指数 API"""
from datetime import datetime

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_db
from app.services.weather_service import get_weather
from app.services.insect_service import calculate_insect_level
from app.services.fishing_index import calculate_fishing_index

router = APIRouter()


@router.get("/fishing-index")
async def fishing_index(
    lat: float = Query(...),
    lng: float = Query(...),
    spot_type: str = Query("黑坑", description="钓点类型用于蚊虫+装备推荐"),
):
    """获取某地点的综合钓鱼指数"""
    weather = await get_weather(lat, lng)

    if not weather:
        # 使用默认气象数据
        weather = {
            "temp": 25.0, "feels_like": 26.0, "humidity": 65.0,
            "wind_speed": 8.0, "wind_direction": "南风", "pressure": 1015.0,
            "weather_desc": "晴", "precipitation_prob": 10.0, "uv_index": 4.0,
            "hourly": [], "sunrise": "06:00", "sunset": "18:30",
        }

    insect = calculate_insect_level(
        temp=weather["temp"],
        humidity=weather["humidity"],
        wind_speed=weather["wind_speed"],
        spot_type=spot_type,
        dt=datetime.now(),
    )

    index = calculate_fishing_index(
        temp=weather["temp"],
        humidity=weather["humidity"],
        wind_speed=weather["wind_speed"],
        wind_direction=weather["wind_direction"],
        pressure=weather["pressure"],
        precipitation_prob=weather["precipitation_prob"],
        weather_desc=weather["weather_desc"],
        insect_level=insect["level"],
        spot_type=spot_type,
        sunrise=weather.get("sunrise", ""),
        sunset=weather.get("sunset", ""),
    )

    return {
        "weather": weather,
        "insect": insect,
        "fishing_index": index,
    }


@router.get("/current")
async def current_weather(
    lat: float = Query(...),
    lng: float = Query(...),
):
    """获取当前天气"""
    weather = await get_weather(lat, lng)
    if not weather:
        return {"error": "无法获取天气数据", "weather": None}
    return {"weather": weather}
