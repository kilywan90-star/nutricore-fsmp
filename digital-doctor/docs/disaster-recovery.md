# Disaster Recovery Plan — 数字医生分身 (Digital Doctor)

## Recovery Objectives

| Metric | Target | Description |
|--------|--------|-------------|
| **RPO** (Recovery Point Objective) | 1 hour | Hourly incremental backups via WAL archiving. Maximum data loss is the interval between the last WAL segment switch and the failure event. |
| **RTO** (Recovery Time Objective) | 4 hours | Time to restore the full backup, replay WAL archives, verify integrity, and bring the service back online. |

## Backup Strategy

### Backup Types
- **Full Backup**: Complete logical dump (pg_dump with gzip compression), daily at 02:00 UTC.
- **Incremental Backup**: PostgreSQL WAL segment archiving, hourly.
- **Retention**: 30 days for full backups, managed automatically by retention enforcement.

### Storage Locations
- **Primary (Local)**: `/app/backups/` on the application server (Docker volume mount: `./backups:/app/backups`).
- **Offsite (S3/MinIO)**: Optional S3-compatible storage for geographic redundancy. Configure via `BACKUP_S3_BUCKET` and `BACKUP_S3_ENDPOINT` env vars.
- **Metadata**: Each backup has a companion `.meta.json` file containing timestamp, size, checksum, and database version.

### Backup Schedule (Crontab)
```
# On the host or in a dedicated cron container:
0 2 * * * /app/scripts/backup-cron.sh full          # Daily full backup at 2am
0 * * * * /app/scripts/backup-cron.sh incremental    # Hourly WAL switch
0 4 * * * /app/scripts/backup-cron.sh verify         # Verify latest at 4am
0 5 * * * /app/scripts/backup-cron.sh cleanup        # Retention cleanup at 5am
```

## Restore Procedure

### Full Restore from Local Backup

1. **Locate the backup file**:
   ```bash
   ls -la backups/backup_full_*.sql.gz
   ```

2. **Verify backup integrity** (dry-run first):
   ```bash
   ./scripts/restore-db.sh backup_full_20260115_020000.sql.gz --dry-run
   ```

3. **Restore the database**:
   ```bash
   ./scripts/restore-db.sh backup_full_20260115_020000.sql.gz
   ```

### Point-in-Time Recovery (PITR)

1. Ensure WAL archives are available in the configured WAL archive directory.

2. Restore with PITR:
   ```bash
   ./scripts/restore-db.sh backup_full_20260115_020000.sql.gz --pitr /path/to/wal_archives
   ```

3. If a specific recovery target time is needed, create `recovery.signal` in the PG data directory:
   ```bash
   touch /var/lib/postgresql/data/recovery.signal
   ```
   And add to `postgresql.conf`:
   ```
   restore_command = 'cp /wal_archive/%f %p'
   recovery_target_time = '2026-01-15 14:30:00 UTC'
   ```

### Restore from S3/MinIO

1. Download the backup from S3:
   ```bash
   aws s3 cp s3://my-backup-bucket/backup_full_20260115_020000.sql.gz ./backups/ \
     --endpoint-url https://s3.example.com
   ```

2. Follow the local restore procedure above.

### Post-Restore Verification

1. Run database migrations:
   ```bash
   cd backend && alembic upgrade head
   ```

2. Verify core functionality:
   ```bash
   # Check health endpoint
   curl http://localhost:8000/health

   # List users (requires admin token)
   curl http://localhost:8000/api/v1/admin/backups \
     -H "Authorization: Bearer <admin_token>"
   ```

3. Run automated test suite:
   ```bash
   cd backend && pytest tests/ -v
   ```

## Testing Schedule

| Test Type | Frequency | Owner | Procedure |
|-----------|-----------|-------|-----------|
| Backup integrity check | Daily (automated) | System | `backup-cron.sh verify` runs at 04:00 |
| Full restore test | Monthly | DevOps | Execute full restore procedure to a staging environment |
| PITR restore test | Quarterly | DevOps | Test point-in-time recovery with WAL replay |
| Disaster drill | Bi-annually | DevOps / Engineering | Full DR scenario: simulate primary failure, restore from offsite, validate |

## Emergency Contacts

| Role | Name | Phone | Email | Notes |
|------|------|-------|-------|-------|
| Primary DevOps | ________ | ________ | ________ | First responder for DB issues |
| Secondary DevOps | ________ | ________ | ________ | Backup contact |
| Engineering Lead | ________ | ________ | ________ | Technical decisions |
| DBA (if applicable) | ________ | ________ | ________ | Database expertise |

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_RETENTION_DAYS` | 30 | Days to keep backups before deletion |
| `BACKUP_STORAGE_TYPE` | `local` | Storage backend: `local` or `s3` |
| `BACKUP_S3_BUCKET` | (empty) | S3 bucket name for offsite backups |
| `BACKUP_S3_ENDPOINT` | (empty) | S3-compatible endpoint URL (for MinIO) |
| `BACKUP_ENCRYPTION_ENABLED` | `true` | Enable backup file encryption (future) |

## Recovery Checklist

In the event of a real disaster, follow these steps:

- [ ] 1. **Assess the scope**: Determine which data was lost and the time of the failure.
- [ ] 2. **Notify stakeholders**: Inform the team per the emergency contacts list.
- [ ] 3. **Locate the backup**: Identify the most recent backup prior to the failure.
- [ ] 4. **Verify backup integrity**: Run `restore-db.sh --dry-run`.
- [ ] 5. **Prepare target environment**: Ensure a clean database instance is available.
- [ ] 6. **Execute restore**: Run `restore-db.sh` with the appropriate options.
- [ ] 7. **Run migrations**: Apply any schema migrations (alembic upgrade head).
- [ ] 8. **Verify service health**: Check `/health` endpoint and run smoke tests.
- [ ] 9. **Update DNS/LB**: Point traffic to the restored instance if needed.
- [ ] 10. **Post-mortem**: Document the incident, root cause, and improvements.
