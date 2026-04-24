CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Add the smallest safe experimental multilane `canon resume` and orchestration-policy slice so parent orchestrators can see and schedule multiple runnable task lanes from enriched task manifests without changing the legacy serial resume path, checkpoint truth model, or artifact-backed release discipline.
</TASK>

<ACCEPTANCE_CRITERIA>
- `canon resume` gains an additive experimental lanes mode that accepts enriched `--tasks-file` entries with optional `depends_on`, `parallel_group`, and `can_run_parallel`, returns explicit multi-lane visibility (`runnable_targets`, `active_targets`, `blocked_targets`, `task_threads`), and preserves current `resume_target`/exit-code behavior when lanes mode is not requested.
- The scheduler derives lane state from existing per-task checkpoints plus manifest metadata only; this task does not change `state-api` schemas, checkpoint write flags, or the canonical 5-phase checkpoint contract.
- Operator-facing docs and agent templates explicitly describe experimental parent-session multi-lane orchestration, including when to use enriched `--tasks-file` lane manifests versus legacy `--handoffs-dir`, and they keep merge/PR advancement artifact-backed and per-task.
- The hard-lock build-discipline rule is updated only behind an explicit experimental multilane opt-in, while the current canon-memory-v1 serial protections, packaged/workspace byte-identity guarantees, and release-gate strictness remain intact.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: CSC
- repository_id: canon-systems
- prior_work_references:
  - none
</CONTEXT>

<REPOSITORY>
- primaryLanguages: ["Python", "Markdown", "HCL"]
- testFramework: pytest
- relevantFiles:
  - src/canon_systems/resume_engine.py
  - src/canon_systems/cli.py
  - src/canon_systems/task_thread_scheduler.py
  - tests/test_resume_engine.py
  - tests/test_task_thread_scheduler.py
  - tests/test_checkpoint_concurrency.py
  - src/canon_systems/templates/agents/release-orchestrator.md
  - .cursor/agents/release-orchestrator.md
  - src/canon_systems/templates/agents/project-planner.md
  - .cursor/agents/project-planner.md
  - src/canon_systems/templates/rules/memory-platform-build-discipline.mdc
  - .cursor/rules/memory-platform-build-discipline.mdc
  - tests/test_agent_templates.py
  - tests/test_wire_distribution.py
  - docs/runbooks/RESUME.md
  - docs/SYSTEM-WORKFLOW.md
  - docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md
  - README.md
  - CHANGELOG.md
- mustNotBreak:
  - Legacy `canon resume --handoffs-dir ...` serial behavior remains deterministic and idempotent
  - Current 5-phase order `scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator` remains the checkpoint truth model
  - No `state-api` backend/model change in this slice
  - No weakening of canon-memory-v1 serial hard lock unless an explicit experimental opt-in is present
  - Existing release merge gate still blocks until incomplete tasks are resolved
  - Packaged/workspace hard-lock rule and release template remain byte-identical where tests require it
  - Respect existing dirty-tree edits in tracked `.cursor/` files by making additive changes only
- downstreamTouchpoints:
  - `canon resume` is dispatched from `src/canon_systems/cli.py`
  - `release-orchestrator` currently interprets only `resume_target` / `resume_available` / `degraded_tasks`
  - `docs/runbooks/RESUME.md` and `docs/SYSTEM-WORKFLOW.md` describe the current single-target resume contract
  - `tests/test_agent_templates.py` locks packaged template wording and workspace sync
  - `tests/test_wire_distribution.py` locks byte-identical packaged/workspace hard-lock rule distribution
- notes:
  - Graph retrieval degraded during planning: `canon graph query` failed after secret-hydration proxy errors and missing `AXON_SERVICE_URL`, so no live `canon graph impact` upstream/downstream map was available.
  - State retrieval was not trustworthy from the packet alone because it omits the checkpoint-hydration identifiers `plan_id` and `workstream_id`; do not guess them when implementing.
  - Canonical retrieval was low-signal here: `.canon/memory/context-latest.md` was scoped to another repo and `canon ask` returned no task-specific prior decisions, so the target surface is grounded in the scoper packet plus direct repo evidence.
</REPOSITORY>

<REASONING>
Scope against `main@02dcefec366a079d72e8f4320b8e0e938568927d` exactly as the packet assumes. Today `src/canon_systems/resume_engine.py` only parses `task_id` + `workstream_id` entries from `--tasks-file` and emits a single `resume_target`; there is no existing `src/canon_systems/task_thread_scheduler.py` or `tests/test_task_thread_scheduler.py`, so the smallest safe implementation is to add a pure scheduler surface that reads enriched manifest metadata (`depends_on`, `parallel_group`, `can_run_parallel`) and combines it with existing checkpoint `(phase, phase_status)` reads to classify runnable, active, and blocked task lanes without any new state writes or schema changes. Then extend `resume_engine.py` and `src/canon_systems/cli.py` additively so lanes mode is explicit and opt-in, only affects the enriched `--tasks-file` path, returns the extra envelope fields (`runnable_targets`, `active_targets`, `blocked_targets`, `task_threads`), and still preserves the legacy `resume_target` JSON shape, sort-order determinism, and exit-code behavior when the flag is absent. After the core contract is stable, update release/project-planner templates plus operator docs (`docs/runbooks/RESUME.md`, `docs/SYSTEM-WORKFLOW.md`, `docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md`, `README.md`, `CHANGELOG.md`) to explain experimental multilane parent-session orchestration versus legacy `--handoffs-dir` serial discovery, while keeping merge/PR advancement per-task and artifact-backed. Finally, update the packaged and workspace hard-lock rule pair together behind an explicit experimental opt-in guard, preserving byte identity and current canon-memory-v1 serial wording by design. Follow `ac_traceability` exactly: AC1 maps to `resume_engine.py` + new scheduler file + CLI + `tests/test_resume_engine.py` / `tests/test_task_thread_scheduler.py`; AC2 maps to scheduler/resume code plus `tests/test_checkpoint_concurrency.py`; AC3 maps to agent templates/docs plus `tests/test_agent_templates.py`; AC4 maps to packaged/workspace rule files plus `tests/test_wire_distribution.py`, with any hard-lock wording assertion consolidated into `tests/test_agent_templates.py` to avoid duplicate ownership of that file across parallel streams.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Add the experimental multilane scheduler contract and resume-engine envelope without changing legacy serial behavior."
    acceptance_criteria:
      - "`canon resume` gains an additive experimental lanes mode that accepts enriched `--tasks-file` entries with optional `depends_on`, `parallel_group`, and `can_run_parallel`, returns explicit multi-lane visibility (`runnable_targets`, `active_targets`, `blocked_targets`, `task_threads`), and preserves current `resume_target`/exit-code behavior when lanes mode is not requested."
      - "The scheduler derives lane state from existing per-task checkpoints plus manifest metadata only; this task does not change `state-api` schemas, checkpoint write flags, or the canonical 5-phase checkpoint contract."
    implementation_targets:
      - "src/canon_systems/task_thread_scheduler.py"
      - "src/canon_systems/resume_engine.py"
      - "src/canon_systems/cli.py"
      - "tests/test_task_thread_scheduler.py"
      - "tests/test_resume_engine.py"
    verification_tests:
      - "tests/test_task_thread_scheduler.py::dependency and parallel-group ready-set computation"
      - "tests/test_resume_engine.py::lanes mode emits runnable/active/blocked/task_threads envelope"
      - "tests/test_resume_engine.py::legacy next-mode output and exit codes stay unchanged without lanes flag"
      - "tests/test_resume_engine.py::enriched tasks-file entries are optional and backward compatible"
      - "tests/test_resume_engine.py::lanes mode with dependency metadata uses checkpoint phase/phase_status only"
      - "tests/test_checkpoint_concurrency.py::pre-existing checkpoint contract remains green"
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Document and template the experimental multilane parent-session policy while keeping release advancement per-task and artifact-backed."
    acceptance_criteria:
      - "Operator-facing docs and agent templates explicitly describe experimental parent-session multi-lane orchestration, including when to use enriched `--tasks-file` lane manifests versus legacy `--handoffs-dir`, and they keep merge/PR advancement artifact-backed and per-task."
      - "The hard-lock build-discipline rule is updated only behind an explicit experimental multilane opt-in, while the current canon-memory-v1 serial protections, packaged/workspace byte-identity guarantees, and release-gate strictness remain intact."
    implementation_targets:
      - "src/canon_systems/templates/agents/release-orchestrator.md"
      - ".cursor/agents/release-orchestrator.md"
      - "src/canon_systems/templates/agents/project-planner.md"
      - ".cursor/agents/project-planner.md"
      - "docs/runbooks/RESUME.md"
      - "docs/SYSTEM-WORKFLOW.md"
      - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
      - "README.md"
      - "CHANGELOG.md"
      - "tests/test_agent_templates.py"
    verification_tests:
      - "tests/test_agent_templates.py::release template mentions experimental multilane resume flow"
      - "tests/test_agent_templates.py::project planner documents parallel-group consumption for multilane orchestration"
      - "tests/test_agent_templates.py::resume runbook covers lanes-mode invocation and legacy fallback"
      - "tests/test_agent_templates.py::hard-lock rule preserves serial canon-memory-v1 wording and adds explicit experimental multilane opt-in guard"
    depends_on: ["ws1"]
    can_run_parallel: true
  - id: "ws3"
    goal: "Add the explicit experimental opt-in guard to the packaged and workspace hard-lock rule pair while preserving byte identity."
    acceptance_criteria:
      - "The hard-lock build-discipline rule is updated only behind an explicit experimental multilane opt-in, while the current canon-memory-v1 serial protections, packaged/workspace byte-identity guarantees, and release-gate strictness remain intact."
    implementation_targets:
      - "src/canon_systems/templates/rules/memory-platform-build-discipline.mdc"
      - ".cursor/rules/memory-platform-build-discipline.mdc"
      - "tests/test_wire_distribution.py"
    verification_tests:
      - "tests/test_wire_distribution.py::template and workspace rule stay byte-identical after update"
    depends_on: ["ws1"]
    can_run_parallel: true
- parent_orchestration:
  - "Launch one `implementer` subagent per workstream marked can_run_parallel=true in a single parallel subagent call."
  - "Pin each coding subagent to `composer-2-fast`."
  - "For dependent streams, execute only after required upstream streams complete."
  - "After all workstreams finish, merge shard outputs into one HANDOFF_TO_QA block for qa-gate."
- execution_waves_example:
  - wave: 1
    stream_ids: ["ws1"]
  - wave: 2
    stream_ids: ["ws2", "ws3"]
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the code changes needed to satisfy all acceptance criteria, plus
tests that cover each. Do not refactor unrelated code.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
When running a single implementation stream, emit this block verbatim (filled
in):

HANDOFF_TO_QA
  handoff_id: "handoff_20260424T1700Z_multilane_scheduler_resume_policy"
  acceptance_criteria_covered:
    - criterion: "<exact AC text>"
      evidence_files:
        - "path/to/impl.ext:<line range>"
      evidence_tests:
        - "path/to/test.ext::<test name>"
  summary: "<1-2 sentences on what changed>"
  decisions:
    - "<notable design decision made during implementation>"
  next_actions:
    - "<follow-up work explicitly deferred>"
  open_questions:
    - "<anything still unclear that QA should verify>"
END_HANDOFF_TO_QA

When running multiple parallel streams, each implementer must emit:

HANDOFF_TO_QA_SHARD
  handoff_id: "handoff_20260424T1700Z_multilane_scheduler_resume_policy"
  shard_id: "<workstream id>"
  acceptance_criteria_covered:
    - criterion: "<exact AC text>"
      evidence_files:
        - "path/to/impl.ext:<line range>"
      evidence_tests:
        - "path/to/test.ext::<test name>"
  summary: "<1 sentence on this shard's changes>"
END_HANDOFF_TO_QA_SHARD

Parent must aggregate all shard outputs into one final `HANDOFF_TO_QA` before
invoking `qa-gate`.

Do not declare the task complete without the required handoff block(s).
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
