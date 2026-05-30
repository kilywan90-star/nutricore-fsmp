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
from src.services.drug_checker import get_drug_checker
from src.services.prescription_review import PrescriptionReviewer

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


# ── Medication / Prescription Review models ────────────────────────────────────

class MedicationItem(BaseModel):
    name: str = Field(..., description="药品通用名/英文名/商品名")
    dose: str = Field(..., description="单次剂量，如 500mg")
    frequency: str = Field(..., description="给药频率，如 bid")


class ReviewPrescriptionRequest(BaseModel):
    diagnosis: str = Field(..., description="诊断，如 type2_diabetes, type2_diabetes_newly_diagnosed")
    medications: list[MedicationItem] = Field(default_factory=list)
    patient_data: dict = Field(default_factory=dict)
    lab_results: dict = Field(default_factory=dict)


class CheckInteractionsRequest(BaseModel):
    medications: list[dict] = Field(default_factory=list)


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


# ── Prescription Review ─────────────────────────────────────────────────────

@router.post("/prescriptions/review", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def review_prescription(
    req: ReviewPrescriptionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Comprehensive prescription review: guideline concordance, interactions,
    renal/hepatic dosing, and contraindications."""
    checker = get_drug_checker()
    reviewer = PrescriptionReviewer(checker)

    meds = [{"name": m.name, "dose": m.dose, "frequency": m.frequency} for m in req.medications]

    result = reviewer.review_prescription(
        diagnosis=req.diagnosis,
        medications=meds,
        patient_data=req.patient_data,
        lab_results=req.lab_results,
    )

    await log_operation(
        user_id=user.id,
        action="REVIEW",
        resource_type="prescription",
        resource_id=str(uuid.uuid4()),
        details={
            "diagnosis": req.diagnosis,
            "medication_count": len(meds),
            "overall_rating": result["overall_rating"],
            "issue_count": result["issue_count"],
        },
        db=db,
    )

    return result


# ── Drug Search ──────────────────────────────────────────────────────────────

@router.get("/drugs", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def search_drugs(
    q: str = Query(default="", description="搜索关键词"),
    user: User = Depends(get_current_user),
):
    """Search drug database by name or drug class."""
    checker = get_drug_checker()
    if not q.strip():
        return {"items": checker.search_drugs("")[:50]}
    results = checker.search_drugs(q)
    return {"items": results}


# ── Drug Interaction Check ──────────────────────────────────────────────────

@router.post("/drugs/check-interactions", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def check_drug_interactions(
    req: CheckInteractionsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check interactions for a list of drug names."""
    checker = get_drug_checker()
    drug_names = [m.get("drug_name", m.get("name", "")) for m in req.medications]
    drug_names = [dn for dn in drug_names if dn]

    interactions = checker.check_interactions(drug_names)

    await log_operation(
        user_id=user.id,
        action="CHECK_INTERACTIONS",
        resource_type="drugs",
        resource_id="batch",
        details={"drug_count": len(drug_names), "interaction_count": len(interactions)},
        db=db,
    )

    return {"medications": drug_names, "interactions": interactions}
