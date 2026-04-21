#!/usr/bin/env bash
# Installed by canon-systems. Do not edit by hand.
# Runs after every assistant response. Captures the turn to AWS memory.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PAYLOAD_PATH="$(mktemp)"
ERR_PATH="$(mktemp)"
trap 'rm -f "${PAYLOAD_PATH}" "${ERR_PATH}"' EXIT
cat > "${PAYLOAD_PATH}" || true
RECOVERY_MARKER="${ROOT_DIR}/.canon/memory/credential-recovery-needed.txt"

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

is_credential_error() {
  local err_file="$1"
  rg -n -e "Unable to locate credentials|AWS Secrets Manager fetch failed|AccessDeniedException|secret does not exist|secret has no SecretString|Missing credentials|NoCredentialProviders" "${err_file}" >/dev/null 2>&1
}

attempt_secret_recovery() {
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

run_capture_with_recovery() {
  if "${CANON_BIN}" --repo-root "${ROOT_DIR}" capture \
    --hook-input "${PAYLOAD_PATH}" \
    --pending-user-file "${ROOT_DIR}/.canon/memory/pending-user-turn.json" \
    --quiet >/dev/null 2>"${ERR_PATH}"; then
    clear_recovery_marker
    return 0
  fi
  if is_credential_error "${ERR_PATH}"; then
    attempt_secret_recovery
    if "${CANON_BIN}" --repo-root "${ROOT_DIR}" capture \
      --hook-input "${PAYLOAD_PATH}" \
      --pending-user-file "${ROOT_DIR}/.canon/memory/pending-user-turn.json" \
      --quiet >/dev/null 2>"${ERR_PATH}"; then
      clear_recovery_marker
      return 0
    fi
    mark_recovery_needed
  fi
  return 1
}

run_capture_with_recovery || true

echo '{}'
