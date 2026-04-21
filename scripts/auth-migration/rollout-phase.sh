#!/usr/bin/env bash
set -euo pipefail

PHASE="${1:-}"
if [[ -z "${PHASE}" ]]; then
  echo "Usage: $0 <prepare|canary|enforce> [--dry-run] [--repo-root <path>] [--domain <host>]" >&2
  exit 2
fi

if [[ "${PHASE}" != "prepare" && "${PHASE}" != "canary" && "${PHASE}" != "enforce" ]]; then
  echo "Invalid phase: ${PHASE}. Expected prepare|canary|enforce." >&2
  exit 2
fi

DRY_FLAG=""
REPO_ROOT=""
DOMAIN="memory.canon-systems.com"

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_FLAG="--dry-run"
      shift
      ;;
    --repo-root)
      REPO_ROOT="${2:-}"
      shift 2
      ;;
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

ROOT_ARGS=()
if [[ -n "${REPO_ROOT}" ]]; then
  ROOT_ARGS=(--repo-root "${REPO_ROOT}")
fi

echo "Applying auth migration phase=${PHASE} domain=${DOMAIN} dry_run=${DRY_FLAG:+yes}${DRY_FLAG:-no}"
canon "${ROOT_ARGS[@]}" auth-migration "${PHASE}" --domain "${DOMAIN}" --scheme https ${DRY_FLAG}

echo "Phase ${PHASE} complete."
