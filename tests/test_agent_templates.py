from importlib import resources


def test_implementer_template_pins_composer_fast() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("implementer.md").read_text(
        encoding="utf-8"
    )
    assert "model: composer-2-fast" in body
    assert "HANDOFF_TO_QA_SHARD" in body
    assert "never ask the user to paste secrets" in body
    assert "Never hallucinate APIs, configs, test outcomes, or command results." in body
    assert "run `canon secrets` (wizard), then retry" in body


def test_project_planner_template_emits_backlog_packet() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("project-planner.md").read_text(
        encoding="utf-8"
    )
    assert "PROJECT_EXECUTION_PLAN" in body
    assert "epic_backlog" in body
    assert "depends_on" in body
    assert "can_run_parallel" in body
    assert "per_task_workflow" in body


def test_cursor_pilot_requires_parallelization_plan() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("cursor-pilot.md").read_text(
        encoding="utf-8"
    )
    assert "<PARALLELIZATION_PLAN>" in body
    assert "parallel-first" in body
    assert "Launch one `implementer` subagent per workstream" in body
    assert "Never hallucinate missing packet fields" in body


def test_default_rule_requires_parallel_implementer_fanout() -> None:
    body = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(
        encoding="utf-8"
    )
    assert "as many `implementer` subagents in parallel as the" in body
    assert "Only run sequentially for streams with explicit dependencies." in body
    assert "PARALLEL_IMPLEMENTER_BATCH" in body
    assert "one parent message" in body
    assert "HANDOFF_TO_QA_SHARD" in body
    assert "Truthfulness + secrets handling (required)" in body
    assert "Do not ask users to paste credentials/tokens/secrets into chat." in body
    assert "Credential recovery automation (required)" in body
    assert "Run this loop automatically:" in body
    assert "switch to **Plan mode** and run" in body
    assert "`project-planner` first" in body


def test_scoper_and_qa_gate_include_no_guessing_policy() -> None:
    scoper = resources.files("canon_systems.templates.agents").joinpath("scoper.md").read_text(
        encoding="utf-8"
    )
    qa_gate = resources.files("canon_systems.templates.agents").joinpath("qa-gate.md").read_text(
        encoding="utf-8"
    )
    assert "Never hallucinate, invent file paths, or fill missing fields arbitrarily." in scoper
    assert "Never fabricate test runs, pass/fail status, coverage, or evidence paths." in qa_gate
    assert "`canon secrets` (wizard), retry once" in qa_gate


def test_hooks_include_credential_recovery_flow() -> None:
    preflight = resources.files("canon_systems.templates.hooks").joinpath("memory-preflight.sh").read_text(
        encoding="utf-8"
    )
    capture = resources.files("canon_systems.templates.hooks").joinpath("memory-capture.sh").read_text(
        encoding="utf-8"
    )
    assert "is_credential_error()" in preflight
    assert "attempt_secret_recovery()" in preflight
    assert "credential-recovery-needed.txt" in preflight
    assert "\"${CANON_BIN}\" --repo-root \"${ROOT_DIR}\" secrets wizard" in preflight
    assert "run_capture_with_recovery()" in capture
    assert "credential-recovery-needed.txt" in capture
    assert "\"${CANON_BIN}\" --repo-root \"${ROOT_DIR}\" secrets wizard" in capture
