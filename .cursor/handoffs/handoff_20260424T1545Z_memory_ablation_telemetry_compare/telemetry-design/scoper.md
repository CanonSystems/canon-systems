HANDOFF_TO_CURSOR_PILOT
  scope_summary: Implement the smallest safe ablation-telemetry slice by keeping the canonical event envelope unchanged and introducing a shared additive `payload.comparison` block on experiment-bearing events. Pair that with one new `task_outcome` event emitted from the release-orchestrator contract, then extend `metrics_rollup` and `canon report` so token usage and outcome metrics can be filtered or compared by `memory_mode` and `experiment_id` without breaking existing rollups. This scope intentionally does not touch `.cursor/plans/memory-ablation-parallelism_3dca6a5c.plan.md`, and it keeps compare UX JSON-first rather than trying to redesign every existing CSV/table surface in one task.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260424T1545Z_memory_ablation_telemetry_compare"
      company_id: "CSC"
      repository_id: "canon-systems"
    story:
      title: "Add experiment-aware telemetry and report comparisons"
      userValue: "Canon developers can run the same task set under different memory treatments and compare both cost and outcome metrics from one canonical NDJSON event stream, instead of manually diffing token logs."
      acceptanceCriteria:
        - "Experiment metadata is an additive shared block at `payload.comparison` on experiment-bearing canonical events, with required string keys `experiment_id`, `memory_mode`, `run_id`, and `task_attempt_id`; `CanonicalEvent` stays `schema_version=1` and no envelope fields are added or renamed."
        - "A new canonical event type `task_outcome` is defined and wired into the release-orchestrator contract so one event is emitted per task attempt with `payload.comparison` plus final task-result fields sufficient for reporting: outcome/status, `qa_gate`, `elapsed_seconds`, `retry_count`, `reopen_count`, and `rework_count`."
        - "`metrics_rollup` remains deterministic and backwards-compatible for legacy callers, but also supports experiment-aware filtering/comparison so runs can be compared by `memory_mode` or `experiment_id`; compare output includes token totals plus outcome summaries (tasks seen, completed/ready, QA pass/fail, average elapsed seconds, retry/reopen/rework totals), and events missing comparison metadata are retained under an `unlabeled` bucket instead of being dropped."
        - "`canon report` adds additive compare/filter UX for this slice: `--experiment-id`, `--memory-mode`, and JSON `--compare-by {memory_mode,experiment_id}` on top of the existing CLI. Existing `--by phase|agent|source`, `--full`, and CSV behavior stay unchanged when compare flags are absent."
    repository:
      primaryLanguages: ["Python", "Markdown"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/retrieval_telemetry.py"
        - "src/canon_systems/metrics_rollup.py"
        - "src/canon_systems/report_cli.py"
        - "src/canon_systems/templates/agents/release-orchestrator.md"
        - ".cursor/agents/release-orchestrator.md"
        - "backend/shared/canon_backend_shared/events.py"
        - "tests/test_retrieval_telemetry.py"
        - "tests/test_metrics_rollup.py"
        - "tests/test_cli_report.py"
        - "tests/test_agent_templates.py"
    constraints:
      dependencies:
        - "Keep `backend/shared/canon_backend_shared/events.py` envelope-compatible; all experiment data must live in payload, not top-level event fields."
        - "Preserve `retrieval_breakdown`'s existing `payload.sources` + `payload.totals` contract so current emitters and tests still pass."
        - "Keep `src/canon_systems/metrics_rollup.py` pure-Python, deterministic, stdlib-only, and free of filesystem I/O or event emission."
        - "Keep `src/canon_systems/report_cli.py` additive/backwards-compatible for existing non-experiment usage."
        - "Sync any release-orchestrator template change in both `src/canon_systems/templates/agents/release-orchestrator.md` and `.cursor/agents/release-orchestrator.md`."
        - "Do not edit `.cursor/plans/memory-ablation-parallelism_3dca6a5c.plan.md`."
      mustNotBreak:
        - "Current `canon report --by phase|agent|source` JSON/CSV outputs when no experiment flags are supplied."
        - "Current `canon report --full` rollup shape for callers that do not request comparison mode."
        - "Existing `tests/test_retrieval_telemetry.py`, `tests/test_metrics_rollup.py`, and `tests/test_cli_report.py` expectations unrelated to experiment grouping."
        - "Existing release-orchestrator auto-publish instructions (`canon release publish-on-pass`) and their template assertions."
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "Experiment metadata is an additive shared block at `payload.comparison` on experiment-bearing canonical events, with required string keys `experiment_id`, `memory_mode`, `run_id`, and `task_attempt_id`; `CanonicalEvent` stays `schema_version=1` and no envelope fields are added or renamed."
        implementation_targets: ["src/canon_systems/retrieval_telemetry.py", "backend/shared/canon_backend_shared/events.py"]
        verification_tests: ["tests/test_retrieval_telemetry.py::comparison metadata is additive on retrieval_breakdown and task_outcome builders", "tests/test_retrieval_telemetry.py::CanonicalEvent envelope remains schema_version 1 with unchanged top-level fields"]
      - criterion: "A new canonical event type `task_outcome` is defined and wired into the release-orchestrator contract so one event is emitted per task attempt with `payload.comparison` plus final task-result fields sufficient for reporting: outcome/status, `qa_gate`, `elapsed_seconds`, `retry_count`, `reopen_count`, and `rework_count`."
        implementation_targets: ["src/canon_systems/retrieval_telemetry.py", "src/canon_systems/templates/agents/release-orchestrator.md", ".cursor/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_retrieval_telemetry.py::task_outcome builder produces canonical payload shape", "tests/test_agent_templates.py::release orchestrator template requires task_outcome emission alongside retrieval telemetry"]
      - criterion: "`metrics_rollup` remains deterministic and backwards-compatible for legacy callers, but also supports experiment-aware filtering/comparison so runs can be compared by `memory_mode` or `experiment_id`; compare output includes token totals plus outcome summaries (tasks seen, completed/ready, QA pass/fail, average elapsed seconds, retry/reopen/rework totals), and events missing comparison metadata are retained under an `unlabeled` bucket instead of being dropped."
        implementation_targets: ["src/canon_systems/metrics_rollup.py"]
        verification_tests: ["tests/test_metrics_rollup.py::compare rollup groups by memory_mode", "tests/test_metrics_rollup.py::compare rollup groups by experiment_id", "tests/test_metrics_rollup.py::legacy aggregate output unchanged when compare is absent", "tests/test_metrics_rollup.py::missing comparison metadata falls into unlabeled bucket", "tests/test_metrics_rollup.py::determinism remains byte-identical under compare mode"]
      - criterion: "`canon report` adds additive compare/filter UX for this slice: `--experiment-id`, `--memory-mode`, and JSON `--compare-by {memory_mode,experiment_id}` on top of the existing CLI. Existing `--by phase|agent|source`, `--full`, and CSV behavior stay unchanged when compare flags are absent."
        implementation_targets: ["src/canon_systems/report_cli.py"]
        verification_tests: ["tests/test_cli_report.py::filters by experiment_id and memory_mode", "tests/test_cli_report.py::full compare_by memory_mode emits grouped JSON rollups", "tests/test_cli_report.py::full compare_by experiment_id emits grouped JSON rollups", "tests/test_cli_report.py::legacy by/source and full csv behavior unchanged without compare flags"]
    risks_and_assumptions:
      assumptions:
        - "Scoped against `main` at commit `02dcefec366a079d72e8f4320b8e0e938568927d` with remote `origin=git@github.com:CanonSystems/canon-systems.git`."
        - "Use `payload.comparison` as the single shared schema location because `CanonicalEvent.payload` is already open-ended and this avoids a breaking envelope revision."
        - "`payload.comparison.run_id` is the experiment execution identifier and must remain distinct from envelope `agent_run_id`, which is still phase/agent-run telemetry."
        - "`payload.comparison.task_attempt_id` is the join key between token events and final outcome events for the same task attempt."
        - "`memory_mode` should be treated as an opaque lowercase slug in this task (for example `full`, `no_graph`, `no_state`, `canonical_only`, `file_only`) rather than enforcing a global enum before runtime switches are implemented."
        - "The realistic one-task CLI surface is JSON-first comparison mode; compare-specific CSV/table rendering is intentionally deferred, while existing CSV paths remain intact when compare flags are not used."
        - "Final task-result emission belongs in the release-orchestrator template because that phase already owns final `RELEASE_STATUS` and sees the task-level QA/merge state."
        - "Graph retrieval degraded in this sandbox (`canon graph query` lacked a usable AXON base URL after secret fetch failure), checkpoint read degraded against `http://localhost:8080`, and `canon ask` returned no relevant prior decisions; scope is therefore derived from repo files and existing tests."
      openQuestions: []
    prior_work_references: []
END_HANDOFF_TO_CURSOR_PILOT
