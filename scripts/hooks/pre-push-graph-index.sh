#!/usr/bin/env bash
# Pre-push hook: run canon graph index with pending commits.
# Install: cp scripts/hooks/pre-push-graph-index.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
set -euo pipefail

COMPANY_ID="${CANON_COMPANY_ID:-unknown}"
REPOSITORY_ID="${CANON_REPOSITORY_ID:-$(basename "$(git rev-parse --show-toplevel)")}"
COMMIT_SHA="$(git rev-parse HEAD)"
CHANGED=$(git diff --name-only "@{push}" 2>/dev/null || true)

if [ -z "${CHANGED}" ]; then
  echo "pre-push-graph-index: no changed files; skipping."
  exit 0
fi

if [ -z "${AXON_SERVICE_URL:-}" ] || [ -z "${AXON_SERVICE_TOKEN:-}" ]; then
  echo "pre-push-graph-index: AXON_SERVICE_URL or AXON_SERVICE_TOKEN unset; skipping (non-blocking)."
  exit 0
fi

canon graph index \
  --company-id "${COMPANY_ID}" \
  --repository-id "${REPOSITORY_ID}" \
  --commit-sha "${COMMIT_SHA}" \
  --changed-files ${CHANGED}
