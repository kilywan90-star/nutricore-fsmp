import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from src.db.session import get_db
from src.models.user import User, UserRole
from src.models.org import DoctorProfile, PatientAssignment, Department, AssignmentType
from src.models.patient import Patient
from src.services.patient_manager import get_patient_list, get_patient_detail
from src.services.alert_engine import check_glucose_alerts
from src.api.auth_deps import require_role, get_current_user
from src.security.authorization import (
    require_patient_access,
    can_access_patient,
    _get_doctor_profile,
    _get_accessible_patient_ids,
    _get_department_patient_ids,
)
from src.security.operation_audit import log_operation

router = APIRouter()


# ── Request/Response models ────────────────────────────────────────────────────

class AssignPatientRequest(BaseModel):
    assignment_type: str = Field(default="primary", pattern="^(primary|consulting)$")


class DoctorProfileResponse(BaseModel):
    id: str
    user_id: str
    department_id: str
    department_name: str
    department_code: str
    title: str
    license_number: Optional[str]
    is_department_head: bool
    patient_count: int


class UpdateProfileRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=50)
    license_number: Optional[str] = Field(default=None, max_length=50)


# ── Patient listing (scoped to accessible patients) ────────────────────────────

@router.get("/patients", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    risk_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    accessible_ids = None
    if user.role != UserRole.ADMIN:
        profile = await _get_doctor_profile(user.id, db)
        if user.role == UserRole.DEPARTMENT_HEAD:
            accessible_ids = await _get_department_patient_ids(profile.department_id, db)
        else:
            accessible_ids = await _get_accessible_patient_ids(profile.id, db)

    return await get_patient_list(
        db,
        page=page,
        page_size=page_size,
        search=search,
        risk_filter=risk_filter,
        patient_ids=accessible_ids,
    )


# ── Patient detail (access-gated) ──────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def patient_detail(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    detail = await get_patient_detail(db, patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found")

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="patient",
        resource_id=patient_id,
        details={"endpoint": "doctor_patient_detail"},
        db=db,
    )
    return detail


# ── Patient alerts (access-gated) ──────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/alerts",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def patient_alerts(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    detail = await get_patient_detail(db, patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found")
    glucose_records = [
        {"value_mmol_l": g["value_mmol_l"], "measure_type": g["measure_type"], "recorded_at": g["recorded_at"]}
        for g in detail.get("glucose_records", [])
    ]
    alerts = check_glucose_alerts(glucose_records)

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="alert",
        resource_id=patient_id,
        details={"alert_count": len(alerts)},
        db=db,
    )
    return {"patient_id": patient_id, "alerts": alerts}


# ── Assign patient to doctor ───────────────────────────────────────────────────

@router.post("/patients/{patient_id}/assign", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def assign_patient(
    patient_id: str,
    req: AssignPatientRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    # Verify patient exists
    patient_stmt = select(Patient).where(Patient.id == pid)
    patient_result = await db.execute(patient_stmt)
    if not patient_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get or verify doctor profile
    doctor_stmt = select(DoctorProfile).where(
        DoctorProfile.user_id == user.id,
        DoctorProfile.is_active == True,
    )
    doctor_result = await db.execute(doctor_stmt)
    doctor = doctor_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=403, detail="No active doctor profile found")

    # Deactivate any existing primary assignments for this patient
    assignment_type = AssignmentType(req.assignment_type)
    if assignment_type == AssignmentType.PRIMARY:
        existing = await db.execute(
            select(PatientAssignment).where(
                PatientAssignment.patient_id == pid,
                PatientAssignment.is_active == True,
                PatientAssignment.assignment_type == AssignmentType.PRIMARY,
            )
        )
        for old in existing.scalars().all():
            old.is_active = False

    # Check for existing assignment from this doctor
    existing_stmt = select(PatientAssignment).where(
        PatientAssignment.patient_id == pid,
        PatientAssignment.doctor_id == doctor.id,
        PatientAssignment.assignment_type == assignment_type,
    )
    existing_result = await db.execute(existing_stmt)
    existing_assignment = existing_result.scalar_one_or_none()

    if existing_assignment:
        existing_assignment.is_active = True
        await db.commit()
        await db.refresh(existing_assignment)
        assignment = existing_assignment
    else:
        assignment = PatientAssignment(
            patient_id=pid,
            doctor_id=doctor.id,
            assignment_type=assignment_type,
            is_active=True,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

    await log_operation(
        user_id=user.id,
        action="ASSIGN",
        resource_type="patient",
        resource_id=patient_id,
        details={
            "doctor_id": str(doctor.id),
            "assignment_type": req.assignment_type,
            "assignment_id": str(assignment.id),
        },
        db=db,
    )

    return {
        "assignment_id": str(assignment.id),
        "patient_id": str(assignment.patient_id),
        "doctor_id": str(assignment.doctor_id),
        "assignment_type": assignment.assignment_type.value,
        "is_active": assignment.is_active,
        "assigned_at": assignment.assigned_at.isoformat(),
    }


# ── My patients (direct assignments only) ──────────────────────────────────────

@router.get("/my-patients", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def my_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.ADMIN:
        return await get_patient_list(db, page=page, page_size=page_size)

    profile = await _get_doctor_profile(user.id, db)
    accessible_ids = await _get_accessible_patient_ids(profile.id, db)

    return await get_patient_list(
        db,
        page=page,
        page_size=page_size,
        patient_ids=accessible_ids,
    )


# ── Department patients (dept head only) ───────────────────────────────────────

@router.get("/department/patients", dependencies=[Depends(require_role("department_head", "admin"))])
async def department_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.ADMIN:
        return await get_patient_list(db, page=page, page_size=page_size)

    profile = await _get_doctor_profile(user.id, db)
    dept_patient_ids = await _get_department_patient_ids(profile.department_id, db)

    return await get_patient_list(
        db,
        page=page,
        page_size=page_size,
        patient_ids=dept_patient_ids,
    )


# ── Doctor profile ─────────────────────────────────────────────────────────────

@router.get("/profile", response_model=DoctorProfileResponse,
            dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def get_doctor_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = await _get_doctor_profile(user.id, db)

    dept_stmt = select(Department).where(Department.id == profile.department_id)
    dept_result = await db.execute(dept_stmt)
    dept = dept_result.scalar_one_or_none()

    patient_count_stmt = select(func.count()).select_from(PatientAssignment).where(
        PatientAssignment.doctor_id == profile.id,
        PatientAssignment.is_active == True,
    )
    patient_count = (await db.execute(patient_count_stmt)).scalar() or 0

    return DoctorProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        department_id=str(profile.department_id),
        department_name=dept.name if dept else "",
        department_code=dept.code if dept else "",
        title=profile.title,
        license_number=profile.license_number,
        is_department_head=profile.is_department_head,
        patient_count=patient_count,
    )


@router.put("/profile", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def update_doctor_profile(
    req: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = await _get_doctor_profile(user.id, db)

    if req.title is not None:
        profile.title = req.title
    if req.license_number is not None:
        profile.license_number = req.license_number

    await db.commit()
    await db.refresh(profile)

    return {
        "id": str(profile.id),
        "title": profile.title,
        "license_number": profile.license_number,
    }


# ── Diagnosis Requests/Response models ───────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    patient_data: dict = Field(..., description="Clinical data dict: fpg, hba1c, bmi, age, egfr, etc.")
    pre_consult_summary: Optional[dict] = Field(default=None, description="Pre-consultation summary")
    lab_results: Optional[dict] = Field(default=None, description="Additional lab results")


class HomaRequest(BaseModel):
    fasting_insulin: float = Field(..., gt=0, description="Fasting insulin (μIU/mL)")
    fasting_glucose: float = Field(..., gt=0, description="Fasting glucose (mmol/L)")


# ── Assisted Diagnosis ──────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/diagnose",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def diagnose_patient(
    patient_id: str,
    req: DiagnoseRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run differential diagnosis for a patient.

    Combines rule-engine classification with optional LLM second-pass
    analysis for complex cases.
    """
    # Verify patient exists
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    patient_stmt = select(Patient).where(Patient.id == pid)
    patient_result = await db.execute(patient_stmt)
    if not patient_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    from src.services.diagnosis_engine import differential_diagnosis

    result = await differential_diagnosis(
        patient_data=req.patient_data,
        pre_consult_summary=req.pre_consult_summary,
        lab_results=req.lab_results,
    )

    await log_operation(
        user_id=user.id,
        action="DIAGNOSE",
        resource_type="patient",
        resource_id=patient_id,
        details={"method": result.get("method"), "confidence": result.get("overall_confidence")},
        db=db,
    )

    return {
        "patient_id": patient_id,
        "doctor_id": str(user.id),
        "diagnosis": result,
    }


# ── HOMA Calculator ─────────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/homa",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def calculate_homa(
    patient_id: str,
    req: HomaRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Calculate HOMA-IR and HOMA-beta for a patient."""
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    patient_stmt = select(Patient).where(Patient.id == pid)
    patient_result = await db.execute(patient_stmt)
    if not patient_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    from src.services.homa_calculator import calculate_homa_ir, calculate_homa_beta

    homa_ir = calculate_homa_ir(req.fasting_insulin, req.fasting_glucose)
    homa_beta = calculate_homa_beta(req.fasting_insulin, req.fasting_glucose)

    await log_operation(
        user_id=user.id,
        action="HOMA_CALC",
        resource_type="patient",
        resource_id=patient_id,
        details={
            "fasting_insulin": req.fasting_insulin,
            "fasting_glucose": req.fasting_glucose,
        },
        db=db,
    )

    return {
        "patient_id": patient_id,
        "homa_ir": homa_ir,
        "homa_beta": homa_beta,
    }
