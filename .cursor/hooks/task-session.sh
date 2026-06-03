#!/usr/bin/env bash
# Installed by canon-systems. Do not edit by hand.
# Runs after every assistant response (before memory-capture). Keeps the active
# task context aligned with task_ref mentions in the turn. Fail-open.
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PAYLOAD_PATH="$(mktemp)"
trap 'rm -f "${PAYLOAD_PATH}"' EXIT
cat > "${PAYLOAD_PATH}" || true

CANON_BIN=""
if command -v canon >/dev/null 2>&1; then
  CANON_BIN="canon"
elif command -v canon-memory-layer >/dev/null 2>&1; then
  CANON_BIN="canon-memory-layer"
else
  echo '{}'
  exit 0
fi

case "${CANON_TASKS_SESSION_HOOK:-1}" in
  0|false|no|off)
    echo '{}'
    exit 0
    ;;
esac

"${CANON_BIN}" --repo-root "${ROOT_DIR}" task record-session \
  --hook-input "${PAYLOAD_PATH}" \
  >/dev/null 2>&1 || true

echo '{}'
