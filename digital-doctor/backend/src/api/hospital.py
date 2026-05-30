"""Hospital management API — admin-only endpoints for hospital CRUD, transfers, and hospital-scoped stats."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from src.db.session import get_db
from src.models.user import User
from src.models.org import (
    Hospital,
    HospitalLevel,
    Department,
    DoctorProfile,
    PatientAssignment,
    TransferRecord,
    TransferStatus,
)
from src.models.patient import Patient
from src.api.auth_deps import require_role, get_current_user
from src.api.hospital_deps import get_current_hospital
from src.services.transfer_service import (
    request_transfer,
    approve_transfer,
    reject_transfer,
    list_transfers,
)

router = APIRouter()

# ── Request/Response models ────────────────────────────────────────────


class CreateHospitalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    address: Optional[str] = Field(default=None, max_length=500)
    level: Optional[str] = Field(default=None, pattern="^(三级甲等|三级乙等|二级甲等|二级乙等|一级甲等)$")


class UpdateHospitalRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    level: Optional[str] = Field(default=None, pattern="^(三级甲等|三级乙等|二级甲等|二级乙等|一级甲等)$")
    is_active: Optional[bool] = None


class CreateTransferRequest(BaseModel):
    patient_id: str
    from_hospital_id: str
    to_hospital_id: str
    reason: Optional[str] = None


class ApproveTransferRequest(BaseModel):
    approved: bool = True


# ── Hospital CRUD ──────────────────────────────────────────────────────


@router.get("/hospitals", dependencies=[Depends(require_role("admin"))])
async def list_hospitals(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Hospital).order_by(Hospital.name)
    result = await db.execute(stmt)
    hospitals = result.scalars().all()

    items = []
    for h in hospitals:
        dept_count_stmt = select(func.count()).select_from(Department).where(
            Department.hospital_id == h.id,
            Department.is_active == True,
        )
        dept_count = (await db.execute(dept_count_stmt)).scalar() or 0

        doctor_count_stmt = select(func.count()).select_from(DoctorProfile).where(
            DoctorProfile.hospital_id == h.id,
            DoctorProfile.is_active == True,
        )
        doctor_count = (await db.execute(doctor_count_stmt)).scalar() or 0

        items.append({
            "id": str(h.id),
            "name": h.name,
            "code": h.code,
            "address": h.address,
            "level": h.level.value if h.level else None,
            "is_active": h.is_active,
            "department_count": dept_count,
            "doctor_count": doctor_count,
        })

    return {"items": items, "total": len(items)}


@router.post("/hospitals", dependencies=[Depends(require_role("admin"))])
async def create_hospital(
    req: CreateHospitalRequest,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Hospital).where(Hospital.code == req.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Hospital code '{req.code}' already exists")

    hospital = Hospital(
        name=req.name,
        code=req.code,
        address=req.address,
        level=HospitalLevel(req.level) if req.level else None,
        is_active=True,
    )
    db.add(hospital)
    await db.commit()
    await db.refresh(hospital)

    return {
        "id": str(hospital.id),
        "name": hospital.name,
        "code": hospital.code,
        "address": hospital.address,
        "level": hospital.level.value if hospital.level else None,
        "is_active": hospital.is_active,
    }


@router.put("/hospitals/{hospital_id}", dependencies=[Depends(require_role("admin"))])
async def update_hospital(
    hospital_id: str,
    req: UpdateHospitalRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        hid = uuid.UUID(hospital_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid hospital_id")

    stmt = select(Hospital).where(Hospital.id == hid)
    result = await db.execute(stmt)
    hospital = result.scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if req.name is not None:
        hospital.name = req.name
    if req.address is not None:
        hospital.address = req.address
    if req.level is not None:
        hospital.level = HospitalLevel(req.level)
    if req.is_active is not None:
        hospital.is_active = req.is_active

    await db.commit()
    await db.refresh(hospital)

    return {
        "id": str(hospital.id),
        "name": hospital.name,
        "code": hospital.code,
        "address": hospital.address,
        "level": hospital.level.value if hospital.level else None,
        "is_active": hospital.is_active,
    }


# ── Hospital statistics ─────────────────────────────────────────────────


@router.get("/hospitals/{hospital_id}/stats", dependencies=[Depends(require_role("admin", "department_head"))])
async def get_hospital_stats(
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        hid = uuid.UUID(hospital_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid hospital_id")

    # Verify hospital exists
    hospital_stmt = select(Hospital).where(Hospital.id == hid)
    hosp_result = await db.execute(hospital_stmt)
    hospital = hosp_result.scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    # Doctor count
    doc_count_stmt = select(func.count()).select_from(DoctorProfile).where(
        DoctorProfile.hospital_id == hid,
        DoctorProfile.is_active == True,
    )
    doctor_count = (await db.execute(doc_count_stmt)).scalar() or 0

    # Department count
    dept_count_stmt = select(func.count()).select_from(Department).where(
        Department.hospital_id == hid,
        Department.is_active == True,
    )
    dept_count = (await db.execute(dept_count_stmt)).scalar() or 0

    # Patient count (via assignments to hospital doctors)
    patient_count_stmt = (
        select(func.count(func.distinct(PatientAssignment.patient_id)))
        .join(DoctorProfile, PatientAssignment.doctor_id == DoctorProfile.id)
        .where(
            DoctorProfile.hospital_id == hid,
            DoctorProfile.is_active == True,
            PatientAssignment.is_active == True,
        )
    )
    patient_count = (await db.execute(patient_count_stmt)).scalar() or 0

    # Pending transfer count
    transfer_count_stmt = select(func.count()).select_from(TransferRecord).where(
        (TransferRecord.from_hospital_id == hid) | (TransferRecord.to_hospital_id == hid),
        TransferRecord.status == TransferStatus.PENDING,
    )
    pending_transfers = (await db.execute(transfer_count_stmt)).scalar() or 0

    return {
        "hospital_id": str(hospital.id),
        "hospital_name": hospital.name,
        "hospital_code": hospital.code,
        "level": hospital.level.value if hospital.level else None,
        "doctor_count": doctor_count,
        "department_count": dept_count,
        "patient_count": patient_count,
        "pending_transfer_count": pending_transfers,
    }


# ── Transfer endpoints ──────────────────────────────────────────────────


@router.post("/transfers", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def create_transfer(
    req: CreateTransferRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        patient_uid = uuid.UUID(req.patient_id)
        from_hid = uuid.UUID(req.from_hospital_id)
        to_hid = uuid.UUID(req.to_hospital_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    try:
        result = await request_transfer(
            db=db,
            patient_id=patient_uid,
            from_hospital_id=from_hid,
            to_hospital_id=to_hid,
            requested_by=user.id,
            reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.post("/transfers/{transfer_id}/approve", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def approve_transfer_endpoint(
    transfer_id: str,
    req: ApproveTransferRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        tid = uuid.UUID(transfer_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid transfer_id")

    try:
        if req.approved:
            result = await approve_transfer(db=db, transfer_id=tid, approved_by=user.id)
        else:
            result = await reject_transfer(db=db, transfer_id=tid, rejected_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.get("/transfers", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def list_transfers_endpoint(
    hospital_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    hid = uuid.UUID(hospital_id) if hospital_id else None
    status_enum = TransferStatus(status) if status else None

    return await list_transfers(
        db=db,
        hospital_id=hid,
        status_filter=status_enum,
        page=page,
        page_size=page_size,
    )
