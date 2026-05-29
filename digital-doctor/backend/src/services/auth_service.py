import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserRole
from src.models.patient import Patient
from src.security.jwt import create_access_token, create_refresh_token, decode_token
from src.security.password import hash_password, verify_password


def _hash_refresh_token(token: str) -> str:
    return hash_password(token)


async def register_patient(
    phone_hash: str,
    password: str,
    db: AsyncSession,
    *,
    name_hash: str = "",
    gender: str = "",
    birth_year: int = 0,
    diabetes_type: str = "type2",
) -> User:
    stmt = select(User).where(User.phone_hash == phone_hash)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ValueError("User with this phone already exists")

    user = User(
        phone_hash=phone_hash,
        password_hash=hash_password(password),
        role=UserRole.PATIENT,
    )
    db.add(user)
    await db.flush()

    patient = Patient(
        user_id=user.id,
        name_hash=name_hash or phone_hash[:32],
        gender=gender or "U",
        birth_year=birth_year or 1990,
        diabetes_type=diabetes_type,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(user)
    return user


async def register_doctor(
    phone_hash: str,
    password: str,
    name: str,
    db: AsyncSession,
) -> User:
    stmt = select(User).where(User.phone_hash == phone_hash)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ValueError("User with this phone already exists")

    user = User(
        phone_hash=phone_hash,
        password_hash=hash_password(password),
        role=UserRole.DOCTOR,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login(
    phone_hash: str,
    password: str,
    db: AsyncSession,
) -> dict:
    stmt = select(User).where(User.phone_hash == phone_hash)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid phone or password")

    if not user.is_active:
        raise ValueError("Account is deactivated")

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    user.refresh_token_hash = _hash_refresh_token(refresh_token)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "role": user.role.value,
            "is_active": user.is_active,
        },
    }


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except ValueError:
        raise ValueError("Invalid refresh token")

    user_id = payload["sub"]
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise ValueError("Invalid token subject")

    stmt = select(User).where(User.id == uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise ValueError("User not found or inactive")

    if not user.refresh_token_hash or not verify_password(refresh_token, user.refresh_token_hash):
        raise ValueError("Refresh token has been revoked")

    new_access_token = create_access_token(str(user.id), user.role.value)
    return {"access_token": new_access_token, "token_type": "bearer"}
