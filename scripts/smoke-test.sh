#!/usr/bin/env bash
# Wave 0 closeout: build → pytest → terraform validate (no cloud credentials).
#
# Venv: if VIRTUAL_ENV is unset, creates .venv-smoke/ at repo root, activates
# it, and runs: pip install -e . pytest -r requirements-dev.txt
# If VIRTUAL_ENV is set, the existing environment is reused (dependencies must
# already be installed).
#
# Stages: build (scripts/backend/build-services.sh), pytest (pytest -q),
# terraform (init -backend=false + validate under infra/terraform).
#
# Escape hatch: if terraform is not on PATH, set SMOKE_SKIP_TERRAFORM=1 to skip
# the terraform stage (default: run terraform; do not set unless you must).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  VENV_DIR="${ROOT}/.venv-smoke"
  if [[ ! -d "${VENV_DIR}" ]]; then
    if ! command -v python3 >/dev/null 2>&1; then
      echo "smoke-test: [venv] need python3 on PATH" >&2
      exit 1
    fi
    python3 -m venv "${VENV_DIR}"
  fi
  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"
  pip install -e . pytest -r requirements-dev.txt
else
  :
fi

run_stage() {
  local id="$1"
  shift
  echo "smoke-test: [${id}] starting..."
  if ! "$@"; then
    echo "smoke-test: STAGE FAILED: ${id}" >&2
    exit 1
  fi
  echo "smoke-test: [${id}] ok"
}

run_stage build bash scripts/backend/build-services.sh
run_stage pytest pytest -q

if [[ "${SMOKE_SKIP_TERRAFORM:-0}" == "1" ]]; then
  echo "smoke-test: [terraform] skipped (SMOKE_SKIP_TERRAFORM=1)" >&2
else
  if ! command -v terraform >/dev/null 2>&1; then
    echo "smoke-test: [terraform] terraform not on PATH; set SMOKE_SKIP_TERRAFORM=1 to skip this stage" >&2
    echo "smoke-test: STAGE FAILED: terraform" >&2
    exit 1
  fi
  run_stage terraform bash -c 'terraform -chdir=infra/terraform init -backend=false -input=false && terraform -chdir=infra/terraform validate'
fi

echo "smoke-test: ALL STAGES PASSED"
