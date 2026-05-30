"""
Cursor-based pagination for FastAPI + SQLAlchemy async.

More efficient than OFFSET/LIMIT for large datasets because:
  - No row-skipping overhead (OFFSET must scan and discard N rows)
  - Stable under concurrent inserts (cursor anchored to a known row)
  - Index-friendly (seeks directly to the cursor position)

Usage in an endpoint:
    from src.api.pagination import CursorPage, CursorParams, cursor_paginate

    @router.get("/patients")
    async def list_patients(
        cursor: str | None = Query(None),
        page_size: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
    ):
        params = CursorParams(cursor=cursor, page_size=page_size)
        query = select(Patient).order_by(Patient.created_at.desc(), Patient.id)
        page = await cursor_paginate(db, query, params, Patient)
        return page
"""

from __future__ import annotations

import base64
import json
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from fastapi import Query
from sqlalchemy import select, and_, or_, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CursorParams:
    """Parsed cursor pagination request parameters."""

    cursor: str | None = None
    page_size: int = 20
    _decoded: dict[str, Any] | None = field(default=None, init=False)

    @property
    def decoded(self) -> dict[str, Any]:
        if self._decoded is not None:
            return self._decoded
        if not self.cursor:
            self._decoded = {}
            return self._decoded
        try:
            payload = base64.urlsafe_b64decode(self.cursor + "==").decode()
            self._decoded = json.loads(payload)
        except Exception:
            self._decoded = {}
        return self._decoded

    @property
    def has_cursor(self) -> bool:
        return bool(self.cursor and self.decoded)


@dataclass
class CursorPage(Generic[T]):
    """Paginated response container with cursor metadata."""

    items: list[Any]
    total: int | None = None
    next_cursor: str | None = None
    has_next: bool = False
    page_size: int = 20

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "total": self.total,
            "next_cursor": self.next_cursor,
            "has_next": self.has_next,
            "page_size": self.page_size,
        }


# ---------------------------------------------------------------------------
# Cursor encoding / decoding
# ---------------------------------------------------------------------------


def encode_cursor(positional_fields: dict[str, Any]) -> str:
    """Encode a cursor position as a base64url string (no padding).

    The cursor captures the ordered field values of the last item on the
    current page. On the next request, these values become the exclusive
    starting point.
    """
    payload = json.dumps(positional_fields, default=str)
    return base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()


# ---------------------------------------------------------------------------
# Optional FastAPI dependency
# ---------------------------------------------------------------------------


async def cursor_params(
    cursor: str | None = Query(None, description="Opaque cursor from previous page"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> CursorParams:
    return CursorParams(cursor=cursor, page_size=page_size)


# ---------------------------------------------------------------------------
# Offset-based (compatibility) dependency
# ---------------------------------------------------------------------------


async def offset_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict[str, int]:
    return {"page": page, "page_size": page_size}


# ---------------------------------------------------------------------------
# Core pagination engine
# ---------------------------------------------------------------------------


async def cursor_paginate(
    db: AsyncSession,
    base_query: Any,
    params: CursorParams,
    model: type[T],
    *,
    cursor_fields: list[Any] | None = None,
    descending: bool = True,
    include_total: bool = False,
) -> CursorPage[T]:
    """Execute a cursor-paginated query.

    The base_query must already have an ORDER BY clause. The cursor
    encodes the last row's ordering values to implement keyset pagination.

    Args:
        db: Async database session.
        base_query: SQLAlchemy select() with ORDER BY already applied.
        params: CursorParams from the request.
        model: The ORM model class being queried.
        cursor_fields: Columns used as cursor (defaults to ORDER BY columns).
        descending: True if ordering is DESC (newest first).
        include_total: If True, also run COUNT(*) query.

    Returns:
        CursorPage with items, next_cursor, has_next, and optionally total.
    """
    query = base_query.limit(params.page_size + 1)  # fetch one extra to detect has_next

    # Resolve cursor_fields once so encoding and filtering use the same columns
    if cursor_fields is None:
        cursor_fields = _infer_order_by_columns(query, model)

    # Apply cursor filter
    if params.has_cursor:
        query = _apply_cursor_filter(query, params.decoded, model, cursor_fields, descending)

    result = await db.execute(query)
    rows = result.scalars().all()

    has_next = len(rows) > params.page_size
    items = rows[: params.page_size]

    # Build next cursor from the last item
    next_cursor = None
    if has_next:
        last_item = items[-1]
        cursor_data = _extract_cursor_values(last_item, model, cursor_fields, descending)
        next_cursor = encode_cursor(cursor_data)

    total = None
    if include_total:
        count_query = base_query.with_only_columns(  # type: ignore[attr-defined]
            base_query.selected_columns
        )
        from sqlalchemy import func, select as _select
        # Rebuild count from base (without cursor filter for accuracy)
        from sqlalchemy import func
        count_stmt = _select(func.count()).select_from(model)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

    return CursorPage(
        items=items,
        total=total,
        next_cursor=next_cursor,
        has_next=has_next,
        page_size=params.page_size,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_cursor_filter(
    query: Any,
    cursor_data: dict[str, Any],
    model: type[T],
    cursor_fields: list[Any],
    descending: bool,
) -> Any:
    """Add WHERE clauses to implement keyset pagination seek."""
    if not cursor_fields:
        return query

    # For a DESC-ordered query on multiple fields, the cursor comparison
    # must use composite row-value comparison or a tuple of conditions.
    # We build: WHERE (col1, col2) < (cursor1, cursor2) for DESC
    # or:        WHERE (col1, col2) > (cursor1, cursor2) for ASC

    def _coerce_cursor_val(col: Any, raw_val: Any) -> Any:
        """Convert string cursor value to the column's Python type for comparison."""
        col_type = col.type
        if isinstance(col_type, PG_UUID) and isinstance(raw_val, str):
            return _uuid.UUID(raw_val)
        if isinstance(col_type, (Date, DateTime)) and isinstance(raw_val, str):
            return datetime.fromisoformat(raw_val)
        return raw_val

    conditions = []
    for i, col in enumerate(cursor_fields):
        prefix_fields = cursor_fields[:i]
        prefix_conditions = []
        for pf in prefix_fields:
            cursor_key = _column_to_cursor_key(pf)
            if cursor_key in cursor_data:
                prefix_conditions.append(pf == _coerce_cursor_val(pf, cursor_data[cursor_key]))

        cursor_key = _column_to_cursor_key(col)
        if cursor_key not in cursor_data:
            continue

        cursor_val = _coerce_cursor_val(col, cursor_data[cursor_key])
        if descending:
            cmp_cond = col < cursor_val
        else:
            cmp_cond = col > cursor_val

        if prefix_conditions:
            conditions.append(and_(*prefix_conditions, cmp_cond))
        else:
            conditions.append(cmp_cond)

    if conditions:
        query = query.where(or_(*conditions))

    return query


def _extract_cursor_values(
    item: Any,
    model: type[T],
    cursor_fields: list[Any],
    descending: bool,
) -> dict[str, Any]:
    """Extract cursor field values from the last item on a page."""
    values = {}
    for col in cursor_fields:
        key = _column_to_cursor_key(col)
        val = getattr(item, key, None)
        if isinstance(val, datetime):
            val = val.isoformat()
        elif hasattr(val, "value"):  # enum
            val = val.value
        values[key] = str(val) if val is not None else None
    return values


def _column_to_cursor_key(col: Any) -> str:
    """Extract a string key from a SQLAlchemy column."""
    return col.key if hasattr(col, "key") else str(col).split(".")[-1]


def _infer_order_by_columns(query: Any, model: type[T]) -> list[Any]:
    """Infer ORDER BY columns from a SQLAlchemy select() statement."""
    try:
        order_by_cols = []
        clauses = getattr(query, "_order_by_clauses", ())
        for clause in clauses:
            # Unwrap UnaryExpression (e.g. desc(column) or asc(column))
            if hasattr(clause, "element") and hasattr(clause, "modifier"):
                col = clause.element
            else:
                col = clause
            col_ref = getattr(col, "key", None)
            if col_ref and hasattr(model, col_ref):
                order_by_cols.append(getattr(model, col_ref))
        return order_by_cols or [getattr(model, "id")]
    except Exception:
        return [getattr(model, "id")]
