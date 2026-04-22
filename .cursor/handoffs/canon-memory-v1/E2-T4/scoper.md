# E2-T4 Scoper Packet

**Task:** Update agent templates to hydrate + checkpoint at phase boundaries
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** scoper subagent (ID 776d0bf6-2742-422c-8be4-b0396020d123)

Note: `canon checkpoint read` only accepts scope flags (`--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`) per `checkpoint_cli.py`; it does not accept `--agent-run-id`, `--phase`, `--actor-type`, or `--actor-id`. Backlog §B uses agent-name values for `phase` (`scoper|cursor-pilot|...`), not `scoping|planning|...`. The handoff adopts wire-accurate CLI and §B phase values, and records the parent brief’s read-flag wording as an explicit open question.

Resolution (parent): adopt wire-accurate CLI (scope flags only on `read`; identity metadata in lease-acquire and write body). Phase labels use §B agent-name values: `scoper`, `cursor-pilot`, `implementer`, `qa-gate`, `release-orchestrator`.

---

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: Wave 2 task E2-T4 adds a shared "Checkpoint (read-before / write-after) contract" to the five core agent playbooks plus a required "Checkpoint contract (required)" block in `memory-layer-defaults.mdc`, aligns prose with the shipped `canon checkpoint` subcommands and the `state-api` README wire protocol, and locks the behavior in with new additive tests and living-spec bullets. Templates must tell agents to skip checkpoint HTTP when `CANON_STATE_API_URL` is unset (local dev/sandbox) while still describing the full lease + optimistic-write sequence when the URL is available.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260422Z_canon-memory-v1_E2-T4"
      company_id: "IMC"
      repository_id: "innermost"
    story:
      title: "E2-T4: Agent templates hydrate + checkpoint at phase boundaries"
      userValue: "Operators and downstream automation get consistent, testable instructions for loading and persisting operational state via state-api at each agent phase, so checkpoints and leases match the DynamoDB §B schema and the stdlib checkpoint CLI without ad-hoc drift."
      acceptanceCriteria:
        - "`src/canon_systems/templates/agents/scoper.md` contains the Markdown heading line `## Checkpoint (read-before / write-after) contract`."
        - "`src/canon_systems/templates/agents/cursor-pilot.md` contains the Markdown heading line `## Checkpoint (read-before / write-after) contract`."
        - "`src/canon_systems/templates/agents/implementer.md` contains the Markdown heading line `## Checkpoint (read-before / write-after) contract`."
        - "`src/canon_systems/templates/agents/qa-gate.md` contains the Markdown heading line `## Checkpoint (read-before / write-after) contract`."
        - "`src/canon_systems/templates/agents/release-orchestrator.md` contains the Markdown heading line `## Checkpoint (read-before / write-after) contract`."
        - "`scoper.md` contains the literal substring `canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>`."
        - "`cursor-pilot.md` contains the same `canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>` substring as in the previous criterion."
        - "`implementer.md` contains that same `canon checkpoint read` substring with all five scope placeholders."
        - "`qa-gate.md` contains that same `canon checkpoint read` substring with all five scope placeholders."
        - "`release-orchestrator.md` contains that same `canon checkpoint read` substring with all five scope placeholders."
        - "`scoper.md` contains the literal substring `canon checkpoint lease-acquire` and the literals `--owner-agent-run-id` and `--owner-actor-id`."
        - "`cursor-pilot.md` contains `canon checkpoint lease-acquire`, `--owner-agent-run-id`, and `--owner-actor-id`."
        - "`implementer.md` contains `canon checkpoint lease-acquire`, `--owner-agent-run-id`, and `--owner-actor-id`."
        - "`qa-gate.md` contains `canon checkpoint lease-acquire`, `--owner-agent-run-id`, and `--owner-actor-id`."
        - "`release-orchestrator.md` contains `canon checkpoint lease-acquire`, `--owner-agent-run-id`, and `--owner-actor-id`."
        - "`scoper.md` contains the literal substring `canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>`."
        - "`cursor-pilot.md` contains that same `canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>` substring."
        - "`implementer.md` contains that same `canon checkpoint write` substring."
        - "`qa-gate.md` contains that same `canon checkpoint write` substring."
        - "`release-orchestrator.md` contains that same `canon checkpoint write` substring."
        - "`scoper.md` contains `--phase scoper` in the checkpoint contract section (value matches `docs/MEMORY-PLATFORM-BACKLOG.md` §B `phase` union)."
        - "`cursor-pilot.md` contains `--phase cursor-pilot` in the checkpoint contract section."
        - "`implementer.md` contains `--phase implementer` in the checkpoint contract section."
        - "`qa-gate.md` contains `--phase qa-gate` in the checkpoint contract section."
        - "`release-orchestrator.md` contains `--phase release-orchestrator` in the checkpoint contract section."
        - "Each of the five core agent templates lists the substring `state-api` and explicitly names the REST paths `GET /state/checkpoint` and `PUT /state/checkpoint` (or the same paths in inline code) as the wire protocol for read/write."
        - "Each of the five core agent templates instructs agents to skip checkpoint/lease HTTP gracefully when `CANON_STATE_API_URL` is unset (dev/sandbox), without failing the task solely for missing state plane connectivity."
        - "`src/canon_systems/templates/rules/memory-layer-defaults.mdc` contains the heading line `## Checkpoint contract (required)`."
        - "`memory-layer-defaults.mdc` states that checkpoint `phase` labels are exactly the §B union `scoper`, `cursor-pilot`, `implementer`, `qa-gate`, `release-orchestrator` and maps each agent role to its phase label."
        - "`memory-layer-defaults.mdc` states that writes require a live lease token from `canon checkpoint lease-acquire` / renew/release via `lease-renew` / `lease-release`, aligned with `state-api`."
        - "`memory-layer-defaults.mdc` states optimistic concurrency: writers pass expected `state_version` and treat CLI exit code `1` as version conflict (`EXIT_VERSION_CONFLICT` / `state_version_conflict`) and exit code `2` as lease denial (`EXIT_LEASE_DENIED`)."
        - "`src/canon_systems/templates/agents/project-planner.md` contains an explicit clause that downstream per-task packets must carry or reference the same checkpoint read-before/write-after contract (propagation to scoper/cursor-pilot/implementer/qa-gate/release-orchestrator)."
        - "`CHANGELOG.md` under `[Unreleased]` → `### Added` inserts a new first bullet documenting E2-T4 agent template + rule-pack checkpoint contract hydration (additive, top of the Added list)."
        - "`README.md` adds one bullet in the agent-template / checkpoint-adjacent documentation describing that installed templates now embed the checkpoint phase-boundary contract."
        - "`docs/SYSTEM-WORKFLOW.md` in §6 adds one bullet tying phase-boundary work to `canon checkpoint read` before agent work and `canon checkpoint write` after, referencing `state-api` and `CANON_STATE_API_URL` behavior."
        - "`tests/test_agent_templates.py` adds a new test function `test_scoper_template_checkpoint_contract` with multiple `assert ... in body` lines and does not remove or alter any existing test function bodies except additive newlines/imports if needed."
        - "`tests/test_agent_templates.py` adds `test_cursor_pilot_template_checkpoint_contract` with multiple assertions on `cursor-pilot.md`."
        - "`tests/test_agent_templates.py` adds `test_implementer_template_checkpoint_contract` with multiple assertions on `implementer.md`."
        - "`tests/test_agent_templates.py` adds `test_qa_gate_template_checkpoint_contract` with multiple assertions on `qa-gate.md`."
        - "`tests/test_agent_templates.py` adds `test_release_orchestrator_template_checkpoint_contract` with multiple assertions on `release-orchestrator.md`."
        - "`tests/test_agent_templates.py` adds `test_memory_layer_defaults_checkpoint_contract` asserting the new required checkpoint block strings in `memory-layer-defaults.mdc`."
        - "`tests/test_agent_templates.py` adds `test_project_planner_template_checkpoint_propagation` asserting the propagation clause strings in `project-planner.md`."
        - "`tests/test_agent_templates.py` adds at least fifteen new `assert` statements total across these new test functions (additive only)."
    repository:
      primaryLanguages: ["Python"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/templates/agents/scoper.md"
        - "src/canon_systems/templates/agents/cursor-pilot.md"
        - "src/canon_systems/templates/agents/implementer.md"
        - "src/canon_systems/templates/agents/qa-gate.md"
        - "src/canon_systems/templates/agents/release-orchestrator.md"
        - "src/canon_systems/templates/agents/project-planner.md"
        - "src/canon_systems/templates/rules/memory-layer-defaults.mdc"
        - "tests/test_agent_templates.py"
        - "CHANGELOG.md"
        - "README.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-BACKLOG.md"
        - "backend/state-api/README.md"
        - "src/canon_systems/checkpoint_cli.py"
    constraints:
      dependencies: ["E2-T3 checkpoint CLI (`canon checkpoint read|write|lease-acquire|lease-renew|lease-release`)", "state-api REST contract in `backend/state-api/README.md`", "Backlog §B checkpoint schema in `docs/MEMORY-PLATFORM-BACKLOG.md`"]
      mustNotBreak: ["All existing assertions and test functions in `tests/test_agent_templates.py`", "`pytest -q` at repo root", "`bash scripts/smoke-test.sh` (smoke)", "`canon qa-validate` PASS where used in workflow", "No edits under forbidden_surfaces"]
    forbidden_surfaces:
      - "backend/**"
      - "infra/**"
      - ".cursor/rules/**"
      - ".cursor/plans/**"
      - ".github/workflows/**"
      - "pyproject.toml"
      - "pytest.ini"
      - "requirements-dev.txt"
      - "scripts/**"
      - "src/canon_systems/*.py (except no src .py changes at all)"
      - "src/canon_systems/hooks/**"
      - "build/**"
      - "*.pyc"
    invariants:
      - "No third-party deps added."
      - "No new CLI flags added; use existing checkpoint CLI surface."
      - "Phase names exactly match backlog §B (agent-name values)."
      - "Additive-only edits: preserve existing assertions/prose verbatim."
    non_goals:
      - "Runtime behavior changes in agents."
      - "Live state-api integration at template-scope time."
      - "Changes outside templates/tests/living-specs."
    done_signals:
      - "tests/test_agent_templates.py green."
      - "pytest -q green."
      - "SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh green."
      - "canon qa-validate --file <qa-gate.md> --require-pass PASS."
    dor_checklist:
      repo_ref_verification: "Implementer SHALL run `git fetch` and confirm `HEAD` matches `8952fee` on `wave/2/canon-memory-v1` (or document the new tip if the branch advanced) before editing; scoper verified backlog §B and `checkpoint_cli.py` parser on disk in-repo."
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "`scoper.md` checkpoint section heading"
        implementation_targets: ["src/canon_systems/templates/agents/scoper.md"]
        verification_tests: ["tests/test_agent_templates.py::test_scoper_template_checkpoint_contract"]
      - criterion: "`cursor-pilot.md` checkpoint section heading"
        implementation_targets: ["src/canon_systems/templates/agents/cursor-pilot.md"]
        verification_tests: ["tests/test_agent_templates.py::test_cursor_pilot_template_checkpoint_contract"]
      - criterion: "`implementer.md` checkpoint section heading"
        implementation_targets: ["src/canon_systems/templates/agents/implementer.md"]
        verification_tests: ["tests/test_agent_templates.py::test_implementer_template_checkpoint_contract"]
      - criterion: "`qa-gate.md` checkpoint section heading"
        implementation_targets: ["src/canon_systems/templates/agents/qa-gate.md"]
        verification_tests: ["tests/test_agent_templates.py::test_qa_gate_template_checkpoint_contract"]
      - criterion: "`release-orchestrator.md` checkpoint section heading"
        implementation_targets: ["src/canon_systems/templates/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_agent_templates.py::test_release_orchestrator_template_checkpoint_contract"]
      - criterion: "Read invocation line in all five core templates"
        implementation_targets: ["src/canon_systems/templates/agents/scoper.md", "src/canon_systems/templates/agents/cursor-pilot.md", "src/canon_systems/templates/agents/implementer.md", "src/canon_systems/templates/agents/qa-gate.md", "src/canon_systems/templates/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_agent_templates.py::test_*_template_checkpoint_contract (read substring asserts)"]
      - criterion: "Lease-acquire + owner identity flags in all five core templates"
        implementation_targets: ["src/canon_systems/templates/agents/scoper.md", "src/canon_systems/templates/agents/cursor-pilot.md", "src/canon_systems/templates/agents/implementer.md", "src/canon_systems/templates/agents/qa-gate.md", "src/canon_systems/templates/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_agent_templates.py::test_*_template_checkpoint_contract (lease-acquire asserts)"]
      - criterion: "Write invocation line in all five core templates"
        implementation_targets: ["src/canon_systems/templates/agents/scoper.md", "src/canon_systems/templates/agents/cursor-pilot.md", "src/canon_systems/templates/agents/implementer.md", "src/canon_systems/templates/agents/qa-gate.md", "src/canon_systems/templates/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_agent_templates.py::test_*_template_checkpoint_contract (write substring asserts)"]
      - criterion: "Per-agent `--phase` values matching §B"
        implementation_targets: ["src/canon_systems/templates/agents/scoper.md", "src/canon_systems/templates/agents/cursor-pilot.md", "src/canon_systems/templates/agents/implementer.md", "src/canon_systems/templates/agents/qa-gate.md", "src/canon_systems/templates/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_agent_templates.py::test_*_template_checkpoint_contract (phase asserts)"]
      - criterion: "`state-api` wire protocol naming for GET/PUT checkpoint"
        implementation_targets: ["src/canon_systems/templates/agents/scoper.md", "src/canon_systems/templates/agents/cursor-pilot.md", "src/canon_systems/templates/agents/implementer.md", "src/canon_systems/templates/agents/qa-gate.md", "src/canon_systems/templates/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_agent_templates.py::test_*_template_checkpoint_contract (state-api path asserts)"]
      - criterion: "`CANON_STATE_API_URL` unset graceful skip"
        implementation_targets: ["src/canon_systems/templates/agents/scoper.md", "src/canon_systems/templates/agents/cursor-pilot.md", "src/canon_systems/templates/agents/implementer.md", "src/canon_systems/templates/agents/qa-gate.md", "src/canon_systems/templates/agents/release-orchestrator.md"]
        verification_tests: ["tests/test_agent_templates.py::test_*_template_checkpoint_contract (skip asserts)"]
      - criterion: "`memory-layer-defaults.mdc` required checkpoint block"
        implementation_targets: ["src/canon_systems/templates/rules/memory-layer-defaults.mdc"]
        verification_tests: ["tests/test_agent_templates.py::test_memory_layer_defaults_checkpoint_contract"]
      - criterion: "`project-planner.md` propagation clause"
        implementation_targets: ["src/canon_systems/templates/agents/project-planner.md"]
        verification_tests: ["tests/test_agent_templates.py::test_project_planner_template_checkpoint_propagation"]
      - criterion: "CHANGELOG / README / SYSTEM-WORKFLOW living-spec bullets"
        implementation_targets: ["CHANGELOG.md", "README.md", "docs/SYSTEM-WORKFLOW.md"]
        verification_tests: ["Manual review + repo grep in qa-gate; optional follow-up test file only if already established pattern"]
      - criterion: "≥15 new asserts across new tests"
        implementation_targets: ["tests/test_agent_templates.py"]
        verification_tests: ["pytest collects new tests; code review count in qa-gate"]
    risks_and_assumptions:
      assumptions: ["`.canon/memory/context-latest.md` lists `company_id`/`repository_id` as IMC/innermost for this workspace; no `memory-layer.local.env` was found on disk — implementer SHOULD confirm tenant ids from the active Canon wiring for the target repo.", "Phase labels in checkpoint writes follow `docs/MEMORY-PLATFORM-BACKLOG.md` §B (`scoper`, `cursor-pilot`, etc.), not informal names like `scoping`/`planning`, so templates and tests stay aligned with the DynamoDB JSON schema and `state-api` examples.", "`canon checkpoint read` (E2-T3) only sends the five scope query parameters; identity metadata belongs in lease acquire (`--owner-agent-run-id`, `--owner-actor-id`) and in the write body via `--body-file`, not as extra read flags.", "Task is additive-only: no Python/src changes, no `.cursor/rules` edits, no backend/infra changes."]
      openQuestions: []
    prior_work_references: []
END_HANDOFF_TO_CURSOR_PILOT
```
