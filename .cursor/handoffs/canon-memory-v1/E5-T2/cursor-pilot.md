<!-- CURSOR_PILOT_PROMPT: E5-T2 synthesis generator -->

# E5-T2 Cursor-Pilot Prompt

## ROLE

Implementer for Canon Memory Platform v1, Wave 5, Task **E5-T2** (backend/synthesis deterministic vault generator). Branch: `wave/5/canon-memory-v1` (tip `bc729c2` = E5-T1). Parent scoper packet: `.cursor/handoffs/canon-memory-v1/E5-T2/scoper.md` (DoR-checked, Ready).

## TASK

Ship `backend/synthesis` as a deterministic vault generator: five Python modules under `backend/synthesis/synthesis/` plus three test files under `backend/synthesis/tests/` that project `CanonicalEvent` rows through the E5-T1 15-field allowlist into an Obsidian-compatible S3 vault, publish them idempotently via content-hash diff, and surface two new HTTP endpoints on the existing FastAPI scaffold. Suite goes **367 → 380** (+13 new tests). Also ship an unwired terraform module stub (`infra/terraform/modules/synthesis-vault/`, `cloud_execution_deferred`) and additive CHANGELOG / SYSTEM-WORKFLOW / `backend/synthesis/README.md` edits. Zero edits to `backend/shared/**`, `docs/VAULT-LAYOUT.md`, `src/canon_systems/**`, `backend/state-api/**`, `backend/axon-service/**`, `backend/memory-adapter/**`, `backend/knowledge-*/**`.

### Acceptance criteria (from SCOPE_PACKET)

1. **AC1** Deterministic output per `(plan_id, task_id, cutoff_timestamp)`. Byte-identical re-render.
2. **AC2** Citations link to `event_id`s (`[[event:<id>]]`) on every rendered fact.
3. **AC3** Idempotent publish; diff-only writes (second publish == 0 writes).
4. **AC4** Exposes `GET /synth/vault/changes?since=<ts>` and `GET /synth/show?plan_id=...[&task_id=...][&format=json|markdown]`.
5. **AC5** `backend/synthesis/tests/test_generator.py` PASS (≥10 unit tests).
6. **AC6** Integration test: publish a sample vault to moto-backed S3, re-publish is no-op.
7. **AC7** Full suite: 367 → **380** passed; zero regressions.
8. **AC8** Allowlist enforced: raw `company_id` / `repository_id` / `model` never serialized; unknown payload keys silently dropped with zero log/stderr output.

## CONTEXT

- company_id: `IMC` · repository_id: `innermost` · handoff_id: `handoff_20260423_e5t2_synthesis_generator`
- wave 5; task E5-T2; branch `wave/5/canon-memory-v1`.
- Prior work (read before coding):
  - `docs/VAULT-LAYOUT.md` — immutable contract (E5-T1).
  - `backend/shared/canon_backend_shared/events.py::CanonicalEvent` — 15 envelope fields + `payload: Mapping`.
  - `backend/axon-service/axon_service/storage.py` — `boto3.client("s3")` injectable pattern.
  - `backend/axon-service/axon_service_tests/conftest.py` — `pytest.importorskip("moto")` + `mock_aws` scaffolding.
  - `backend/state-api/tests/conftest.py` — FastAPI `TestClient` + `app.dependency_overrides` pattern.
  - `src/canon_systems/retrieval_telemetry.py` — `from canon_backend_shared.events import CanonicalEvent` discipline.
  - `infra/terraform/modules/axon-snapshots/{main,variables,outputs}.tf` + `README.md` — S3 module template.

## REPOSITORY

**Files to create (14):** 4 modules (`redaction.py`, `sources.py`, `generator.py`, `publisher.py`), 3 test files, `tests/__init__.py`, `tests/_fakes.py`, `tests/conftest.py`, 4 terraform files under `infra/terraform/modules/synthesis-vault/`.

**Files to modify (additive, 5):** `backend/synthesis/synthesis/__init__.py`, `backend/synthesis/synthesis/main.py`, `backend/synthesis/pyproject.toml`, `backend/synthesis/README.md`, `CHANGELOG.md`, `docs/SYSTEM-WORKFLOW.md`.

**Forbidden surfaces:** `docs/VAULT-LAYOUT.md`, `backend/shared/**`, `src/canon_systems/**`, `backend/state-api/**`, `backend/axon-service/**`, `backend/memory-adapter/**`, `backend/knowledge-*/**`, `infra/terraform/main.tf`, any existing test file outside `backend/synthesis/tests/`.

## IMPLEMENTATION SPECIFICATION

### 1. `backend/synthesis/synthesis/redaction.py`

Pure `CanonicalEvent → SafeEvent` projection. Zero I/O. Zero logging. Zero wallclock.

```python
"""E5-T1 allowlist redaction: CanonicalEvent → SafeEvent projection.

Sole enforcement point for docs/VAULT-LAYOUT.md §5. Unknown fields and unknown
payload keys are silently dropped — no logs, no warnings, no telemetry.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping
from canon_backend_shared.events import CanonicalEvent

SAFE_ENVELOPE_FIELDS: frozenset[str] = frozenset({
    "schema_version", "event_id", "parent_event_id", "event_type",
    "plan_id", "task_id", "handoff_id", "agent_name", "timestamp", "state_version",
})
SCOPE_SAFE_ALIASED: frozenset[str] = frozenset({
    "company_id", "repository_id", "agent_run_id", "actor_id",
})
FRONTMATTER_ANCHOR_ORDER: tuple[str, ...] = ("schema_version", "event_id")


@dataclass(frozen=True)
class SafeEvent:
    frontmatter: dict[str, Any]
    path_shorthashes: dict[str, str]
    payload: dict[str, Any]
    event_type: str
    event_id: str


def shorthash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def project_payload(event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if event_type == "retrieval_breakdown":
        return _project_retrieval_breakdown(payload)
    if event_type == "lease_stall_detected":
        return _project_lease_stall(payload)
    if event_type == "checkpoint_write":
        return _project_checkpoint_write(payload)
    return {}


def _project_retrieval_breakdown(payload): ...
def _project_lease_stall(payload): ...  # drop diagnostic.owner; compute owner_suffix
def _project_checkpoint_write(payload): ...  # drop lease_token, body

def project_safe(ev: CanonicalEvent) -> SafeEvent: ...
```

**Rules:** never include `model` anywhere in `SafeEvent`; never include raw ids in frontmatter (only shorthash/suffix in `path_shorthashes`); unknown event_type → empty dict, no log/warn/raise.

### 2. `backend/synthesis/synthesis/sources.py`

```python
"""Event acquisition seam: InMemoryEventSource + Wave-5-waived StateApiEventSource stub."""
from __future__ import annotations
from typing import Iterable, Protocol
from canon_backend_shared.events import CanonicalEvent


class SourceError(RuntimeError): ...


class EventSource(Protocol):
    def iter_events(self, *, plan_id: str | None, task_id: str | None,
                    cutoff_timestamp: str) -> Iterable[CanonicalEvent]: ...


class InMemoryEventSource:
    def __init__(self, events: list[CanonicalEvent]) -> None: ...
    def iter_events(self, *, plan_id, task_id, cutoff_timestamp): ...  # filter + yield


class StateApiEventSource:
    def __init__(self, *, base_url: str, fetch_fn=None) -> None: ...
    def iter_events(self, *, plan_id, task_id, cutoff_timestamp):
        if self._fetch_fn is None:
            raise SourceError(
                "wave-5 waiver: state-api event query endpoint pending; "
                "use InMemoryEventSource or CLI-fed JSONL for now"
            )
```

### 3. `backend/synthesis/synthesis/generator.py`

Pure; **NO `datetime`/`time` imports** (enforced by `test_no_wallclock_reads_in_generator_module`).

```python
"""Deterministic CanonicalEvent → VaultBundle generator. Pure; no network/S3/wallclock."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Iterable, Mapping
from canon_backend_shared.events import CanonicalEvent
from synthesis.redaction import FRONTMATTER_ANCHOR_ORDER, SafeEvent, project_safe, shorthash


@dataclass(frozen=True)
class VaultBundle:
    pages: dict[str, bytes]
    write_once_keys: frozenset[str] = field(default_factory=frozenset)
    def keys(self) -> Iterable[str]: return self.pages.keys()


def generate_vault(events: Iterable[CanonicalEvent], *, company_id: str,
                   repository_id: str, cutoff_timestamp: str) -> VaultBundle: ...

def render_frontmatter(safe: SafeEvent) -> str: ...
def render_task_page(safe, context): ...
def render_plan_page(plan_id, safe_events): ...
def render_agent_run_page(safe): ...
def render_retrieval_breakdown_page(safe): ...
def render_stall_page(safe): ...  # owner_suffix only; never raw owner
def render_opaque_page(safe): ...  # include `dropped_payload: true` marker

def _wire_wikilinks(pages): ...  # cross-linker: raw id → [[event:<id>]]
def _render_indices(safe_events): ...  # vault-librarian: _index/by-*.md
def _render_obsidian_seed(): ...  # .obsidian/{app,workspace,graph}.json (write_once)
def _render_readme(company_id, repository_id): ...  # README.md; no raw ids
```

### 4. `backend/synthesis/synthesis/publisher.py`

```python
"""S3 publisher with SHA-256 content-hash sidecar diff-only writes."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable
from botocore.exceptions import ClientError
from synthesis.generator import VaultBundle


@dataclass(frozen=True)
class PublishResult:
    written: int
    skipped: int
    keys_written: list[str] = field(default_factory=list)


class SynthesisPublisher:
    def __init__(self, *, bucket: str, s3_client: Any, prefix: str) -> None:
        self._bucket = bucket
        self._s3 = s3_client
        self._prefix = prefix.rstrip("/")

    def publish(self, bundle: VaultBundle, *, write_once: Iterable[str] = ()) -> PublishResult: ...
    def list_remote_hashes(self, sub_prefix: str = "") -> dict[str, str]: ...
    def put_page(self, key: str, body: bytes) -> None: ...  # ContentType='text/markdown; charset=utf-8'
    def put_attachment(self, key: str, body_bytes: bytes) -> None: ...  # ContentType='application/json'

    @staticmethod
    def _content_hash(body: bytes) -> str:
        return hashlib.sha256(body).hexdigest()
```

Idempotence: second `publish()` same bundle → `PublishResult(written=0, skipped=N)`. `.obsidian/` write_once: skip if present, write if absent.

### 5. `backend/synthesis/synthesis/__init__.py` (replace 1-liner)

```python
"""synthesis package."""
from synthesis.generator import VaultBundle, generate_vault
from synthesis.publisher import PublishResult, SynthesisPublisher
from synthesis.redaction import SafeEvent, project_safe, shorthash
from synthesis.sources import EventSource, InMemoryEventSource, SourceError, StateApiEventSource

__all__ = [
    "EventSource", "InMemoryEventSource", "PublishResult", "SafeEvent",
    "SourceError", "StateApiEventSource", "SynthesisPublisher",
    "VaultBundle", "generate_vault", "project_safe", "shorthash",
]
```

### 6. `backend/synthesis/synthesis/main.py` (replace, preserve /healthz)

```python
"""FastAPI entrypoint: healthz + /synth/vault/changes + /synth/show."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response
from synthesis.generator import generate_vault
from synthesis.redaction import project_safe
from synthesis.sources import EventSource, InMemoryEventSource

app = FastAPI(title="synthesis", version="0.1.0")


def get_event_source() -> EventSource:
    return InMemoryEventSource(events=[])


def _parse_iso8601(value: str) -> str:
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "synthesis"}


@app.get("/synth/vault/changes")
def synth_vault_changes(
    since: str = Query(...),
    source: EventSource = Depends(get_event_source),
) -> dict[str, Any]:
    try:
        cutoff = _parse_iso8601(since)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid since: {exc}") from exc
    events = list(source.iter_events(plan_id=None, task_id=None, cutoff_timestamp=cutoff))
    # Build deterministic changes list sorted by (timestamp, event_id).
    ...


@app.get("/synth/show")
def synth_show(
    plan_id: str = Query(...),
    task_id: str | None = Query(default=None),
    format: str = Query(default="json", pattern="^(json|markdown)$"),
    source: EventSource = Depends(get_event_source),
) -> Any:
    # Fetch + render scoped page; 404 on empty-after-redaction.
    # Return JSON envelope `{"vault_key": ..., "schema_version": 1, "markdown": ...}`
    # OR raw bytes with ContentType='text/markdown; charset=utf-8' when format=markdown.
    ...
```

**NOTE:** `datetime` import IS allowed in `main.py` (not in the generator/redaction core). The wallclock-free rule only applies to `generator.py` + `redaction.py` + `sources.py`.

### 7-12. Test files

**`tests/__init__.py`** — empty.

**`tests/_fakes.py`** — `DictS3Client` with `head_object` (raises `ClientError` code="404" when missing), `put_object`, `list_objects_v2`, `get_paginator`.

**`tests/conftest.py`** — fixtures `event_factory` (deterministic defaults, no wallclock), `dict_s3_client`, `moto_s3_bucket` (`pytest.importorskip("moto")`), `client` (FastAPI TestClient with `app.dependency_overrides[get_event_source]`).

**`tests/test_generator.py`** (≥10 tests) — full verbatim from cursor-pilot authoring session (see pilot reference below; implementer may also improvise tests as long as ≥10 pass and all ACs are covered):

1. `test_generator_deterministic_byte_identical_output` — same input → identical output.
2. `test_generator_event_ordering_stable_across_permutations` — shuffled input → identical output.
3. `test_redaction_drops_model_field_from_frontmatter` — `model` absent from bundle bytes/frontmatter.
4. `test_redaction_never_emits_raw_company_id_or_repository_id` — neither string appears in keys/values; only shorthashes.
5. `test_redaction_silently_drops_unknown_payload_keys` — unknown payload keys vanish; `caplog.records == []`.
6. `test_redaction_unknown_event_type_routes_to_opaque_with_dropped_payload_marker` — unknown type → `events/opaque/<event_id>.md` with `dropped_payload: true`.
7. `test_citations_present_for_every_rendered_fact` — every non-index/non-README page body contains ≥1 `[[event:<id>]]`.
8. `test_shorthashes_are_deterministic_sha256_prefix` — `shorthash("IMC") == sha256(b"IMC").hexdigest()[:8]`.
9. `test_frontmatter_key_order_anchors_first_then_alphabetical` — parse YAML; keys[:2] == ["schema_version","event_id"]; rest sorted.
10. `test_no_wallclock_reads_in_generator_module` — source grep: no `datetime.now`, no `import datetime`, no `import time` in `generator.py`/`redaction.py`.
11. (optional) `test_allowlist_frozensets_match_vault_layout_spec_section_5` — `len(SAFE_ENVELOPE_FIELDS)==10`, `"model" not in` either frozenset.

**`tests/test_endpoints.py`** (≥2 tests):
- `test_synth_vault_changes_returns_deterministic_change_list` — 200 + `schema_version==1` + sorted `changes[]`; 422 on junk `since`.
- `test_synth_show_returns_json_envelope_and_markdown_alt_format` — JSON envelope default; `?format=markdown` returns raw body + `Content-Type: text/markdown`; 404 on empty-after-redaction.

**`tests/test_publisher_moto.py`** (≥1 test):
- `test_publish_is_idempotent_no_duplicate_writes` — `pytest.importorskip("moto")`; first publish writes N; second writes 0, skips N; `head_object.Metadata["content-hash"]` is 64 hex.

### 13. `backend/synthesis/pyproject.toml` (replace)

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "synthesis"
version = "0.1.0"
description = "Synthesis / vault generation service (E5-T2 deterministic generator + publisher)."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "Proprietary" }
dependencies = [
  "canon-backend-shared",
  "fastapi>=0.115,<1",
  "uvicorn>=0.30,<1",
  "pydantic>=2.7,<3",
  "boto3>=1.35,<2",
]

[project.optional-dependencies]
test = [
  "pytest>=8.2,<9",
  "moto[s3]>=5.0,<6",
  "httpx>=0.27,<1",
]

[tool.setuptools]
package-dir = { "" = "." }

[tool.setuptools.packages.find]
where = ["."]
include = ["synthesis*"]
```

**IMPORTANT:** verify existing `backend/synthesis/pyproject.toml` current content; if fields differ (e.g. different version or existing deps), merge additively rather than clobbering.

### 14. `backend/synthesis/README.md` — append section

```markdown

## Infra requirements (operator-applied)

Depends on the **unwired** `infra/terraform/modules/synthesis-vault/` module (Precedent §1 — `cloud_execution_deferred`).

| Variable | Description |
| --- | --- |
| `SYNTHESIS_S3_BUCKET` | Target bucket (module output `bucket_name`). |
| `AWS_REGION` | AWS region (default `us-east-1`). |
| `STATE_API_BASE_URL` | Reserved for Wave-5-waived `StateApiEventSource`; no-op in CI. |

CI runs against an in-process `DictS3Client` fake + one `moto`-backed integration test. No live AWS credentials required.
```

### 15. `CHANGELOG.md` — prepend E5-T2 bullet above E5-T1

```markdown
- **E5-T2** `backend/synthesis` deterministic vault generator + publisher: five new modules (`redaction.py`, `sources.py`, `generator.py`, `publisher.py`, plus additive routes on `main.py`) project `CanonicalEvent` rows through the E5-T1 15-field allowlist into an Obsidian-compatible S3 vault. `project_safe()` enforces SAFE / SCOPE-SAFE-aliased / DROPPED per `docs/VAULT-LAYOUT.md §5` (raw `company_id`/`repository_id`/`model` never serialized; unknown payload keys silently dropped with zero log/stderr output). `generate_vault()` is pure (no network, no S3, no wallclock — enforced by source-grep test), sorts events by `(timestamp, event_id)`, emits frontmatter anchors first then alphabetical, and absorbs the cross-linker (`_wire_wikilinks`) + vault-librarian (`_render_indices`) obsidian-mind behaviors. `SynthesisPublisher` writes diff-only via SHA-256 content-hash sidecar metadata against injectable `boto3.client("s3")`; `.obsidian/` seed files are write-once. Two new FastAPI routes: `GET /synth/vault/changes?since=<iso8601>` (422 on junk, deterministic sorted change list) and `GET /synth/show?plan_id=...[&task_id=...][&format=json|markdown]` (JSON envelope default, raw markdown alt, 404 on empty). Tests: 10 in `tests/test_generator.py` + 2 in `tests/test_endpoints.py` + 1 moto idempotence in `tests/test_publisher_moto.py`. Suite 367 → 380 passed. Deps: `boto3>=1.35,<2` prod; `pytest>=8.2,<9`, `moto[s3]>=5.0,<6`, `httpx>=0.27,<1` test-only. New unwired terraform module `infra/terraform/modules/synthesis-vault/` captures infra under Precedent §1 `cloud_execution_deferred` — NOT wired into `infra/terraform/main.tf`.
```

### 16. `docs/SYSTEM-WORKFLOW.md` — insert after E5-T1 bullet in §3

```markdown
- **E5-T2 synthesis generator + publisher:** `backend/synthesis` renders `CanonicalEvent` rows deterministically into the E5-T1 S3 vault layout via `redaction.py` (15-field allowlist + per-event-type payload catalogue), `sources.py` (`InMemoryEventSource` for tests/E5-T3 CLI; `StateApiEventSource` Wave-5-waived stub), `generator.py` (pure `events → VaultBundle`; no wallclock, no S3, no network), `publisher.py` (SHA-256 content-hash diff-only writes via injectable `boto3.client("s3")`, `.obsidian/` write-once), and two new FastAPI routes (`GET /synth/vault/changes`, `GET /synth/show`). Suite +13 (367 → 380). Unwired terraform module `infra/terraform/modules/synthesis-vault/` under Precedent §1 `cloud_execution_deferred` waiver.
```

### 17. Terraform stub — `infra/terraform/modules/synthesis-vault/` (4 files)

**`main.tf`** — S3 bucket + versioning + SSE-AES256 + public_access_block all-true + iam_policy_document allowing publisher role PutObject/GetObject/ListBucket/DeleteObject and optional `dynamic` reader role statement for `vault_web_reader_role_arn` (GetObject/ListBucket). Mirror `infra/terraform/modules/axon-snapshots/main.tf` style.

**`variables.tf`** — `name_prefix` (string), `publisher_role_arn` (string), `vault_web_reader_role_arn` (string, default null).

**`outputs.tf`** — `bucket_name`, `bucket_arn`, `bucket_regional_domain_name`.

**`README.md`** — purpose, cloud-apply waiver, inputs/outputs tables, security posture (versioning on, object-lock off, SSE-S3, public-access-block all 4 true, single-writer IAM, per-company `s3:prefix` deferred to E5-T4), `terraform import` example.

## REASONING

1. Read scoper.md end-to-end.
2. Read `docs/VAULT-LAYOUT.md` to re-confirm §5 (15-field allowlist), §6 (payload catalogue), §7 (citations), §8 (determinism/idempotence).
3. Read `CanonicalEvent` dataclass.
4. Read `backend/axon-service` storage + moto conftest as template.
5. Implement `redaction.py` → `sources.py` → `generator.py` → `publisher.py` → `__init__.py` exports → `main.py` routes.
6. Install test deps: `pip install -e 'backend/synthesis[test]'`.
7. Write 3 test files; focus: `pytest backend/synthesis/tests -q` → 13 passed.
8. Full suite: `pytest -q` → **380 passed**.
9. Add terraform stub (4 files). Do NOT wire into root.
10. Living-spec edits (CHANGELOG/SYSTEM-WORKFLOW/backend README).
11. Emit `HANDOFF_TO_QA` to `.cursor/handoffs/canon-memory-v1/E5-T2/implementer.md`.

## OUTPUT FORMAT

Implementer packet with:
- `handoff_id: handoff_20260423_e5t2_synthesis_generator`
- `task_id: E5-T2`
- `branch: wave/5/canon-memory-v1`
- `files_created:` 14 paths · `files_modified:` 5 paths
- `acceptance_criteria:` AC1-AC8, each `status: MET`, `evidence`, `run_result`, `covering_tests` (block-style YAML; bare pytest node IDs or bare file paths; every AC ≥1 entry; NO `shell::`/`manual::` prefixes).
- `suite_result: total=380 passed=380 skipped=0`.

## STOP CONDITIONS

Stop and escalate if:
1. `docs/VAULT-LAYOUT.md` drifted from scoper expectations (schema_version 1 + 15-field allowlist).
2. `CanonicalEvent` dataclass grew or removed fields since scoper wrote.
3. Python version bump beyond `>=3.10` required.
4. Any forbidden surface would need editing.
5. Full suite regresses below 367.
6. Moto test requires live AWS (violates Wave-5 waiver).
7. `test_no_wallclock_reads_in_generator_module` fails because `generator.py` or `redaction.py` imports `datetime`/`time`.
