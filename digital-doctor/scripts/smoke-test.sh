#!/usr/bin/env bash
# smoke-test.sh — Post-deployment smoke tests.
#
# Usage:
#   smoke-test.sh <base_url> [admin_token]
#
# Checks:
#   1. /health                   returns 200
#   2. /health/ready             returns 200 (DB + Redis connectivity)
#   3. /api/v1/auth/login        endpoint reachable (200 or 401 is ok — means app responds)
#   4. Frontend index.html        serves (200)
#
# Exit codes:
#   0 — all checks passed
#   1 — at least one check failed (triggers rollback)

set -euo pipefail

BASE_URL="${1:-${SMOKE_BASE_URL:-http://localhost:8000}}"
ADMIN_TOKEN="${2:-${ADMIN_TOKEN:-}}"

# Strip trailing slash
BASE_URL="${BASE_URL%/}"

PASS=0
FAIL=0
TOTAL=4

log_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
log_fail() { echo "  [FAIL] $1 — $2"; FAIL=$((FAIL + 1)); }

echo "=== Smoke Tests ==="
echo "Target: ${BASE_URL}"
echo ""

# ── 1. /health ──────────────────────────────────────────────────
echo "[1/4] Health endpoint..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}/health" 2>/dev/null || echo "000")
if [ "${HEALTH_STATUS}" = "200" ]; then
    log_pass "/health returned ${HEALTH_STATUS}"
else
    log_fail "/health returned ${HEALTH_STATUS}" "expected 200"
fi

# ── 2. /health/ready ────────────────────────────────────────────
echo "[2/4] Readiness endpoint..."
READY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}/health/ready" 2>/dev/null || echo "000")
if [ "${READY_STATUS}" = "200" ]; then
    log_pass "/health/ready returned ${READY_STATUS}"
else
    log_fail "/health/ready returned ${READY_STATUS}" "expected 200"
fi

# ── 3. /api/v1/auth/login ───────────────────────────────────────
echo "[3/4] Auth login endpoint..."
AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"smoke_test","password":"smoke_test"}' 2>/dev/null || echo "000")
# 200 (success) or 401 (invalid credentials) both mean the app is responsive
if [ "${AUTH_STATUS}" = "200" ] || [ "${AUTH_STATUS}" = "401" ] || [ "${AUTH_STATUS}" = "422" ]; then
    log_pass "/api/v1/auth/login returned ${AUTH_STATUS} (app responsive)"
else
    log_fail "/api/v1/auth/login returned ${AUTH_STATUS}" "expected 200/401/422"
fi

# ── 4. Frontend index.html ──────────────────────────────────────
echo "[4/4] Frontend index.html..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}:3000/" 2>/dev/null || echo "000")
# Try common frontend URL patterns
if [ "${FRONTEND_STATUS}" = "200" ]; then
    log_pass "Frontend index.html returned ${FRONTEND_STATUS}"
else
    # Try without port (nginx proxy)
    FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}/" 2>/dev/null || echo "000")
    if [ "${FRONTEND_STATUS}" = "200" ]; then
        log_pass "Frontend index.html returned ${FRONTEND_STATUS}"
    else
        log_fail "Frontend unreachable" "tried ${BASE_URL}:3000/ and ${BASE_URL}/ (got ${FRONTEND_STATUS})"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "=== Smoke Test Summary: ${PASS}/${TOTAL} passed ==="

if [ "${FAIL}" -gt 0 ]; then
    echo "SMOKE TESTS FAILED"
    exit 1
fi

echo "SMOKE TESTS PASSED"
exit 0
