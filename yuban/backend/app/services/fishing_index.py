"""钓鱼指数综合评分算法

综合评分 = Σ(各维度评分 × 权重)

维度:
- 气温适宜度 20%
- 气压趋势 15%
- 风力风向 15%
- 降水概率 15%
- 湿度适宜度 10%
- 蚊虫活跃度 15%
- 月相/日照 10%
"""


def calculate_fishing_index(
    temp: float,
    humidity: float,
    wind_speed: float,
    wind_direction: str,
    pressure: float,
    precipitation_prob: float,
    weather_desc: str,
    insect_level: int,
    spot_type: str = "其他",
    sunrise: str = "",
    sunset: str = "",
) -> dict:
    """计算综合钓鱼指数 (0-100)"""

    scores = {}

    # 1. 气温适宜度 (20%)
    if 18 <= temp <= 28:
        scores["temp"] = 95
    elif 15 <= temp < 18 or 28 < temp <= 33:
        scores["temp"] = 75
    elif 10 <= temp < 15 or 33 < temp <= 36:
        scores["temp"] = 50
    elif 5 <= temp < 10:
        scores["temp"] = 30
    else:
        scores["temp"] = 15

    # 2. 气压趋势 (15%)
    if 1015 <= pressure <= 1025:
        scores["pressure"] = 90
    elif 1010 <= pressure < 1015 or 1025 < pressure <= 1030:
        scores["pressure"] = 75
    elif 1005 <= pressure < 1010:
        scores["pressure"] = 50
    else:
        scores["pressure"] = 30

    # 3. 风力风向 (15%)
    if wind_speed < 6:  # 1-2级风
        scores["wind"] = 95
    elif wind_speed < 12:  # 2-3级风
        scores["wind"] = 85
    elif wind_speed < 20:  # 3-4级风
        scores["wind"] = 60
    elif wind_speed < 29:  # 4-5级风
        scores["wind"] = 30
    else:
        scores["wind"] = 10

    # 特定风向扣分 (西北风/北风对大部分地区不利)
    bad_winds = ["西北风", "北风", "东北风"]
    if any(bw in wind_direction for bw in bad_winds) and wind_speed > 10:
        scores["wind"] = max(scores["wind"] - 15, 10)

    # 4. 降水概率 (15%)
    if precipitation_prob < 15:
        scores["precip"] = 95
    elif precipitation_prob < 30:
        scores["precip"] = 80
    elif precipitation_prob < 50:
        scores["precip"] = 55
    elif precipitation_prob < 70:
        scores["precip"] = 30
    else:
        scores["precip"] = 10

    # 雨天实际比预报更影响钓鱼
    rain_keywords = ["雨", "暴雨", "大雨", "中雨", "小雨", "阵雨", "雷阵雨"]
    if any(r in weather_desc for r in rain_keywords):
        scores["precip"] = min(scores["precip"], 40)

    # 5. 湿度适宜度 (10%)
    if 50 <= humidity <= 75:
        scores["humidity"] = 90
    elif 40 <= humidity < 50 or 75 < humidity <= 85:
        scores["humidity"] = 75
    elif 30 <= humidity < 40 or 85 < humidity <= 95:
        scores["humidity"] = 50
    else:
        scores["humidity"] = 25

    # 6. 蚊虫 (15%) — 逆向映射
    insect_scores = {1: 95, 2: 80, 3: 60, 4: 35, 5: 15}
    scores["insect"] = insect_scores.get(insect_level, 60)

    # 7. 日照/月相基础分 (10%)
    scores["sun"] = 75  # 默认基础分

    # 加权总分
    weights = {
        "temp": 0.20, "pressure": 0.15, "wind": 0.15,
        "precip": 0.15, "humidity": 0.10, "insect": 0.15, "sun": 0.10,
    }

    total = sum(scores[k] * weights[k] for k in weights)

    # 生成一句话建议
    summary = _generate_summary(total, scores, insect_level, weather_desc)

    # 装备推荐
    gear = _recommend_gear(temp, precipitation_prob, wind_speed, insect_level, spot_type)

    return {
        "score": round(total),
        "summary": summary,
        "details": {
            k: {"score": scores[k], "weight": f"{int(weights[k] * 100)}%"}
            for k in scores
        },
        "gear_recommendations": gear,
    }


def _generate_summary(score: float, details: dict, insect_level: int, weather: str) -> str:
    if score >= 80:
        base = "今天是个钓鱼的好日子!"
    elif score >= 60:
        base = "条件尚可，可以出门试试"
    elif score >= 40:
        base = "不太理想，但瘾大的可以去"
    else:
        base = "建议改天，今天更适合在家绑钩"

    warnings = []
    if insect_level >= 4:
        warnings.append("蚊虫凶猛，带足防护装备")
    if "雨" in weather:
        warnings.append("有雨，记得带雨具")
    if details.get("wind", 50) < 40:
        warnings.append("风大，选背风钓位")

    if warnings:
        base += "。" + "；".join(warnings)

    return base


def _recommend_gear(
    temp: float,
    precip_pct: float,
    wind_speed: float,
    insect_level: int,
    spot_type: str,
) -> list[dict]:
    """基于天气条件推荐装备"""
    gear = []

    # 基础装备
    gear.append({"category": "必备", "items": ["钓竿+线组", "浮漂", "饵料/窝料", "抄网", "鱼护", "钓箱/钓椅"]})

    # 天气相关
    weather_items = []
    if precip_pct > 30:
        weather_items.extend(["雨衣/雨伞", "防水鞋套", "防水手机袋"])
    if temp > 30:
        weather_items.extend(["遮阳帽", "偏光镜", "防晒霜SPF50+", "大容量水壶(2L+)"])
    elif temp < 10:
        weather_items.extend(["保暖内衣", "防风外套", "暖宝宝", "保温杯"])
    if wind_speed > 15:
        weather_items.append("防风面罩")
    if weather_items:
        gear.append({"category": "天气防护", "items": weather_items})

    # 蚊虫防护
    if insect_level >= 3:
        insect_items = ["驱蚊喷雾(DEET 20%+)", "蚊香/电子蚊香"]
        if insect_level >= 4:
            insect_items.extend(["防蚊面罩", "长袖速干衣(浅色)", "便携风扇(驱蚊)"])
        gear.append({"category": "防蚊装备", "items": insect_items})

    # 夜间装备
    gear.append({"category": "随时备用", "items": ["头灯/夜钓灯", "充电宝", "急救包", "垃圾袋"]})

    return gear
