#!/usr/bin/env bash
# Installed by canon-memory-layer. Do not edit by hand.
# Runs after every assistant response. Captures the turn to AWS memory.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PAYLOAD_PATH="$(mktemp)"
trap 'rm -f "${PAYLOAD_PATH}"' EXIT
cat > "${PAYLOAD_PATH}" || true

if ! command -v canon-memory-layer >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi

canon-memory-layer --repo-root "${ROOT_DIR}" capture \
  --hook-input "${PAYLOAD_PATH}" \
  --pending-user-file "${ROOT_DIR}/.canon/memory/pending-user-turn.json" \
  --quiet >/dev/null 2>&1 || true

echo '{}'
