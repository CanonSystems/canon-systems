#!/usr/bin/env bash
# Installed by canon-systems. Do not edit by hand.
# Runs before every user prompt. Hydrates .canon/memory/context-latest.md
# and stores the pending user turn for paired capture.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PAYLOAD_PATH="$(mktemp)"
ERR_PATH="$(mktemp)"
trap 'rm -f "${PAYLOAD_PATH}" "${ERR_PATH}"' EXIT
cat > "${PAYLOAD_PATH}" || true
RECOVERY_MARKER="${ROOT_DIR}/.canon/memory/credential-recovery-needed.txt"

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

is_credential_error() {
  local err_file="$1"
  rg -n -e "Unable to locate credentials|AWS Secrets Manager fetch failed|AccessDeniedException|secret does not exist|secret has no SecretString|Missing credentials|NoCredentialProviders" "${err_file}" >/dev/null 2>&1
}

attempt_secret_recovery() {
  # Interactive wizard only works in a real TTY. Hooks usually run headless.
  if [[ -t 0 && -t 1 ]]; then
    "${CANON_BIN}" --repo-root "${ROOT_DIR}" secrets wizard || true
  fi
}

mark_recovery_needed() {
  mkdir -p "${ROOT_DIR}/.canon/memory"
  {
    echo "Credential recovery required for repo memory integration."
    echo "Run: canon --repo-root \"${ROOT_DIR}\" secrets"
    echo "Tip: if reusing credentials, say: use credentials from <repo/system>."
  } > "${RECOVERY_MARKER}"
}

clear_recovery_marker() {
  if [[ -f "${RECOVERY_MARKER}" ]]; then
    rm -f "${RECOVERY_MARKER}" || true
  fi
}

run_with_recovery() {
  if "$@" >/dev/null 2>"${ERR_PATH}"; then
    clear_recovery_marker
    return 0
  fi
  if is_credential_error "${ERR_PATH}"; then
    attempt_secret_recovery
    if "$@" >/dev/null 2>"${ERR_PATH}"; then
      clear_recovery_marker
      return 0
    fi
    mark_recovery_needed
  fi
  return 1
}

run_with_recovery preflight \
  "${CANON_BIN}" --repo-root "${ROOT_DIR}" preflight \
  --hook-input "${PAYLOAD_PATH}" --quiet || true

"${CANON_BIN}" --repo-root "${ROOT_DIR}" store-pending-user \
  --hook-input "${PAYLOAD_PATH}" \
  --output-file "${ROOT_DIR}/.canon/memory/pending-user-turn.json" >/dev/null 2>&1 || true

if [[ -f "${RECOVERY_MARKER}" ]]; then
  MSG="$(cat "${RECOVERY_MARKER}")"
  printf '{ "permission": "allow", "systemMessage": %s }\n' \
    "$(printf '%s' "${MSG}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
  exit 0
fi

echo '{ "permission": "allow" }'
