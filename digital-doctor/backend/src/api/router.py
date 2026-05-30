from fastapi import APIRouter
from src.api.patient import router as patient_router
from src.api.doctor import router as doctor_router
from src.api.auth import router as auth_router
from src.api.backup import router as backup_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(patient_router, prefix="/patient", tags=["patient"])
api_router.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(backup_router, prefix="/admin/backups", tags=["admin"])
