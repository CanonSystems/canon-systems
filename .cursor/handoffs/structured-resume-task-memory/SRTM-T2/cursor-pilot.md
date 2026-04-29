CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Fix top-level `canon resume` flag passthrough so Canon operators can run documented resume sweeps with `canon resume --plan-id ...` directly, without requiring `--` or `python3 -m canon_systems.resume_engine`.
</TASK>

<ACCEPTANCE_CRITERIA>
- Running `canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory` reaches `resume_engine.run(...)` with the documented flags instead of failing in the top-level parser.
- The existing `python3 -m canon_systems.resume_engine --plan-id ...` path remains unchanged.
- Existing top-level passthrough behavior for checkpoint, graph, report, stall-watchdog, vault, synth, and release does not regress.
- Focused pytest coverage proves `canon_systems.cli.main(["resume", "--plan-id", ...])` dispatches without requiring `--`, and preserves the current `--`-separated compatibility case if still supported.
- No documentation changes are made unless the implementation discovers existing docs that explicitly require updating; the desired behavior is already the documented behavior.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: CSC
- repository_id: canon-systems
- handoff_id: structured-resume-task-memory
- plan_id: structured-resume-task-memory
- task_id: SRTM-T2
- workstream_id: ws-main
- prior_work_references:
  - artifact_id: art_memcap_20260429T150239Z_usr_new.moon3461; source: canonical; relevance: Recent session memory context for structured resume/task memory release-gate work.
  - artifact_id: art_memcap_20260429T142810Z_usr_new.moon3461; source: canonical; relevance: Recent session memory context adjacent to SRTM-T1/SRTM-T2 workflow stabilization.
- retrieval_notes:
  - graph: degraded; `canon graph query` and `canon graph impact` exited 2 because AWS credentials/AXON_SERVICE_URL were unavailable.
  - state: degraded; `canon checkpoint read` exited 5 because local state-api at localhost:8080 refused the connection.
  - canonical: used `.canon/memory/context-latest.md` and scoper prior_work_references.
  - file: inspected `src/canon_systems/cli.py`, `src/canon_systems/resume_engine.py`, `tests/test_resume_engine.py`, and nearby CLI passthrough tests.
</CONTEXT>

<REPOSITORY>
- primaryLanguages: Python, Markdown, Terraform, Shell
- testFramework: pytest
- relevantFiles:
  - src/canon_systems/cli.py
  - src/canon_systems/resume_engine.py
  - tests/test_resume_engine.py
  - tests/test_cli_checkpoint.py
  - tests/test_cli_report.py
  - tests/test_cli_synth_show.py
  - tests/test_cli_synth_publish.py
  - tests/test_vault_sync.py
  - tests/test_release_publish.py
- mustNotBreak:
  - Do not require users to insert `--` before documented `canon resume` flags.
  - Do not regress passthrough command tails for `checkpoint`, `graph`, `report`, `stall-watchdog`, `vault`, `synth`, or `release`.
  - Do not include unrelated dirty files or generated memory/cache artifacts.
- downstream_blast_radius:
  - `canon_systems.cli.main` is the console-script entrypoint from `pyproject.toml`; preserve `--repo-root`, setup/self-update/rewire side effects, and command dispatch order.
  - `resume_engine.run` already owns resume flags; do not duplicate its full parser in `cli.py`.
</REPOSITORY>

<REASONING>
The failure is in `src/canon_systems/cli.py`: passthrough subcommands are modeled with `argparse.REMAINDER`, but leading option flags after a subcommand can be rejected by the top-level parser before the child command receives them. Implement a narrowly scoped passthrough dispatch path for commands such as `resume`, preserving global option handling and existing setup/self-update/rewire behavior, then call `run_resume_engine` with the normalized tail. Preserve compatibility for the existing `resume -- --plan-id ...` test case, preferably by treating a single leading `--` as an optional separator before forwarding to the child parser. Do not change `src/canon_systems/resume_engine.py` unless tests reveal an actual module-entry regression.

AC traceability:
- AC1 maps to `src/canon_systems/cli.py` and `tests/test_resume_engine.py::test_canon_cli_dispatches_resume_args_without_separator`.
- AC2 maps to preserving `src/canon_systems/resume_engine.py` behavior and running direct module or resume-engine tests.
- AC3 maps to `src/canon_systems/cli.py` plus nearby passthrough regression suites for checkpoint, graph, report, stall-watchdog, vault, synth, and release.
- AC4 maps to focused `canon_systems.cli.main([...])` tests in `tests/test_resume_engine.py`.
- AC5 maps to avoiding docs edits unless implementation discovers a real contradiction.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Fix top-level resume passthrough and add focused resume dispatch tests."
    acceptance_criteria:
      - "Running `canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory` reaches `resume_engine.run(...)` with the documented flags instead of failing in the top-level parser."
      - "The existing `python3 -m canon_systems.resume_engine --plan-id ...` path remains unchanged."
      - "Focused pytest coverage proves `canon_systems.cli.main([\"resume\", \"--plan-id\", ...])` dispatches without requiring `--`, and preserves the current `--`-separated compatibility case if still supported."
    implementation_targets:
      - "src/canon_systems/cli.py"
      - "tests/test_resume_engine.py"
    verification_tests:
      - "tests/test_resume_engine.py::test_canon_cli_dispatches_resume_args_without_separator"
      - "tests/test_resume_engine.py::test_canon_cli_dispatches_resume_lanes_args"
      - "python -m pytest tests/test_resume_engine.py -q"
    depends_on: []
    can_run_parallel: false
  - id: "ws2"
    goal: "Prove nearby passthrough commands still dispatch correctly."
    acceptance_criteria:
      - "Existing top-level passthrough behavior for checkpoint, graph, report, stall-watchdog, vault, synth, and release does not regress."
      - "No documentation changes are made unless the implementation discovers existing docs that explicitly require updating; the desired behavior is already the documented behavior."
    implementation_targets:
      - "src/canon_systems/cli.py"
      - "tests/test_cli_checkpoint.py"
      - "tests/test_cli_report.py"
      - "tests/test_cli_synth_show.py"
      - "tests/test_cli_synth_publish.py"
      - "tests/test_vault_sync.py"
      - "tests/test_release_publish.py"
    verification_tests:
      - "python -m pytest tests/test_cli_checkpoint.py tests/test_cli_report.py tests/test_cli_synth_show.py tests/test_cli_synth_publish.py tests/test_vault_sync.py tests/test_release_publish.py -q"
      - "git diff --name-only -- docs"
    depends_on: ["ws1"]
    can_run_parallel: false
- parent_orchestration:
  - "Launch one `implementer` subagent per workstream marked can_run_parallel=true in a single parallel subagent call."
  - "Pin each coding subagent to `composer-2-fast`."
  - "For dependent streams, execute only after required upstream streams complete."
  - "After all workstreams finish, merge shard outputs into one HANDOFF_TO_QA block for qa-gate."
- execution_waves_example:
  - wave: 1
    stream_ids: ["ws1"]
  - wave: 2
    stream_ids: ["ws2"]
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the code changes needed to satisfy all acceptance criteria, plus
tests that cover each. Do not refactor unrelated code.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
When running a single implementation stream, emit this block verbatim (filled
in):

HANDOFF_TO_QA
  handoff_id: "structured-resume-task-memory"
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
  handoff_id: "structured-resume-task-memory"
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
