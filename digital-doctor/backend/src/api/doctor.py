from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.db.session import get_db
from src.services.patient_manager import get_patient_list, get_patient_detail
from src.services.alert_engine import check_glucose_alerts
from src.api.auth_deps import require_role

router = APIRouter()


@router.get("/patients", dependencies=[Depends(require_role("doctor", "admin"))])
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    risk_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_patient_list(db, page=page, page_size=page_size, search=search, risk_filter=risk_filter)


@router.get("/patients/{patient_id}", dependencies=[Depends(require_role("doctor", "admin"))])
async def patient_detail(patient_id: str, db: AsyncSession = Depends(get_db)):
    detail = await get_patient_detail(db, patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found")
    return detail


@router.get("/patients/{patient_id}/alerts", dependencies=[Depends(require_role("doctor", "admin"))])
async def patient_alerts(patient_id: str, db: AsyncSession = Depends(get_db)):
    detail = await get_patient_detail(db, patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found")
    glucose_records = [
        {"value_mmol_l": g["value_mmol_l"], "measure_type": g["measure_type"], "recorded_at": g["recorded_at"]}
        for g in detail.get("glucose_records", [])
    ]
    alerts = check_glucose_alerts(glucose_records)
    return {"patient_id": patient_id, "alerts": alerts}
