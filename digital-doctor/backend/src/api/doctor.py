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
from src.services.critical_alert_service import CriticalAlertService
from src.models.critical_alert import CriticalAlert, CriticalAlertStatus
from src.api.auth_deps import require_role, get_current_user
from src.security.authorization import (
    require_patient_access,
    can_access_patient,
    _get_doctor_profile,
    _get_accessible_patient_ids,
    _get_department_patient_ids,
)
from src.security.operation_audit import log_operation
from src.services.cgm_service import get_cgm_summary, detect_patterns, calculate_cgm_metrics
from src.services.prescription_review import PrescriptionReviewer
from src.services.explainability import explainability_engine, generate_explanation_summary
from src.services.record_generator import generate_soap_note, generate_discharge_summary
from src.services.record_service import (
    create_record,
    get_records,
    get_record,
    update_record,
    finalize_record,
)
from src.models.records import RecordType, RecordStatus
from src.models.cgm import CGMRecord, CGMSession

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


# ── Medical Record Generation / Management models ────────────────────────

class GenerateRecordRequest(BaseModel):
    encounter_data: dict = Field(default_factory=dict)


class GenerateDischargeRequest(BaseModel):
    admission_data: dict = Field(default_factory=dict)


class EditRecordRequest(BaseModel):
    content: dict = Field(default_factory=dict)
    markdown: str | None = None


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


# ── Explainability Endpoints ──────────────────────────────────────────────


class ExplainPrescriptionRequest(BaseModel):
    review_result: dict = Field(..., description="Full review result from POST /prescriptions/review")
    patient_data: dict = Field(default_factory=dict, description="Patient clinical data")


@router.get(
    "/patients/{patient_id}/diagnosis/{diagnosis_id}/explain",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def explain_diagnosis(
    patient_id: str,
    diagnosis_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get feature attribution for a specific diagnosis result."""
    detail = await get_patient_detail(db, patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Extract patient clinical data from detail
    latest_glucose = None
    for g in detail.get("glucose_records", []):
        latest_glucose = g
        if g.get("measure_type") == "fasting":
            break
    if not latest_glucose and detail.get("glucose_records"):
        latest_glucose = detail["glucose_records"][0]

    latest_report = detail.get("lab_reports", [None])[0] if detail.get("lab_reports") else None
    age = 2026 - detail.get("birth_year", 1970) if detail.get("birth_year") else None

    patient_data: dict = {
        "fpg": latest_glucose.get("value_mmol_l") if latest_glucose else None,
        "hba1c": latest_report.get("results", {}).get("hba1c") if latest_report else None,
        "bmi": detail.get("bmi"),
        "age": age,
        "birth_year": detail.get("birth_year"),
        "gender": detail.get("gender"),
        "egfr": latest_report.get("results", {}).get("egfr") if latest_report else None,
        "tc": latest_report.get("results", {}).get("tc") if latest_report else None,
        "tg": latest_report.get("results", {}).get("tg") if latest_report else None,
        "ldl": latest_report.get("results", {}).get("ldl") if latest_report else None,
        "hdl": latest_report.get("results", {}).get("hdl") if latest_report else None,
        "diabetes_type": detail.get("diabetes_type"),
        "family_history": detail.get("family_history"),
        "has_hypertension": detail.get("has_hypertension"),
        "waist_circumference": detail.get("waist_circumference"),
        "physical_activity": detail.get("physical_activity"),
    }

    from src.services.diagnosis_engine import differential_diagnosis
    from src.engine.rule_loader import RuleLoader
    from src.engine.rule_engine import RuleEngine

    diagnosis_result = await differential_diagnosis(patient_data)
    loader = RuleLoader()
    rules = loader.load("t2dm_guidelines_v1")
    engine = RuleEngine(rules)
    rule_matches = engine.evaluate(patient_data, category="diagnosis")

    explanation = explainability_engine.explain_diagnosis(
        diagnosis_result, patient_data, rule_matches
    )

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="explanation",
        resource_id=patient_id,
        details={"type": "diagnosis", "confidence": explanation.confidence},
        db=db,
    )

    return explanation.to_dict()


@router.post(
    "/prescriptions/review/explain",
    dependencies=[Depends(require_role("doctor", "department_head", "admin"))],
)
async def explain_prescription(
    req: ExplainPrescriptionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed feature attribution for a prescription review result."""
    explanation = explainability_engine.explain_prescription_review(
        req.review_result, req.patient_data
    )

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="explanation",
        resource_id="prescription_review",
        details={"overall_rating": explanation.overall_rating},
        db=db,
    )

    return explanation.to_dict()


@router.get(
    "/patients/{patient_id}/risk-explanation",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def explain_risk_endpoint(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get risk factor breakdown with actionable interpretation."""
    detail = await get_patient_detail(db, patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found")

    age = 2026 - detail.get("birth_year", 1970) if detail.get("birth_year") else 35
    bmi = detail.get("bmi", 24.0)
    waist = detail.get("waist_circumference", 85.0)
    family_history = bool(detail.get("family_history"))
    physical_activity = detail.get("physical_activity", "moderate")

    latest_glucose = None
    for g in detail.get("glucose_records", []):
        if g.get("measure_type") == "fasting":
            latest_glucose = g
            break
    if not latest_glucose and detail.get("glucose_records"):
        latest_glucose = detail["glucose_records"][0]

    fpg = latest_glucose.get("value_mmol_l", 5.5) if latest_glucose else 5.5
    has_htn = bool(detail.get("has_hypertension"))

    from src.services.risk_assessment import calculate_diabetes_risk
    risk_result = calculate_diabetes_risk(
        age=age,
        bmi=float(bmi),
        waist_circumference=float(waist),
        family_history=family_history,
        physical_activity=str(physical_activity),
        fasting_glucose=float(fpg),
        has_hypertension=has_htn,
    )

    explanation = explainability_engine.explain_risk_assessment(
        risk_result, risk_result.get("factor_scores", {})
    )

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="explanation",
        resource_id=patient_id,
        details={"type": "risk_assessment", "risk_level": explanation.risk_level},
        db=db,
    )

    return explanation.to_dict()


# ── Medical Record Generation ─────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/records/generate",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def generate_record(
    patient_id: str,
    req: GenerateRecordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a SOAP medical record from current encounter data.

    Calls the LLM-powered record generator with encounter_data (pre-consult
    summary, lab results, glucose data, diagnosis, medications). Falls back
    to template-based generation if LLM is unavailable.
    """
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    try:
        uid = uuid.UUID(str(user.id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    content = await generate_soap_note(req.encounter_data)
    record = await create_record(pid, uid, RecordType.SOAP, content, db)

    await log_operation(
        user_id=user.id,
        action="CREATE",
        resource_type="medical_record",
        resource_id=str(record.id),
        details={"record_type": "soap", "patient_id": patient_id},
        db=db,
    )

    return {
        "id": str(record.id),
        "patient_id": str(record.patient_id),
        "doctor_id": str(record.doctor_id),
        "record_type": record.record_type.value,
        "content": record.content,
        "markdown": record.markdown,
        "status": record.status.value,
        "version": record.version,
        "versions": record.versions,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@router.post(
    "/patients/{patient_id}/records/generate-discharge",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def generate_discharge_record(
    patient_id: str,
    req: GenerateDischargeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a discharge summary from admission data."""
    try:
        pid = uuid.UUID(patient_id)
        uid = uuid.UUID(str(user.id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id or user_id")

    content = await generate_discharge_summary(req.admission_data)
    record = await create_record(pid, uid, RecordType.DISCHARGE, content, db)

    await log_operation(
        user_id=user.id,
        action="CREATE",
        resource_type="medical_record",
        resource_id=str(record.id),
        details={"record_type": "discharge", "patient_id": patient_id},
        db=db,
    )

    return {
        "id": str(record.id),
        "patient_id": str(record.patient_id),
        "doctor_id": str(record.doctor_id),
        "record_type": record.record_type.value,
        "content": record.content,
        "markdown": record.markdown,
        "status": record.status.value,
        "version": record.version,
        "versions": record.versions,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


# ── Medical Record CRUD ───────────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/records",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def list_patient_records(
    patient_id: str,
    record_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List medical records for a patient, optionally filtered by type."""
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    rt = RecordType(record_type) if record_type else None
    records = await get_records(pid, db, rt)

    return {
        "patient_id": patient_id,
        "total": len(records),
        "items": [
            {
                "id": str(r.id),
                "patient_id": str(r.patient_id),
                "doctor_id": str(r.doctor_id),
                "record_type": r.record_type.value,
                "status": r.status.value,
                "version": r.version,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in records
        ],
    }


@router.get(
    "/records/{record_id}",
    dependencies=[Depends(require_role("doctor", "department_head", "admin"))],
)
async def get_record_detail(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single medical record with full content."""
    try:
        rid = uuid.UUID(record_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid record_id")

    record = await get_record(rid, db)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return {
        "id": str(record.id),
        "patient_id": str(record.patient_id),
        "doctor_id": str(record.doctor_id),
        "record_type": record.record_type.value,
        "content": record.content,
        "markdown": record.markdown,
        "status": record.status.value,
        "version": record.version,
        "versions": record.versions,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@router.put(
    "/records/{record_id}",
    dependencies=[Depends(require_role("doctor", "department_head", "admin"))],
)
async def edit_record(
    record_id: str,
    req: EditRecordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Edit a medical record, saving current version to history."""
    try:
        rid = uuid.UUID(record_id)
        uid = uuid.UUID(str(user.id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid record_id or user_id")

    edits = {"content": req.content}
    if req.markdown is not None:
        edits["markdown"] = req.markdown

    record = await update_record(rid, edits, uid, db)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    await log_operation(
        user_id=user.id,
        action="UPDATE",
        resource_type="medical_record",
        resource_id=record_id,
        details={"new_version": record.version},
        db=db,
    )

    return {
        "id": str(record.id),
        "patient_id": str(record.patient_id),
        "doctor_id": str(record.doctor_id),
        "record_type": record.record_type.value,
        "content": record.content,
        "markdown": record.markdown,
        "status": record.status.value,
        "version": record.version,
        "versions": record.versions,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@router.post(
    "/records/{record_id}/finalize",
    dependencies=[Depends(require_role("doctor", "department_head", "admin"))],
)
async def finalize_record_endpoint(
    record_id: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Finalize a medical record — status changes to FINALIZED.

    Accepts optional signature data:
    - signed_by: str (UUID of signing user)
    - content_hash: str (SHA-256 content hash from digital signature)
    """
    try:
        rid = uuid.UUID(record_id)
        uid = uuid.UUID(str(user.id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid record_id or user_id")

    signed_by_str = body.get("signed_by") if isinstance(body, dict) else None
    content_hash_val = body.get("content_hash") if isinstance(body, dict) else None
    signed_by = uuid.UUID(signed_by_str) if signed_by_str else None

    record = await finalize_record(rid, uid, db, signed_by=signed_by, content_hash=content_hash_val)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    await log_operation(
        user_id=user.id,
        action="FINALIZE",
        resource_type="medical_record",
        resource_id=record_id,
        details={"signed": bool(content_hash_val)},
        db=db,
    )

    return {
        "id": str(record.id),
        "status": record.status.value,
        "updated_at": record.updated_at.isoformat(),
        "signed_by": str(record.signed_by) if record.signed_by else None,
        "content_hash": record.content_hash,
    }


# ── Critical Alert Endpoints ──────────────────────────────────────────────

class CriticalAlertResponse(BaseModel):
    id: str
    patient_id: str
    alert_type: str
    severity: str
    title: str
    detail: str
    value: float
    detected_at: str
    doctor_user_id: str | None
    status: str
    status_history: list | None = None
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None
    escalated_to: str | None = None
    resolution: str | None = None
    closed_at: str | None = None


class TriggerCriticalAlertRequest(BaseModel):
    patient_id: str
    alert_type: str = Field(default="severe_hyperglycemia")
    value: float = Field(default=18.0)


class AcknowledgeCriticalAlertRequest(BaseModel):
    resolution: str = Field(default="已处理", pattern="^(已处理|已联系患者|转急诊)$")


class CriticalAlertStatsResponse(BaseModel):
    open_count: int
    acknowledged_count: int
    resolved_count: int
    escalated_count: int
    expired_count: int


def _critical_alert_to_response(alert: CriticalAlert) -> CriticalAlertResponse:
    return CriticalAlertResponse(
        id=str(alert.id),
        patient_id=str(alert.patient_id),
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        detail=alert.detail,
        value=alert.value,
        detected_at=alert.detected_at.isoformat(),
        doctor_user_id=str(alert.doctor_user_id) if alert.doctor_user_id else None,
        status=alert.status.value,
        status_history=alert.status_history,
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
        escalated_to=str(alert.escalated_to) if alert.escalated_to else None,
        resolution=alert.resolution,
        closed_at=alert.closed_at.isoformat() if alert.closed_at else None,
    )


@router.post("/critical-alerts", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def trigger_critical_alert(
    req: TriggerCriticalAlertRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger a manual critical alert (dev/test)."""
    try:
        patient_id = uuid.UUID(req.patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_id,
        alert_type=req.alert_type,
        value=req.value,
        db=db,
    )
    if not alert:
        raise HTTPException(status_code=500, detail="Failed to create critical alert")

    await log_operation(
        user_id=user.id,
        action="CREATE",
        resource_type="critical_alert",
        resource_id=str(alert.id),
        details={"patient_id": req.patient_id, "alert_type": req.alert_type, "value": req.value},
        db=db,
    )
    return _critical_alert_to_response(alert)


@router.get("/critical-alerts", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def list_critical_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List critical alerts for the current doctor, paginated and filterable by status."""
    query = select(CriticalAlert)

    if user.role != UserRole.ADMIN:
        query = query.where(CriticalAlert.doctor_user_id == user.id)

    if status_filter:
        try:
            s = CriticalAlertStatus(status_filter)
            query = query.where(CriticalAlert.status == s)
        except ValueError:
            valid = [v.value for v in CriticalAlertStatus]
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid}")

    query = query.order_by(CriticalAlert.detected_at.desc())

    # Count
    count_stmt = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_critical_alert_to_response(a) for a in alerts],
    }


@router.post("/critical-alerts/{alert_id}/acknowledge", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def acknowledge_critical_alert(
    alert_id: str,
    req: AcknowledgeCriticalAlertRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Doctor acknowledges a critical alert with resolution."""
    try:
        aid = uuid.UUID(alert_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    alert = await CriticalAlertService.doctor_acknowledge(
        alert_id=aid,
        doctor_id=user.id,
        resolution=req.resolution,
        db=db,
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Critical alert not found")

    await log_operation(
        user_id=user.id,
        action="ACKNOWLEDGE",
        resource_type="critical_alert",
        resource_id=alert_id,
        details={"resolution": req.resolution},
        db=db,
    )
    return _critical_alert_to_response(alert)


@router.post("/critical-alerts/{alert_id}/nurse-confirm", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def nurse_confirm_critical_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Nurse confirms a critical alert (standard/complete mode)."""
    try:
        aid = uuid.UUID(alert_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    alert = await CriticalAlertService.nurse_confirm(
        alert_id=aid,
        nurse_id=user.id,
        db=db,
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Critical alert not found")

    await log_operation(
        user_id=user.id,
        action="CONFIRM",
        resource_type="critical_alert",
        resource_id=alert_id,
        details={"role": "nurse"},
        db=db,
    )
    return _critical_alert_to_response(alert)


@router.get("/critical-alerts/stats", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def critical_alert_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Summary statistics for critical alerts: open, acknowledged, resolved, escalated, expired counts."""
    async def _count(status_filter: list[CriticalAlertStatus]) -> int:
        stmt = select(func.count()).select_from(CriticalAlert).where(
            CriticalAlert.status.in_(status_filter)
        )
        if user.role != UserRole.ADMIN:
            stmt = stmt.where(CriticalAlert.doctor_user_id == user.id)
        result = await db.execute(stmt)
        return result.scalar() or 0

    open_count = await _count([CriticalAlertStatus.DETECTED, CriticalAlertStatus.NOTIFIED_DOCTOR])
    acknowledged_count = await _count([
        CriticalAlertStatus.DOCTOR_ACKNOWLEDGED,
        CriticalAlertStatus.NURSE_CONFIRMED,
        CriticalAlertStatus.PATIENT_NOTIFIED,
    ])
    resolved_count = await _count([CriticalAlertStatus.RESOLVED])
    escalated_count = await _count([CriticalAlertStatus.ESCALATED])
    expired_count = await _count([CriticalAlertStatus.EXPIRED])

    return CriticalAlertStatsResponse(
        open_count=open_count,
        acknowledged_count=acknowledged_count,
        resolved_count=resolved_count,
        escalated_count=escalated_count,
        expired_count=expired_count,
    )


# ── CGM Doctor View endpoints ──────────────────────────────────────────


@router.get(
    "/patients/{patient_id}/cgm/sessions",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def view_patient_cgm_sessions(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """View a patient's CGM sessions (doctor view)."""
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    stmt = (
        select(CGMSession)
        .where(CGMSession.patient_id == pid)
        .order_by(CGMSession.sensor_start.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="cgm_session",
        resource_id=patient_id,
        details={"session_count": len(sessions)},
        db=db,
    )

    return {
        "patient_id": patient_id,
        "sessions": [
            {
                "id": str(s.id),
                "device_type": s.device_type.value,
                "sensor_start": s.sensor_start.isoformat(),
                "sensor_end": s.sensor_end.isoformat() if s.sensor_end else None,
                "total_readings": s.total_readings,
                "avg_glucose": s.avg_glucose,
                "estimated_hba1c": s.estimated_hba1c,
                "cv_percent": s.cv_percent,
                "time_in_range_pct": s.time_in_range_pct,
                "time_above_range_pct": s.time_above_range_pct,
                "time_below_range_pct": s.time_below_range_pct,
                "mage": s.mage,
                "source_file_name": s.source_file_name,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get(
    "/patients/{patient_id}/cgm/summary",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def view_patient_cgm_summary(
    patient_id: str,
    days: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """View a patient's CGM AGP summary (doctor view)."""
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    summary = await get_cgm_summary(pid, days=days, db=db)

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="cgm_summary",
        resource_id=patient_id,
        details={"days": days},
        db=db,
    )

    return summary


@router.get(
    "/patients/{patient_id}/cgm/patterns",
    dependencies=[Depends(require_role("doctor", "department_head", "admin")),
                  Depends(require_patient_access())],
)
async def view_patient_cgm_patterns(
    patient_id: str,
    session_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Detect glycemic patterns from a patient's latest CGM session."""
    try:
        pid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    if session_id:
        try:
            sid = uuid.UUID(session_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid session_id")
        patterns = await detect_patterns(sid, db)
    else:
        # Use latest session
        stmt = (
            select(CGMSession)
            .where(CGMSession.patient_id == pid)
            .order_by(CGMSession.sensor_start.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest_session = result.scalar_one_or_none()
        if not latest_session:
            return {"patient_id": patient_id, "patterns": []}
        patterns = await detect_patterns(latest_session.id, db)

    await log_operation(
        user_id=user.id,
        action="VIEW",
        resource_type="cgm_patterns",
        resource_id=patient_id,
        details={"pattern_count": len(patterns)},
        db=db,
    )

    return {"patient_id": patient_id, "patterns": patterns}
