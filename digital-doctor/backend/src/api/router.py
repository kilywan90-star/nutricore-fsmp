from fastapi import APIRouter
from src.api.patient import router as patient_router
from src.api.doctor import router as doctor_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(patient_router, prefix="/patient", tags=["patient"])
api_router.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
