#!/usr/bin/env bash
# backup-db.sh — Full database backup with gzip compression, checksum, and metadata.
# Usage: ./backup-db.sh [--s3]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../backups}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_FILE="backup_full_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
METADATA_FILE="${BACKUP_PATH}.meta.json"

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-ddd}"
DB_NAME="${DB_NAME:-digital_doctor}"
DB_PASSWORD="${DB_PASSWORD:-ddd_secret_dev}"

S3_BUCKET="${BACKUP_S3_BUCKET:-}"
S3_ENDPOINT="${BACKUP_S3_ENDPOINT:-}"
UPLOAD_TO_S3=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --s3) UPLOAD_TO_S3=true; shift ;;
        *) shift ;;
    esac
done

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +%H:%M:%S)] Starting full backup..."

export PGPASSWORD="${DB_PASSWORD}"

pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-owner --no-acl \
    | gzip > "${BACKUP_PATH}"

echo "[$(date -u +%H:%M:%S)] pg_dump completed."

SIZE=$(stat -c%s "${BACKUP_PATH}" 2>/dev/null || stat -f%z "${BACKUP_PATH}" 2>/dev/null || echo 0)
CHECKSUM=$(sha256sum "${BACKUP_PATH}" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "${BACKUP_PATH}" | cut -d' ' -f1)

DB_VERSION=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -tAc \
    "SELECT current_setting('server_version');" 2>/dev/null || echo "unknown")

cat > "${METADATA_FILE}" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "filename": "${BACKUP_FILE}",
  "size_bytes": ${SIZE},
  "checksum_sha256": "${CHECKSUM}",
  "db_version": "${DB_VERSION}",
  "db_host": "${DB_HOST}",
  "db_name": "${DB_NAME}",
  "backup_type": "full",
  "compression": "gzip"
}
EOF

echo "[$(date -u +%H:%M:%S)] Metadata written to ${METADATA_FILE}"
echo "  File:     ${BACKUP_PATH}"
echo "  Size:     ${SIZE} bytes"
echo "  Checksum: ${CHECKSUM}"

# S3/MinIO upload (optional)
if [ "${UPLOAD_TO_S3}" = true ] && [ -n "${S3_BUCKET}" ]; then
    echo "[$(date -u +%H:%M:%S)] Uploading to S3..."
    S3_CMD="aws s3 cp"
    if [ -n "${S3_ENDPOINT}" ]; then
        S3_CMD="${S3_CMD} --endpoint-url ${S3_ENDPOINT}"
    fi
    ${S3_CMD} "${BACKUP_PATH}" "s3://${S3_BUCKET}/${BACKUP_FILE}"
    ${S3_CMD} "${METADATA_FILE}" "s3://${S3_BUCKET}/${BACKUP_FILE}.meta.json"
    echo "[$(date -u +%H:%M:%S)] S3 upload complete."
fi

# Retention enforcement
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
DELETED=0
for f in "${BACKUP_DIR}"/backup_full_*.sql.gz; do
    [ -f "$f" ] || continue
    age_days=$(( ($(date +%s) - $(stat -c%Y "$f" 2>/dev/null || stat -f%m "$f")) / 86400 ))
    if [ "$age_days" -gt "${RETENTION_DAYS}" ]; then
        echo "[$(date -u +%H:%M:%S)] Removing expired backup: $(basename "$f") (age: ${age_days}d)"
        rm -f "$f" "${f}.meta.json"
        DELETED=$((DELETED + 1))
    fi
done
echo "[$(date -u +%H:%M:%S)] Retention cleanup: ${DELETED} backups removed."

echo "[$(date -u +%H:%M:%S)] Backup finished."
