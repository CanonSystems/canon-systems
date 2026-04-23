# E5-T1 Scoper Packet — Vault layout spec + redaction allowlist

## SCOPE_SUMMARY

**Task:** Publish `docs/VAULT-LAYOUT.md` — the versioned specification for how `backend/synthesis` (E5-T2) will project canonical events into an Obsidian-compatible S3 vault.

**Why now:** E5-T2's generator MUST be deterministic and privacy-safe from day 1. Without a committed allowlist, the generator is guaranteed to leak internal fields the moment it starts rendering arbitrary `payload.*` keys. The layout spec is the contract E5-T2..E5-T7 implement against; nothing in Wave 5 can start until this lands.

**Scope:** Documentation-only. Zero production-code changes. One new doc, one additive pointer in `backend/synthesis/README.md`, living-spec bullets in `CHANGELOG.md` and `docs/SYSTEM-WORKFLOW.md §3`. Suite delta: +0..+2 (optional lightweight schema-version assertion test — recommended but not required by done_signal).

## SCOPE_PACKET

### 1. Deliverables

1. **NEW** `docs/VAULT-LAYOUT.md` with the following required sections:
   - `schema_version: 1` (at top, in a YAML frontmatter block).
   - `## 1. Layout overview` — tree diagram of the S3 vault layout.
   - `## 2. Scoping (per-company + per-repo)` — prefix convention `s3://<bucket>/vault/<company_id>/<repository_id>/...`.
   - `## 3. Markdown file contract` — YAML frontmatter schema, wikilinks `[[...]]`, backlinks via generator, attachments path.
   - `## 4. .obsidian/ seed config` — what files are generated (`.obsidian/app.json`, `.obsidian/workspace.json`, `.obsidian/graph.json`), what is NOT (plugins).
   - `## 5. Event-field allowlist (redaction)` — the exhaustive list of `CanonicalEvent` fields safe to render; everything else is silently dropped.
   - `## 6. Per-page type catalogue` — what pages are generated per event_type (task pages, retrieval-breakdown dashboards, stall-watchdog incident pages).
   - `## 7. Citation contract` — every rendered fact cites its source `event_id`.
   - `## 8. Idempotence contract` — deterministic output per `(plan_id, task_id, cutoff_timestamp)`; re-publish is a no-op diff.
   - `## 9. Versioning policy` — schema_version bump rules; backward-compat for older vaults.

2. **MODIFY** `backend/synthesis/README.md` — add a single additive pointer line at the END: `See [docs/VAULT-LAYOUT.md](../../docs/VAULT-LAYOUT.md) for the vault projection contract (schema_version: 1).`

3. **MODIFY** `CHANGELOG.md` — prepend E5-T1 bullet at TOP of `## [Unreleased] ### Added`.

4. **MODIFY** `docs/SYSTEM-WORKFLOW.md §3` — append additive bullet near the E4 bullets pointing to the new vault layout spec as the contract Wave 5 builds against.

5. **OPTIONAL** (recommended, +1 test): `tests/test_vault_layout_spec.py` — locks the layout file's `schema_version: 1` and the presence of the §5 allowlist table. This future-proofs the contract: if anyone edits the spec without bumping `schema_version`, the test fires.

### 2. CanonicalEvent field allowlist — canonical list

From `backend/shared/canon_backend_shared/events.py::CanonicalEvent` (the single source of truth per Wave-3 discipline):

**SAFE — render into vault frontmatter/body:**
- `schema_version` (fixed `1`)
- `event_id` (cited via backlinks)
- `parent_event_id` (cited via backlinks)
- `event_type`
- `plan_id`, `task_id`, `handoff_id` (used for page routing)
- `agent_name` (e.g., `scoper`, `implementer`, `canon-stall-watchdog`)
- `timestamp` (ISO 8601)
- `state_version`

**SCOPE-SAFE but MUST be abbreviated or aliased** (never raw, per redaction policy — downstream docs treat them as identifiers, not PII):
- `company_id` → render as shortened hash suffix (e.g., `company-a1b2c3d4`) in page filenames/wikilinks; never raw company_id in YAML frontmatter.
- `repository_id` → same treatment.
- `agent_run_id` → last-8 hex suffix only.
- `actor_id` → last-8 hex suffix only.

**DROPPED — silently excluded from vault:**
- `model` (LLM model slug) — internal telemetry, not vault-grade.
- Any `payload.*` key not explicitly enumerated in §6 per-page type catalogue.

**Per-event-type payload allowlist (§6 catalogue):**

- `event_type=retrieval_breakdown` — payload.sources, payload.phase, payload.agent (already canonical per E3-T5).
- `event_type=lease_stall_detected` — payload.diagnostic.expires_at, payload.diagnostic.owner_suffix (last-8 of owner_agent_run_id), payload.suggested_next_step.message. DO NOT render payload.diagnostic.owner (raw agent_run_id).
- `event_type=checkpoint_write` — payload.phase, payload.state_version. DO NOT render payload.lease_token or payload.body.
- Unknown `event_type` — generator emits a placeholder "opaque event" page with only the SAFE frontmatter set and a `dropped_payload: true` flag; no payload fields rendered.

### 3. Layout diagram (required in §1)

```
s3://<bucket>/vault/<company_shorthash>/<repo_shorthash>/
├── README.md
├── .obsidian/
│   ├── app.json
│   ├── workspace.json
│   └── graph.json
├── attachments/
│   └── <event_id>.json         (raw event as evidence, frontmatter-less)
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

### 4. Forbidden surfaces

- `backend/synthesis/synthesis/**/*.py` — E5-T2 territory, NOT E5-T1.
- `backend/synthesis-web/**` — E5-T4 territory.
- `src/canon_systems/**/*.py` — no CLI yet; E5-T3/E5-T5/E5-T6 add CLIs.
- `infra/**` — S3 bucket terraform is out-of-scope here (handled in E5-T2 infra additive or later).
- `.cursor/rules/**`, `.cursor/plans/**` — rules are locked.
- Any existing test file except the new optional `tests/test_vault_layout_spec.py`.

### 5. Acceptance criteria (mirror backlog)

1. **AC1:** Layout covers markdown with YAML frontmatter, wikilinks, seeded `.obsidian/` config, `attachments/`. Verified by substring assertions against `docs/VAULT-LAYOUT.md`.
2. **AC2:** Allowlist lists every safe event field; everything else is silently dropped by the generator. Verified by asserting every non-payload `CanonicalEvent` dataclass field from `backend/shared/canon_backend_shared/events.py` appears in the doc's §5 allowlist table, AND that the doc explicitly names `model` in the DROPPED column AND names the "silently drop unknown payload keys" rule.
3. **AC3:** Versioned spec (`schema_version: 1`). Verified by asserting `schema_version: 1` appears in the doc's YAML frontmatter.
4. **AC4:** `backend/synthesis/README.md` links to `docs/VAULT-LAYOUT.md` (backlog done_signal).
5. **AC5:** Additive CHANGELOG + SYSTEM-WORKFLOW bullets (no existing line reordered).
6. **AC6:** Full suite remains green (363 + 2 from Wave 4 = 365; + 0..+2 here → 365 or 366 or 367).
7. **AC7:** Zero production-code changes under `backend/**/*.py`, `src/canon_systems/**/*.py`, `infra/**`.

### 6. Done signal (from backlog)

`docs/VAULT-LAYOUT.md committed and referenced by backend/synthesis README.` Verified by a plain-file existence + substring check.

### 7. Risks / mitigation

- **Risk:** Allowlist drifts from `CanonicalEvent` dataclass over time.
  **Mitigation:** The optional test asserts field-set equality between the dataclass and the §5 allowlist table. Recommend including it.
- **Risk:** E5-T2 implementer interprets "silently drop" loosely and logs warnings for unknown keys, leaking via stderr.
  **Mitigation:** Spec text uses the word "silently" with emphasis and adds an explicit note: "No logs, no warnings, no telemetry on dropped fields — redaction is a hot path."
- **Risk:** `.obsidian/` seed config drifts against Obsidian desktop compatibility.
  **Mitigation:** Spec pins minimum Obsidian version (≥1.5) and lists exact JSON keys used in each seed file.

### 8. Out of scope

- No FastAPI endpoints (E5-T2).
- No S3 credentials, no Terraform (E5-T2 / infra later).
- No redaction-policy JSON file (the doc IS the policy; E5-T2 importing it is implicit).

### prior_work_references

- `backend/shared/canon_backend_shared/events.py::CanonicalEvent` — canonical fields enumerated (lines 9-40).
- `docs/OBSIDIAN-MIND-CATALOGUE.md` — upstream capability catalogue from Wave 0 (informs §6 per-event-type catalogue structure).
- `backend/synthesis/README.md` — existing scaffold; 2-line current body.
- `backend/synthesis/synthesis/main.py` — FastAPI `/healthz` scaffold; shows E5-T2 will extend this.
- Precedent §3 (shared-surface discipline): CHANGELOG top-of-Unreleased; no README reflows.

### Handoff to cursor-pilot

Parent orchestrator will author cursor-pilot packet directly (small doc-only scope). Pilot captures:
- Exact layout-diagram ASCII.
- Exact YAML frontmatter block for the doc itself.
- Exact allowlist table markdown.
- Exact test body for the optional vault-layout test.

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E5-T1 publishes docs/VAULT-LAYOUT.md (schema_version: 1) — the 9-section contract for how backend/synthesis (E5-T2) projects CanonicalEvent rows into an Obsidian-compatible S3 vault. Links from backend/synthesis/README.md. New tests/test_vault_layout_spec.py locks schema_version + the 15-field CanonicalEvent allowlist + the README backlink. Additive CHANGELOG + SYSTEM-WORKFLOW §3 edits. Zero production-code changes (backend/**/*.py, src/canon_systems/**, infra/**)."
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260423_e5t1_vault_layout_spec"
      task_id: "E5-T1"
      wave: 5
      branch: "wave/5/canon-memory-v1"
    story:
      title: "Vault layout spec + redaction allowlist"
      acceptanceCriteria:
        - "docs/VAULT-LAYOUT.md exists with schema_version: 1 frontmatter and all 9 required sections."
        - "§5 allowlist covers every non-payload CanonicalEvent field (15 entries including `model` in DROPPED row)."
        - "Payload policy codifies 'silently drop' for unknown payload keys (no logs, no warnings)."
        - "backend/synthesis/README.md links to docs/VAULT-LAYOUT.md and carries `schema_version: 1`."
        - "tests/test_vault_layout_spec.py ships 2 passing tests."
        - "CHANGELOG top-of-Unreleased + SYSTEM-WORKFLOW §3 additive bullets; no existing line reordered."
        - "Full suite: 365 → 367 passed (+2); zero skipped."
        - "Zero edits to backend/**/*.py, src/canon_systems/**/*.py, infra/**, .cursor/rules/**, .cursor/plans/**."
    constraints:
      dependencies: ["E2-T1"]
      mustNotBreak:
        - "365-test baseline (post-Wave 4)"
        - "backend/synthesis/README.md existing 5-line body"
        - "CanonicalEvent dataclass field set (single source of truth)"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
      prior_work_references: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
