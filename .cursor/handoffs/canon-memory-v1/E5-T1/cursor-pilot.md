<!-- CURSOR_PILOT_PROMPT: E5-T1 vault layout spec + redaction allowlist -->

# E5-T1 Cursor-Pilot Prompt

## ROLE
Implementer for Canon Memory Platform v1, Wave 5, Task E5-T1 (Vault layout spec + redaction allowlist). Branch: `wave/5/canon-memory-v1` (cut from origin/main at `d3f79c4`).

## TASK
Publish `docs/VAULT-LAYOUT.md` — the `schema_version: 1` versioned contract for how `backend/synthesis` will project canonical events into an Obsidian-compatible S3 vault. Add a pointer from `backend/synthesis/README.md`. Additive CHANGELOG + SYSTEM-WORKFLOW edits. Optional (recommended): `tests/test_vault_layout_spec.py` to lock the schema_version + allowlist shape.

## REPOSITORY

### Files to create (2)
1. `docs/VAULT-LAYOUT.md`
2. `tests/test_vault_layout_spec.py` (RECOMMENDED — 2 new tests)

### Files to modify (additive only, 3)
3. `backend/synthesis/README.md` — append single pointer line at END.
4. `CHANGELOG.md` — prepend E5-T1 bullet at TOP of `## [Unreleased] ### Added`, above existing E4-T4 bullet.
5. `docs/SYSTEM-WORKFLOW.md` — additive bullet in §3.

### Forbidden surfaces
- `backend/synthesis/synthesis/**` (E5-T2 territory).
- `backend/synthesis-web/**` (E5-T4).
- `src/canon_systems/**/*.py` (no CLI in this task).
- `infra/**` (no S3 bucket provisioning here).
- Any other existing test file.

## IMPLEMENTATION SPECIFICATION

### 1. `docs/VAULT-LAYOUT.md` (NEW)

Full body — copy verbatim (YAML frontmatter then 9 sections):

```markdown
---
schema_version: 1
doc_id: VAULT-LAYOUT
owner: backend/synthesis (Wave 5)
stability: stable-contract
---

# Vault Layout Specification

The canonical projection contract for `backend/synthesis` (Wave 5 / E5-T2). Defines how `CanonicalEvent` rows from the historical plane are transformed into an Obsidian-compatible S3 vault that three read paths (web, agent CLI, in-repo mirror) consume.

This spec is the source of truth. Every generator, every renderer, every redaction decision in Wave 5 is measured against it. `schema_version: 1` is a stable contract; bumps follow §9.

## 1. Layout overview

```
s3://<bucket>/vault/<company_shorthash>/<repo_shorthash>/
├── README.md
├── .obsidian/
│   ├── app.json
│   ├── workspace.json
│   └── graph.json
├── attachments/
│   └── <event_id>.json
├── plans/
│   └── <plan_id>/
│       ├── index.md
│       └── tasks/
│           └── <task_id>/
│               ├── index.md
│               ├── scoper.md
│               ├── cursor-pilot.md
│               ├── implementer.md
│               ├── qa-gate.md
│               └── release-orchestrator.md
├── agents/
│   └── <agent_name>/
│       └── runs/
│           └── <run_suffix>.md
├── events/
│   ├── retrieval-breakdown/
│   │   └── <plan_id>/<task_id>.md
│   ├── stall-watchdog/
│   │   └── <plan_id>/<task_id>.md
│   └── opaque/
│       └── <event_id>.md
└── _index/
    ├── by-event-type.md
    ├── by-plan.md
    └── by-agent.md
```

The root `vault/` prefix is fixed. Everything under it is generated; no hand edits.

## 2. Scoping (per-company + per-repo)

Every vault path carries tenant context via `company_shorthash` + `repo_shorthash` prefix. Shorthashes are the last-8 hex of a SHA-256 of the raw identifier — they are opaque but deterministic, collision-resistant at the scales we care about, and **never leak the raw company_id / repository_id into page URLs, filenames, wikilinks, or frontmatter values**.

Generator composes:
- `company_shorthash = sha256(company_id).hexdigest()[:8]` → `"a1b2c3d4"`
- `repo_shorthash = sha256(repository_id).hexdigest()[:8]`

Multi-tenant hosting of vault-web (E5-T4) keys off these prefixes; a user with access to `company=X` MAY NOT see any object with a different `company_shorthash` prefix (enforced at the S3 bucket policy layer, out of scope for this doc — see E5-T2 infra).

## 3. Markdown file contract

Every generated markdown file carries YAML frontmatter. Canonical frontmatter schema:

```yaml
---
schema_version: 1
event_id: <event_id>         # primary citation anchor
parent_event_id: <id>         # for chain traceability
event_type: <event_type>
plan_id: <plan_id>
task_id: <task_id>
handoff_id: <handoff_id>
agent_name: <agent_name>
timestamp: <ISO 8601>
state_version: <int>
---
```

**No company_id, repository_id, agent_run_id, actor_id, or model** in frontmatter values. Tenant context is encoded in the path prefix; actor/run context is encoded in page links using 8-char hex suffixes (see §5).

Body conventions:
- `[[wikilinks]]` for cross-page references — e.g., a task page wikilinks its parent plan page and its 5 phase pages.
- `[[event:<event_id>]]` for citation backlinks. The generator maintains the reverse index in `_index/by-event-type.md`.
- Attachment references point into `attachments/<event_id>.json` which holds the raw (frontmatter-less) event envelope.

## 4. .obsidian/ seed config

On first publish, the generator seeds `.obsidian/` with the minimum Obsidian ≥1.5-compatible config. Files written (idempotent — never overwritten on subsequent publishes):

- `.obsidian/app.json` — default workspace settings: `"alwaysUpdateLinks": true`, `"showLineNumber": false`, `"attachmentFolderPath": "attachments"`.
- `.obsidian/workspace.json` — minimal single-pane workspace layout so the vault opens cleanly without prompts.
- `.obsidian/graph.json` — graph view defaults: all folders shown, tag nodes on, orphans off.

**NOT seeded:** plugins (`.obsidian/plugins/`), themes (`.obsidian/themes/`), hotkeys (`.obsidian/hotkeys.json`), user snippets (`.obsidian/snippets/`). Operators own those per-user.

## 5. Event-field allowlist (redaction)

This is the exhaustive list of `CanonicalEvent` envelope fields (from `backend/shared/canon_backend_shared/events.py::CanonicalEvent`) safe to project into the vault. **Any field not in the SAFE column is silently dropped — no logs, no warnings, no telemetry. Redaction is a hot path.**

| Field | Disposition | Rendered as |
|---|---|---|
| `schema_version` | SAFE | frontmatter |
| `event_id` | SAFE | frontmatter + page anchor |
| `parent_event_id` | SAFE | frontmatter + backlink |
| `event_type` | SAFE | frontmatter + page-type routing |
| `plan_id` | SAFE | frontmatter + path |
| `task_id` | SAFE | frontmatter + path |
| `handoff_id` | SAFE | frontmatter + path |
| `agent_name` | SAFE | frontmatter + page-type routing |
| `timestamp` | SAFE | frontmatter |
| `state_version` | SAFE | frontmatter |
| `company_id` | SCOPE-SAFE (aliased) | `company_shorthash` prefix in path only |
| `repository_id` | SCOPE-SAFE (aliased) | `repo_shorthash` prefix in path only |
| `agent_run_id` | SCOPE-SAFE (aliased) | last-8 hex suffix only (`run_suffix`) |
| `actor_id` | SCOPE-SAFE (aliased) | last-8 hex suffix only |
| `model` | **DROPPED** | never rendered — internal telemetry |

**Payload (`payload.*`) policy:** silently drop any payload key not explicitly enumerated in §6 per-event-type catalogue. No exceptions. The generator treats unknown payload keys exactly like unknown top-level fields: invisible, unlogged, unmentioned.

## 6. Per-page type catalogue

Payload fields safe to render, by `event_type`:

### `event_type: retrieval_breakdown`
- `payload.sources` — 4-bucket breakdown `{graph, state, canonical, file}` with per-source `tokens_in` / `tokens_out`.
- `payload.phase` — one of `scoper|cursor-pilot|implementer|qa-gate|release-orchestrator`.
- `payload.agent` — agent role emitting the event.
- Routed to `events/retrieval-breakdown/<plan_id>/<task_id>.md`.

### `event_type: lease_stall_detected`
- `payload.diagnostic.expires_at` — ISO 8601 timestamp.
- `payload.diagnostic.owner_suffix` — last-8 hex of the stalled `agent_run_id`.
- `payload.suggested_next_step.message` — human-readable recovery hint.
- **NOT rendered:** `payload.diagnostic.owner` (raw agent_run_id). Generator replaces it with the `_suffix` variant before frontmatter serialization.
- Routed to `events/stall-watchdog/<plan_id>/<task_id>.md`.

### `event_type: checkpoint_write`
- `payload.phase`.
- `payload.state_version`.
- **NOT rendered:** `payload.lease_token`, `payload.body`.
- Surfaced inside the relevant `plans/<plan_id>/tasks/<task_id>/<phase>.md` page body as a "Checkpoint committed at state_version=N" line.

### Unknown `event_type`
Generator emits a placeholder page at `events/opaque/<event_id>.md` with only the SAFE frontmatter set and a visible body marker `dropped_payload: true`. No payload fields rendered. No warning logged.

## 7. Citation contract

Every rendered fact cites its source `event_id`. Citations use the `[[event:<event_id>]]` wikilink form so Obsidian's graph view wires them into backlinks automatically. No orphan facts; no uncited claims.

Example task page body:

```markdown
The implementer phase landed 14 new tests ([[event:01J...]]) and advanced `state_version` from 12 to 13 ([[event:01J...]]).
```

## 8. Idempotence contract

Output MUST be deterministic per `(plan_id, task_id, cutoff_timestamp)`. Re-running the generator with identical inputs produces byte-identical output for every page. The publish step (E5-T3) does a content-hash diff before writing — unchanged pages are not re-uploaded.

Determinism rules for the generator:
- Event ordering: primary key `timestamp`, secondary `event_id`.
- No wallclock-derived strings except `cutoff_timestamp` passed in.
- No hash salts — `shorthash` and `suffix` use raw SHA-256, no per-run seed.
- Dict iteration in frontmatter uses insertion-order-stable alphabetical sort for non-anchor fields; anchor fields (`schema_version`, `event_id`) always first.

## 9. Versioning policy

`schema_version: 1` is a stable contract. Bumps:

- **Patch** (no bump): typo fixes, non-normative clarifications, diagram polish. Generator ignores.
- **Minor** (`1` → `2`): additive allowlist entries, new per-event-type sections, new directory conventions. Generator advertises `supports=[1,2]`; backward-compatible consumers OK.
- **Major** (`2` → `3`): breaking — field removal, path restructure, redaction-policy tightening. Requires a migration note + deprecation of old `schema_version` for ≥1 wave.

Vault consumers pin to a `schema_version` range; the generator writes its own `schema_version` into every frontmatter block and into `/README.md` frontmatter at vault root for top-level consumer checks.
```

### 2. `backend/synthesis/README.md` — append pointer

Append a single line at the END of the existing README:

```markdown

See [docs/VAULT-LAYOUT.md](../../docs/VAULT-LAYOUT.md) for the vault projection contract (schema_version: 1).
```

Preserve the existing 5 lines exactly.

### 3. `CHANGELOG.md` — prepend E5-T1 bullet

Insert at TOP of `## [Unreleased] ### Added`, directly above the E4-T4 bullet:

```markdown
- **E5-T1** Vault layout spec + redaction allowlist: new `docs/VAULT-LAYOUT.md` (`schema_version: 1`) publishes the versioned contract for how `backend/synthesis` (Wave 5 / E5-T2) will project `CanonicalEvent` rows into an Obsidian-compatible S3 vault. 9 sections cover the S3 layout tree, per-company/per-repo shorthash scoping (never raw company_id/repository_id in page values), markdown frontmatter schema, `.obsidian/` seed config (app/workspace/graph only; no plugins/themes), the exhaustive 15-field redaction allowlist (10 SAFE + 4 SCOPE-SAFE-aliased + `model` DROPPED; unknown payload keys silently dropped — no logs, no warnings), the per-event-type payload catalogue (`retrieval_breakdown`, `lease_stall_detected`, `checkpoint_write`, opaque fallback), the `[[event:<id>]]` citation contract, the determinism/idempotence rules, and the schema_version bump policy. `backend/synthesis/README.md` now links to the spec. New `tests/test_vault_layout_spec.py` locks `schema_version: 1`, the §5 allowlist completeness against `CanonicalEvent`, and the `backend/synthesis/README.md` backlink. Documentation-only; zero production-code changes.
```

### 4. `docs/SYSTEM-WORKFLOW.md` — append §3 bullet

Insert adjacent to the existing Wave-4 bullets in §3 (after the E4-T3 bullet, before the `## 4) DoR rejection telemetry contract` heading):

```markdown
- **E5-T1 vault layout spec (schema_version 1):** new `docs/VAULT-LAYOUT.md` is the Wave-5 projection contract. Defines the Obsidian-compatible S3 vault layout, `company_shorthash`/`repo_shorthash` path scoping, the 15-field `CanonicalEvent` redaction allowlist (with `model` dropped + unknown payload keys silently dropped), the per-event-type payload catalogue, citation/idempotence rules, and the `schema_version` bump policy. E5-T2..E5-T7 implement against this contract; `backend/synthesis/README.md` links it.
```

### 5. `tests/test_vault_layout_spec.py` (NEW, RECOMMENDED)

```python
from dataclasses import fields
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_vault_layout_spec_is_schema_v1_and_has_required_sections() -> None:
    spec = REPO_ROOT / "docs" / "VAULT-LAYOUT.md"
    assert spec.is_file(), f"Vault layout spec missing at {spec}"
    body = spec.read_text(encoding="utf-8")
    assert "schema_version: 1" in body
    for heading in (
        "## 1. Layout overview",
        "## 2. Scoping (per-company + per-repo)",
        "## 3. Markdown file contract",
        "## 4. .obsidian/ seed config",
        "## 5. Event-field allowlist (redaction)",
        "## 6. Per-page type catalogue",
        "## 7. Citation contract",
        "## 8. Idempotence contract",
        "## 9. Versioning policy",
    ):
        assert heading in body, f"Missing required section: {heading}"
    assert "attachments/" in body
    assert "wikilinks" in body.lower() or "[[" in body
    assert ".obsidian/" in body
    assert "schema_version" in body


def test_vault_layout_allowlist_covers_canonical_event_fields_and_backend_readme_links() -> None:
    import sys
    sys.path.insert(0, str(REPO_ROOT / "backend" / "shared"))
    from canon_backend_shared.events import CanonicalEvent  # type: ignore  # noqa: E402

    spec_body = (REPO_ROOT / "docs" / "VAULT-LAYOUT.md").read_text(encoding="utf-8")

    canonical_fields = {f.name for f in fields(CanonicalEvent)} - {"payload"}
    for field_name in canonical_fields:
        assert f"`{field_name}`" in spec_body, (
            f"CanonicalEvent field {field_name!r} missing from §5 allowlist table"
        )

    assert "DROPPED" in spec_body
    assert "`model`" in spec_body
    assert "silently drop" in spec_body.lower() or "silently dropped" in spec_body.lower()

    backend_readme = (REPO_ROOT / "backend" / "synthesis" / "README.md").read_text(encoding="utf-8")
    assert "docs/VAULT-LAYOUT.md" in backend_readme
    assert "schema_version: 1" in backend_readme
```

## REASONING

1. Read `backend/shared/canon_backend_shared/events.py::CanonicalEvent` to confirm the 15-field dataclass.
2. Read `backend/synthesis/README.md` (5 lines) to confirm append point.
3. Read `CHANGELOG.md` top (confirm E4-T4 bullet is at line 12).
4. Read `docs/SYSTEM-WORKFLOW.md` §3 (confirm E4-T3 is at line 47).
5. Create `docs/VAULT-LAYOUT.md` verbatim from §1 above.
6. Append 1 line to `backend/synthesis/README.md`.
7. Prepend CHANGELOG bullet. Append SYSTEM-WORKFLOW bullet.
8. Write `tests/test_vault_layout_spec.py`.
9. Focused test: `pytest tests/test_vault_layout_spec.py -q` → expect 2 passed.
10. Full suite: `pytest -q` → expect 365 + 2 = 367 passed.
11. Emit `HANDOFF_TO_QA` to `.cursor/handoffs/canon-memory-v1/E5-T1/implementer.md`.

## OUTPUT FORMAT

Full implementer packet with `HANDOFF_TO_QA` block:
- `handoff_id: handoff_20260423_e5t1_vault_layout_spec`
- `task_id: E5-T1`
- `branch: wave/5/canon-memory-v1`
- `files_modified:` 5 paths (2 new + 3 modified).
- `acceptance_criteria:` 7 ACs (AC1-AC7 per scoper), each `status: MET`, `evidence`, `run_result`, `covering_tests` (block-style YAML; bare node IDs; every AC ≥1 entry).
- `suite_result:` total=367 passed=367 skipped=0.

## STOP CONDITIONS

Stop if:
- `backend/synthesis/README.md` append touches any existing line.
- Full suite drops below 365 (regression).
- Any forbidden surface is touched.
- `CanonicalEvent` dataclass has fields I missed in the allowlist — correct the spec before emitting packet.
