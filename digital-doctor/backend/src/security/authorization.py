"""Enhanced RBAC authorization with department isolation and patient access control."""

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.api.auth_deps import get_current_user
from src.models.user import User, UserRole
from src.models.org import DoctorProfile, PatientAssignment, Department

ROLE_HIERARCHY = {
    UserRole.ADMIN: 100,
    UserRole.DEPARTMENT_HEAD: 80,
    UserRole.DOCTOR: 60,
    UserRole.PATIENT: 40,
}


async def _get_doctor_profile(user_id: uuid.UUID, db: AsyncSession) -> DoctorProfile:
    stmt = select(DoctorProfile).where(
        DoctorProfile.user_id == user_id,
        DoctorProfile.is_active == True,
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active doctor profile found for this user",
        )
    return profile


def require_department(department_code: str) -> Callable:
    """FastAPI dependency: restricts access to a specific department.

    Usage: Depends(require_department("endocrinology"))
    """

    async def inner(user: User, db: AsyncSession = Depends(get_db)) -> User:
        if user.role == UserRole.ADMIN:
            return user

        profile = await _get_doctor_profile(user.id, db)

        dept_stmt = select(Department).where(
            Department.id == profile.department_id,
            Department.code == department_code,
            Department.is_active == True,
        )
        dept_result = await db.execute(dept_stmt)
        if not dept_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to department: {department_code}",
            )
        return user

    return inner


async def _get_accessible_patient_ids(doctor_id: uuid.UUID, db: AsyncSession) -> set[uuid.UUID]:
    """Get the set of patient IDs accessible to a doctor via active assignments."""
    stmt = select(PatientAssignment.patient_id).where(
        PatientAssignment.doctor_id == doctor_id,
        PatientAssignment.is_active == True,
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


async def _get_department_patient_ids(department_id: uuid.UUID, db: AsyncSession) -> set[uuid.UUID]:
    """Get all patient IDs for doctors in a given department."""
    stmt = (
        select(PatientAssignment.patient_id)
        .join(DoctorProfile, PatientAssignment.doctor_id == DoctorProfile.id)
        .where(
            DoctorProfile.department_id == department_id,
            DoctorProfile.is_active == True,
            PatientAssignment.is_active == True,
        )
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


async def can_access_patient(doctor_id: uuid.UUID, patient_id: uuid.UUID, db: AsyncSession) -> bool:
    """Check if a doctor has access to a specific patient via active assignment.

    Returns True if an active PatientAssignment exists for (doctor_id, patient_id).
    """
    stmt = select(PatientAssignment).where(
        PatientAssignment.doctor_id == doctor_id,
        PatientAssignment.patient_id == patient_id,
        PatientAssignment.is_active == True,
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def is_department_head(user: User, db: AsyncSession) -> bool:
    """Check if the given user is a department head."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role not in (UserRole.DEPARTMENT_HEAD, UserRole.DOCTOR):
        return False

    stmt = select(DoctorProfile).where(
        DoctorProfile.user_id == user.id,
        DoctorProfile.is_department_head == True,
        DoctorProfile.is_active == True,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


def require_patient_access(patient_id_param: str = "patient_id") -> Callable:
    """FastAPI dependency: checks if the current doctor has access to the specified patient.

    Usage: Depends(require_patient_access())
    The path parameter must be named 'patient_id' (or override via param).
    """

    async def checker(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if user.role == UserRole.ADMIN:
            return user

        patient_id_str = request.path_params.get(patient_id_param)
        if not patient_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing path parameter: {patient_id_param}",
            )

        try:
            pid = uuid.UUID(patient_id_str)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid patient_id")

        if user.role == UserRole.DEPARTMENT_HEAD:
            profile = await _get_doctor_profile(user.id, db)
            dept_patients = await _get_department_patient_ids(profile.department_id, db)
            if pid not in dept_patients:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: patient not in your department",
                )
            return user

        profile = await _get_doctor_profile(user.id, db)
        if not await can_access_patient(profile.id, pid, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: patient not assigned to you",
            )
        return user

    return checker
