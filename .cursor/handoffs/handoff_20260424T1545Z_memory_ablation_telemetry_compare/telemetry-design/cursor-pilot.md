CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Add experiment-aware telemetry and report comparisons so Canon developers can run the same task set under different memory treatments and compare cost and outcome metrics from one canonical NDJSON stream instead of manually diffing token logs.
</TASK>

<ACCEPTANCE_CRITERIA>
- Experiment metadata is an additive shared block at `payload.comparison` on experiment-bearing canonical events, with required string keys `experiment_id`, `memory_mode`, `run_id`, and `task_attempt_id`; `CanonicalEvent` stays `schema_version=1` and no envelope fields are added or renamed.
- A new canonical event type `task_outcome` is defined and wired into the release-orchestrator contract so one event is emitted per task attempt with `payload.comparison` plus final task-result fields sufficient for reporting: outcome/status, `qa_gate`, `elapsed_seconds`, `retry_count`, `reopen_count`, and `rework_count`.
- `metrics_rollup` remains deterministic and backwards-compatible for legacy callers, but also supports experiment-aware filtering/comparison so runs can be compared by `memory_mode` or `experiment_id`; compare output includes token totals plus outcome summaries (tasks seen, completed/ready, QA pass/fail, average elapsed seconds, retry/reopen/rework totals), and events missing comparison metadata are retained under an `unlabeled` bucket instead of being dropped.
- `canon report` adds additive compare/filter UX for this slice: `--experiment-id`, `--memory-mode`, and JSON `--compare-by {memory_mode,experiment_id}` on top of the existing CLI. Existing `--by phase|agent|source`, `--full`, and CSV behavior stay unchanged when compare flags are absent.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: CSC
- repository_id: canon-systems
- prior_work_references: []
</CONTEXT>

<REPOSITORY>
- primaryLanguages: ["Python", "Markdown"]
- testFramework: pytest
- relevantFiles:
  - src/canon_systems/retrieval_telemetry.py
  - src/canon_systems/metrics_rollup.py
  - src/canon_systems/report_cli.py
  - src/canon_systems/templates/agents/release-orchestrator.md
  - .cursor/agents/release-orchestrator.md
  - backend/shared/canon_backend_shared/events.py
  - tests/test_retrieval_telemetry.py
  - tests/test_metrics_rollup.py
  - tests/test_cli_report.py
  - tests/test_agent_templates.py
- mustNotBreak:
  - Current `canon report --by phase|agent|source` JSON/CSV outputs when no experiment flags are supplied.
  - Current `canon report --full` rollup shape for callers that do not request comparison mode.
  - Existing `tests/test_retrieval_telemetry.py`, `tests/test_metrics_rollup.py`, and `tests/test_cli_report.py` expectations unrelated to experiment grouping.
  - Existing release-orchestrator auto-publish instructions (`canon release publish-on-pass`) and their template assertions.
- downstreamTouchpoints:
  - src/canon_systems/synth_cli.py
  - src/canon_systems/report_cli.py
  - tests/test_retrieval_telemetry.py
  - tests/test_metrics_rollup.py
  - tests/test_cli_report.py
  - tests/test_agent_templates.py
- notes:
  - Graph retrieval degraded during planning (`canon graph query` failed after AWS secret fetch failure and missing `AXON_SERVICE_URL`), so no live `canon graph impact` upstream/downstream map was available.
  - State retrieval degraded during planning (`canon checkpoint read` returned transport error against `http://localhost:8080`), so no checkpoint hydration data was available.
  - Canonical retrieval was not useful for this task (`canon ask` returned no relevant repo decisions, and `.canon/memory/context-latest.md` was scoped to another repo), so the target surface is grounded in the scoper packet plus direct repo evidence.
</REPOSITORY>

<REASONING>
Use `src/canon_systems/retrieval_telemetry.py` together with `backend/shared/canon_backend_shared/events.py` to keep the canonical envelope unchanged while introducing a shared additive `payload.comparison` block for experiment-bearing events and a `task_outcome` canonical event builder. Update both release-orchestrator templates so the final orchestration phase emits one `task_outcome` per task attempt without disturbing the existing `canon release publish-on-pass` contract or its template assertions. In parallel, extend `src/canon_systems/metrics_rollup.py` to aggregate, filter, and compare by `memory_mode` and `experiment_id`, preserving the legacy no-compare output shape and determinism while retaining unlabeled events under an `unlabeled` bucket and joining token events to task outcomes through `payload.comparison.task_attempt_id`. After that contract is stable, wire `src/canon_systems/report_cli.py` to expose additive `--experiment-id`, `--memory-mode`, and JSON `--compare-by` flags while keeping existing `--by`, `--full`, and CSV behavior unchanged when compare mode is absent. Cover AC1 and AC2 with `tests/test_retrieval_telemetry.py` plus `tests/test_agent_templates.py`, AC3 with `tests/test_metrics_rollup.py`, and AC4 with `tests/test_cli_report.py`, following the `ac_traceability` mapping exactly. Preserve `payload.sources` + `payload.totals`, keep `memory_mode` as an opaque lowercase slug, and keep `payload.comparison.run_id` distinct from envelope `agent_run_id`.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Add shared comparison metadata and task_outcome emission contract."
    acceptance_criteria:
      - "Experiment metadata is an additive shared block at `payload.comparison` on experiment-bearing canonical events, with required string keys `experiment_id`, `memory_mode`, `run_id`, and `task_attempt_id`; `CanonicalEvent` stays `schema_version=1` and no envelope fields are added or renamed."
      - "A new canonical event type `task_outcome` is defined and wired into the release-orchestrator contract so one event is emitted per task attempt with `payload.comparison` plus final task-result fields sufficient for reporting: outcome/status, `qa_gate`, `elapsed_seconds`, `retry_count`, `reopen_count`, and `rework_count`."
    implementation_targets:
      - "src/canon_systems/retrieval_telemetry.py"
      - "backend/shared/canon_backend_shared/events.py"
      - "src/canon_systems/templates/agents/release-orchestrator.md"
      - ".cursor/agents/release-orchestrator.md"
    verification_tests:
      - "tests/test_retrieval_telemetry.py::comparison metadata is additive on retrieval_breakdown and task_outcome builders"
      - "tests/test_retrieval_telemetry.py::CanonicalEvent envelope remains schema_version 1 with unchanged top-level fields"
      - "tests/test_retrieval_telemetry.py::task_outcome builder produces canonical payload shape"
      - "tests/test_agent_templates.py::release orchestrator template requires task_outcome emission alongside retrieval telemetry"
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Extend deterministic metrics rollup with experiment-aware comparison and unlabeled retention."
    acceptance_criteria:
      - "`metrics_rollup` remains deterministic and backwards-compatible for legacy callers, but also supports experiment-aware filtering/comparison so runs can be compared by `memory_mode` or `experiment_id`; compare output includes token totals plus outcome summaries (tasks seen, completed/ready, QA pass/fail, average elapsed seconds, retry/reopen/rework totals), and events missing comparison metadata are retained under an `unlabeled` bucket instead of being dropped."
    implementation_targets:
      - "src/canon_systems/metrics_rollup.py"
    verification_tests:
      - "tests/test_metrics_rollup.py::compare rollup groups by memory_mode"
      - "tests/test_metrics_rollup.py::compare rollup groups by experiment_id"
      - "tests/test_metrics_rollup.py::legacy aggregate output unchanged when compare is absent"
      - "tests/test_metrics_rollup.py::missing comparison metadata falls into unlabeled bucket"
      - "tests/test_metrics_rollup.py::determinism remains byte-identical under compare mode"
    depends_on: []
    can_run_parallel: true
  - id: "ws3"
    goal: "Add additive report CLI compare/filter flags on top of the new rollup contract."
    acceptance_criteria:
      - "`canon report` adds additive compare/filter UX for this slice: `--experiment-id`, `--memory-mode`, and JSON `--compare-by {memory_mode,experiment_id}` on top of the existing CLI. Existing `--by phase|agent|source`, `--full`, and CSV behavior stay unchanged when compare flags are absent."
    implementation_targets:
      - "src/canon_systems/report_cli.py"
    verification_tests:
      - "tests/test_cli_report.py::filters by experiment_id and memory_mode"
      - "tests/test_cli_report.py::full compare_by memory_mode emits grouped JSON rollups"
      - "tests/test_cli_report.py::full compare_by experiment_id emits grouped JSON rollups"
      - "tests/test_cli_report.py::legacy by/source and full csv behavior unchanged without compare flags"
    depends_on: ["ws2"]
    can_run_parallel: false
- parent_orchestration:
  - "Launch one `implementer` subagent per workstream marked can_run_parallel=true in a single parallel subagent call."
  - "Pin each coding subagent to `composer-2-fast`."
  - "For dependent streams, execute only after required upstream streams complete."
  - "After all workstreams finish, merge shard outputs into one HANDOFF_TO_QA block for qa-gate."
- execution_waves_example:
  - wave: 1
    stream_ids: ["ws1", "ws2"]
  - wave: 2
    stream_ids: ["ws3"]
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the code changes needed to satisfy all acceptance criteria, plus
tests that cover each. Do not refactor unrelated code.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
When running a single implementation stream, emit this block verbatim (filled
in):

HANDOFF_TO_QA
  handoff_id: "handoff_20260424T1545Z_memory_ablation_telemetry_compare"
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
  handoff_id: "handoff_20260424T1545Z_memory_ablation_telemetry_compare"
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
