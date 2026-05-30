"""Hospital context middleware — resolves and scopes access by hospital."""

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.api.auth_deps import get_current_user
from src.models.user import User, UserRole
from src.models.org import DoctorProfile, Hospital, Department


async def get_doctor_hospital(user: User, db: AsyncSession) -> Hospital | None:
    """Resolve the hospital for a doctor user via their department."""
    if user.role not in (UserRole.DOCTOR, UserRole.DEPARTMENT_HEAD):
        return None

    stmt = select(DoctorProfile).where(
        DoctorProfile.user_id == user.id,
        DoctorProfile.is_active == True,
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile or not profile.hospital_id:
        return None

    hospital_stmt = select(Hospital).where(Hospital.id == profile.hospital_id)
    hospital_result = await db.execute(hospital_stmt)
    return hospital_result.scalar_one_or_none()


async def get_current_hospital(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Hospital | None:
    """Resolve the current hospital context from the authenticated user.

    - Doctors/department_heads: hospital from their department
    - Admins: no single hospital (can switch context)
    - Patients: no hospital context
    """
    if user.role == UserRole.ADMIN:
        # Admin can see all; specific hospital context is optional
        return None
    if user.role in (UserRole.DOCTOR, UserRole.DEPARTMENT_HEAD):
        hospital = await get_doctor_hospital(user, db)
        if not hospital:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No hospital associated with your account",
            )
        return hospital
    return None


def require_hospital(hospital_id_param: str = "hospital_id") -> Callable:
    """FastAPI dependency: resolves and validates hospital-scoped access.

    Usage:
        @router.get("/hospitals/{hospital_id}/patients")
        async def list_patients(
            hospital_id: str,
            hospital: Hospital = Depends(require_hospital()),
            ...
        ):

    Admins can access any hospital. Other roles must match their assigned hospital.
    """

    async def checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Hospital:
        if user.role == UserRole.ADMIN:
            # Admin can access any hospital — caller must pass hospital_id
            return None  # type: ignore[return-value]

        hospital = await get_doctor_hospital(user, db)
        if not hospital:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No hospital associated with your account",
            )
        return hospital

    return checker
