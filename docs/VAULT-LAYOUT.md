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
