import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserRole
from src.models.patient import Patient
from src.security.jwt import create_access_token, create_refresh_token, decode_token
from src.security.password import hash_password, verify_password
from src.config import settings


def _hash_refresh_token(token: str) -> str:
    return hash_password(token)


# ── WeChat code → openid exchange (mock for dev/test) ──────────────────────────

_wechat_code_to_openid_override: dict[str, str] | None = None


def _exchange_wechat_code(code: str) -> str:
    """Exchange a WeChat wx.login() code for an openid.

    In dev/test, returns a deterministic hash so tests can predict the outcome.
    Production would call https://api.weixin.qq.com/sns/jscode2session.
    """
    if _wechat_code_to_openid_override is not None:
        return _wechat_code_to_openid_override.get(code, "")

    # Mock for dev/test: derive openid from code
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        # Return a deterministic openid from the code
        return f"mock_openid_{hash(code) & 0xFFFFFFFFF:09x}"

    # Real implementation would call WeChat API here
    return f"wx_openid_{code}"


async def wechat_code_login(
    code: str,
    db: AsyncSession,
    *,
    name_hash: str = "",
    gender: str = "",
    birth_year: int = 0,
    diabetes_type: str = "type2",
) -> dict:
    """Login or register a user via WeChat mini-program code.

    Exchanges the code for an openid, creates a new User+Patient if this is the
    first login, or returns JWT tokens for an existing user.
    """
    openid = _exchange_wechat_code(code)
    if not openid:
        raise ValueError("Failed to exchange WeChat code")

    # Look up by openid
    stmt = select(User).where(User.wechat_openid == openid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # New user — register via WeChat
        user = User(
            phone_hash=f"wechat_{openid}",
            password_hash=hash_password(openid),  # WeChat users auth via openid
            role=UserRole.PATIENT,
            wechat_openid=openid,
        )
        db.add(user)
        await db.flush()

        patient = Patient(
            user_id=user.id,
            name_hash=name_hash or openid[:32],
            gender=gender or "U",
            birth_year=birth_year or 1990,
            diabetes_type=diabetes_type,
        )
        db.add(patient)
        await db.commit()
        await db.refresh(user)

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
