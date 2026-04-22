HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E0-T5 closes Wave 0 by adding an automated smoke harness that proves the consolidated canon-systems repo still builds, imports, tests, and terraform-validates end-to-end from a clean checkout — WITHOUT any AWS credentials or hits against the live three URLs. Deliverables: (1) scripts/smoke-test.sh orchestrator (build → pytest → terraform validate); (2) .github/workflows/ci.yml single ubuntu-latest runner invoking smoke-test.sh on PR + push to main/wave/**; (3) tests/test_consolidation_smoke.py structural assertions; (4) docs/WAVE-0-CLOSEOUT.md recording wave acceptance + deferred OQs; (5) living-spec updates. Backlog AC 'integration harness exercises capture -> ask -> dor-log' is reinterpreted as the consolidation harness; live reachability is deferred to OQ-E0-T5-01. No canon CLI invocations (not on PATH — E0-T3/T4 precedent). No push, no PR, no commit inside this task — orchestrator opens the wave PR after E0-T5 lands per rule §10."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E0-T5"
      workstream_id: "wave-0e"
      epic_id: "E0"
      repo_ref: "canon-systems @ wave/0/canon-memory-v1 (tip 30a3b59)"

    story:
      title: "Smoke-test consolidated stack"
      acceptanceCriteria:
        - "scripts/smoke-test.sh exists, mode 0755, set -euo pipefail, three stages: bash scripts/backend/build-services.sh, pytest -q, terraform -chdir=infra/terraform init -backend=false -input=false && terraform -chdir=infra/terraform validate. Non-zero on any stage failure with clear stage identifier."
        - "scripts/smoke-test.sh detects VIRTUAL_ENV and reuses it; otherwise creates .venv-smoke/ and installs deps. .venv-smoke/ is gitignored."
        - ".github/workflows/ci.yml exists. Single ubuntu-latest job 'smoke-test': checkout@v4, setup-python@v5 (3.11), setup-terraform@v3 (~1.5.0, terraform_wrapper: false), pip install + requirements-dev, bash scripts/smoke-test.sh. Triggers: pull_request + push to main/wave/**."
        - ".github/workflows/template-policy-guard.yml NOT modified."
        - "tests/test_consolidation_smoke.py asserts: smoke-test.sh exists/executable/safe/references 3 stages; ci.yml parses + has smoke-test job on ubuntu-latest with bash scripts/smoke-test.sh step + Python 3.11; .venv-smoke/ in .gitignore; docs/WAVE-0-CLOSEOUT.md exists and mentions both OQ-E0-T4-01 and OQ-E0-T5-01. No subprocess/pip/terraform from inside pytest."
        - "docs/WAVE-0-CLOSEOUT.md records wave branch, final tip, per-task commit table (E0-T1..T5), green-signal definition, deferred OQs, explicit acceptance 'Wave 0 is complete under: consolidation complete, reconciliation pending'."
        - "Living-spec updated: README.md (smoke-test subsection), CHANGELOG.md (Unreleased: E0-T5), docs/SYSTEM-WORKFLOW.md §10 (smoke-test harness paragraph)."
        - "Root pytest -q ≥ 104 tests, exit 0."
        - "bash scripts/smoke-test.sh exits 0 locally in this session."
        - "No writes to: backend/**, src/canon_systems/**, infra/terraform/**, infra/auth-ingress/**, canon-systems-v2/**, pyproject.toml root, pytest.ini, .cursor/rules/plans, docs/MEMORY-PLATFORM-* or docs/WAVE-0-AUDIT.md or docs/E0-T*-*.md (frozen), existing template-policy-guard.yml, backend/<svc>/tests/, Dockerfiles, deploy/**."

      done_signal:
        - "bash scripts/smoke-test.sh exits 0 from clean shell at repo root."
        - "pytest -q tests/test_consolidation_smoke.py exits 0."
        - "Root pytest -q exits 0 (≥ 104 tests)."
        - "python3 -c 'import yaml, pathlib; yaml.safe_load(pathlib.Path(\".github/workflows/ci.yml\").read_text())' exits 0."

      reinterpreted_backlog_acs:
        - backlog_criterion: "Integration harness exercises capture -> ask -> dor-log path"
          reinterpretation: "Harness exercises consolidation integration (build → import-smoke → pytest → terraform validate); live canon capture/ask/dor-log requires creds + canon CLI — deferred to OQ-E0-T5-01."
        - backlog_criterion: "Run is green against the consolidated stack in dev"
          reinterpretation: "'Green' proven by scripts/smoke-test.sh exit 0 + CI workflow wired to run on PR/push. 'In dev' (live AWS) deferred to OQ-E0-T5-01."

    in_scope_paths_to_create:
      - "scripts/smoke-test.sh"
      - ".github/workflows/ci.yml"
      - "tests/test_consolidation_smoke.py"
      - "docs/WAVE-0-CLOSEOUT.md"
      - "requirements-dev.txt (if pyyaml needed)"

    in_scope_paths_to_modify:
      - ".gitignore"
      - "README.md"
      - "CHANGELOG.md"
      - "docs/SYSTEM-WORKFLOW.md"

    out_of_scope_paths:
      - "backend/**, src/canon_systems/**, infra/terraform/**, infra/auth-ingress/**"
      - "canon-systems-v2/** (read-only)"
      - "pyproject.toml root, pytest.ini"
      - ".cursor/rules/**, .cursor/plans/**"
      - "docs/MEMORY-PLATFORM-{PLAN,BACKLOG}.md, docs/WAVE-0-AUDIT.md, docs/OBSIDIAN-MIND-CATALOGUE.md"
      - "docs/DEPRECATIONS.md, docs/E0-T1-*.md, docs/E0-T3-MIGRATION-NOTES.md, docs/E0-T4-INFRA-IMPORT.md (frozen)"
      - ".github/workflows/template-policy-guard.yml"
      - "scripts/backend/build-services.sh, scripts/backend/install-workspace.sh (reuse unchanged)"

    forbidden_surface:
      no_cloud_commands:
        - "terraform apply/destroy/import/refresh"
        - "aws *, aws-vault *"
        - "canon capture/ask/dor-log/qa-validate/flow-audit/memory-health"
        - "curl/http to KNOWLEDGE_API_URL / KNOWLEDGE_WORKER_URL / MEMORY_ADAPTER_URL"
        - "act, docker run for workflow exec"
      permitted:
        - "bash scripts/smoke-test.sh, scripts/backend/build-services.sh"
        - "pip install -e, pytest, terraform init -backend=false + validate + fmt -check"
        - "python3 -c 'import yaml; ...' for parse validation"

    acceptable_scope_expansion:
      pre_authorized:
        - "Add requirements-dev.txt (pyyaml) as tests-only dev deps; must be consumed by both local smoke-test.sh and CI install step. Root pyproject.toml / pytest.ini stay untouched."
        - ".venv-smoke/ creation + gitignore entry."
      not_pre_authorized:
        - "Modifying root pyproject.toml/pytest.ini."
        - "Matrix strategy on CI workflow."
        - "Live AWS calls."
        - "Modifying scripts/backend/build-services.sh or template-policy-guard.yml."
        - "Live-reachability probes for the three URLs."

    smoke_script_contract:
      shebang: "#!/usr/bin/env bash"
      safety: "set -euo pipefail"
      stages:
        - {id: "build", command: "bash scripts/backend/build-services.sh"}
        - {id: "pytest", command: "pytest -q"}
        - {id: "terraform", command: "terraform -chdir=infra/terraform init -backend=false -input=false && terraform -chdir=infra/terraform validate"}
      venv_handling: "If VIRTUAL_ENV unset: create .venv-smoke/, activate, pip install -e . + pytest. Else reuse."
      final_message: "smoke-test: ALL STAGES PASSED"

    ci_workflow_contract:
      file: ".github/workflows/ci.yml"
      name: "Canon Smoke Test"
      triggers:
        pull_request: {}
        push: {branches: ["main", "wave/**"]}
      job_id: "smoke-test"
      runs_on: "ubuntu-latest"
      steps:
        - "actions/checkout@v4"
        - "actions/setup-python@v5 with python-version: '3.11'"
        - "hashicorp/setup-terraform@v3 (terraform_version: '~1.5.0', terraform_wrapper: false)"
        - "pip install + requirements-dev.txt"
        - "bash scripts/smoke-test.sh"
      matrix: NONE
      timeout_minutes: 20

    wave0_closeout_doc_contract:
      path: "docs/WAVE-0-CLOSEOUT.md"
      required_sections:
        - "Wave summary (branch, final tip, scope E0-T1..T5)"
        - "Per-task commit table (SHA, title, qa verdict): E0-T1 7eba576, E0-T2 da02e41, E0-T3 35df118, E0-T4 30a3b59, E0-T5 TBD"
        - "Green-signal definition"
        - "Deferred follow-ups"
      deferred_oqs:
        - id: "OQ-E0-T4-01"
          description: "terraform plan shows no changes against production — operator post-merge."
        - id: "OQ-E0-T5-01"
          description: "canon capture → ask → dor-log exercised against live three URLs — operator post-merge or wave-1."
      acceptance_statement: "Wave 0 is complete under: consolidation complete, reconciliation pending."

    openQuestions:
      - id: "OQ-E0-T5-01"
        question: "Live reachability — hit the three URLs from smoke harness?"
        proposed_resolution: "NO in E0-T5. Document as operator follow-up; candidate owners E1-T1 or post-merge."
        blocking_for_this_task: false
      - id: "OQ-E0-T5-02"
        question: "Matrix of Python versions?"
        proposed_resolution: "NO. Single runner for wave 0 close."
        blocking_for_this_task: false
      - id: "OQ-E0-T5-03"
        question: "Cache pip installs in CI?"
        proposed_resolution: "NO. Keep workflow minimal; add actions/cache@v4 only if CI > 10min."
        blocking_for_this_task: false
      - id: "OQ-E0-T5-04"
        question: "Include ruff/formatting in smoke?"
        proposed_resolution: "NO. Separate concern; add in follow-up."
        blocking_for_this_task: false
      - id: "OQ-E0-T5-05"
        question: "Replace template-policy-guard.yml?"
        proposed_resolution: "NO. Orthogonal workflows; coexist."
        blocking_for_this_task: false
      - id: "OQ-E0-T5-06"
        question: "pyyaml for workflow parse assertion?"
        proposed_resolution: "YES via requirements-dev.txt."
        blocking_for_this_task: false
      - id: "OQ-E0-T5-07"
        question: "canon qa-validate / dor-log for E0-T5?"
        proposed_resolution: "NO; canon not on PATH; waive per E0-T3/T4 precedent."
        blocking_for_this_task: false

    prior_work_references:
      - ".cursor/handoffs/canon-memory-v1/E0-T3/scoper.md (build-services.sh contract)"
      - ".cursor/handoffs/canon-memory-v1/E0-T4/scoper.md (terraform validate contract)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md §E E0-T5"
      - ".cursor/rules/memory-platform-build-discipline.mdc §§9-10"
      - ".github/workflows/template-policy-guard.yml (sibling, do not modify)"

    dor_checklist:
      all: "pass"

END_HANDOFF_TO_CURSOR_PILOT
