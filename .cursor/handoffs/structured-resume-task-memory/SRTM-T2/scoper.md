HANDOFF_TO_CURSOR_PILOT
  scope_summary: Fix SRTM-T2 by making the top-level `canon resume` command pass documented resume-engine flags through directly, without requiring `--` or `python3 -m canon_systems.resume_engine`. The work should be narrowly scoped to CLI dispatch behavior and focused regression tests, preserving existing passthrough behavior for checkpoint, graph, report, stall-watchdog, vault, synth, and release commands.
  scope_packet:
    identifiers:
      handoff_id: "structured-resume-task-memory"
      plan_id: "structured-resume-task-memory"
      task_id: "SRTM-T2"
      workstream_id: "ws-main"
      company_id: "CSC"
      repository_id: "canon-systems"
      repo_ref: "task/SRTM-structured-resume-task-memory@112884c53c5796ea88891cf1eb005b8a7a0c58c8"
      packet_persistence_path: ".cursor/handoffs/structured-resume-task-memory/SRTM-T2/scoper.md"
    story:
      title: "Fix top-level canon resume flag passthrough"
      userValue: "Canon operators can run the documented pre-merge resume sweep through `canon resume --plan-id ...` directly, keeping release gates usable without hidden `--` or module-invocation workarounds."
      acceptanceCriteria:
        - "Running `canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory` reaches `resume_engine.run(...)` with the documented flags instead of failing in the top-level parser."
        - "The existing `python3 -m canon_systems.resume_engine --plan-id ...` path remains unchanged."
        - "Existing top-level passthrough behavior for checkpoint, graph, report, stall-watchdog, vault, synth, and release does not regress."
        - "Focused pytest coverage proves `canon_systems.cli.main([\"resume\", \"--plan-id\", ...])` dispatches without requiring `--`, and preserves the current `--`-separated compatibility case if still supported."
        - "No documentation changes are made unless the implementation discovers existing docs that explicitly require updating; the desired behavior is already the documented behavior."
    scope:
      in_scope:
        - "Inspect and adjust top-level command parsing/dispatch in `src/canon_systems/cli.py` for passthrough commands, with the direct bug target being `resume`."
        - "Add or update focused CLI dispatch tests, most likely in `tests/test_resume_engine.py`, where `test_canon_cli_dispatches_resume_lanes_args` already covers `resume` dispatch only when `--` is present."
        - "Run targeted regression tests around resume and nearby passthrough commands."
      out_of_scope:
        - "Changing resume-engine checkpoint scanning semantics, JSON envelope shape, lane scheduling, or exit-code behavior."
        - "Changing state-api, graph, report, vault, synth, release, Terraform, or generated memory artifacts."
        - "Touching unrelated dirty files: `.canon/memory/capture-failures.log`, `.canon/memory/capture-latest.json`, `infra/terraform/variables.tf`, `scripts/clone_memory_layer_secret.py`."
        - "Broad CLI rewrites beyond what is needed to make passthrough dispatch correct and tested."
    repository:
      primaryLanguages: ["Python", "Markdown", "Terraform", "Shell"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/cli.py"
        - "src/canon_systems/resume_engine.py"
        - "tests/test_resume_engine.py"
        - "tests/test_cli_checkpoint.py"
        - "tests/test_cli_report.py"
        - "tests/test_cli_synth_show.py"
        - "tests/test_cli_synth_publish.py"
        - "tests/test_vault_sync.py"
        - "tests/test_release_publish.py"
    constraints:
      dependencies:
        - "Use existing repo patterns and keep `canon_systems.cli.main` as the top-level script entrypoint from `pyproject.toml`."
        - "Preserve existing direct module parser behavior in `src/canon_systems/resume_engine.py`; the evidence shows it already supports the documented flags."
        - "Preserve `--repo-root` handling, repo-root environment setup, self-update/rewire calls, and command dispatch order in `src/canon_systems/cli.py`."
      mustNotBreak:
        - "Do not require users to insert `--` before documented `canon resume` flags."
        - "Do not regress passthrough command tails for `checkpoint`, `graph`, `report`, `stall-watchdog`, `vault`, `synth`, or `release`."
        - "Do not include unrelated dirty files or generated memory/cache artifacts."
    dor_checklist:
      repo_ref_verification: "pass: current branch `task/SRTM-structured-resume-task-memory`, current sha `112884c53c5796ea88891cf1eb005b8a7a0c58c8`."
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "Running `canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory` reaches `resume_engine.run(...)` with the documented flags instead of failing in the top-level parser."
        implementation_targets: ["src/canon_systems/cli.py"]
        verification_tests:
          - "tests/test_resume_engine.py::test_canon_cli_dispatches_resume_args_without_separator"
          - "canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory"
      - criterion: "The existing `python3 -m canon_systems.resume_engine --plan-id ...` path remains unchanged."
        implementation_targets: ["src/canon_systems/resume_engine.py"]
        verification_tests:
          - "python3 -m canon_systems.resume_engine --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory"
          - "python -m pytest tests/test_resume_engine.py -q"
      - criterion: "Existing top-level passthrough behavior for checkpoint, graph, report, stall-watchdog, vault, synth, and release does not regress."
        implementation_targets: ["src/canon_systems/cli.py"]
        verification_tests:
          - "python -m pytest tests/test_cli_checkpoint.py tests/test_cli_report.py tests/test_cli_synth_show.py tests/test_cli_synth_publish.py tests/test_vault_sync.py tests/test_release_publish.py -q"
      - criterion: "Focused pytest coverage proves `canon_systems.cli.main([\"resume\", \"--plan-id\", ...])` dispatches without requiring `--`, and preserves the current `--`-separated compatibility case if still supported."
        implementation_targets: ["tests/test_resume_engine.py"]
        verification_tests:
          - "python -m pytest tests/test_resume_engine.py::test_canon_cli_dispatches_resume_lanes_args tests/test_resume_engine.py::test_canon_cli_dispatches_resume_args_without_separator -q"
      - criterion: "No documentation changes are made unless the implementation discovers existing docs that explicitly require updating; the desired behavior is already the documented behavior."
        implementation_targets: ["docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md", "docs/SYSTEM-WORKFLOW.md"]
        verification_tests:
          - "git diff --name-only -- docs"
    risks_and_assumptions:
      assumptions:
        - "`resume_engine.run` is already the source of truth for `canon resume` flags; SRTM-T2 should not duplicate its parser at the top level."
        - "A shared passthrough-command handling path in `src/canon_systems/cli.py` may be safer than a resume-only special case if it preserves existing tests."
        - "The observed top-level parser failure is caused by `argparse.REMAINDER` passthrough behavior with leading optional flags."
      risks:
        - "Changing top-level parser flow can accidentally bypass setup/self-update/rewire side effects if implemented as an early return."
        - "Normalizing or stripping `--` from captured tails can break existing compatibility tests if not handled deliberately."
        - "Fixing all passthrough commands at once could alter documented quirks in `report` tests; keep changes focused and test nearby commands."
      openQuestions: []
    prior_work_references:
      - artifact_id: "art_memcap_20260429T150239Z_usr_new.moon3461"
        source: "canonical"
        relevance: "Recent session memory context for structured resume/task memory release-gate work."
      - artifact_id: "art_memcap_20260429T142810Z_usr_new.moon3461"
        source: "canonical"
        relevance: "Recent session memory context adjacent to SRTM-T1/SRTM-T2 workflow stabilization."
    retrieval_notes:
      graph:
        status: "degraded"
        evidence: "`canon graph query --company-id CSC --repository-id canon-systems --commit-sha 112884c53c5796ea88891cf1eb005b8a7a0c58c8 --q ...` exited 5 with transport 403 under sandbox networking."
      state:
        status: "degraded"
        evidence: "`canon checkpoint read ... SRTM-T2 ...` exited 5 with localhost connection refused; no state checkpoint was available in this environment."
      canonical:
        status: "partial"
        evidence: "Read `.canon/memory/context-latest.md`; `canon ask ...` attempted but exited 1 because read-only sandbox prevented writing the MemPalace retry queue."
      file:
        status: "used"
        evidence: "Read `src/canon_systems/cli.py`, `src/canon_systems/resume_engine.py`, `tests/test_resume_engine.py`, `tests/test_cli_checkpoint.py`, `tests/test_cli_report.py`, and `pyproject.toml`."
    concrete_verification_commands:
      - "python -m pytest tests/test_resume_engine.py -q"
      - "python -m pytest tests/test_cli_checkpoint.py tests/test_cli_report.py tests/test_cli_synth_show.py tests/test_cli_synth_publish.py tests/test_vault_sync.py tests/test_release_publish.py -q"
      - "canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory"
      - "python3 -m canon_systems.resume_engine --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory"
END_HANDOFF_TO_CURSOR_PILOT
