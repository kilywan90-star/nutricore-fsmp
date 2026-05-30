"""Tests for cursor-based and offset pagination utilities."""
import base64
import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy import select, desc

from src.api.pagination import (
    CursorParams,
    CursorPage,
    cursor_paginate,
    cursor_params,
    offset_params,
    encode_cursor,
)
from src.models.patient import Patient


def _make_cursor(created_at: datetime, patient_id: uuid.UUID) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(patient_id)}, default=str
    )
    return base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()


class TestCursorPagination:
    """Decode and encode cursors; apply cursor WHERE filters."""

    def test_cursor_params_decode(self):
        """CursorParams decodes a valid base64 cursor."""
        cursor = encode_cursor({"created_at": "2025-01-15T10:30:00", "id": "a" * 32})
        params = CursorParams(cursor=cursor, page_size=10)
        assert params.has_cursor is True
        assert params.decoded["created_at"] == "2025-01-15T10:30:00"

    def test_cursor_params_decode_invalid_falls_back(self):
        """Invalid cursor string yields empty decoded dict (no crash)."""
        params = CursorParams(cursor="not-valid-base64!!!", page_size=10)
        assert params.has_cursor is False
        assert params.decoded == {}

    def test_cursor_params_no_cursor(self):
        params = CursorParams(cursor=None, page_size=20)
        assert params.has_cursor is False
        assert params.decoded == {}

    @pytest.mark.asyncio
    async def test_cursor_paginate_first_page(self, db_session):
        """First page (no cursor) returns exactly page_size items."""
        # Seed 5 patients
        for i in range(5):
            p = Patient(
                id=uuid.uuid4(),
                name_hash=f"patient_{i}",
                gender="M" if i % 2 == 0 else "F",
                birth_year=1980 + i,
                diabetes_type="type2",
                created_at=datetime(2025, 1, 15, 10, 0, i),
            )
            db_session.add(p)
        await db_session.commit()

        query = select(Patient).order_by(desc(Patient.created_at), Patient.id)
        params = CursorParams(cursor=None, page_size=3)

        page = await cursor_paginate(db_session, query, params, Patient)
        assert len(page.items) == 3
        assert page.has_next is True
        assert page.next_cursor is not None
        assert page.page_size == 3

    @pytest.mark.asyncio
    async def test_cursor_paginate_second_page(self, db_session):
        """Second page uses cursor from first page to seek forward."""
        for i in range(5):
            p = Patient(
                id=uuid.uuid4(),
                name_hash=f"patient_{i}",
                gender="M" if i % 2 == 0 else "F",
                birth_year=1980 + i,
                diabetes_type="type2",
                created_at=datetime(2025, 1, 15, 10, 0, i),
            )
            db_session.add(p)
        await db_session.commit()

        query = select(Patient).order_by(desc(Patient.created_at), Patient.id)

        # Page 1
        page1 = await cursor_paginate(
            db_session, query, CursorParams(cursor=None, page_size=3), Patient
        )
        assert len(page1.items) == 3
        assert page1.next_cursor is not None

        # Page 2
        page2 = await cursor_paginate(
            db_session, query, CursorParams(cursor=page1.next_cursor, page_size=3), Patient
        )
        assert len(page2.items) == 2  # Only 2 remaining
        assert page2.has_next is False
        assert page2.next_cursor is None

        # Ensure no overlap between pages
        page1_ids = {str(p.id) for p in page1.items}
        page2_ids = {str(p.id) for p in page2.items}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_cursor_paginate_with_total(self, db_session):
        """When include_total=True, total count is returned."""
        for i in range(7):
            p = Patient(
                id=uuid.uuid4(),
                name_hash=f"patient_{i}",
                gender="M",
                birth_year=1980,
                diabetes_type="type2",
                created_at=datetime(2025, 1, 15),
            )
            db_session.add(p)
        await db_session.commit()

        query = select(Patient).order_by(desc(Patient.created_at), Patient.id)
        params = CursorParams(cursor=None, page_size=3)

        page = await cursor_paginate(db_session, query, params, Patient, include_total=True)
        assert page.total == 7
        assert len(page.items) == 3


class TestOffsetPagination:
    """Verify offset-based pagination dependency works for backward compatibility."""

    @pytest.mark.asyncio
    async def test_offset_params_defaults(self):
        params = await offset_params(page=1, page_size=20)
        assert params == {"page": 1, "page_size": 20}

    @pytest.mark.asyncio
    async def test_offset_params_custom(self):
        params = await offset_params(page=3, page_size=50)
        assert params == {"page": 3, "page_size": 50}


class TestFastAPIDependencies:
    """Verify dependency callables work with FastAPI dependency injection."""

    @pytest.mark.asyncio
    async def test_cursor_params_dependency(self):
        """cursor_params FastAPI dependency parses cursor and page_size."""
        params = await cursor_params(cursor=None, page_size=25)
        assert isinstance(params, CursorParams)
        assert params.page_size == 25
        assert params.has_cursor is False

    @pytest.mark.asyncio
    async def test_cursor_params_dependency_with_cursor(self):
        """cursor_params with a valid cursor parses correctly."""
        cursor = encode_cursor({"created_at": "2025-06-01T08:00:00", "id": "abc"})
        params = await cursor_params(cursor=cursor, page_size=10)
        assert params.has_cursor is True
        assert params.decoded["created_at"] == "2025-06-01T08:00:00"

    @pytest.mark.asyncio
    async def test_cursor_page_to_dict(self):
        """CursorPage.to_dict returns a serializable dict."""
        page = CursorPage(
            items=[{"id": "1"}, {"id": "2"}],
            total=50,
            next_cursor="next-cursor-value",
            has_next=True,
            page_size=20,
        )
        d = page.to_dict()
        assert d["items"] == [{"id": "1"}, {"id": "2"}]
        assert d["total"] == 50
        assert d["next_cursor"] == "next-cursor-value"
        assert d["has_next"] is True
        assert d["page_size"] == 20
