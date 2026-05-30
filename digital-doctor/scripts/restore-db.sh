#!/usr/bin/env bash
# restore-db.sh — Restore database from backup with verification, PITR, and dry-run.
# Usage: ./restore-db.sh <backup_file> [--pitr <wal_dir>] [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../backups}"

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-ddd}"
DB_NAME="${DB_NAME:-digital_doctor}"
DB_PASSWORD="${DB_PASSWORD:-ddd_secret_dev}"

PITR_DIR=""
DRY_RUN=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pitr)
            PITR_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_file> [--pitr <wal_dir>] [--dry-run]"
    echo ""
    echo "Options:"
    echo "  --pitr <wal_dir>   Point-in-time recovery directory (WAL archives)"
    echo "  --dry-run          Verify backup only, do not restore"
    exit 1
fi

FULL_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
if [ ! -f "${FULL_PATH}" ]; then
    FULL_PATH="${BACKUP_FILE}"
fi

if [ ! -f "${FULL_PATH}" ]; then
    echo "ERROR: Backup file not found: ${FULL_PATH}"
    exit 1
fi

echo "[$(date -u +%H:%M:%S)] Starting restore process..."
echo "  Backup: ${FULL_PATH}"

# ---- Verification ----
echo ""
echo "=== Backup Verification ==="

export PGPASSWORD="${DB_PASSWORD}"

# Check gzip integrity
if file "${FULL_PATH}" | grep -q "gzip"; then
    echo "[verify] Testing gzip integrity..."
    if gzip -t "${FULL_PATH}" 2>/dev/null; then
        echo "[verify] gzip integrity: PASS"
    else
        echo "[verify] gzip integrity: FAIL — aborting"
        exit 1
    fi
else
    echo "[verify] File is not gzip-compressed, checking header..."
    echo "[verify] gzip integrity: SKIP (not gzipped)"
fi

# Check checksum from metadata
META_FILE="${FULL_PATH}.meta.json"
if [ -f "${META_FILE}" ]; then
    RECORDED_CHECKSUM=$(grep -o '"checksum_sha256":\s*"[^"]*"' "${META_FILE}" | cut -d'"' -f4 || echo "")
    if [ -n "${RECORDED_CHECKSUM}" ]; then
        ACTUAL_CHECKSUM=$(sha256sum "${FULL_PATH}" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "${FULL_PATH}" | cut -d' ' -f1)
        if [ "${ACTUAL_CHECKSUM}" = "${RECORDED_CHECKSUM}" ]; then
            echo "[verify] Checksum: PASS"
        else
            echo "[verify] Checksum: FAIL"
            echo "  Expected: ${RECORDED_CHECKSUM}"
            echo "  Actual:   ${ACTUAL_CHECKSUM}"
            exit 1
        fi
    fi
else
    SKIPPED_CHECKSUM=$(sha256sum "${FULL_PATH}" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "${FULL_PATH}" | cut -d' ' -f1)
    echo "[verify] No metadata file found, checksum not verified."
    echo "[verify] Current checksum: ${SKIPPED_CHECKSUM}"
fi

# Check size from metadata
if [ -f "${META_FILE}" ]; then
    RECORDED_SIZE=$(grep -o '"size_bytes":\s*[0-9]*' "${META_FILE}" | grep -o '[0-9]*' || echo "0")
    ACTUAL_SIZE=$(stat -c%s "${FULL_PATH}" 2>/dev/null || stat -f%z "${FULL_PATH}" 2>/dev/null || echo 0)
    if [ "${ACTUAL_SIZE}" -eq "${RECORDED_SIZE}" ]; then
        echo "[verify] Size: PASS (${ACTUAL_SIZE} bytes)"
    else
        echo "[verify] Size: FAIL"
        echo "  Expected: ${RECORDED_SIZE}"
        echo "  Actual:   ${ACTUAL_SIZE}"
        exit 1
    fi
fi

echo "[verify] Backup verification complete."
echo ""

if [ "${DRY_RUN}" = true ]; then
    echo "[dry-run] Dry-run mode — exiting without restore."
    exit 0
fi

# ---- Restore ----
echo "=== Restore ==="
echo "[restore] Dropping and recreating database..."

psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}';" 2>/dev/null || true
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${DB_NAME};" 2>/dev/null
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null

echo "[restore] Restoring from dump..."
if file "${FULL_PATH}" | grep -q "gzip"; then
    gunzip -c "${FULL_PATH}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"
else
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "${FULL_PATH}"
fi

echo "[restore] Database restore complete."

# ---- Point-in-Time Recovery ----
if [ -n "${PITR_DIR}" ]; then
    echo ""
    echo "=== Point-in-Time Recovery ==="
    echo "[pitr] Recovering WAL archives from: ${PITR_DIR}"

    if [ ! -d "${PITR_DIR}" ]; then
        echo "ERROR: WAL directory not found: ${PITR_DIR}"
        exit 1
    fi

    # Copy WAL files to PostgreSQL pg_wal directory
    PG_WAL_DIR=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -tAc \
        "SHOW data_directory;" 2>/dev/null || echo "/var/lib/postgresql/data")
    PG_WAL_DIR="${PG_WAL_DIR}/pg_wal"

    WAL_COUNT=$(find "${PITR_DIR}" -type f | wc -l)
    echo "[pitr] Copying ${WAL_COUNT} WAL files to ${PG_WAL_DIR} ..."
    cp -r "${PITR_DIR}/"* "${PG_WAL_DIR}/" 2>/dev/null || echo "[pitr] WARNING: Could not copy WAL files (may need container access)"

    echo "[pitr] WAL replay requires a PostgreSQL restart or recovery.conf setup."
    echo "[pitr] Consider creating recovery.signal in the PG data directory and restarting."
fi

echo ""
echo "[$(date -u +%H:%M:%S)] Restore process finished."
