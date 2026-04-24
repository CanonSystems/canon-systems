HANDOFF_TO_CURSOR_PILOT
  scope_summary: Implement the smallest safe multilane slice by making `canon resume` capable of computing an experimental parent-session lane view from an enriched task manifest, while preserving the existing single-target resume behavior for legacy callers. Keep state and checkpoint storage additive by deriving lane status from existing per-task checkpoints plus planner metadata (`depends_on`, `parallel_group`, `can_run_parallel`), and update the release/template/rule/docs layer so this mode is explicit, opt-in, and still conservative for the existing memory-platform-v1 hard lock.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260424T1700Z_multilane_scheduler_resume_policy"
      company_id: "CSC"
      repository_id: "canon-systems"
    story:
      title: "Add experimental multilane resume and orchestration policy"
      userValue: "Parent orchestrators can safely see and schedule multiple runnable task lanes in one session without losing deterministic artifact/state control, while existing serial workflows keep working unchanged."
      acceptanceCriteria:
        - "`canon resume` gains an additive experimental lanes mode that accepts enriched `--tasks-file` entries with optional `depends_on`, `parallel_group`, and `can_run_parallel`, returns explicit multi-lane visibility (`runnable_targets`, `active_targets`, `blocked_targets`, `task_threads`), and preserves current `resume_target`/exit-code behavior when lanes mode is not requested."
        - "The scheduler derives lane state from existing per-task checkpoints plus manifest metadata only; this task does not change `state-api` schemas, checkpoint write flags, or the canonical 5-phase checkpoint contract."
        - "Operator-facing docs and agent templates explicitly describe experimental parent-session multi-lane orchestration, including when to use enriched `--tasks-file` lane manifests versus legacy `--handoffs-dir`, and they keep merge/PR advancement artifact-backed and per-task."
        - "The hard-lock build-discipline rule is updated only behind an explicit experimental multilane opt-in, while the current canon-memory-v1 serial protections, packaged/workspace byte-identity guarantees, and release-gate strictness remain intact."
    repository:
      primaryLanguages: ["Python", "Markdown", "HCL"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/resume_engine.py"
        - "src/canon_systems/cli.py"
        - "src/canon_systems/task_thread_scheduler.py"
        - "tests/test_resume_engine.py"
        - "tests/test_task_thread_scheduler.py"
        - "src/canon_systems/templates/agents/release-orchestrator.md"
        - ".cursor/agents/release-orchestrator.md"
        - "src/canon_systems/templates/agents/project-planner.md"
        - ".cursor/agents/project-planner.md"
        - "src/canon_systems/templates/rules/memory-platform-build-discipline.mdc"
        - ".cursor/rules/memory-platform-build-discipline.mdc"
        - "tests/test_agent_templates.py"
        - "tests/test_wire_distribution.py"
        - "docs/runbooks/RESUME.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "README.md"
        - "CHANGELOG.md"
    constraints:
      dependencies: ["Existing `resume_engine` JSON/exit-code contract", "Existing `checkpoint_cli`/`state-api` checkpoint schema and whitelisted extra fields", "Planner-emitted `depends_on`/`can_run_parallel`/`parallel_group` fields in `project-planner`", "Release-orchestrator merge-gate dependency on `canon resume`", "Workspace/template byte-identity tests for release template and hard-lock rule", "Do not edit `.cursor/plans/memory-ablation-parallelism_3dca6a5c.plan.md`"]
      mustNotBreak: ["Legacy `canon resume --handoffs-dir ...` serial behavior remains deterministic and idempotent", "Current 5-phase order `scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator` remains the checkpoint truth model", "No `state-api` backend/model change in this slice", "No weakening of canon-memory-v1 serial hard lock unless an explicit experimental opt-in is present", "Existing release merge gate still blocks until incomplete tasks are resolved", "Packaged/workspace hard-lock rule and release template remain byte-identical where tests require it", "Respect existing dirty-tree edits in tracked `.cursor/` files by making additive changes only"]
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "`canon resume` gains an additive experimental lanes mode that accepts enriched `--tasks-file` entries with optional `depends_on`, `parallel_group`, and `can_run_parallel`, returns explicit multi-lane visibility (`runnable_targets`, `active_targets`, `blocked_targets`, `task_threads`), and preserves current `resume_target`/exit-code behavior when lanes mode is not requested."
        implementation_targets: ["src/canon_systems/resume_engine.py", "src/canon_systems/task_thread_scheduler.py", "src/canon_systems/cli.py"]
        verification_tests: ["tests/test_task_thread_scheduler.py::dependency and parallel-group ready-set computation", "tests/test_resume_engine.py::lanes mode emits runnable/active/blocked/task_threads envelope", "tests/test_resume_engine.py::legacy next-mode output and exit codes stay unchanged without lanes flag"]
      - criterion: "The scheduler derives lane state from existing per-task checkpoints plus manifest metadata only; this task does not change `state-api` schemas, checkpoint write flags, or the canonical 5-phase checkpoint contract."
        implementation_targets: ["src/canon_systems/task_thread_scheduler.py", "src/canon_systems/resume_engine.py"]
        verification_tests: ["tests/test_resume_engine.py::enriched tasks-file entries are optional and backward compatible", "tests/test_resume_engine.py::lanes mode with dependency metadata uses checkpoint phase/phase_status only", "tests/test_checkpoint_concurrency.py::pre-existing checkpoint contract remains green"]
      - criterion: "Operator-facing docs and agent templates explicitly describe experimental parent-session multi-lane orchestration, including when to use enriched `--tasks-file` lane manifests versus legacy `--handoffs-dir`, and they keep merge/PR advancement artifact-backed and per-task."
        implementation_targets: ["src/canon_systems/templates/agents/release-orchestrator.md", ".cursor/agents/release-orchestrator.md", "src/canon_systems/templates/agents/project-planner.md", ".cursor/agents/project-planner.md", "docs/runbooks/RESUME.md", "docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "README.md", "CHANGELOG.md"]
        verification_tests: ["tests/test_agent_templates.py::release template mentions experimental multilane resume flow", "tests/test_agent_templates.py::project planner documents parallel-group consumption for multilane orchestration", "tests/test_agent_templates.py::resume runbook covers lanes-mode invocation and legacy fallback"]
      - criterion: "The hard-lock build-discipline rule is updated only behind an explicit experimental multilane opt-in, while the current canon-memory-v1 serial protections, packaged/workspace byte-identity guarantees, and release-gate strictness remain intact."
        implementation_targets: ["src/canon_systems/templates/rules/memory-platform-build-discipline.mdc", ".cursor/rules/memory-platform-build-discipline.mdc", "tests/test_wire_distribution.py", "tests/test_agent_templates.py"]
        verification_tests: ["tests/test_wire_distribution.py::template and workspace rule stay byte-identical after update", "tests/test_agent_templates.py::hard-lock rule preserves serial canon-memory-v1 wording and adds explicit experimental multilane opt-in guard"]
    risks_and_assumptions:
      assumptions: ["Scope against `main@02dcefec366a079d72e8f4320b8e0e938568927d` with `origin` = `git@github.com:CanonSystems/canon-systems.git`.", "Smallest safe slice is read-only scheduling/visibility plus docs/rules/templates; it does not add new parent write/claim/advance CLIs.", "Experimental multilane mode should require enriched `--tasks-file` metadata; plain `--handoffs-dir` remains the legacy serial discovery path.", "Lane status can be represented without new state storage by combining manifest dependency metadata with existing checkpoint `(phase, phase_status)` reads.", "Policy updates should explicitly keep canon-memory-v1 serial unless a separate plan/runtime opt-in enables multilane behavior."]
      openQuestions: []
    prior_work_references: []
END_HANDOFF_TO_CURSOR_PILOT
