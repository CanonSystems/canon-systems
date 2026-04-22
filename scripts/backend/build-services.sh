#!/usr/bin/env bash
# Install backend/shared and each leaf Python service, then import-smoke `*.main.app`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PYTHON_CMD="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
if [[ -z "${PYTHON_CMD}" ]]; then
  echo "build-services: need python3 or python on PATH" >&2
  exit 1
fi

pip install -e backend/shared
pip install -e backend/knowledge-schema
pip install -e backend/knowledge-policy
pip install -e backend/knowledge-client
pip install -e backend/memory-adapter

for svc in knowledge-api knowledge-worker memory-adapter state-api axon-service synthesis; do
  pip install -e "backend/${svc}"
  case "${svc}" in
    knowledge-api) pkg=app ;;
    knowledge-worker) pkg=knowledge_worker ;;
    memory-adapter) pkg=memory_adapter ;;
    state-api) pkg=state_api ;;
    axon-service) pkg=axon_service ;;
    synthesis) pkg=synthesis ;;
    *) echo "unknown service: ${svc}" >&2; exit 1 ;;
  esac
  "${PYTHON_CMD}" -c "import ${pkg}.main as _m; assert hasattr(_m, 'app')"
done
