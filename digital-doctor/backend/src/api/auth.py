from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.services.auth_service import register_patient, login, refresh_access_token
from src.api.auth_deps import get_current_user
from src.models.user import User

router = APIRouter()


class RegisterRequest(BaseModel):
    phone_hash: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    name_hash: str = Field(default="", max_length=128)
    gender: str = Field(default="", max_length=1)
    birth_year: int = Field(default=0, ge=1900, le=2026)
    diabetes_type: str = Field(default="type2", max_length=20)


class RegisterResponse(BaseModel):
    id: str
    role: str
    message: str


class LoginRequest(BaseModel):
    phone_hash: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=6, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str


class UserProfileResponse(BaseModel):
    id: str
    role: str
    is_active: bool


@router.post("/register", response_model=RegisterResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_patient(
            phone_hash=req.phone_hash,
            password=req.password,
            db=db,
            name_hash=req.name_hash,
            gender=req.gender,
            birth_year=req.birth_year,
            diabetes_type=req.diabetes_type,
        )
        return RegisterResponse(id=str(user.id), role=user.role.value, message="Registration successful")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await login(req.phone_hash, req.password, db)
        return LoginResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_endpoint(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await refresh_access_token(req.refresh_token, db)
        return RefreshResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserProfileResponse(id=str(user.id), role=user.role.value, is_active=user.is_active)
