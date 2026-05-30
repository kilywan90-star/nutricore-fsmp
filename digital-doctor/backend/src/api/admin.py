"""Admin API endpoints — department management, doctor listing, audit logs."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from src.db.session import get_db
from src.models.user import User
from src.models.org import Department, DoctorProfile, PatientAssignment
from src.api.auth_deps import require_role
from src.security.operation_audit import get_audit_logs

router = APIRouter()

# ── Request/Response models ────────────────────────────────────────────────────

class CreateDepartmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    hospital_id: Optional[str] = Field(default=None)


class AssignDepartmentRequest(BaseModel):
    department_id: str


# ── Department endpoints ───────────────────────────────────────────────────────

@router.get("/departments", dependencies=[Depends(require_role("admin"))])
async def list_departments(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Department).order_by(Department.name)
    result = await db.execute(stmt)
    depts = result.scalars().all()

    items = []
    for d in depts:
        doctor_count_stmt = select(func.count()).select_from(DoctorProfile).where(
            DoctorProfile.department_id == d.id,
            DoctorProfile.is_active == True,
        )
        dc = (await db.execute(doctor_count_stmt)).scalar() or 0
        items.append({
            "id": str(d.id),
            "name": d.name,
            "code": d.code,
            "hospital_id": str(d.hospital_id) if d.hospital_id else None,
            "is_active": d.is_active,
            "doctor_count": dc,
        })

    return {"items": items, "total": len(items)}


@router.post("/departments", dependencies=[Depends(require_role("admin"))])
async def create_department(
    req: CreateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Department).where(Department.code == req.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Department code '{req.code}' already exists")

    dept = Department(
        name=req.name,
        code=req.code,
        hospital_id=uuid.UUID(req.hospital_id) if req.hospital_id else None,
        is_active=True,
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)

    return {
        "id": str(dept.id),
        "name": dept.name,
        "code": dept.code,
        "hospital_id": str(dept.hospital_id) if dept.hospital_id else None,
        "is_active": dept.is_active,
    }


# ── Doctor listing ─────────────────────────────────────────────────────────────

@router.get("/doctors", dependencies=[Depends(require_role("admin"))])
async def list_doctors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(DoctorProfile)
    count_stmt = select(func.count()).select_from(DoctorProfile)
    total = (await db.execute(count_stmt)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(DoctorProfile.title)
    result = await db.execute(query)
    doctors = result.scalars().all()

    items = []
    for doc in doctors:
        dept_stmt = select(Department).where(Department.id == doc.department_id)
        dept_result = await db.execute(dept_stmt)
        dept = dept_result.scalar_one_or_none()

        patient_count_stmt = select(func.count()).select_from(PatientAssignment).where(
            PatientAssignment.doctor_id == doc.id,
            PatientAssignment.is_active == True,
        )
        pc = (await db.execute(patient_count_stmt)).scalar() or 0

        items.append({
            "id": str(doc.id),
            "user_id": str(doc.user_id),
            "department_id": str(doc.department_id),
            "department_name": dept.name if dept else "",
            "department_code": dept.code if dept else "",
            "title": doc.title,
            "license_number": doc.license_number,
            "is_department_head": doc.is_department_head,
            "is_active": doc.is_active,
            "patient_count": pc,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/doctors/{doctor_id}/assign-department", dependencies=[Depends(require_role("admin"))])
async def assign_doctor_department(
    doctor_id: str,
    req: AssignDepartmentRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        did = uuid.UUID(doctor_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid doctor_id")

    try:
        dept_id = uuid.UUID(req.department_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid department_id")

    doc_stmt = select(DoctorProfile).where(DoctorProfile.id == did)
    doc_result = await db.execute(doc_stmt)
    doctor = doc_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    dept_stmt = select(Department).where(Department.id == dept_id)
    dept_result = await db.execute(dept_stmt)
    dept = dept_result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    doctor.department_id = dept_id
    await db.commit()
    await db.refresh(doctor)

    return {
        "id": str(doctor.id),
        "user_id": str(doctor.user_id),
        "department_id": str(doctor.department_id),
        "department_name": dept.name,
        "department_code": dept.code,
        "title": doctor.title,
        "is_department_head": doctor.is_department_head,
    }


# ── Audit log query ─────────────────────────────────────────────────────────────

@router.get("/audit-logs", dependencies=[Depends(require_role("admin"))])
async def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id) if user_id else None
    return await get_audit_logs(
        db,
        user_id=uid,
        action=action,
        resource_type=resource_type,
        page=page,
        page_size=page_size,
    )
