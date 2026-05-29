"""
高德地图POI爬虫 - 钓点数据采集
用法: python scripts/scrape_amap.py
需要环境变量: AMAP_API_KEY
"""
import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 目标城市列表（覆盖主要钓鱼城市）
CITIES = [
    # 直辖市
    "北京", "上海", "天津", "重庆",
    # 东三省
    "哈尔滨", "长春", "沈阳", "大连", "吉林",
    # 华北
    "石家庄", "太原", "呼和浩特", "唐山", "保定",
    # 华东
    "南京", "苏州", "无锡", "常州", "杭州", "宁波", "温州", "合肥", "芜湖",
    "南昌", "九江", "济南", "青岛", "烟台", "威海", "福州", "厦门", "泉州",
    # 华中
    "郑州", "洛阳", "武汉", "宜昌", "长沙", "岳阳", "株洲",
    # 华南
    "广州", "深圳", "东莞", "佛山", "珠海", "南宁", "桂林", "海口", "三亚",
    # 西南
    "成都", "绵阳", "昆明", "大理", "贵阳", "遵义",
    # 西北
    "西安", "兰州", "银川", "西宁", "乌鲁木齐",
    # 其他重点钓鱼城市
    "徐州", "扬州", "镇江", "南通", "连云港", "日照", "威海",
    "湖州", "嘉兴", "绍兴", "金华", "台州", "漳州",
    "荆州", "襄阳", "黄石", "岳阳", "常德", "衡阳",
    "绵阳", "德阳", "宜宾", "南充", "泸州",
    "柳州", "北海", "钦州",
]

# 搜索关键词组合
KEYWORDS = [
    "钓鱼场", "钓场", "垂钓园", "垂钓中心", "黑坑",
    "路亚基地", "路亚钓场", "野钓", "水库钓鱼", "海钓",
    "休闲钓鱼", "农家乐钓鱼", "渔场", "钓鱼基地",
    "钓虾馆", "溪流钓",
]

# 高德POI类型
POI_TYPES = "080000|110000|170000|200000"  # 体育休闲|风景名胜|生活服务|商家

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    key = os.environ.get("AMAP_API_KEY")
    if not key:
        print("错误: 请设置环境变量 AMAP_API_KEY")
        print("获取Key: https://console.amap.com/dev/")
        sys.exit(1)
    return key


def dedup_key(name: str, lng: float, lat: float) -> str:
    """生成去重key（附近500米+名称相似视为同一钓点）"""
    rounded_lat = round(float(lat), 3)
    rounded_lng = round(float(lng), 3)
    raw = f"{name[:4]}|{rounded_lng}|{rounded_lat}"
    return hashlib.md5(raw.encode()).hexdigest()


async def search_city_keyword(
    client: httpx.AsyncClient,
    api_key: str,
    city: str,
    keyword: str,
) -> list[dict]:
    """搜索单个城市+关键词组合"""
    url = "https://restapi.amap.com/v3/place/text"
    results = []
    page = 1

    while page <= 4:  # 最多4页 = 100条/组合
        params = {
            "key": api_key,
            "keywords": keyword,
            "types": POI_TYPES,
            "city": city,
            "citylimit": "true",
            "offset": 25,
            "page": page,
            "extensions": "all",
        }
        try:
            resp = await client.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("status") != "1":
                break
            pois = data.get("pois", [])
            if not pois:
                break
            results.extend(pois)
            total = int(data.get("count", 0))
            if page * 25 >= total:
                break
            page += 1
            await asyncio.sleep(0.15)  # 控制频率
        except Exception as e:
            print(f"  请求失败: {city}/{keyword} page={page}: {e}")
            break

    return results


def clean_poi(poi: dict) -> dict:
    """清洗单条POI数据"""
    name = (poi.get("name") or "").strip()
    if not name:
        return None

    # 过滤无关结果
    blacklist = [
        "钓鱼执法", "钓鱼网站", "钓鱼邮件", "钓鱼攻击",
        "渔具", "渔网", "渔药", "鱼药", "饲料", "鱼苗",
        "水族", "观赏鱼", "海鲜", "鱼庄", "全鱼宴",
        "钓鱼台国宾馆", "钓鱼台",
    ]
    for kw in blacklist:
        if kw in name:
            return None

    location = (poi.get("location") or "").split(",")
    if len(location) != 2:
        return None

    lng, lat = location[0], location[1]

    biz_ext = poi.get("biz_ext", {}) or {}
    deep_info = poi.get("deep_info", {}) or {}

    # 推测钓点类型
    spot_type = "其他"
    name_lower = name.lower()
    if any(kw in name for kw in ["黑坑", "竞技"]):
        spot_type = "黑坑"
    elif any(kw in name for kw in ["野钓", "野河", "野塘"]):
        spot_type = "野钓"
    elif any(kw in name for kw in ["水库", "大坝"]):
        spot_type = "水库"
    elif any(kw in name for kw in ["海钓", "海钓场", "船钓"]):
        spot_type = "海钓"
    elif any(kw in name for kw in ["溪流", "溪钓"]):
        spot_type = "溪流"
    elif any(kw in name for kw in ["路亚", "lure"]):
        spot_type = "路亚基地"
    elif any(kw in name for kw in ["垂钓", "钓鱼", "钓场", "休闲"]):
        spot_type = "黑坑"

    photos = []
    for photo in poi.get("photos", []) or []:
        url = photo.get("url", "")
        if url:
            photos.append(url)

    return {
        "name": name,
        "lng": float(lng),
        "lat": float(lat),
        "address": poi.get("address", ""),
        "province": poi.get("pname", ""),
        "city": poi.get("cityname", ""),
        "district": poi.get("adname", ""),
        "type": spot_type,
        "tel": poi.get("tel", "") or biz_ext.get("tel", "") or "",
        "rating": float(biz_ext.get("rating", 0) or 0),
        "photos": photos[:5],  # 最多5张图片
        "cost": biz_ext.get("cost", "") or deep_info.get("cost", ""),
        "source": "高德地图",
        "amap_id": poi.get("id", ""),
        "_dedup": dedup_key(name, lng, lat),
    }


async def main():
    api_key = get_api_key()
    print(f"开始爬取 {len(CITIES)} 个城市, {len(KEYWORDS)} 个关键词")
    print(f"预计搜索次数: {len(CITIES) * len(KEYWORDS)}")

    all_raw = []
    seen = set()

    async with httpx.AsyncClient() as client:
        for i, city in enumerate(CITIES):
            for keyword in KEYWORDS:
                print(f"[{i+1}/{len(CITIES)}] {city} - {keyword}", end=" ", flush=True)
                pois = await search_city_keyword(client, api_key, city, keyword)
                new_count = 0
                for poi in pois:
                    cleaned = clean_poi(poi)
                    if cleaned and cleaned["_dedup"] not in seen:
                        seen.add(cleaned["_dedup"])
                        del cleaned["_dedup"]
                        all_raw.append(cleaned)
                        new_count += 1
                print(f"-> {len(pois)}条原始, {new_count}条新增")

            # 每5个城市保存一次进度
            if (i + 1) % 5 == 0:
                save_progress(all_raw)

    save_progress(all_raw)
    print(f"\n完成! 共获取 {len(all_raw)} 条钓点数据")
    print(f"输出文件: {OUTPUT_DIR / 'amap_pois.json'}")

    # 输出统计
    types = {}
    for s in all_raw:
        types[s["type"]] = types.get(s["type"], 0) + 1
    print("\n钓点类型分布:")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")


def save_progress(data: list[dict]):
    output_file = OUTPUT_DIR / "amap_pois.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
