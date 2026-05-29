"""和风天气 + 高德天气 服务"""
import httpx
from app.config import settings

QW_API = "https://devapi.qweather.com/v7"
AMAP_WEATHER = "https://restapi.amap.com/v3/weather/weatherInfo"


async def get_weather(lat: float, lng: float) -> dict | None:
    """获取实时天气+逐小时预报+日出日落"""

    # 优先用和风天气
    if settings.qweather_api_key:
        result = await _qweather_weather(lat, lng)
        if result:
            return result

    # 降级到高德天气
    result = await _amap_weather(lng, lat)
    return result


async def _qweather_weather(lat: float, lng: float) -> dict | None:
    """和风天气 API"""
    try:
        async with httpx.AsyncClient() as client:
            # 实时天气
            now_resp = await client.get(
                f"{QW_API}/weather/now",
                params={
                    "location": f"{lng},{lat}",
                    "key": settings.qweather_api_key,
                },
            )

            # 24小时逐小时
            hourly_resp = await client.get(
                f"{QW_API}/weather/24h",
                params={
                    "location": f"{lng},{lat}",
                    "key": settings.qweather_api_key,
                },
            )

            # 日出日落
            sun_resp = await client.get(
                f"{QW_API}/astronomy/sun",
                params={
                    "location": f"{lng},{lat}",
                    "key": settings.qweather_api_key,
                    "date": "today",
                },
            )

            if now_resp.status_code != 200:
                return None

            now_data = now_resp.json()
            if now_data.get("code") != "200":
                return None

            now = now_data["now"]
            hourly_data = hourly_resp.json() if hourly_resp.status_code == 200 else {}
            sun_data = sun_resp.json() if sun_resp.status_code == 200 else {}

            hourly = []
            for h in hourly_data.get("hourly", []):
                hourly.append({
                    "time": h.get("fxTime", ""),
                    "temp": h.get("temp", ""),
                    "wind_speed": h.get("windSpeed", ""),
                    "precip": h.get("precip", "0"),
                    "humidity": h.get("humidity", ""),
                })

            sun = sun_data.get("sun", {}) if sun_data.get("code") == "200" else {}

            return {
                "temp": float(now.get("temp", 0)),
                "feels_like": float(now.get("feelsLike", 0)),
                "humidity": float(now.get("humidity", 0)),
                "wind_speed": float(now.get("windSpeed", 0)),
                "wind_direction": now.get("windDir", ""),
                "pressure": float(now.get("pressure", 1013)),
                "weather_desc": now.get("text", ""),
                "precipitation_prob": float(hourly[0].get("precip", 0)) if hourly else 0,
                "uv_index": float(now.get("uvIndex", 0) or 0),
                "hourly": hourly[:12],
                "sunrise": sun.get("sunrise", "06:00"),
                "sunset": sun.get("sunset", "18:00"),
            }
    except Exception:
        return None


async def _amap_weather(lng: float, lat: float) -> dict | None:
    """高德天气 API（降级方案）"""
    if not settings.amap_api_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                AMAP_WEATHER,
                params={
                    "key": settings.amap_api_key,
                    "location": f"{lng},{lat}",
                    "extensions": "all",
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("status") != "1":
                return None

            forecast = data.get("forecasts", [{}])[0]
            casts = forecast.get("casts", [])
            today = casts[0] if casts else {}

            return {
                "temp": float(today.get("daytemp", 20)),
                "feels_like": float(today.get("daytemp", 20)),
                "humidity": 60.0,
                "wind_speed": float(today.get("daypower", "2").split("级")[0]) * 3.6 if today.get("daypower") else 3.6,
                "wind_direction": today.get("daywind", "南风"),
                "pressure": 1013.0,
                "weather_desc": today.get("dayweather", "晴"),
                "precipitation_prob": 10.0 if "雨" not in str(today.get("dayweather", "")) else 60.0,
                "uv_index": 3.0,
                "hourly": [],
                "sunrise": today.get("sunrise", "06:00") if today else "06:00",
                "sunset": today.get("sunset", "18:00") if today else "18:00",
            }
    except Exception:
        return None
