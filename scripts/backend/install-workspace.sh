#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

pip install -e backend/shared
for svc in knowledge-api knowledge-worker memory-adapter state-api axon-service synthesis; do
  pip install -e "backend/${svc}"
done
