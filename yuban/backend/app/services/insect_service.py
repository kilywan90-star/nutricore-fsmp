"""蚊虫活跃度预报服务

基于气象条件+钓点环境+时间+季节的综合模型

模型因子:
- 温度: 蚊虫最活跃区间 22-32°C
- 湿度: 蚊虫需要 >50% 湿度
- 时间: 黄昏/清晨蚊虫更活跃
- 季节: 夏季>秋季>春季>冬季
- 钓点类型: 静水>流水, 草丛>石滩
- 风速: >3级风抑制蚊虫活动
"""

from datetime import datetime


def calculate_insect_level(
    temp: float,
    humidity: float,
    wind_speed: float,
    spot_type: str = "黑坑",
    dt: datetime | None = None,
) -> dict:
    """计算蚊虫活跃等级 (1-5)

    Args:
        temp: 温度 (°C)
        humidity: 相对湿度 (%)
        wind_speed: 风速 (km/h)
        spot_type: 钓点类型
        dt: 日期时间（默认当前）
    """
    dt = dt or datetime.now()
    month = dt.month
    hour = dt.hour

    score = 0.0

    # 温度因子 (最适区间22-32°C满分)
    if 22 <= temp <= 32:
        score += 35
    elif 18 <= temp < 22 or 32 < temp <= 35:
        score += 25
    elif 10 <= temp < 18:
        score += 15
    elif temp > 35:
        score += 10
    else:
        score += 5

    # 湿度因子 (>50%蚊虫活跃)
    if humidity > 80:
        score += 30
    elif humidity > 60:
        score += 25
    elif humidity > 40:
        score += 15
    else:
        score += 5

    # 季节因子
    if month in [6, 7, 8]:  # 夏季
        score += 20
    elif month in [5, 9]:  # 初夏/初秋
        score += 15
    elif month in [4, 10]:  # 春末/秋末
        score += 10
    elif month in [3, 11]:  # 初春/深秋
        score += 5
    else:  # 冬季
        score += 0

    # 时间因子 (黄昏17-19点 和 清晨4-6点 蚊虫最活跃)
    if 4 <= hour <= 6 or 17 <= hour <= 19:
        score += 10
    elif 19 < hour <= 22:
        score += 5

    # 风速因子 (>3级风 = >19km/h 抑制蚊虫)
    if wind_speed < 5.5:
        score += 5
    elif wind_speed < 12:
        score += 3
    else:
        score += 0

    # 钓点类型因子
    water_bonus = {
        "水库": 8, "野钓": 10, "溪流": 3,
        "海钓": 2, "黑坑": 5, "路亚基地": 4, "其他": 5,
    }
    score += water_bonus.get(spot_type, 5)

    # 总分映射到1-5级
    if score >= 80:
        level = 5
        desc = "蚊虫肆虐，强烈建议全副武装"
        advice = "必须穿长袖长裤+高浓度驱蚊液+蚊香，不建议夜钓"
    elif score >= 60:
        level = 4
        desc = "蚊虫严重，需要充分防护"
        advice = "建议穿长袖+驱蚊液+蚊香，减少裸露皮肤"
    elif score >= 40:
        level = 3
        desc = "蚊虫较多，随身携带驱蚊用品"
        advice = "建议携带驱蚊喷雾和蚊香，穿轻薄长裤"
    elif score >= 20:
        level = 2
        desc = "偶有蚊虫，基本不影响"
        advice = "可备驱蚊液，傍晚时段适当防范"
    else:
        level = 1
        desc = "几乎无蚊虫，舒适度高"
        advice = "无需特别防护"

    return {
        "level": level,
        "score": round(score, 1),
        "description": desc,
        "advice": advice,
        "factors": {
            "temp_factor": "高" if 22 <= temp <= 32 else "中" if 10 <= temp <= 35 else "低",
            "humidity_factor": "高" if humidity > 70 else "中" if humidity > 40 else "低",
            "season_factor": "高" if month in [6, 7, 8] else "中" if month in [4, 5, 9, 10] else "低",
            "time_factor": "高" if 4 <= hour <= 7 or 17 <= hour <= 20 else "低",
        },
    }
