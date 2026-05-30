"""Admin API endpoints — department management, doctor listing, audit logs, dashboard, config."""

import json
import uuid
from datetime import datetime, timedelta, date, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from src.db.session import get_db
from src.models.user import User, UserRole
from src.models.org import Department, DoctorProfile, PatientAssignment
from src.models.patient import Patient, GlucoseRecord
from src.models.clinical import Alert, AlertSeverity
from src.api.auth_deps import require_role
from src.security.operation_audit import get_audit_logs

router = APIRouter()

# ── Config file paths ────────────────────────────────────────────────────────────

_RULES_DIR = Path(__file__).parent.parent / "engine" / "rules"
_CONFIG_FILE = _RULES_DIR / "admin_config.json"
_CONFIG_VERSIONS_DIR = _RULES_DIR / "admin_config_versions"

DEFAULT_CONFIG: dict = {
    "fpg_diagnostic_threshold": 7.0,
    "hba1c_diagnostic_threshold": 6.5,
    "hba1c_treatment_target": 7.0,
    "elderly_hba1c_target": 8.0,
    "egfr_metformin_contraindication": 45,
    "severe_hyperglycemia_threshold": 16.7,
    "hypoglycemia_threshold": 3.9,
}


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {**DEFAULT_CONFIG}


def _save_config(cfg: dict, version: int) -> None:
    _CONFIG_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    cfg_with_meta = {
        **cfg,
        "config_version": version,
        "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg_with_meta, f, ensure_ascii=False, indent=2)
    version_file = _CONFIG_VERSIONS_DIR / f"admin_config_v{version}.json"
    with open(version_file, "w", encoding="utf-8") as f:
        json.dump(cfg_with_meta, f, ensure_ascii=False, indent=2)


def _get_next_version() -> int:
    cfg = _load_config()
    return cfg.get("config_version", 0) + 1


# ── Request/Response models ──────────────────────────────────────────────────────

class CreateDepartmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    hospital_id: Optional[str] = Field(default=None)


class UpdateDepartmentRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    is_active: Optional[bool] = Field(default=None)


class AssignDepartmentRequest(BaseModel):
    department_id: str


class UpdateConfigRequest(BaseModel):
    fpg_diagnostic_threshold: Optional[float] = Field(default=None, ge=3.0, le=20.0)
    hba1c_diagnostic_threshold: Optional[float] = Field(default=None, ge=3.0, le=15.0)
    hba1c_treatment_target: Optional[float] = Field(default=None, ge=3.0, le=15.0)
    elderly_hba1c_target: Optional[float] = Field(default=None, ge=3.0, le=15.0)
    egfr_metformin_contraindication: Optional[float] = Field(default=None, ge=1.0, le=120.0)
    severe_hyperglycemia_threshold: Optional[float] = Field(default=None, ge=5.0, le=50.0)
    hypoglycemia_threshold: Optional[float] = Field(default=None, ge=1.0, le=10.0)


# ── Dashboard ────────────────────────────────────────────────────────────────────

@router.get("/dashboard", dependencies=[Depends(require_role("admin"))])
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
):
    # Total patients
    total_patients_stmt = select(func.count()).select_from(Patient)
    total_patients = (await db.execute(total_patients_stmt)).scalar() or 0

    # Active patients (glucose record in last 30 days)
    thirty_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    active_patients_stmt = (
        select(func.count(func.distinct(GlucoseRecord.patient_id)))
        .where(GlucoseRecord.recorded_at >= thirty_days_ago)
    )
    active_patients = (await db.execute(active_patients_stmt)).scalar() or 0

    # Total doctors
    total_doctors_stmt = select(func.count()).select_from(DoctorProfile).where(
        DoctorProfile.is_active == True
    )
    total_doctors = (await db.execute(total_doctors_stmt)).scalar() or 0

    # Total departments
    total_depts_stmt = select(func.count()).select_from(Department).where(
        Department.is_active == True
    )
    total_departments = (await db.execute(total_depts_stmt)).scalar() or 0

    # Alert counts by severity
    alert_counts = {}
    for sev in AlertSeverity:
        count_stmt = (
            select(func.count())
            .select_from(Alert)
            .where(Alert.severity == sev, Alert.acknowledged == False)
        )
        alert_counts[sev.value] = (await db.execute(count_stmt)).scalar() or 0

    # Glucose control rate
    glucose_control_stmt = (
        select(GlucoseRecord)
        .order_by(GlucoseRecord.patient_id, GlucoseRecord.recorded_at.desc())
    )
    # This is a simplified query; for a real system we would use a window function.
    # Instead we query the latest glucose per patient efficiently with a subquery.
    latest_glucose_subq = (
        select(
            GlucoseRecord.patient_id,
            GlucoseRecord.value_mmol_l,
            func.row_number()
            .over(
                partition_by=GlucoseRecord.patient_id,
                order_by=GlucoseRecord.recorded_at.desc(),
            )
            .label("rn"),
        )
        .where(GlucoseRecord.recorded_at >= thirty_days_ago)
        .subquery()
    )
    latest_vals = select(
        latest_glucose_subq.c.value_mmol_l
    ).where(latest_glucose_subq.c.rn == 1)

    result = await db.execute(latest_vals)
    latest_values = [row[0] for row in result.all()]

    if latest_values:
        in_range = sum(1 for v in latest_values if 3.9 <= v <= 10.0)
        glucose_control_rate = round(in_range / len(latest_values) * 100, 1)
    else:
        glucose_control_rate = 0.0

    # Patient registration trend (last 7 days)
    trend = []
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day + timedelta(days=1), datetime.min.time())
        count_stmt = (
            select(func.count())
            .select_from(Patient)
            .where(Patient.created_at >= day_start, Patient.created_at < day_end)
        )
        day_count = (await db.execute(count_stmt)).scalar() or 0
        trend.append({"date": day.isoformat(), "count": day_count})

    return {
        "total_patients": total_patients,
        "active_patients": active_patients,
        "total_doctors": total_doctors,
        "total_departments": total_departments,
        "alerts_by_severity": alert_counts,
        "glucose_control_rate": glucose_control_rate,
        "patient_registration_trend": trend,
    }


# ── Department endpoints ─────────────────────────────────────────────────────────

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

        patient_count_stmt = (
            select(func.count(func.distinct(PatientAssignment.patient_id)))
            .select_from(PatientAssignment)
            .join(DoctorProfile, DoctorProfile.id == PatientAssignment.doctor_id)
            .where(
                DoctorProfile.department_id == d.id,
                PatientAssignment.is_active == True,
            )
        )
        pc = (await db.execute(patient_count_stmt)).scalar() or 0

        items.append({
            "id": str(d.id),
            "name": d.name,
            "code": d.code,
            "hospital_id": str(d.hospital_id) if d.hospital_id else None,
            "is_active": d.is_active,
            "doctor_count": dc,
            "patient_count": pc,
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


@router.put("/departments/{department_id}", dependencies=[Depends(require_role("admin"))])
async def update_department(
    department_id: str,
    req: UpdateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        did = uuid.UUID(department_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid department_id")

    stmt = select(Department).where(Department.id == did)
    result = await db.execute(stmt)
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    if req.code is not None and req.code != dept.code:
        existing = await db.execute(
            select(Department).where(Department.code == req.code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Department code '{req.code}' already exists")
        dept.code = req.code

    if req.name is not None:
        dept.name = req.name
    if req.is_active is not None:
        dept.is_active = req.is_active

    await db.commit()
    await db.refresh(dept)

    return {
        "id": str(dept.id),
        "name": dept.name,
        "code": dept.code,
        "hospital_id": str(dept.hospital_id) if dept.hospital_id else None,
        "is_active": dept.is_active,
    }


@router.delete("/departments/{department_id}", dependencies=[Depends(require_role("admin"))])
async def delete_department(
    department_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        did = uuid.UUID(department_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid department_id")

    stmt = select(Department).where(Department.id == did)
    result = await db.execute(stmt)
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    doctor_count_stmt = select(func.count()).select_from(DoctorProfile).where(
        DoctorProfile.department_id == did,
        DoctorProfile.is_active == True,
    )
    dc = (await db.execute(doctor_count_stmt)).scalar() or 0
    if dc > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete department with {dc} active doctors")

    await db.delete(dept)
    await db.commit()

    return {"detail": "Department deleted"}


# ── Doctor listing ───────────────────────────────────────────────────────────────

@router.get("/doctors", dependencies=[Depends(require_role("admin"))])
async def list_doctors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(DoctorProfile)
    count_query = select(func.count()).select_from(DoctorProfile)

    dept_uuid: Optional[uuid.UUID] = None
    if department_id:
        try:
            dept_uuid = uuid.UUID(department_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid department_id")
        query = query.where(DoctorProfile.department_id == dept_uuid)
        count_query = count_query.where(DoctorProfile.department_id == dept_uuid)

    total = (await db.execute(count_query)).scalar() or 0

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

        user_stmt = select(User).where(User.id == doc.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

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
            "last_login_at": user.last_login_at.isoformat() if user and user.last_login_at else None,
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


@router.put("/doctors/{doctor_id}/toggle-active", dependencies=[Depends(require_role("admin"))])
async def toggle_doctor_active(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        did = uuid.UUID(doctor_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid doctor_id")

    doc_stmt = select(DoctorProfile).where(DoctorProfile.id == did)
    doc_result = await db.execute(doc_stmt)
    doctor = doc_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor.is_active = not doctor.is_active
    await db.commit()
    await db.refresh(doctor)

    return {"id": str(doctor.id), "is_active": doctor.is_active}


# ── Patient listing (admin) ──────────────────────────────────────────────────────

@router.get("/patients", dependencies=[Depends(require_role("admin"))])
async def list_admin_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    department_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    glucose_control: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Patient)
    count_query = select(func.count()).select_from(Patient)

    # Filter by department (via PatientAssignment -> DoctorProfile -> Department)
    if department_id:
        try:
            dept_uuid = uuid.UUID(department_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid department_id")
        dept_patient_subq = (
            select(func.distinct(PatientAssignment.patient_id))
            .join(DoctorProfile, DoctorProfile.id == PatientAssignment.doctor_id)
            .where(
                DoctorProfile.department_id == dept_uuid,
                PatientAssignment.is_active == True,
            )
        )
        patient_ids_result = await db.execute(dept_patient_subq)
        dept_patient_ids = [row[0] for row in patient_ids_result.all()]
        if not dept_patient_ids:
            return {"total": 0, "page": page, "page_size": page_size, "items": []}
        query = query.where(Patient.id.in_(dept_patient_ids))
        count_query = count_query.where(Patient.id.in_(dept_patient_ids))

    if search:
        query = query.where(Patient.name_hash.ilike(f"%{search}%"))
        count_query = count_query.where(Patient.name_hash.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Patient.created_at.desc())
    result = await db.execute(query)
    patients = result.scalars().all()

    items = []
    for p in patients:
        # Latest glucose
        latest_g_stmt = (
            select(GlucoseRecord.value_mmol_l)
            .where(GlucoseRecord.patient_id == p.id)
            .order_by(GlucoseRecord.recorded_at.desc())
            .limit(1)
        )
        lg = (await db.execute(latest_g_stmt)).scalar()

        # Unacknowledged alert count
        alert_count_stmt = select(func.count()).where(
            Alert.patient_id == p.id,
            Alert.acknowledged == False,
        )
        alert_count = (await db.execute(alert_count_stmt)).scalar() or 0

        # Determine glucose control status
        glucose_status = "no_data"
        if lg is not None:
            if lg < 3.9:
                glucose_status = "hypo"
            elif lg <= 7.0:
                glucose_status = "controlled"
            elif lg <= 10.0:
                glucose_status = "elevated"
            else:
                glucose_status = "poor"

        # Post-filter by glucose_control
        if glucose_control and glucose_status != glucose_control:
            continue

        items.append({
            "id": str(p.id),
            "gender": p.gender,
            "birth_year": p.birth_year,
            "diabetes_type": p.diabetes_type,
            "hba1c_target": p.hba1c_target,
            "latest_glucose": round(lg, 1) if lg else None,
            "alert_count": alert_count,
            "glucose_control_status": glucose_status,
        })

    # Post-filter for risk_level
    if risk_level:
        # Simple heuristic: high risk if alert_count >=3 or latest glucose > 13.9
        filtered = []
        for item in items:
            item_risk = (
                "high"
                if (item["alert_count"] >= 3 or (item["latest_glucose"] is not None and item["latest_glucose"] > 13.9))
                else "low"
            )
            if item_risk == risk_level:
                filtered.append(item)
        items = filtered

    # If glucose_control was specified, we need to adjust total (approximation)
    if glucose_control or risk_level:
        total = len(items)

    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ── Config management ────────────────────────────────────────────────────────────

@router.get("/config", dependencies=[Depends(require_role("admin"))])
async def get_config():
    cfg = _load_config()
    version = cfg.get("config_version", 0)
    sorted_keys = [
        "fpg_diagnostic_threshold",
        "hba1c_diagnostic_threshold",
        "hba1c_treatment_target",
        "elderly_hba1c_target",
        "egfr_metformin_contraindication",
        "severe_hyperglycemia_threshold",
        "hypoglycemia_threshold",
    ]
    params = {k: cfg.get(k, DEFAULT_CONFIG[k]) for k in sorted_keys}

    # List versions
    versions = []
    if _CONFIG_VERSIONS_DIR.exists():
        for vf in sorted(_CONFIG_VERSIONS_DIR.glob("admin_config_v*.json")):
            try:
                v_num = int(vf.stem.replace("admin_config_v", ""))
                mtime = datetime.fromtimestamp(vf.stat().st_mtime).isoformat()
                versions.append({"version": v_num, "updated_at": mtime})
            except (ValueError, OSError):
                pass

    return {
        "params": params,
        "config_version": version,
        "versions": versions,
    }


@router.post("/config", dependencies=[Depends(require_role("admin"))])
async def update_config(req: UpdateConfigRequest):
    cfg = _load_config()
    version = _get_next_version()

    updates = req.model_dump(exclude_none=True)
    for key, val in updates.items():
        cfg[key] = val

    _save_config(cfg, version)

    return {
        "params": {k: cfg.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG},
        "config_version": version,
        "detail": "Configuration updated",
    }


@router.post("/config/reset", dependencies=[Depends(require_role("admin"))])
async def reset_config():
    version = _get_next_version()
    _save_config({**DEFAULT_CONFIG}, version)

    return {
        "params": DEFAULT_CONFIG,
        "config_version": version,
        "detail": "Configuration reset to defaults",
    }


# ── Audit log query ──────────────────────────────────────────────────────────────

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
