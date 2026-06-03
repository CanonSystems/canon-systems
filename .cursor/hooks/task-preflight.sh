#!/usr/bin/env bash
# Installed by canon-systems. Do not edit by hand.
# Runs before every user prompt: refreshes active task context, surfaces open
# tasks, and links the session to canon task + memory capture automatically.
# Strictly fail-open: any error allows the prompt with no message.
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

CANON_BIN=""
if command -v canon >/dev/null 2>&1; then
  CANON_BIN="canon"
elif command -v canon-memory-layer >/dev/null 2>&1; then
  CANON_BIN="canon-memory-layer"
else
  echo '{ "permission": "allow" }'
  exit 0
fi

case "${CANON_TASKS_PREFLIGHT:-1}" in
  0|false|no|off)
    echo '{ "permission": "allow" }'
    exit 0
    ;;
esac

PAYLOAD="$("${CANON_BIN}" --repo-root "${ROOT_DIR}" task active --refresh --preflight --json 2>/dev/null || echo '{}')"

MSG="$(printf '%s' "${PAYLOAD}" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not isinstance(data, dict):
    sys.exit(0)
msg = (data.get("preflight_message") or "").strip()
if msg:
    print(msg)
' 2>/dev/null || true)"

if [ -n "${MSG}" ]; then
  printf '{ "permission": "allow", "systemMessage": %s }\n' \
    "$(printf '%s' "${MSG}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
  exit 0
fi

echo '{ "permission": "allow" }'
