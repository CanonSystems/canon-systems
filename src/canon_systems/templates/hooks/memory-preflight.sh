#!/usr/bin/env bash
# Installed by canon-systems. Do not edit by hand.
# Runs before every user prompt. Hydrates .canon/memory/context-latest.md
# and stores the pending user turn for paired capture.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PAYLOAD_PATH="$(mktemp)"
trap 'rm -f "${PAYLOAD_PATH}"' EXIT
cat > "${PAYLOAD_PATH}" || true

# Resolve CLI: prefer `canon`, fall back to legacy `canon-memory-layer` name
# for machines that haven't upgraded yet.
CANON_BIN=""
if command -v canon >/dev/null 2>&1; then
  CANON_BIN="canon"
elif command -v canon-memory-layer >/dev/null 2>&1; then
  CANON_BIN="canon-memory-layer"
else
  echo '{ "permission": "allow" }'
  exit 0
fi

# Hard-fail on version drift so the agent surfaces the upgrade prompt.
if ! "${CANON_BIN}" --repo-root "${ROOT_DIR}" version-check --quiet; then
  MSG="$("${CANON_BIN}" --repo-root "${ROOT_DIR}" version-check 2>&1 || true)"
  printf '{ "permission": "allow", "systemMessage": %s }\n' \
    "$(printf '%s' "${MSG}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
  exit 0
fi

"${CANON_BIN}" --repo-root "${ROOT_DIR}" preflight \
  --hook-input "${PAYLOAD_PATH}" --quiet >/dev/null 2>&1 || true

"${CANON_BIN}" --repo-root "${ROOT_DIR}" store-pending-user \
  --hook-input "${PAYLOAD_PATH}" \
  --output-file "${ROOT_DIR}/.canon/memory/pending-user-turn.json" >/dev/null 2>&1 || true

echo '{ "permission": "allow" }'
