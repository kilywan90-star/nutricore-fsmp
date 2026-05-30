#!/usr/bin/env bash
# version.sh — Generate version from git describe, write to .version file.
# Used by Docker build for image tagging.
#
# Output format:
#   - Tagged release:  v0.1.0            (exact tag)
#   - Post-release:    v0.1.0-3-gabc1234 (3 commits after v0.1.0, git sha)
#   - No tags:          abc1234           (short sha)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/.version"

# Derive version from git
if VERSION=$(git describe --tags --always --dirty 2>/dev/null); then
    echo "${VERSION}"
else
    # Fallback when not in a git repo (e.g., building from source tarball)
    VERSION="unknown"
    echo "${VERSION}"
fi

echo "${VERSION}" > "${VERSION_FILE}"
echo "[version] Written '${VERSION}' to ${VERSION_FILE}"
