"""种子数据导入脚本 - 将爬取的JSON导入SQLite"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models import Base, Spot, SpotType

DATA_DIR = Path(__file__).parent.parent.parent / "data"


async def import_amap_data():
    json_file = DATA_DIR / "amap_pois.json"
    if not json_file.exists():
        print(f"数据文件不存在: {json_file}")
        print("请先运行: python scripts/scrape_amap.py")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        pois = json.load(f)

    print(f"读取到 {len(pois)} 条钓点数据")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    imported = 0
    async with async_session() as session:
        for poi in pois:
            spot = Spot(
                name=poi["name"],
                lat=poi["lat"],
                lng=poi["lng"],
                address=poi.get("address", ""),
                province=poi.get("province", ""),
                city=poi.get("city", ""),
                district=poi.get("district", ""),
                type=SpotType(poi.get("type", "其他")),
                photos=poi.get("photos", []),
                rating=poi.get("rating", 0.0),
                source=poi.get("source", "高德地图"),
                amap_id=poi.get("amap_id", ""),
                tel=poi.get("tel", ""),
                price_info={"mode": "未知", "amount": poi.get("cost", 0)} if poi.get("cost") else {},
            )
            session.add(spot)
            imported += 1

        await session.commit()

    print(f"成功导入 {imported} 条钓点数据到数据库")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_amap_data())
