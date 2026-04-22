GATE_RESULTS
  handoff_id: "canon-memory-v1"
  task_id: "E0-T5"
  branch: "wave/0/canon-memory-v1"
  verdict: PASS
  acceptance_criteria:
    - criterion: "scripts/smoke-test.sh exists, mode 0755, set -euo pipefail, three stages (build-services.sh, pytest -q, terraform validate). Non-zero on any stage failure."
      status: PASS
      covering_tests:
        - "tests/test_consolidation_smoke.py::test_smoke_script_exists_executable_and_content"
        - "scripts/smoke-test.sh live run — exit 0"
      run_result: "pass — mode -rwxr-xr-x; all three stages complete"
    - criterion: "VIRTUAL_ENV reuse or .venv-smoke/ creation; .venv-smoke/ gitignored."
      status: PASS
      covering_tests:
        - "tests/test_consolidation_smoke.py::test_venv_smoke_gitignored"
      run_result: "pass — `.venv-smoke/` in .gitignore; VIRTUAL_ENV branch verified in source"
    - criterion: ".github/workflows/ci.yml single ubuntu-latest smoke-test job with correct toolchain + trigger set."
      status: PASS
      covering_tests:
        - "tests/test_consolidation_smoke.py::test_ci_yml_parses_and_smoke_job_contract"
        - "python3 -c yaml.safe_load gate"
      run_result: "pass — runs-on ubuntu-latest; python-version 3.11; terraform ~1.5.0 wrapper:false; bash scripts/smoke-test.sh step present"
    - criterion: ".github/workflows/template-policy-guard.yml NOT modified."
      status: PASS
      covering_tests:
        - "git diff HEAD (empty)"
      run_result: "pass"
    - criterion: "tests/test_consolidation_smoke.py hermetic; no subprocess import."
      status: PASS
      covering_tests:
        - "5 tests under test_consolidation_smoke.py"
      run_result: "pass — 5/5 in <2s; AST guard verifies no subprocess import"
    - criterion: "docs/WAVE-0-CLOSEOUT.md has wave summary + commit table + green signal + OQ-E0-T4-01 + OQ-E0-T5-01 + acceptance line."
      status: PASS
      covering_tests:
        - "tests/test_consolidation_smoke.py::test_wave0_closeout_doc_and_oq_refs"
      run_result: "pass — SHAs 7eba576/da02e41/35df118/30a3b59 present; acceptance line verbatim"
    - criterion: "Living-spec updated: README, CHANGELOG, SYSTEM-WORKFLOW §10."
      status: PASS
      covering_tests:
        - "git diff HEAD -- README.md CHANGELOG.md docs/SYSTEM-WORKFLOW.md"
      run_result: "pass — smoke-test subsection + Unreleased entry + §10 paragraph all present"
    - criterion: "Root pytest ≥ 104 tests, exit 0."
      status: PASS
      covering_tests:
        - "pytest -q"
      run_result: "pass — 107 passed in 0.53s"
    - criterion: "bash scripts/smoke-test.sh exits 0 locally."
      status: PASS
      covering_tests:
        - "live run"
      run_result: "pass — final 'smoke-test: ALL STAGES PASSED' (~22s wall)"
    - criterion: "No writes to forbidden surfaces."
      status: PASS
      covering_tests:
        - "git status --short + git diff --stat scope check"
      run_result: "pass — changes confined to scripts/, .github/workflows/ci.yml (new), tests/, docs/, README, CHANGELOG, .gitignore, requirements-dev.txt, handoff packets. tests/test_infra_layout.py narrowly adjusted (git ls-files); invariants preserved (8/8 pass)."
  additional_gates:
    canon_qa_validate: "NOT_RUN — canon CLI not on PATH (wave-0 precedent; OQ-E0-T5-07)"
    canon_flow_audit: "NOT_RUN — same reason"
  iterations: 0
  regression_checked: true
  remaining_gaps: []
  notes: "All 10 ACs green in 0 iterations. tests/test_infra_layout.py git ls-files adjustment is scope-defensible: same invariants (no committed tfstate/lock/cache), now robust to local terraform init (required by smoke harness). E0-T5 ready for commit + wave close."
END_GATE_RESULTS
