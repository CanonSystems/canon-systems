HANDOFF_TO_QA
  task_id: E0-T5
  handoff_id: canon-memory-v1
  branch: wave/0/canon-memory-v1
  acceptance_criteria_covered:
    - "scripts/smoke-test.sh: 0755, set -euo pipefail, build → pytest -q → terraform validate (or SMOKE_SKIP_TERRAFORM=1), venv at .venv-smoke when VIRTUAL_ENV unset, clear stage failures, final ALL STAGES PASSED"
    - ".github/workflows/ci.yml: single smoke-test job, triggers (PR + push to main + wave/**), setup-python 3.11, setup-terraform ~1.5.0, pip + requirements-dev, bash scripts/smoke-test.sh; template-policy-guard.yml untouched"
    - "tests/test_consolidation_smoke.py: hermetic (PyYAML + file reads; AST walk guards against subprocess import)"
    - "docs/WAVE-0-CLOSEOUT.md: SHAs (E0-T1..T4; E0-T5 TBD), OQ-E0-T4-01, OQ-E0-T5-01, wave acceptance line"
    - "requirements-dev.txt: pyyaml>=6.0"
    - "README, CHANGELOG, SYSTEM-WORKFLOW §10 updated"
    - ".gitignore: .venv-smoke/"
  changed_files:
    created:
      - "scripts/smoke-test.sh"
      - ".github/workflows/ci.yml"
      - "tests/test_consolidation_smoke.py"
      - "docs/WAVE-0-CLOSEOUT.md"
      - "requirements-dev.txt"
    modified:
      - ".gitignore"
      - "README.md"
      - "CHANGELOG.md"
      - "docs/SYSTEM-WORKFLOW.md"
      - "tests/test_infra_layout.py"
  how_to_run_tests:
    gate_1: "bash scripts/smoke-test.sh → exit 0 (terraform stage ok on host; final line 'smoke-test: ALL STAGES PASSED')"
    gate_2: "pytest tests/test_consolidation_smoke.py -v → 5 passed"
    gate_3: "pytest -q → 107 passed (≥ 104)"
    gate_4: "python3 -c yaml.safe_load on ci.yml → exit 0"
  decisions:
    - "SMOKE_SKIP_TERRAFORM=1 escape hatch only skips terraform stage when explicitly set; otherwise hard-fails with a pointer to the env var."
    - "tests/test_infra_layout.py .terraform.lock.hcl + .terraform cache checks now use `git ls-files` so a local `terraform init` from smoke doesn't leak into follow-up pytest runs. No writes under infra/terraform/**."
    - "tests/test_consolidation_smoke.py uses AST walk for 'no subprocess import' guard (avoids docstring false positives)."
  next_actions:
    - "Parent agent: stage + commit on wave/0/canon-memory-v1 per rule §9."
    - "After commit, fill E0-T5 SHA into docs/WAVE-0-CLOSEOUT.md per-task table + final tip (optional; release-orchestrator may request)."
    - "Open wave PR per rule §10."
  open_questions:
    - "OQ-E0-T4-01: production terraform reconciliation deferred to operator post-merge."
    - "OQ-E0-T5-01: live canon capture/ask/dor-log path against the three URLs deferred to operator or E1-T1."
END_HANDOFF_TO_QA
