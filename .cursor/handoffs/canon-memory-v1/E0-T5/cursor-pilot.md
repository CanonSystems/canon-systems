CURSOR_PILOT_PROMPT

<ROLE>
implementer subagent for E0-T5 — Wave 0 closeout smoke harness.
</ROLE>

<TASK>
Implement the consolidation smoke harness per scoper packet at
.cursor/handoffs/canon-memory-v1/E0-T5/scoper.md. No AWS creds, no live URL
hits, no canon CLI invocations (not on PATH), no git commit/push.
</TASK>

<DELIVERABLES>
1. scripts/smoke-test.sh (mode 0755, set -euo pipefail)
   Stages in order:
     a. bash scripts/backend/build-services.sh
     b. pytest -q
     c. terraform -chdir=infra/terraform init -backend=false -input=false && terraform -chdir=infra/terraform validate
   Venv: if VIRTUAL_ENV unset, create .venv-smoke/, activate, pip install -e . + pytest + -r requirements-dev.txt.
   Exit non-zero with clear stage message on failure; final "smoke-test: ALL STAGES PASSED".

2. .github/workflows/ci.yml
   name: "Canon Smoke Test"
   on: pull_request + push to main, wave/**
   jobs.smoke-test: runs-on ubuntu-latest, timeout 20min
   steps: checkout@v4 -> setup-python@v5 (3.11) -> setup-terraform@v3 (~1.5.0, terraform_wrapper: false) -> pip install -e . + pytest + -r requirements-dev.txt -> bash scripts/smoke-test.sh

3. tests/test_consolidation_smoke.py — hermetic assertions only:
   - smoke-test.sh exists, executable, contains "set -euo pipefail", references "scripts/backend/build-services.sh", "pytest", "terraform validate"
   - ci.yml parses via yaml.safe_load (use pyyaml from requirements-dev.txt; gracefully skip if unavailable via importlib check)
   - ci.yml has jobs.smoke-test.runs-on == "ubuntu-latest"; has step invoking "bash scripts/smoke-test.sh"; uses python-version 3.11
   - .venv-smoke/ in .gitignore
   - docs/WAVE-0-CLOSEOUT.md exists and references "OQ-E0-T4-01" and "OQ-E0-T5-01"
   MUST NOT: subprocess launch terraform/pytest/pip.

4. docs/WAVE-0-CLOSEOUT.md — sections:
   - Wave summary (branch wave/0/canon-memory-v1, final tip TBD-after-commit, scope E0-T1..T5)
   - Per-task commit table: E0-T1 7eba576, E0-T2 da02e41, E0-T3 35df118, E0-T4 30a3b59, E0-T5 (this commit, TBD)
   - Green-signal definition
   - Deferred follow-ups with explicit mention of OQ-E0-T4-01 and OQ-E0-T5-01
   - Explicit acceptance: "Wave 0 is complete under: consolidation complete, reconciliation pending."

5. requirements-dev.txt — pyyaml (at minimum)

6. Living spec:
   - README.md — add "Smoke test" subsection under Backend or Infra section
   - CHANGELOG.md — Unreleased entry for E0-T5
   - docs/SYSTEM-WORKFLOW.md §10 — augment with smoke-test paragraph

7. .gitignore — add .venv-smoke/
</DELIVERABLES>

<FORBIDDEN_SURFACE>
- No writes to: backend/**, src/canon_systems/**, infra/terraform/**, infra/auth-ingress/**, canon-systems-v2/**, pyproject.toml (root), pytest.ini, .cursor/rules/**, .cursor/plans/**, docs/MEMORY-PLATFORM-{PLAN,BACKLOG}.md, docs/WAVE-0-AUDIT.md, docs/DEPRECATIONS.md, docs/E0-T1-*.md, docs/E0-T3-MIGRATION-NOTES.md, docs/E0-T4-INFRA-IMPORT.md, docs/OBSIDIAN-MIND-CATALOGUE.md, existing .github/workflows/template-policy-guard.yml, scripts/backend/build-services.sh.
- No terraform apply/destroy/import/refresh, no aws *, no canon * CLI, no curl to live URLs, no act/docker.
- No git commit/push/branch switch.
</FORBIDDEN_SURFACE>

<VALIDATION_GATES>
Run all three after file creation:
  1. bash scripts/smoke-test.sh  → exit 0 (MUST PASS)
  2. pytest tests/test_consolidation_smoke.py -v → all pass
  3. pytest -q (root) → ≥ 104 tests, exit 0
  4. python3 -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())" → exit 0
</VALIDATION_GATES>

<OUTPUT_FORMAT>
Emit HANDOFF_TO_QA with acceptance_criteria_covered, changed_files (created/modified), how_to_run_tests (with actual results), decisions, next_actions, open_questions.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
- Do not push, commit, or change branch.
- Do not touch forbidden surfaces.
- Do not call canon CLI or hit live URLs.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
