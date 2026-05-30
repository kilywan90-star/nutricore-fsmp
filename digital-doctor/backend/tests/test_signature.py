"""Tests for digital signature system — immutable audit chain and content hashing."""
import uuid

import pytest
from sqlalchemy import select

from src.models.signature import SignatureRecord
from src.models.user import User, UserRole
from src.security.content_hash import hash_content, verify_content_integrity
from src.services.signature_service import SignatureService


_fixture_counter = 0


def _unique_phone() -> str:
    global _fixture_counter
    _fixture_counter += 1
    return f"test_sign_{_fixture_counter}"


@pytest.fixture
async def doctor_user(db_session):
    """Create a doctor user."""
    user = User(
        phone_hash=_unique_phone(),
        password_hash="hash",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def doctor_user2(db_session):
    """Create a second doctor user for chain testing."""
    user = User(
        phone_hash=_unique_phone(),
        password_hash="hash",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


# ── Test 1: create signature and verify chain ──────────────────────────────


@pytest.mark.asyncio
async def test_create_signature_and_verify_chain(db_session, doctor_user, doctor_user2):
    """Creating two signatures for the same resource should form a valid chain."""
    resource_id = uuid.uuid4()
    content1 = {"diagnosis": "type2_diabetes", "confidence": 0.85}
    content2 = {"diagnosis": "type2_diabetes", "confidence": 0.90, "reviewed": True}

    sig1 = await SignatureService.sign(
        user_id=doctor_user.id,
        resource_type="diagnosis",
        resource_id=resource_id,
        action="confirmed",
        content=content1,
        db=db_session,
        ip_address="192.168.1.1",
    )
    assert sig1.id is not None
    assert sig1.previous_signature_id is None
    assert len(sig1.content_hash) == 64

    sig2 = await SignatureService.sign(
        user_id=doctor_user2.id,
        resource_type="diagnosis",
        resource_id=resource_id,
        action="approved",
        content=content2,
        db=db_session,
        ip_address="192.168.1.2",
    )
    assert sig2.previous_signature_id == sig1.id

    # Verify chain
    result = await SignatureService.verify_chain("diagnosis", resource_id, db_session)
    assert result.valid is True
    assert len(result.signatures) == 2
    assert len(result.broken_links) == 0
    assert result.signatures[0].verified is True
    assert result.signatures[1].verified is True

    # Get audit trail
    trail = await SignatureService.get_audit_trail("diagnosis", resource_id, db_session)
    assert len(trail) == 2
    assert trail[0]["user_id"] == str(doctor_user.id)
    assert trail[1]["user_id"] == str(doctor_user2.id)


# ── Test 2: verify detects tampered content ────────────────────────────────


@pytest.mark.asyncio
async def test_verify_detects_tampered_content(db_session, doctor_user):
    """Content that has been modified should not match the signed hash."""
    resource_id = uuid.uuid4()
    original = {"prescription": ["metformin 500mg bid"], "signed": True}

    sig = await SignatureService.sign(
        user_id=doctor_user.id,
        resource_type="prescription",
        resource_id=resource_id,
        action="confirmed",
        content=original,
        db=db_session,
    )

    # Verify original content
    assert verify_content_integrity(original, sig.content_hash) is True

    # Tampered content should NOT verify
    tampered = {"prescription": ["metformin 1000mg bid"], "signed": True}
    assert verify_content_integrity(tampered, sig.content_hash) is False

    # Different key order in dict should still match (canonical JSON)
    reordered = {"signed": True, "prescription": ["metformin 500mg bid"]}
    assert verify_content_integrity(reordered, sig.content_hash) is True


# ── Test 3: chain with broken link is detected ─────────────────────────────


@pytest.mark.asyncio
async def test_chain_with_broken_link_detected(db_session, doctor_user):
    """A chain where a signature references a non-existent previous signature is broken."""
    resource_id = uuid.uuid4()

    # Create a signature with a fake previous_signature_id
    fake_prev_id = uuid.uuid4()
    broken = SignatureRecord(
        id=uuid.uuid4(),
        user_id=doctor_user.id,
        resource_type="medical_record",
        resource_id=resource_id,
        action="approved",
        signature_data={"signed_at": "2024-01-01T00:00:00"},
        content_hash=hash_content({"test": "content"}),
        previous_signature_id=fake_prev_id,
    )
    db_session.add(broken)
    await db_session.commit()

    result = await SignatureService.verify_chain("medical_record", resource_id, db_session)
    assert result.valid is False
    assert len(result.broken_links) >= 1
    assert any("not found" in link for link in result.broken_links)


# ── Test 4: content hash deterministic (same content = same hash) ──────────


def test_content_hash_deterministic():
    """Identical content should always produce identical hashes."""
    content1 = {"patient_id": "abc-123", "diagnosis": {"type": "t2dm", "severity": "moderate"}}
    content2 = {"patient_id": "abc-123", "diagnosis": {"type": "t2dm", "severity": "moderate"}}

    h1 = hash_content(content1)
    h2 = hash_content(content2)

    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)

    # String content should also be deterministic
    h3 = hash_content("hello world")
    h4 = hash_content("hello world")
    assert h3 == h4


# ── Test 5: content hash different for different content ───────────────────


def test_content_hash_different_for_different_content():
    """Different content should always produce different hashes."""
    a = {"key": "value1"}
    b = {"key": "value2"}
    c = "different string"

    ha = hash_content(a)
    hb = hash_content(b)
    hc = hash_content(c)

    assert ha != hb
    assert ha != hc
    assert hb != hc

    # Verify all are valid SHA-256 hex strings
    for h in [ha, hb, hc]:
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
