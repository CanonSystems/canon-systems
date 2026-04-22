# E2-T4 Cursor-Pilot Packet

**Task:** Update agent templates to hydrate + checkpoint at phase boundaries
**Wave branch:** `wave/2/canon-memory-v1` (tip 8952fee)
**Produced by:** parent orchestrator from E2-T4 scoper packet
**Source:** `.cursor/handoffs/canon-memory-v1/E2-T4/scoper.md`

---

```
CURSOR_PILOT_PROMPT

ROLE: Additive-only template + docs + tests implementer. No src/**.py changes. No backend/infra changes. No .cursor/rules edits. No scripts.

TASK (E2-T4): Hydrate the five core agent templates (scoper/cursor-pilot/implementer/qa-gate/release-orchestrator) and the `memory-layer-defaults.mdc` rule pack with an explicit "Checkpoint (read-before / write-after) contract" section that references the shipped `canon checkpoint` CLI (E2-T3) and the `state-api` wire protocol (E2-T2). Add a propagation clause to `project-planner.md`. Lock the contract with additive assertions in `tests/test_agent_templates.py`. Add living-spec bullets.

CONTEXT:
- E2-T3 shipped `canon checkpoint {read, write, lease-acquire, lease-renew, lease-release}` with these exact flag surfaces (read checkpoint_cli.py for truth):
    read         --base-url --timeout-ms --company-id --repository-id --plan-id --task-id --workstream-id
    write        --base-url --timeout-ms --company-id --repository-id --plan-id --task-id --workstream-id --lease-token --expected-version --body-file|--body-stdin
    lease-acquire --base-url --timeout-ms --company-id --repository-id --plan-id --task-id --workstream-id --owner-agent-run-id --owner-actor-id [--owner-actor-type] --ttl-seconds
    lease-renew  --base-url --timeout-ms --company-id --repository-id --plan-id --task-id --workstream-id --lease-token --ttl-seconds
    lease-release --base-url --timeout-ms --company-id --repository-id --plan-id --task-id --workstream-id --lease-token
  CLI exit codes: 0=OK, 1=state_version_conflict (EXIT_VERSION_CONFLICT), 2=lease denied (EXIT_LEASE_DENIED), 3=not found, 4=usage, 5=transport.
- `state-api` wire endpoints: `GET /state/checkpoint`, `PUT /state/checkpoint`, `POST /state/lease/{acquire,renew,release}`.
- Backlog §B `phase` union (agent-name values): scoper | cursor-pilot | implementer | qa-gate | release-orchestrator. Use these exact strings as `--phase` values in template prose.
- Env seam: `CANON_STATE_API_URL`. When unset in dev/sandbox, templates must say: skip checkpoint HTTP gracefully; do not fail task solely on missing state plane connectivity.

REPOSITORY:
- Workdir: /Users/edwardwalker/localwork/canon-systems
- Branch: wave/2/canon-memory-v1
- Scope packet: .cursor/handoffs/canon-memory-v1/E2-T4/scoper.md (authoritative 42 ACs)

REASONING:
- All edits are additive. Do NOT delete or rewrap existing prose. Append new sections.
- Each of the five core agent templates gets the SAME canonical heading `## Checkpoint (read-before / write-after) contract` followed by prose that includes:
    1. A "Read before work" subsection with a fenced shell block containing the exact CLI invocation:
         canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>
       (MUST appear verbatim as an `assert ... in body` substring in the corresponding test.)
    2. A "Acquire lease" subsection that mentions `canon checkpoint lease-acquire`, `--owner-agent-run-id`, and `--owner-actor-id` (substrings, not necessarily one line).
    3. A "Write after work" subsection with a fenced shell block containing the exact CLI invocation:
         canon checkpoint write --lease-token <lease_token> --expected-version <state_version> --body-file <path>
    4. A "Phase" line stating `--phase <agent>` where `<agent>` is the §B phase for the template (scoper / cursor-pilot / implementer / qa-gate / release-orchestrator).
    5. A "Wire protocol" line mentioning `state-api`, `GET /state/checkpoint`, `PUT /state/checkpoint`.
    6. A "Dev/sandbox skip" line stating that when `CANON_STATE_API_URL` is unset, the agent skips checkpoint HTTP gracefully (keep the env var name verbatim).
- `memory-layer-defaults.mdc` gets a new additive block `## Checkpoint contract (required)` with:
    - Phase label enumeration (quote the §B union: `scoper`, `cursor-pilot`, `implementer`, `qa-gate`, `release-orchestrator`).
    - Lease lifecycle (acquire/renew/release via `canon checkpoint lease-acquire|lease-renew|lease-release`, referencing `state-api`).
    - Optimistic concurrency: pass `--expected-version` = `state_version`; exit 1 == `EXIT_VERSION_CONFLICT` / `state_version_conflict`; exit 2 == `EXIT_LEASE_DENIED`.
- `project-planner.md` gets an additive clause stating that per-task packets must carry or reference the checkpoint read-before/write-after contract (propagation to scoper/cursor-pilot/implementer/qa-gate/release-orchestrator).
- `tests/test_agent_templates.py`: add SEVEN new test functions (one per core template + memory-layer-defaults + project-planner) with ≥15 new `assert ... in body` statements total. Do NOT touch existing functions. Reuse the existing `importlib.resources` pattern.
- Living specs:
    - CHANGELOG.md: prepend ONE bullet at the TOP of `[Unreleased] ### Added` (above the E2-T3 bullet) beginning `E2-T4: agent templates + memory-layer-defaults hydrate checkpoint contract —`.
    - README.md: add ONE additive bullet referencing the template checkpoint-contract hydration (pick an existing templates-adjacent bullet list; do not reflow columns).
    - docs/SYSTEM-WORKFLOW.md: add ONE additive bullet in §6 tying phase-boundary work to `canon checkpoint read` before / `canon checkpoint write` after, referencing `state-api` and `CANON_STATE_API_URL`.

OUTPUT FORMAT:
- Emit HANDOFF_TO_QA (YAML-ish block) mapping every scoper AC to at least one covering_tests entry (file path or `file::test_name`).
- Include a `files_changed` list.

STOP CONDITIONS (all must hold before emitting HANDOFF_TO_QA):
- `pytest -q` exits 0 at repo root.
- `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` exits 0.
- `git diff --name-only` shows only paths in the E2-T4 allowlist:
    src/canon_systems/templates/agents/{scoper,cursor-pilot,implementer,qa-gate,release-orchestrator,project-planner}.md
    src/canon_systems/templates/rules/memory-layer-defaults.mdc
    tests/test_agent_templates.py
    CHANGELOG.md
    README.md
    docs/SYSTEM-WORKFLOW.md
- No edits to forbidden surfaces listed in the scoper packet.
- All existing `test_agent_templates.py` assertions still pass verbatim.

DO NOT:
- Commit or push.
- Add third-party deps.
- Modify any Python source file (src/**.py) including cli.py or checkpoint_cli.py.
- Edit backend/**, infra/**, .cursor/rules/**, .cursor/plans/**, .github/**, scripts/**, pyproject.toml, pytest.ini.
- Remove or reflow any existing lines in the templates or tests.

END_CURSOR_PILOT_PROMPT
```
