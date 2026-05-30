# Digital Doctor — Query Optimization Guide

## Index Strategy

### Critical Composite Indexes

| Table | Index Columns | Query Pattern | Benefit |
|-------|--------------|---------------|---------|
| `glucose_records` | `(patient_id, recorded_at DESC)` | `SELECT ... WHERE patient_id = ? ORDER BY recorded_at DESC LIMIT ?` | Eliminates full scan on per-patient glucose history |
| `alerts` | `(patient_id, acknowledged, created_at DESC)` | `SELECT ... WHERE patient_id = ? AND acknowledged = false ORDER BY created_at DESC` | Speeds up unacknowledged alert count and listing |
| `lab_reports` | `(patient_id, report_date DESC)` | `SELECT ... WHERE patient_id = ? ORDER BY report_date DESC LIMIT 10` | Fast per-patient report history |
| `medication_reminders` | `(patient_id, is_active)` | `SELECT ... WHERE patient_id = ? AND is_active = true` | Efficient active medication lookup |
| `notifications` | `(user_id, status, scheduled_at DESC)` | `SELECT ... WHERE user_id = ? AND status = ? ORDER BY scheduled_at DESC` | Notification list pagination |
| `users` | `(role, is_active)` | `SELECT ... WHERE role = ? AND is_active = true` | Admin role-based user queries |

### Index Rules of Thumb

1. **Always include the filter column first** in composite indexes
2. **Add ORDER BY columns** to the index to avoid filesort
3. **Use partial indexes** when filtering on boolean flags:
   ```sql
   CREATE INDEX ix_alerts_unacknowledged ON alerts (patient_id, created_at DESC)
       WHERE acknowledged = false;
   ```
4. **Monitor with `pg_stat_user_indexes`** — drop indexes with `idx_scan = 0`

## Query Patterns to Avoid

### N+1 Queries
The `get_patient_list` function in `patient_manager.py` makes N+1 queries:
```python
for p in patients:
    latest_glucose = await _get_latest_glucose(db, p.id)  # 1 query per patient
    alert_count = await _get_unacknowledged_alert_count(db, p.id)  # 1 query per patient
```

**Fix**: Use a single lateral join or subquery with aggregation:
```python
# Batch-fetch all glucose values and alert counts in 2 queries total
from sqlalchemy import select, func, and_

# Subquery for latest glucose per patient
glucose_subq = (
    select(
        GlucoseRecord.patient_id,
        GlucoseRecord.value_mmol_l,
        func.row_number().over(
            partition_by=GlucoseRecord.patient_id,
            order_by=GlucoseRecord.recorded_at.desc()
        ).label("rn")
    ).subquery()
)
glucose_latest = select(
    glucose_subq.c.patient_id, glucose_subq.c.value_mmol_l
).where(glucose_subq.c.rn == 1)

# Subquery for alert count per patient
alert_counts = (
    select(
        Alert.patient_id,
        func.count().label("cnt")
    ).where(Alert.acknowledged == False)
    .group_by(Alert.patient_id)
).subquery()
```

### Offset Pagination on Large Tables
`OFFSET + LIMIT` requires scanning and discarding offset rows. For datasets > 10k rows, prefer cursor pagination.

### Non-Sargable WHERE Clauses
Avoid wrapping indexed columns in functions:
```sql
-- BAD: prevents index usage
WHERE LOWER(name_hash) LIKE '%john%'

-- GOOD: index can be used
WHERE name_hash ILIKE '%john%'
```

### Missing FK Indexes
Every foreign key should have an index. Verify with:
```sql
SELECT c.conname, c.conrelid::regclass
FROM pg_constraint c
LEFT JOIN pg_index i ON i.indrelid = c.conrelid AND c.conkey <@ i.indkey
WHERE c.contype = 'f' AND i.indrelid IS NULL;
```

## Caching Strategy

See `services/cache.py` for the Redis caching layer. Cacheable patterns:

| Data | TTL | Rationale |
|------|-----|-----------|
| Patient list | 60s | High read rate, tolerable staleness |
| Lab report interpretations | 300s | LLM results are expensive and stable |
| Rule engine results | 3600s | Clinical guidelines change rarely |
| Department stats | 120s | Dashboard refresh rate |

## Monitoring

- **Prometheus**: `pg_stat_database` metrics exported via `src/services/metrics.py`
- **Slow query log**: Call `analyze_slow_queries()` periodically or on-demand
- **EXPLAIN ANALYZE**: Use PostgreSQL's built-in planner to verify index usage

## Execution Plan

Run these checks after making any query change:

```python
from src.db.optimize import add_indexes, analyze_slow_queries, get_index_info

# 1. Ensure indexes exist
await add_indexes()

# 2. Verify index coverage
indexes = await get_index_info(db)

# 3. Check for slow queries
slow = await analyze_slow_queries(db, threshold_ms=200)
```
