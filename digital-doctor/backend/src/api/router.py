from fastapi import APIRouter
from src.api.patient import router as patient_router
from src.api.doctor import router as doctor_router
from src.api.auth import router as auth_router
from src.api.admin import router as admin_router
from src.api.backup import router as backup_router
from src.api.notification import router as notification_router
from src.api.hospital import router as hospital_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(patient_router, prefix="/patient", tags=["patient"])
api_router.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(backup_router, prefix="/admin/backups", tags=["backups"])
api_router.include_router(hospital_router, prefix="/admin", tags=["hospitals"])
api_router.include_router(notification_router, prefix="", tags=["notifications"])
