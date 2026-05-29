import pytest
import pytest_asyncio
from sqlalchemy import select
from src.models.user import User, UserRole
from src.services.auth_service import register_patient, login, refresh_access_token


@pytest.mark.asyncio
async def test_register_patient(db_session):
    user = await register_patient(
        phone_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        password="test_password123",
        db=db_session,
        name_hash="test_user",
        gender="M",
        birth_year=1985,
        diabetes_type="type2",
    )
    assert user.id is not None
    assert user.role == UserRole.PATIENT
    assert user.password_hash != "test_password123"

    stmt = select(User).where(User.phone_hash == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4")
    result = await db_session.execute(stmt)
    db_user = result.scalar_one()
    assert db_user.id == user.id


@pytest.mark.asyncio
async def test_login(db_session):
    phone = "b1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    password = "login_test_123"
    await register_patient(phone_hash=phone, password=password, db=db_session)

    result = await login(phone_hash=phone, password=password, db=db_session)
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["token_type"] == "bearer"
    assert result["user"]["role"] == "patient"


@pytest.mark.asyncio
async def test_refresh_token(db_session):
    phone = "c1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    password = "refresh_test_123"
    await register_patient(phone_hash=phone, password=password, db=db_session)
    login_result = await login(phone_hash=phone, password=password, db=db_session)

    refresh_result = await refresh_access_token(login_result["refresh_token"], db_session)
    assert "access_token" in refresh_result
    assert refresh_result["token_type"] == "bearer"
    # New access token should be valid and decode correctly
    from src.security.jwt import decode_token
    payload = decode_token(refresh_result["access_token"])
    assert payload["role"] == "patient"
