# SCOPE_SUMMARY

E5-T2 implements the deterministic vault generator that projects `CanonicalEvent`s into the Obsidian-compatible S3 layout specified by E5-T1 (`docs/VAULT-LAYOUT.md`, `schema_version: 1`). The service ships as five modules under `backend/synthesis/synthesis/` (`redaction.py`, `generator.py`, `sources.py`, `publisher.py`, plus `main.py` route additions) with a pure `events → pages` core, an injectable `boto3.client("s3")` publisher that writes only on content-hash mismatch, and two FastAPI endpoints (`/synth/vault/changes`, `/synth/show`) hung off the existing scaffold. Determinism is pinned by `(timestamp, event_id)` ordering plus anchor-first / alphabetical frontmatter serialization; the 15-field E5-T1 allowlist is enforced via a `project_safe(CanonicalEvent) -> SafeEvent` helper that imports from `canon_backend_shared.events` and never redefines it. Cloud wiring stays in a waived terraform module stub (`infra/terraform/modules/synthesis-vault/`) that operators apply manually per Precedent §1.

---

# SCOPE_PACKET

## 1. Module layout (`backend/synthesis/synthesis/*.py`)

| File | Responsibility | Key symbols |
|---|---|---|
| `redaction.py` | Pure `CanonicalEvent → SafeEvent` projection enforcing the E5-T1 §5 allowlist. Imports `CanonicalEvent` from `canon_backend_shared.events`; never redefines. Owns the per-event-type payload projection catalogue (§6 of the spec). | `SAFE_ENVELOPE_FIELDS` (frozenset of 10), `SCOPE_SAFE_ALIASED` (frozenset of 4, `model` explicitly **DROPPED**), `project_safe(ev: CanonicalEvent) -> SafeEvent`, `project_payload(event_type: str, payload: Mapping) -> dict` with per-type dispatch (`retrieval_breakdown`, `lease_stall_detected`, `checkpoint_write`, opaque), `shorthash(raw: str) -> str` (`sha256(raw.encode()).hexdigest()[:8]`). |
| `sources.py` | Event acquisition seam. Primary (production, partially-waived): `StateApiEventSource`; test/CLI: `InMemoryEventSource(events: list[CanonicalEvent])` pure, zero I/O. Both implement `iter_events(*, plan_id: str \| None, task_id: str \| None, cutoff_timestamp: str) -> Iterable[CanonicalEvent]`. | `EventSource` Protocol, `InMemoryEventSource`, `StateApiEventSource`, `SourceError`. |
| `generator.py` | Deterministic core: `generate_vault(events, *, company_id, repository_id, cutoff_timestamp) -> VaultBundle`. `VaultBundle` is `{key: bytes}`. Pure function; no S3, no network, no wallclock reads. | `VaultBundle` (dataclass), `generate_vault`, `render_frontmatter(safe)`, `render_task_page`, `render_plan_page`, `render_agent_run_page`, `render_retrieval_breakdown_page`, `render_stall_page`, `render_opaque_page`, `_wire_wikilinks`, `_render_indices`. |
| `publisher.py` | S3 writer with content-hash diff. `SynthesisPublisher(bucket, s3_client, prefix)`. Compares SHA-256 of body against remote `x-amz-meta-content-hash`; writes only on mismatch/absence. Injectable client for moto/dict-fake in tests. | `SynthesisPublisher`, `publish(bundle, *, write_once=()) -> PublishResult`, `list_remote_hashes`, `put_page`, `put_attachment`, `_content_hash`. |
| `main.py` additive | Keep `/healthz`. Add `GET /synth/vault/changes?since=<iso8601>` and `GET /synth/show?plan_id=<id>&task_id=<id>[&format=json\|markdown]`. FastAPI dependency overrides for `EventSource` and `SynthesisPublisher`. Same `FastAPI(title="synthesis")` instance. | `get_event_source`, `get_publisher`, route handlers. |

Package `__init__.py` re-exports `generate_vault`, `project_safe`, `SynthesisPublisher`, `InMemoryEventSource`.

## 2. Determinism + idempotence design

- **Event ordering** — `sorted(events, key=lambda e: (e.timestamp, e.event_id))`.
- **Frontmatter key order** — anchors first (`schema_version`, `event_id`), then `sorted()` alphabetically for the rest. Explicit `_ANCHOR_ORDER` tuple + manual emission (no reliance on `yaml.safe_dump` ordering).
- **Shorthash** — `hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]`. Applied to `company_id`, `repository_id`, `agent_run_id`, `actor_id`.
- **Path template** — `vault/{company_shorthash}/{repo_shorthash}/...` always driven by shorthashes, never raw ids.
- **No wallclock reads** — generator takes `cutoff_timestamp` argument; `datetime.now()` forbidden in `generator.py`/`redaction.py`/`sources.py` (unit-test enforced via source grep).
- **Body canonicalization** — markdown bodies end with single trailing `\n`; frontmatter fenced exactly `---\n...---\n`; JSON attachments `json.dumps(..., ensure_ascii=True, sort_keys=True, separators=(",", ":"))`.
- **Publisher diff** — `content_hash = sha256(body).hexdigest()`; compare against `HeadObject.Metadata["content-hash"]`. Equal → skip. Absent/different → `PutObject` with `Metadata={"content-hash": content_hash}` + correct `ContentType`. Own sidecar hash chosen over ETag (ETag ≠ byte-content for multipart uploads).
- **`.obsidian/` seed write-once** — `app.json`/`workspace.json`/`graph.json` in bundle every run; publisher treats as "write if absent, skip if present" via `write_once: frozenset[str]` arg.

## 3. Input source contract

- **Primary (production, partially-waived)**: `StateApiEventSource` pulls canonical events via a future state-api HTTP endpoint. E5-T2 ships the source abstraction; `StateApiEventSource` stub raises `NotImplementedError("wave-5 waiver: state-api event query endpoint pending; use InMemoryEventSource or CLI-fed JSONL for now")` if invoked without an overridden `fetch_fn`. Endpoint URL and request shape documented in README for a later state-api follow-up.
- **Test path (and E5-T3 CLI path)**: `InMemoryEventSource(events: list[CanonicalEvent])` — deterministic, zero-I/O.
- **Wave-5 HTTP-seam waiver** — CI runs `InMemoryEventSource` only; consistent with Waves 2-4.

## 4. S3 interface

- `boto3.client("s3")` injectable via constructor param for moto-backed tests (mirrors `backend/axon-service/axon_service/storage.py`).
- Public surface:
  - `__init__(self, *, bucket, s3_client, prefix)` — `prefix` = `f"vault/{company_shorthash}/{repo_shorthash}"`.
  - `list_remote_hashes(sub_prefix="") -> dict[str, str]` — paginated `list_objects_v2` + `head_object`.
  - `put_page(key, body)` — `ContentType="text/markdown; charset=utf-8"`.
  - `put_attachment(key, body_bytes)` — `ContentType="application/json"`.
  - `publish(bundle, *, write_once=()) -> PublishResult(written, skipped, keys_written)`.
- **Idempotence**: second `publish()` with same bundle → `PublishResult(written=0, skipped=N, keys_written=[])`.
- **Unit-test fake**: `DictS3Client` in `backend/synthesis/tests/_fakes.py` (dict-of-dicts `head_object`/`list_objects_v2`/`put_object`). Moto reserved for 1 integration test (mirrors axon-service).

## 5. Endpoint design

### `GET /synth/vault/changes?since=<iso8601>`
- 422 if `since` unparseable.
- Calls `EventSource.iter_events(..., cutoff_timestamp=since)` across all plans/tasks; runs `generate_vault`; returns JSON:
  ```json
  {"since":"2026-04-23T10:00:00Z","schema_version":1,"changes":[{"vault_key":"plans/<pid>/tasks/<tid>/index.md","event_id":"01J...","timestamp":"2026-04-23T10:05:00Z"}],"count":7}
  ```
- `changes[]` sorted by `(timestamp, event_id)` for determinism. No publish.

### `GET /synth/show?plan_id=<id>&task_id=<id>[&format=json|markdown]`
- Required `plan_id`; optional `task_id` (if omitted → plan index body); optional `format` (default `json`).
- JSON envelope `{"vault_key":"...","schema_version":1,"markdown":"---\n..."}` gives vault-web (E5-T4) a stable contract with room for future fields. `?format=markdown` returns raw body with `Content-Type: text/markdown; charset=utf-8` for `canon synth show` (E5-T3) / curl.
- 404 if empty-after-redaction for the scope.

`/healthz` unchanged.

## 6. Absorbed obsidian-mind behaviors

1. **cross-linker** → `generator.py::_wire_wikilinks(pages)` walks rendered pages, replaces raw id strings with `[[event:<id>]]` / `[[plan:<pid>]]` / `[[task:<tid>]]` via a canonical alias table for byte-stability.
2. **vault-librarian** → `generator.py::_render_indices(safe_events)` owns `_index/by-event-type.md`, `_index/by-plan.md`, `_index/by-agent.md`. Per §7 of the spec, `by-event-type.md` also serves as the reverse citation index.
3. **context-loader** → realized by `GET /synth/show` (context-hydration surface for agents).

Skipped: `brag-spotter`, `people-profiler`, `review-*`, `incident-capture`, `slack-archaeologist`, `vault-migrator` (out of platform-vault scope).

## 7. Test matrix

**Target: 367 baseline → ≥380 passed (+13).**

### `backend/synthesis/tests/test_generator.py` (≥10 tests)

1. `test_generator_deterministic_byte_identical_output`
2. `test_generator_event_ordering_stable_across_permutations`
3. `test_redaction_drops_model_field_from_frontmatter`
4. `test_redaction_never_emits_raw_company_id_or_repository_id`
5. `test_redaction_silently_drops_unknown_payload_keys` (caplog records zero warnings/errors)
6. `test_redaction_unknown_event_type_routes_to_opaque_with_dropped_payload_marker`
7. `test_citations_present_for_every_rendered_fact`
8. `test_shorthashes_are_deterministic_sha256_prefix`
9. `test_frontmatter_key_order_anchors_first_then_alphabetical`
10. `test_no_wallclock_reads_in_generator_module` (source grep on `datetime.now`)

### `backend/synthesis/tests/test_endpoints.py` (≥2 tests — FastAPI `TestClient`)

11. `test_synth_vault_changes_returns_deterministic_change_list`
12. `test_synth_show_returns_json_envelope_and_markdown_alt_format` (default JSON + `?format=markdown` escape + 404 on empty)

### `backend/synthesis/tests/test_publisher_moto.py` (≥1 moto integration)

13. `test_publish_is_idempotent_no_duplicate_writes` (+ content-hash metadata assertion)

**Fixtures** (`backend/synthesis/tests/conftest.py`): `event_factory`, `dict_s3_client`, `moto_s3_bucket` (gated by `pytest.importorskip("moto")`), `client` (FastAPI TestClient + dependency overrides).

**Pyproject**: `[project.optional-dependencies].test` gains `pytest>=8.2,<9`, `moto[s3]>=5.0,<6`, `httpx>=0.27,<1`. Production `dependencies` gains `boto3>=1.35,<2`.

## 8. Forbidden surfaces

- NO `docs/VAULT-LAYOUT.md` edits (E5-T1 locked).
- NO `backend/shared/**/*.py` edits (CanonicalEvent single source of truth).
- NO `src/canon_systems/**/*.py`, `backend/state-api/**/*.py`, `backend/axon-service/**/*.py`, `backend/memory-adapter/**/*.py`, `backend/knowledge-*/**/*.py`.
- NO root-level `main.tf` wiring of the new terraform module.
- NO `terraform apply`, no live AWS creds, no network calls in tests.
- NO editing `docs/OBSIDIAN-MIND-CATALOGUE.md` or `docs/SYSTEM-WORKFLOW.md` beyond the additive Wave-5 entry.

**Allowed**: `backend/synthesis/**/*` (new modules + tests + pyproject + README), `infra/terraform/modules/synthesis-vault/**/*` (new module, NOT wired to root), `CHANGELOG.md` (additive `[Unreleased]` entry), `.cursor/handoffs/canon-memory-v1/E5-T2/**/*`.

## 9. Infra waiver

New unwired `infra/terraform/modules/synthesis-vault/` module:

- `main.tf` — `aws_s3_bucket` (`<prefix>-synthesis-vault`, `object_lock_enabled=false`), `aws_s3_bucket_versioning Enabled`, SSE-S3 (`AES256`), `aws_s3_bucket_public_access_block` (all 4 flags true), `aws_s3_bucket_policy` (publisher IAM role allowlist). Mirrors `infra/terraform/modules/axon-snapshots/main.tf`.
- `variables.tf` — `name_prefix`, `publisher_role_arn`, `vault_web_reader_role_arn` (nullable for E5-T4).
- `outputs.tf` — `bucket_name`, `bucket_arn`, `bucket_regional_domain_name`.
- `README.md` — convention, SSE, versioning on, object-lock off, single-publisher bucket policy; per-company s3:prefix constraint deferred to E5-T4 multi-tenant hardening.

**Not wired into `infra/terraform/main.tf`**. `infra_waiver: cloud_execution_deferred` (Precedent §1).

`backend/synthesis/README.md` gains "## Infra requirements (operator-applied)" section listing env vars: `SYNTHESIS_S3_BUCKET`, `AWS_REGION`, `STATE_API_BASE_URL` (Wave-5 waived no-op).

## 10. Suite target

- Baseline: **367 passed**.
- New: 10 + 2 + 1 = **13 new tests**.
- Target: **≥380 passed** (hard floor per backlog done_signal: `backend/synthesis/tests/test_generator.py` PASS + moto idempotence PASS). No existing regressions. Packet commits to exactly **380**.

---

## prior_work_references

- `docs/VAULT-LAYOUT.md` (E5-T1, landed at `bc729c2`) — immediate dependency and contract this task implements.
- `backend/shared/canon_backend_shared/events.py::CanonicalEvent` — single source of truth; `redaction.py` imports, never redefines.
- `src/canon_systems/retrieval_telemetry.py` — reference pattern for canonical-event emission.
- `backend/state-api/state_api/storage.py` + `backend/state-api/tests/conftest.py` — moto fixtures + boto3 injectable-client pattern.
- `backend/axon-service/axon_service/storage.py` + `backend/axon-service/axon_service_tests/conftest.py` — S3 `boto3.client("s3")` + moto `mock_aws` fixture; `SynthesisPublisher` mirrors shape.
- `backend/synthesis/synthesis/main.py` + `backend/synthesis/README.md` + `backend/synthesis/pyproject.toml` — existing FastAPI scaffold extended, not replaced.
- `docs/OBSIDIAN-MIND-CATALOGUE.md` — Wave-0 capability inventory; drove §6 pick.
- `infra/terraform/modules/axon-snapshots/main.tf` + README — S3-bucket terraform pattern mirrored by `synthesis-vault`.
- `.cursor/handoffs/canon-memory-v1/E4-T4/scoper.md` — `HANDOFF_TO_CURSOR_PILOT` closing-block template.

---

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E5-T2 ships backend/synthesis as a deterministic vault generator that projects CanonicalEvent rows through the E5-T1 allowlist into an Obsidian-compatible S3 layout. Modules: redaction.py (project_safe + per-event-type payload catalogue + shorthash), generator.py (pure events→VaultBundle with cross-linker + vault-librarian behaviors), sources.py (EventSource Protocol; InMemoryEventSource primary for tests, StateApiEventSource stub per Wave-5 HTTP waiver), publisher.py (SynthesisPublisher with content-hash diff-only writes via boto3 S3), main.py (new /synth/vault/changes + /synth/show routes on the existing FastAPI app). Tests: ≥10 generator unit tests + 2 endpoint tests (FastAPI TestClient) + 1 moto-backed idempotence integration test. Suite goes 367 → 380. Plus unwired terraform module infra/terraform/modules/synthesis-vault/ (cloud_execution_deferred)."
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260423_e5t2_synthesis_generator"
      task_id: "E5-T2"
      wave: 5
      branch: "wave/5/canon-memory-v1"
      company_id: "IMC"
      repository_id: "innermost"
    story:
      title: "backend/synthesis generator service (absorbs obsidian-mind)"
      userValue: "Backend service can deterministically render canonical+state events into an Obsidian-compatible S3 vault that vault-web (E5-T4), canon synth publish CLI (E5-T3), and agent context-loader all read from — unlocking Wave 5 consumer surfaces."
      acceptanceCriteria:
        - "Deterministic output per (plan_id, task_id, cutoff_timestamp)."
        - "Citations link to event_ids."
        - "Idempotent publish; diff-only writes."
        - "Exposes GET /synth/vault/changes?since=<ts> and GET /synth/show?plan_id=... endpoints."
        - "backend/synthesis/tests/test_generator.py PASS (≥10 unit tests)."
        - "Integration test publishes a sample vault to moto-backed S3 and re-publish is a no-op."
        - "Full suite goes from 367 to ≥380 passed; zero regressions."
        - "Allowlist enforced: raw company_id/repository_id/model never serialized; unknown payload keys silently dropped with zero log/stderr output."
    repository:
      primaryLanguages: ["python"]
      testFramework: "pytest + FastAPI TestClient + moto[s3]"
      relevantFiles:
        - "docs/VAULT-LAYOUT.md"
        - "backend/shared/canon_backend_shared/events.py"
        - "backend/synthesis/synthesis/main.py"
        - "backend/synthesis/README.md"
        - "backend/synthesis/pyproject.toml"
        - "backend/state-api/state_api/storage.py"
        - "backend/state-api/tests/conftest.py"
        - "backend/axon-service/axon_service/storage.py"
        - "backend/axon-service/axon_service_tests/conftest.py"
        - "src/canon_systems/retrieval_telemetry.py"
        - "infra/terraform/modules/axon-snapshots/main.tf"
        - "docs/OBSIDIAN-MIND-CATALOGUE.md"
    constraints:
      dependencies: ["E5-T1"]
      mustNotBreak:
        - "367-test baseline"
        - "docs/VAULT-LAYOUT.md contract (schema_version: 1)"
        - "CanonicalEvent single source of truth (backend/shared)"
        - "Wave-5 HTTP/S3 seam waiver (no live AWS in CI; moto or dict-fake only)"
        - "Zero edits to src/canon_systems/**/*.py, backend/state-api/**/*.py, backend/axon-service/**/*.py, backend/memory-adapter/**/*.py, backend/knowledge-*/**/*.py, backend/shared/**/*.py"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
      prior_work_references: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
