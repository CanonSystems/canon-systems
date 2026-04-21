#!/usr/bin/env bash
set -euo pipefail

DRY_FLAG=""
REPO_ROOT=""

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

echo "Rolling back auth migration dry_run=${DRY_FLAG:+yes}${DRY_FLAG:-no}"
canon "${ROOT_ARGS[@]}" auth-migration rollback ${DRY_FLAG}
canon "${ROOT_ARGS[@]}" auth-migration status
