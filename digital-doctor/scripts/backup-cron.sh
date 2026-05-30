#!/usr/bin/env bash
# backup-cron.sh — Cron entry point that triggers backup via the backend API.
# Usage in crontab:
#   0 2 * * * /app/scripts/backup-cron.sh full
#   0 * * * * /app/scripts/backup-cron.sh incremental
#   0 4 * * * /app/scripts/backup-cron.sh verify
#   0 5 * * * /app/scripts/backup-cron.sh cleanup

set -euo pipefail

ACTION="${1:-full}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [backup-cron] $*"
}

case "${ACTION}" in
    full)
        log "Triggering daily full backup..."
        if [ -n "${ADMIN_TOKEN}" ]; then
            curl -s -X POST "${BACKEND_URL}/api/v1/admin/backups?backup_type=full" \
                -H "Authorization: Bearer ${ADMIN_TOKEN}" \
                -H "Content-Type: application/json" || {
                log "API call failed, falling back to direct pg_dump..."
                "${SCRIPT_DIR}/backup-db.sh"
            }
        else
            log "No ADMIN_TOKEN set, running direct pg_dump..."
            "${SCRIPT_DIR}/backup-db.sh"
        fi
        ;;

    incremental)
        log "Triggering incremental backup (WAL switch)..."
        export PGPASSWORD="${DB_PASSWORD:-ddd_secret_dev}"
        psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-ddd}" \
            -d "${DB_NAME:-digital_doctor}" -c "SELECT pg_switch_wal();" 2>/dev/null || {
            log "WAL switch via psql failed, trying API..."
            if [ -n "${ADMIN_TOKEN}" ]; then
                curl -s -X POST "${BACKEND_URL}/api/v1/admin/backups?backup_type=incremental" \
                    -H "Authorization: Bearer ${ADMIN_TOKEN}"
            fi
        }
        ;;

    verify)
        log "Verifying latest backup..."
        if [ -n "${ADMIN_TOKEN}" ]; then
            # Get latest backup ID and verify it
            LATEST_ID=$(curl -s "${BACKEND_URL}/api/v1/admin/backups?limit=1" \
                -H "Authorization: Bearer ${ADMIN_TOKEN}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
            if [ -n "${LATEST_ID}" ]; then
                curl -s "${BACKEND_URL}/api/v1/admin/backups/${LATEST_ID}/verify" \
                    -H "Authorization: Bearer ${ADMIN_TOKEN}"
            fi
        else
            # Use the restore-db.sh dry-run on latest backup file
            LATEST_BACKUP=$(ls -t "${SCRIPT_DIR}/../backups"/backup_full_*.sql.gz 2>/dev/null | head -1 || echo "")
            if [ -n "${LATEST_BACKUP}" ]; then
                "${SCRIPT_DIR}/restore-db.sh" "$(basename "${LATEST_BACKUP}")" --dry-run
            else
                log "No backup files found to verify."
            fi
        fi
        ;;

    cleanup)
        log "Running retention cleanup..."
        "${SCRIPT_DIR}/backup-db.sh"  # backup-db.sh includes retention enforcement
        ;;

    *)
        echo "Usage: $0 {full|incremental|verify|cleanup}"
        exit 1
        ;;
esac

log "Action '${ACTION}' completed."
