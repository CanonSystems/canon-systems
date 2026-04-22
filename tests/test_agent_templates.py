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


def test_release_orchestrator_template_has_merge_and_deploy_gates() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "Branch strategy" in body
    assert "Merge gates (all required)" in body
    assert "dev -> staging -> production/TestFlight" in body
    assert "Never bypass branch protection." in body
    assert "RELEASE_STATUS" in body
    assert "CANON_SLACK_BLOCKER_CHANNEL_ID" in body
    assert "Blocker escalation (repo-scoped Slack channel)" in body
    assert "Artifact persistence contract (required)" in body
    assert ".cursor/handoffs/<handoff_id>/<task_id>/scoper.md" in body
    assert "Task-unit execution (no slicing drift)" in body
    assert "If no progress or output for >10 minutes" in body
    assert "Memory capture discipline" in body
    assert "canon qa-validate --file" in body
    assert "--require-dor-telemetry" in body
    assert "canon flow-audit --handoff-id" in body
    assert "memory-health" in body
    assert ".cursor/handoffs/<handoff_id>/<task_id>/memory-health.json" in body
    assert "--require-memory-health" in body
    assert "canon memory-health --output" in body
    assert "DoR rejection telemetry contract (required)" in body
    assert "handoff-not-ready/<stage>-<timestamp>.md" in body
    assert "dor-failure/<stage>-<timestamp>.json" in body
    assert "canon dor-log --event-file" in body


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
    assert "`release-orchestrator` governs branch/PR/merge/deploy" in body
    assert "Release governance (required)" in body
    assert "Slack escalation (required)" in body
    assert "CANON_SLACK_BLOCKER_CHANNEL_ID" in body
    assert "Task granularity + packet persistence (required)" in body
    assert ".cursor/handoffs/<handoff_id>/<task_id>/" in body
    assert "HANDOFF_NOT_READY" in body
    assert "run `canon dor-log --event-file <that json>`" in body
    assert "stalls (>10 minutes without progress)" in body
    assert "canon qa-validate --require-pass" in body
    assert "--require-dor-telemetry" in body
    assert "sampled `canon flow-audit` PASS" in body


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


def test_scoper_template_checkpoint_contract() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("scoper.md").read_text(encoding="utf-8")
    assert "## Checkpoint (read-before / write-after) contract" in body
    assert (
        "canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>"
        in body
    )
    assert "canon checkpoint lease-acquire" in body
    assert "--owner-agent-run-id" in body
    assert "--owner-actor-id" in body
    assert (
        "canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>"
        in body
    )
    assert "--phase scoper" in body
    assert "state-api" in body
    assert "GET /state/checkpoint" in body
    assert "PUT /state/checkpoint" in body
    assert "CANON_STATE_API_URL" in body
    assert "skip checkpoint HTTP gracefully" in body


def test_cursor_pilot_template_checkpoint_contract() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("cursor-pilot.md").read_text(encoding="utf-8")
    assert "## Checkpoint (read-before / write-after) contract" in body
    assert (
        "canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>"
        in body
    )
    assert "canon checkpoint lease-acquire" in body
    assert "--owner-agent-run-id" in body
    assert "--owner-actor-id" in body
    assert (
        "canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>"
        in body
    )
    assert "--phase cursor-pilot" in body
    assert "state-api" in body
    assert "GET /state/checkpoint" in body
    assert "PUT /state/checkpoint" in body
    assert "CANON_STATE_API_URL" in body
    assert "skip checkpoint HTTP gracefully" in body


def test_implementer_template_checkpoint_contract() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("implementer.md").read_text(encoding="utf-8")
    assert "## Checkpoint (read-before / write-after) contract" in body
    assert (
        "canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>"
        in body
    )
    assert "canon checkpoint lease-acquire" in body
    assert "--owner-agent-run-id" in body
    assert "--owner-actor-id" in body
    assert (
        "canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>"
        in body
    )
    assert "--phase implementer" in body
    assert "state-api" in body
    assert "GET /state/checkpoint" in body
    assert "PUT /state/checkpoint" in body
    assert "CANON_STATE_API_URL" in body
    assert "skip checkpoint HTTP gracefully" in body


def test_qa_gate_template_checkpoint_contract() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("qa-gate.md").read_text(encoding="utf-8")
    assert "## Checkpoint (read-before / write-after) contract" in body
    assert (
        "canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>"
        in body
    )
    assert "canon checkpoint lease-acquire" in body
    assert "--owner-agent-run-id" in body
    assert "--owner-actor-id" in body
    assert (
        "canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>"
        in body
    )
    assert "--phase qa-gate" in body
    assert "state-api" in body
    assert "GET /state/checkpoint" in body
    assert "PUT /state/checkpoint" in body
    assert "CANON_STATE_API_URL" in body
    assert "skip checkpoint HTTP gracefully" in body


def test_release_orchestrator_template_checkpoint_contract() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "## Checkpoint (read-before / write-after) contract" in body
    assert (
        "canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>"
        in body
    )
    assert "canon checkpoint lease-acquire" in body
    assert "--owner-agent-run-id" in body
    assert "--owner-actor-id" in body
    assert (
        "canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>"
        in body
    )
    assert "--phase release-orchestrator" in body
    assert "state-api" in body
    assert "GET /state/checkpoint" in body
    assert "PUT /state/checkpoint" in body
    assert "CANON_STATE_API_URL" in body
    assert "skip checkpoint HTTP gracefully" in body


def test_memory_layer_defaults_checkpoint_contract() -> None:
    body = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(
        encoding="utf-8"
    )
    assert "## Checkpoint contract (required)" in body
    assert "`scoper`, `cursor-pilot`, `implementer`, `qa-gate`, `release-orchestrator`" in body
    assert "canon checkpoint lease-acquire" in body
    assert "canon checkpoint lease-renew" in body
    assert "canon checkpoint lease-release" in body
    assert "state-api" in body
    assert "state_version" in body
    assert "EXIT_VERSION_CONFLICT" in body
    assert "state_version_conflict" in body
    assert "EXIT_LEASE_DENIED" in body
    assert "CANON_STATE_API_URL" in body
    assert "--expected-version" in body
    assert "Each agent role writes its own phase label" in body


def test_project_planner_template_checkpoint_propagation() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("project-planner.md").read_text(
        encoding="utf-8"
    )
    assert "checkpoint read-before/write-after contract" in body
    assert "scoper" in body
    assert "cursor-pilot" in body
    assert "implementer" in body
    assert "qa-gate" in body
    assert "release-orchestrator" in body


def test_memory_layer_defaults_retrieval_policy() -> None:
    body = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(
        encoding="utf-8"
    )
    assert "## Retrieval policy (required)" in body
    assert "graph → state → canonical → file" in body
    assert "canon graph query" in body
    assert "canon checkpoint read" in body
    assert "canon ask" in body
    assert "AXON_SERVICE_URL" in body
    assert "Fail-open fallback" in body


def test_retrieval_policy_order_is_stable() -> None:
    body = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(
        encoding="utf-8"
    )
    assert body.count("graph → state → canonical → file") == 1


def test_scoper_template_graph_first_retrieval() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("scoper.md").read_text(encoding="utf-8")
    assert "## Graph-first retrieval (required)" in body
    assert "canon graph query" in body
    assert "source_spans" in body


def test_cursor_pilot_template_graph_first_retrieval() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("cursor-pilot.md").read_text(
        encoding="utf-8"
    )
    assert "## Graph-first retrieval (required)" in body
    assert "canon graph query" in body
    assert "canon graph impact" in body


def test_implementer_template_graph_first_retrieval() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("implementer.md").read_text(
        encoding="utf-8"
    )
    assert "## Graph-first retrieval (required)" in body
    assert "canon graph query" in body
    assert "before broad repo exploration" in body.lower() or "broad repo exploration" in body.lower()
