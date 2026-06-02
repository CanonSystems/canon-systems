#!/usr/bin/env bash
# Installed by canon-systems. Do not edit by hand.
# Runs before every user prompt. Surfaces open tasks assigned to (or authored
# by) the current user for this repo, so handed-off work is visible inline.
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

# Honour an opt-out so noisy repos can silence the surfacing hook.
case "${CANON_TASKS_PREFLIGHT:-1}" in
  0|false|no|off)
    echo '{ "permission": "allow" }'
    exit 0
    ;;
esac

TASKS_JSON="$("${CANON_BIN}" --repo-root "${ROOT_DIR}" task list --mine --json 2>/dev/null || echo '[]')"

MSG="$(printf '%s' "${TASKS_JSON}" | python3 -c '
import json, sys
try:
    tasks = json.load(sys.stdin)
except Exception:
    tasks = []
if not isinstance(tasks, list):
    tasks = []
open_tasks = [t for t in tasks if t.get("status") not in ("done", "cancelled")]
if not open_tasks:
    sys.exit(0)
lines = ["You have %d open Canon task(s) assigned to you in this repo:" % len(open_tasks)]
for t in open_tasks[:10]:
    ref = t.get("task_ref", "?")
    title = t.get("title", "")
    prio = t.get("priority", "normal")
    tag = " !%s" % prio if prio in ("high", "urgent") else ""
    lines.append("  - %s: %s%s" % (ref, title, tag))
if len(open_tasks) > 10:
    lines.append("  ... and %d more (run: canon task list --mine)" % (len(open_tasks) - 10))
print("\n".join(lines))
' 2>/dev/null || true)"

if [ -n "${MSG}" ]; then
  printf '{ "permission": "allow", "systemMessage": %s }\n' \
    "$(printf '%s' "${MSG}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
  exit 0
fi

echo '{ "permission": "allow" }'
