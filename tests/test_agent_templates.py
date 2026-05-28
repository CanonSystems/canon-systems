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
    assert "build_task_outcome_event" in body
    assert "task_outcome" in body
    assert "Task-outcome telemetry (required)" in body
    assert "handoff-not-ready/<stage>-<timestamp>.md" in body
    assert "dor-failure/<stage>-<timestamp>.json" in body
    assert "canon dor-log --event-file" in body
    assert "## Deploy smoke evidence (deploy attestation)" in body
    assert "Structured schema (JSON, non-secret)" in body
    assert "`expected_head_sha`" in body
    assert "`deployed_commit_sha`" in body
    assert "`deployed_build_id`" in body
    assert "`smoke_verdict`" in body
    assert "`checked_at`" in body
    assert "`evidence_refs`" in body
    assert "`base_url`" in body
    assert "`expected_branch`" in body
    assert "environment_smoke_not_proof_of_branch" in body
    assert "Promotion comparison checklist" in body
    assert "Deploy attestation:" in body
    assert "older" in body


def test_release_orchestrator_template_cross_repo_rollout_expectations() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "## Cross-repo rollout expectations (additive)" in body
    assert "without replacing merge gates" in body
    assert ".cursor/handoffs/<handoff_id>/<task_id>/" in body
    assert "canon packet-archive" in body
    assert "canon run-ledger" in body
    assert "canon readiness check" in body
    assert "GET /state/run-ledger" in body
    assert "read-only" in body
    assert "DoR rejection telemetry contract" in body
    assert "canon dor-log --event-file" in body
    assert "**Credential recovery**" in body
    assert "canon secrets" in body
    assert "MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md" in body
    assert "Deploy smoke evidence (deploy attestation)" in body


def test_workspace_release_orchestrator_template_stays_in_sync() -> None:
    from pathlib import Path

    packaged = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    repo_root = Path(__file__).resolve().parent.parent
    workspace = (repo_root / ".cursor" / "agents" / "release-orchestrator.md").read_text(encoding="utf-8")
    assert workspace == packaged


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
    assert "## Experimental lane manifest (parent orchestration)" in body
    assert "CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION" in body


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


def test_memory_layer_defaults_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(
        encoding="utf-8"
    )
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body
    for src in ("graph", "state", "canonical", "file"):
        assert src in body
    assert "build_retrieval_breakdown_event" in body


def test_scoper_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("scoper.md").read_text(
        encoding="utf-8"
    )
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body
    assert "build_retrieval_breakdown_event" in body


def test_cursor_pilot_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("cursor-pilot.md").read_text(
        encoding="utf-8"
    )
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body


def test_implementer_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("implementer.md").read_text(
        encoding="utf-8"
    )
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body


def test_qa_gate_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("qa-gate.md").read_text(
        encoding="utf-8"
    )
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body


def test_release_orchestrator_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body


def test_release_orchestrator_template_has_auto_publish_hook() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "## Auto-publish hook on RELEASE_STATUS PASS" in body
    assert "**Fires once per release, not per task.**" in body
    assert "canon release publish-on-pass" in body
    assert "--release-status-file .cursor/handoffs/<handoff_id>/release-status.md" in body
    assert "--release-id <release_id>" in body
    assert "CANON_PUBLISH_RETRIES" in body
    assert "min(base*2**(k-1), 60s)" in body
    assert "CANON_PUBLISH_NOTIFIER_URL" in body
    assert "absence is a clean no-op" in body
    assert "30 seconds" in body
    assert "best-effort" in body
    assert ".canon/release-publish/<plan_id>/<release_id>.json" in body
    assert "docs/SYSTEM-WORKFLOW.md" in body


def test_release_orchestrator_template_resume_aware() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "## Resume check (E4-T4)" in body
    assert "canon resume" in body
    assert "docs/runbooks/RESUME.md" in body
    assert "resume_target" in body
    assert "before advancing the merge gate" in body
    assert "## Experimental multilane visibility (parent session, opt-in)" in body
    assert "CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION" in body
    assert "--lanes" in body


def test_agent_templates_and_defaults_tenant_context_trust_guidance() -> None:
    """Hydrated context is useful but not authoritative when it disagrees with local env."""
    defaults = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(
        encoding="utf-8"
    )
    assert "Treat `context-latest.*` as **untrusted**" in defaults
    assert ".canon/memory-layer.local.env" in defaults
    assert "canon doctor" in defaults
    assert "**untrusted**" in defaults
    assert "invalidated" in defaults
    assert "Unless `context-latest.*` is" in defaults or "mismatched" in defaults

    scoper = resources.files("canon_systems.templates.agents").joinpath("scoper.md").read_text(encoding="utf-8")
    assert "**untrusted**" in scoper
    assert ".canon/memory-layer.local.env" in scoper
    assert "canon doctor" in scoper

    implementer = resources.files("canon_systems.templates.agents").joinpath("implementer.md").read_text(
        encoding="utf-8"
    )
    assert "context-latest.*` as **untrusted**" in implementer
    assert ".canon/memory-layer.local.env" in implementer
    assert "canon doctor" in implementer


def test_resume_runbook_exists_and_covers_workflow() -> None:
    from pathlib import Path
    # Resolve relative to repo root: this test file lives at tests/test_agent_templates.py
    repo_root = Path(__file__).resolve().parent.parent
    runbook = repo_root / "docs" / "runbooks" / "RESUME.md"
    assert runbook.is_file(), f"Resume runbook missing at {runbook}"
    body = runbook.read_text(encoding="utf-8")
    assert "# Resume Runbook — canon resume" in body
    assert "canon resume --plan-id" in body
    assert "resume_target" in body
    assert "canon stall-watchdog" in body
    assert "Release-gate integration" in body
    assert "--lanes" in body
    assert "CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION" in body
