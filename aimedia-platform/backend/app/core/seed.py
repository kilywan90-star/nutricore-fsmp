"""种子数据: 创建测试医院、用户、渠道"""

import uuid

from app.core.database import get_engine, get_sessionmaker
from app.core.security import hash_password
from app.models.user import Hospital, User
from app.models.publish import Channel


async def seed():
    engine = get_engine()
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        # 检查是否已种植
        from sqlalchemy import select
        existing = await db.execute(select(Hospital).limit(1))
        if existing.scalar_one_or_none():
            print("Seed data already exists, skipping.")
            return

        # ── 医院 ──
        hospital_id = uuid.uuid4()
        hospital = Hospital(
            id=hospital_id,
            name="测试人民医院",
            code="TEST-001",
            level="三级甲等",
            admin_phone="010-12345678",
            review_config={"levels": 3, "sla_hours": 24},
        )
        db.add(hospital)

        # ── 用户 ──
        users = [
            User(id=uuid.uuid4(), hospital_id=hospital_id, username="admin",
                 hashed_password=hash_password("admin123"), display_name="系统管理员",
                 role="admin", department="信息科"),
            User(id=uuid.uuid4(), hospital_id=hospital_id, username="doctor_zhang",
                 hashed_password=hash_password("doctor123"), display_name="张医生",
                 role="doctor", department="骨科"),
            User(id=uuid.uuid4(), hospital_id=hospital_id, username="dept_head_li",
                 hashed_password=hash_password("head123"), display_name="李主任",
                 role="dept_head", department="骨科"),
            User(id=uuid.uuid4(), hospital_id=hospital_id, username="editor_wang",
                 hashed_password=hash_password("editor123"), display_name="王编辑",
                 role="editor", department="宣传科"),
            User(id=uuid.uuid4(), hospital_id=hospital_id, username="director_chen",
                 hashed_password=hash_password("director123"), display_name="陈科长",
                 role="director", department="宣传科"),
        ]
        for u in users:
            db.add(u)

        # ── 渠道 ──
        channels = [
            Channel(id=uuid.uuid4(), hospital_id=hospital_id, name="wechat_mp",
                    display_name="微信公众号", config={"app_id": "", "app_secret": ""}),
            Channel(id=uuid.uuid4(), hospital_id=hospital_id, name="douyin",
                    display_name="抖音", config={"app_id": "", "app_secret": ""}),
            Channel(id=uuid.uuid4(), hospital_id=hospital_id, name="kuaishou",
                    display_name="快手", config={"app_id": "", "app_secret": ""}),
        ]
        for ch in channels:
            db.add(ch)

        await db.commit()
        print(f"Seeded: 1 hospital, {len(users)} users, {len(channels)} channels")
        print("  admin / admin123")
        print("  doctor_zhang / doctor123")
        print("  dept_head_li / head123")
        print("  editor_wang / editor123")
        print("  director_chen / director123")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())
