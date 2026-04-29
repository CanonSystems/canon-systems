HANDOFF_TO_QA
  handoff_id: "structured-resume-task-memory"
  plan_id: "structured-resume-task-memory"
  task_id: "SRTM-T2"
  workstream_id: "ws-main"
  acceptance_criteria_covered:
    - criterion: "Running `canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory` reaches `resume_engine.run(...)` with the documented flags instead of failing in the top-level parser."
      evidence_files:
        - "src/canon_systems/cli.py:131-157"
        - "src/canon_systems/cli.py:460-474"
      evidence_tests:
        - "tests/test_resume_engine.py::test_canon_cli_dispatches_resume_args_without_separator"
        - "manual::canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory"
    - criterion: "The existing `python3 -m canon_systems.resume_engine --plan-id ...` path remains unchanged."
      evidence_files:
        - "src/canon_systems/resume_engine.py:no edits"
      evidence_tests:
        - "python3 -m canon_systems.resume_engine --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory"
        - "python3 -m pytest tests/test_resume_engine.py -q"
    - criterion: "Existing top-level passthrough behavior for checkpoint, graph, report, stall-watchdog, vault, synth, and release does not regress."
      evidence_files:
        - "src/canon_systems/cli.py:376-419"
        - "src/canon_systems/cli.py:665-689"
      evidence_tests:
        - "python3 -m pytest tests/test_cli_checkpoint.py tests/test_cli_report.py tests/test_cli_synth_show.py tests/test_cli_synth_publish.py tests/test_vault_sync.py tests/test_release_publish.py -q"
        - "python3 -m pytest tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help tests/test_stall_watchdog.py::test_cli_wiring_passes_args_to_subcommand -q"
    - criterion: "Focused pytest coverage proves `canon_systems.cli.main([\"resume\", \"--plan-id\", ...])` dispatches without requiring `--`, and preserves the current `--`-separated compatibility case if still supported."
      evidence_files:
        - "tests/test_resume_engine.py:474-534"
      evidence_tests:
        - "tests/test_resume_engine.py::test_canon_cli_dispatches_resume_args_without_separator"
        - "tests/test_resume_engine.py::test_canon_cli_dispatches_resume_lanes_args"
    - criterion: "No documentation changes are made unless the implementation discovers existing docs that explicitly require updating; the desired behavior is already the documented behavior."
      evidence_files:
        - "src/canon_systems/cli.py:131-157"
        - "tests/test_resume_engine.py:474-534"
      evidence_tests:
        - "git diff --name-only -- docs (shows only pre-existing SRTM-T1 documentation changes, no SRTM-T2 docs edits)"
  summary: "SRTM-T2 adds a top-level `canon resume` fast-path that forwards documented resume flags to `resume_engine.run` before argparse rejects them, while preserving optional `resume -- ...` compatibility. Focused and nearby CLI passthrough regression tests pass."
  decisions:
    - "Do not duplicate the resume parser in `cli.py`; detect the `resume` subcommand at the Canon CLI boundary and forward the tail to `resume_engine.run`."
    - "Strip a single optional `--` after `resume` to preserve existing separator compatibility."
  next_actions:
    - "Run qa-gate for SRTM-T2."
    - "Rerun SRTM-T1 release gates after SRTM-T2 is integrated so the resume pre-merge sweep blocker can clear."
  open_questions: []
  commands_run:
    - "python3 -m pytest tests/test_resume_engine.py -q (19 passed)"
    - "python3 -m pytest tests/test_cli_checkpoint.py tests/test_cli_report.py tests/test_cli_synth_show.py tests/test_cli_synth_publish.py tests/test_vault_sync.py tests/test_release_publish.py -q (147 passed)"
    - "canon resume --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory (exit 0)"
    - "python3 -m canon_systems.resume_engine --plan-id structured-resume-task-memory --company-id CSC --repository-id canon-systems --handoffs-dir .cursor/handoffs/structured-resume-task-memory (exit 0)"
END_HANDOFF_TO_QA
