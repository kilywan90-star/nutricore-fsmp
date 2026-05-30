"""Signature API — digital signing and tamper-proof audit chain."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.user import User
from src.api.auth_deps import get_current_user, require_role
from src.services.signature_service import SignatureService, VALID_ACTIONS, VALID_RESOURCE_TYPES

router = APIRouter()


# ── Request/Response models ────────────────────────────────────────────────


class CreateSignatureRequest(BaseModel):
    resource_type: str = Field(..., description="diagnosis | prescription | medical_record | alert_ack")
    resource_id: str = Field(..., description="UUID of the resource being signed")
    action: str = Field(..., description="confirmed | approved | rejected | acknowledged")
    content: dict | str = Field(..., description="The resource content at signing time")
    confirmation_token: str | None = Field(default=None, description="Optional re-authentication token")


class SignatureResponse(BaseModel):
    id: str
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    signature_data: dict
    content_hash: str
    previous_signature_id: str | None
    created_at: str


class AuditTrailItem(BaseModel):
    id: str
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    signature_data: dict
    content_hash: str
    previous_signature_id: str | None
    created_at: str


class AuditTrailResponse(BaseModel):
    resource_type: str
    resource_id: str
    signatures: list[AuditTrailItem]


class ChainVerificationItemResponse(BaseModel):
    signature_id: str
    user_id: str
    action: str
    timestamp: str
    verified: bool
    content_hash: str


class ChainVerificationResponse(BaseModel):
    valid: bool
    signatures: list[ChainVerificationItemResponse]
    broken_links: list[str]


class VerifyContentRequest(BaseModel):
    current_content: dict | str = Field(..., description="Current content to verify against latest signature")


class ContentVerificationResponse(BaseModel):
    signature_id: str
    content_hash_ok: bool
    stored_hash: str
    current_hash: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/signatures", response_model=SignatureResponse)
async def create_signature(
    body: CreateSignatureRequest,
    request: Request,
    user: User = Depends(require_role("doctor", "department_head", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a digital signature for a clinical resource.

    Links into the signature chain for the resource and stores the SHA-256
    content hash for tamper-proof verification.
    """
    if body.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {', '.join(sorted(VALID_ACTIONS))}",
        )
    if body.resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type. Must be one of: {', '.join(sorted(VALID_RESOURCE_TYPES))}",
        )

    try:
        resource_uuid = uuid.UUID(body.resource_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid resource_id UUID")

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    sig = await SignatureService.sign(
        user_id=user.id,
        resource_type=body.resource_type,
        resource_id=resource_uuid,
        action=body.action,
        content=body.content,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
        confirmation_token=body.confirmation_token,
    )

    return SignatureResponse(
        id=str(sig.id),
        user_id=str(sig.user_id),
        resource_type=sig.resource_type,
        resource_id=str(sig.resource_id),
        action=sig.action,
        signature_data=sig.signature_data,
        content_hash=sig.content_hash,
        previous_signature_id=str(sig.previous_signature_id) if sig.previous_signature_id else None,
        created_at=sig.created_at.isoformat(),
    )


@router.get("/signatures/{resource_type}/{resource_id}", response_model=AuditTrailResponse)
async def get_audit_trail(
    resource_type: str,
    resource_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full chronological audit trail of all signatures for a resource."""
    if resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type. Must be one of: {', '.join(sorted(VALID_RESOURCE_TYPES))}",
        )

    try:
        resource_uuid = uuid.UUID(resource_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid resource_id UUID")

    items = await SignatureService.get_audit_trail(resource_type, resource_uuid, db)

    return AuditTrailResponse(
        resource_type=resource_type,
        resource_id=resource_id,
        signatures=[AuditTrailItem(**item) for item in items],
    )


@router.post("/signatures/verify/{resource_type}/{resource_id}", response_model=ChainVerificationResponse)
async def verify_signature_chain(
    resource_type: str,
    resource_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify the integrity of the entire signature chain for a resource.

    Returns whether the chain is valid, per-signature verification status,
    and any broken links detected.
    """
    if resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type. Must be one of: {', '.join(sorted(VALID_RESOURCE_TYPES))}",
        )

    try:
        resource_uuid = uuid.UUID(resource_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid resource_id UUID")

    result = await SignatureService.verify_chain(resource_type, resource_uuid, db)

    return ChainVerificationResponse(
        valid=result.valid,
        signatures=[
            ChainVerificationItemResponse(
                signature_id=item.signature_id,
                user_id=item.user_id,
                action=item.action,
                timestamp=item.timestamp,
                verified=item.verified,
                content_hash=item.content_hash,
            )
            for item in result.signatures
        ],
        broken_links=result.broken_links,
    )


@router.post("/signatures/verify-content/{resource_type}/{resource_id}", response_model=ContentVerificationResponse)
async def verify_content(
    resource_type: str,
    resource_id: str,
    body: VerifyContentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify current content against the latest signature's stored hash."""
    if resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type. Must be one of: {', '.join(sorted(VALID_RESOURCE_TYPES))}",
        )

    try:
        resource_uuid = uuid.UUID(resource_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid resource_id UUID")

    results = await SignatureService.verify_content_against_current(
        resource_type, resource_uuid, body.current_content, db
    )

    if not results:
        raise HTTPException(status_code=404, detail="No signature found for this resource")

    return ContentVerificationResponse(**results[0])
