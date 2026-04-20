#!/usr/bin/env bash
# Installed by canon-systems. Do not edit by hand.
# Runs after every assistant response. Captures the turn to AWS memory.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PAYLOAD_PATH="$(mktemp)"
trap 'rm -f "${PAYLOAD_PATH}"' EXIT
cat > "${PAYLOAD_PATH}" || true

# Resolve CLI: prefer `canon`, fall back to legacy name.
CANON_BIN=""
if command -v canon >/dev/null 2>&1; then
  CANON_BIN="canon"
elif command -v canon-memory-layer >/dev/null 2>&1; then
  CANON_BIN="canon-memory-layer"
else
  echo '{}'
  exit 0
fi

"${CANON_BIN}" --repo-root "${ROOT_DIR}" capture \
  --hook-input "${PAYLOAD_PATH}" \
  --pending-user-file "${ROOT_DIR}/.canon/memory/pending-user-turn.json" \
  --quiet >/dev/null 2>&1 || true

echo '{}'
