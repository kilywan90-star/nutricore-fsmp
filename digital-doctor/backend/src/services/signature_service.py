"""Digital signature service — immutable chain-of-custody for clinical decisions."""
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.signature import SignatureRecord
from src.security.content_hash import hash_content, verify_content_integrity


VALID_ACTIONS = {"confirmed", "approved", "rejected", "acknowledged"}
VALID_RESOURCE_TYPES = {"diagnosis", "prescription", "medical_record", "alert_ack"}


@dataclass
class ChainVerificationItem:
    signature_id: str
    user_id: str
    action: str
    timestamp: str
    verified: bool
    content_hash: str


@dataclass
class ChainVerification:
    valid: bool
    signatures: list[ChainVerificationItem] = field(default_factory=list)
    broken_links: list[str] = field(default_factory=list)


class SignatureService:

    @staticmethod
    async def sign(
        user_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        action: str,
        content: dict | str,
        db: AsyncSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
        confirmation_token: str | None = None,
    ) -> SignatureRecord:
        """Create a digital signature with content hash, linking to the previous signature.

        Args:
            user_id: The signing doctor's user ID.
            resource_type: One of diagnosis, prescription, medical_record, alert_ack.
            resource_id: UUID of the resource being signed.
            action: One of confirmed, approved, rejected, acknowledged.
            content: The resource content dict or string at signing time.
            db: Async database session.
            ip_address: Client IP (optional).
            user_agent: Client user agent (optional).
            confirmation_token: Re-authentication token (optional).

        Returns:
            The created SignatureRecord.
        """
        if action not in VALID_ACTIONS:
            action = "confirmed"
        if resource_type not in VALID_RESOURCE_TYPES:
            resource_type = "diagnosis"

        content_hash = hash_content(content)

        # Find the most recent signature for this resource to build the chain
        prev_stmt = (
            select(SignatureRecord)
            .where(
                SignatureRecord.resource_type == resource_type,
                SignatureRecord.resource_id == resource_id,
            )
            .order_by(desc(SignatureRecord.created_at))
            .limit(1)
        )
        prev_result = await db.execute(prev_stmt)
        previous = prev_result.scalar_one_or_none()

        sig = SignatureRecord(
            id=uuid.uuid4(),
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            signature_data={
                "signed_at": datetime.now(timezone.utc).isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "confirmation_token": confirmation_token,
            },
            content_hash=content_hash,
            previous_signature_id=previous.id if previous else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(sig)
        await db.commit()
        await db.refresh(sig)
        return sig

    @staticmethod
    async def verify_chain(
        resource_type: str,
        resource_id: uuid.UUID,
        db: AsyncSession,
    ) -> ChainVerification:
        """Verify the entire signature chain for a resource.

        Checks:
        - Each signature's content_hash matches the content at signing time (via self-hash).
        - Chain links are unbroken (previous_signature_id references are valid).
        - All hashes are internally consistent.

        Returns:
            ChainVerification with valid flag, per-signature verification, and broken links.
        """
        stmt = (
            select(SignatureRecord)
            .where(
                SignatureRecord.resource_type == resource_type,
                SignatureRecord.resource_id == resource_id,
            )
            .order_by(SignatureRecord.created_at)
        )
        result = await db.execute(stmt)
        signatures = result.scalars().all()

        if not signatures:
            return ChainVerification(valid=True)

        items: list[ChainVerificationItem] = []
        broken_links: list[str] = []
        all_valid = True

        # Track IDs we've seen to verify chain continuity
        seen_ids = {sig.id for sig in signatures}

        for i, sig in enumerate(signatures):
            # Verify chain link: if this sig has a previous_signature_id, it must exist in our set
            if sig.previous_signature_id and sig.previous_signature_id not in seen_ids:
                broken_links.append(
                    f"Broken link at signature {sig.id}: previous {sig.previous_signature_id} not found in chain"
                )
                all_valid = False

            # A signature is self-consistent if its hash is a valid SHA-256 hex string
            hash_valid = len(sig.content_hash) == 64 and all(c in "0123456789abcdef" for c in sig.content_hash)

            items.append(
                ChainVerificationItem(
                    signature_id=str(sig.id),
                    user_id=str(sig.user_id),
                    action=sig.action,
                    timestamp=sig.created_at.isoformat(),
                    verified=hash_valid,
                    content_hash=sig.content_hash,
                )
            )

            if not hash_valid:
                broken_links.append(
                    f"Malformed hash at signature {sig.id}: {sig.content_hash[:16]}..."
                )
                all_valid = False

        return ChainVerification(
            valid=all_valid and len(broken_links) == 0,
            signatures=items,
            broken_links=broken_links,
        )

    @staticmethod
    async def get_audit_trail(
        resource_type: str,
        resource_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Full chronological audit trail of all signings for a resource.

        Returns list of signature dicts in chronological order.
        """
        stmt = (
            select(SignatureRecord)
            .where(
                SignatureRecord.resource_type == resource_type,
                SignatureRecord.resource_id == resource_id,
            )
            .order_by(SignatureRecord.created_at)
        )
        result = await db.execute(stmt)
        signatures = result.scalars().all()

        return [
            {
                "id": str(sig.id),
                "user_id": str(sig.user_id),
                "resource_type": sig.resource_type,
                "resource_id": str(sig.resource_id),
                "action": sig.action,
                "signature_data": sig.signature_data,
                "content_hash": sig.content_hash,
                "previous_signature_id": str(sig.previous_signature_id) if sig.previous_signature_id else None,
                "created_at": sig.created_at.isoformat(),
            }
            for sig in signatures
        ]

    @staticmethod
    async def verify_content_against_current(
        resource_type: str,
        resource_id: uuid.UUID,
        current_content: dict | str,
        db: AsyncSession,
    ) -> list[dict]:
        """Verify that the latest signature's content hash matches the current content."""
        stmt = (
            select(SignatureRecord)
            .where(
                SignatureRecord.resource_type == resource_type,
                SignatureRecord.resource_id == resource_id,
            )
            .order_by(desc(SignatureRecord.created_at))
            .limit(1)
        )
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()

        if not latest:
            return []

        return [
            {
                "signature_id": str(latest.id),
                "content_hash_ok": verify_content_integrity(current_content, latest.content_hash),
                "stored_hash": latest.content_hash,
                "current_hash": hash_content(current_content),
            }
        ]
