<!-- CURSOR_PILOT_PROMPT: E3-T4 graph-first retrieval policy -->

# E3-T4 Cursor-Pilot Prompt

## ROLE
You are the implementer for Canon Memory Platform v1, Wave 3, Task E3-T4. Work on branch `wave/3/canon-memory-v1` (tip 3e9093d).

## TASK
Encode the graph-first retrieval policy from build plan §Wave 3 into (1) the authoritative `memory-layer-defaults.mdc` rule and (2) the three coder-facing agent templates (scoper, cursor-pilot, implementer). Add 5 new assertions to `tests/test_agent_templates.py`. Update CHANGELOG / README / SYSTEM-WORKFLOW additively.

## CONTEXT

### Canonical retrieval order
`graph → state → canonical → file`. Concrete tool invocations in order:
1. `canon graph query` (+ `canon graph impact` where appropriate) — axon-service GET.
2. `canon checkpoint read` — state-api checkpoint read.
3. `canon ask "<q>"` / `.canon/memory/context-latest.md` — canonical layer.
4. Raw file reads / repo exploration — last resort only.

### Fail-open semantics
If `AXON_SERVICE_URL` / `AXON_SERVICE_TOKEN` are unset, or if `canon graph query` exits with code 2/3/4/5, agents fall back gracefully to `state → canonical → file`. No retrieval step is a hard blocker.

### Prior work reference
- `memory-layer-defaults.mdc` already ends with `## Checkpoint contract (required)` (see lines ~199-205). Append the new `## Retrieval policy (required)` section AFTER that, preserving all existing content.
- `scoper.md` / `cursor-pilot.md` / `implementer.md` already contain `## Checkpoint (read-before / write-after) contract` sections. Add a new `## Graph-first retrieval (required)` section adjacent (either just before or just after the Checkpoint contract section). Do not reflow or reorder other content.

## REPOSITORY

### Files to modify (exactly 6)
1. `src/canon_systems/templates/rules/memory-layer-defaults.mdc` — append `## Retrieval policy (required)` section.
2. `src/canon_systems/templates/agents/scoper.md` — add `## Graph-first retrieval (required)` section.
3. `src/canon_systems/templates/agents/cursor-pilot.md` — add `## Graph-first retrieval (required)` section (must additionally cite `canon graph impact`).
4. `src/canon_systems/templates/agents/implementer.md` — add `## Graph-first retrieval (required)` section.
5. `tests/test_agent_templates.py` — add 5 new test functions (keep all existing tests unchanged).
6. `CHANGELOG.md` — prepend E3-T4 bullet to TOP of `[Unreleased] ### Added`.
7. `README.md` — additive one-line mention (no table reflow).
8. `docs/SYSTEM-WORKFLOW.md` — additive bullet in §6.

(Total: 8 files. Living-spec trio counts as 3; core work is 5.)

### Forbidden surfaces
backend/**, infra/**, src/canon_systems/{cli,checkpoint_cli,graph_indexer,flow_audit,qa_validate,memory_health,checkpoints}.py, .cursor/rules/**, .cursor/plans/**, any test file other than `tests/test_agent_templates.py`, any template other than the 4 listed above.

## IMPLEMENTATION SPECIFICATION

### `memory-layer-defaults.mdc` — append this section (place AFTER the final `## Checkpoint contract (required)` section)

```
## Retrieval policy (required)

For coding work (multi-file changes, refactors, new endpoints, test authoring),
consult memory sources in this fixed order before making assumptions or reading
arbitrary files:

**graph → state → canonical → file**

1. **Graph (axon-service)** — structural retrieval. Run
   `canon graph query --company-id <company_id> --repository-id <repository_id> --commit-sha <sha> --q "<scoped question>"`
   and, when investigating blast radius, `canon graph impact --symbol <fqname>`.
   Cite `results[].source_spans` as evidence in downstream packets.
2. **State (state-api)** — operational context. Run
   `canon checkpoint read --company-id <company_id> --repository-id <repository_id> --plan-id <plan_id> --task-id <task_id> --workstream-id <workstream_id>`
   to load the latest phase checkpoint before beginning work.
3. **Canonical layer** — decision history. Read
   `.canon/memory/context-latest.md` for the preflight summary, and/or run
   `canon ask "<question>"` for targeted lookups across canonical events and
   MemPalace, scoped to this repo.
4. **File reads** — last resort. Only open files that were cited by steps 1-3,
   or whose existence was explicitly required by the user prompt. Broad
   repo-wide greps or speculative `ls -R` are discouraged when steps 1-3
   return usable evidence.

### Fail-open fallback

If `AXON_SERVICE_URL` or `AXON_SERVICE_TOKEN` are unset, or if
`canon graph query` exits with code 2/3/4/5 (usage, 4xx, 5xx, transport), fall
back to `state → canonical → file`. No retrieval step is a hard blocker; record
the degradation in the HANDOFF_TO_QA `notes:` field so reviewers can see which
sources were consulted.

The order `graph → state → canonical → file` is the single canonical phrasing;
do not paraphrase it elsewhere.
```

### `scoper.md` — add this subsection (adjacent to the existing Checkpoint contract section)

```
## Graph-first retrieval (required)

Before broad repo exploration, run the graph retrieval step:

```
canon graph query --company-id <company_id> --repository-id <repository_id> \
  --commit-sha <current_sha> --q "<scope-question>"
```

Cite `results[].source_spans` in the SCOPE_PACKET.prior_work_references block
when the hits are usable. If the axon-service is unset or returns 2/3/4/5, fall
back to state (`canon checkpoint read`) → canonical (`canon ask`) → file reads,
and record the degradation in the scoper packet's `notes:` field.

See also: `## Retrieval policy (required)` in
`src/canon_systems/templates/rules/memory-layer-defaults.mdc`.
```

### `cursor-pilot.md` — add this subsection

```
## Graph-first retrieval (required)

Before finalizing the target surface in the CURSOR_PILOT_PROMPT, consult:

```
canon graph query  --company-id <c> --repository-id <r> --commit-sha <sha> --q "<scope>"
canon graph impact --company-id <c> --repository-id <r> --commit-sha <sha> --symbol <target>
```

Use `canon graph impact` to enumerate blast radius for refactors and to surface
downstream symbols the implementer must not break. Fold the returned
`upstream`/`downstream` lists into the REPOSITORY section of the prompt.

Fail-open: if axon is unreachable or returns 2/3/4/5, fall through to
`canon checkpoint read` → `canon ask` → file reads; record degradation in
`notes:`.

See also: `## Retrieval policy (required)` in
`src/canon_systems/templates/rules/memory-layer-defaults.mdc`.
```

### `implementer.md` — add this subsection

```
## Graph-first retrieval (required)

Before broad repo exploration (repo-wide `grep`, speculative `ls -R`, opening
unrelated files), run:

```
canon graph query --company-id <c> --repository-id <r> --commit-sha <sha> --q "<current-task>"
```

and, when the task is a refactor, rename, or cross-file change:

```
canon graph impact --company-id <c> --repository-id <r> --commit-sha <sha> --symbol <target>
```

Cite `results[].source_spans` in `HANDOFF_TO_QA.acceptance_criteria[].evidence`
where applicable. If axon is unset or returns 2/3/4/5, fall back to
`canon checkpoint read` → `canon ask` → file reads and record the degradation
in the HANDOFF_TO_QA `notes:` field.

See also: `## Retrieval policy (required)` in
`src/canon_systems/templates/rules/memory-layer-defaults.mdc`.
```

### `tests/test_agent_templates.py` — add exactly these 5 new test functions (keep all existing tests unchanged)

```python
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
```

### `CHANGELOG.md` additive (prepend to TOP of `[Unreleased] ### Added`)

```
- **E3-T4** Retrieval policy codified as graph-first across canon rules + coder-facing agent templates. New `## Retrieval policy (required)` section in `memory-layer-defaults.mdc` fixes the order to `graph → state → canonical → file` with an explicit fail-open fallback to state/canonical/file when `AXON_SERVICE_URL` is unset or `canon graph query` fails. New `## Graph-first retrieval (required)` subsections in `scoper.md`, `cursor-pilot.md`, and `implementer.md` cite `canon graph query` (and `canon graph impact` for the pilot) as the first retrieval step before broad repo exploration. Five new assertions in `tests/test_agent_templates.py`.
```

### `README.md` additive
Add ONE new bullet immediately under the existing "agent templates" / canon-commands mention (no table reflow; no deletions). Suggested placement: append as a new line in whichever section introduces template wiring. Example wording:

```
- Graph-first retrieval is the default for all coder-facing agent templates (scoper/cursor-pilot/implementer). See `## Retrieval policy (required)` in `src/canon_systems/templates/rules/memory-layer-defaults.mdc`.
```

### `docs/SYSTEM-WORKFLOW.md` §6 additive bullet

```
- **Retrieval policy (graph-first)**: Coder-facing templates (scoper/cursor-pilot/implementer) consult memory sources in a fixed order — `graph → state → canonical → file`. Graph reads via `canon graph query`/`canon graph impact`, state via `canon checkpoint read`, canonical via `.canon/memory/context-latest.md` + `canon ask`. Fail-open when axon is unset or returns 2/3/4/5; degradation is recorded in the HANDOFF_TO_QA `notes:` field.
```

## REASONING
1. Read `memory-layer-defaults.mdc` end and confirm the Checkpoint section is the final section, so the new Retrieval policy appends cleanly.
2. Read each of the three agent templates and locate the Checkpoint contract subsection as an anchor for the new Graph-first retrieval subsection (add adjacent, additive).
3. Apply the eight file edits.
4. Run `pytest tests/test_agent_templates.py -q` — expect all prior tests + 5 new tests to PASS.
5. Run `pytest -q` from repo root — expect green.
6. Emit HANDOFF_TO_QA at `.cursor/handoffs/canon-memory-v1/E3-T4/implementer.md`.

## OUTPUT FORMAT
Emit a `HANDOFF_TO_QA` block with:
- `handoff_id: handoff_20260422_e3t4_graph_first_policy`
- `branch: wave/3/canon-memory-v1`
- `files_modified:` exact list (8 paths)
- `acceptance_criteria:` 12 ACs each with `status: MET`, `evidence`, `run_result`, and `covering_tests:` (YAML block-style list of `tests/test_agent_templates.py::<test>` entries or `<file>` grep checks as bare paths).
- `suite_result:` pytest summary lines for focused + full runs.

## STOP CONDITIONS
Stop and surface a blocker (do not improvise) if:
- The Checkpoint contract section has been removed or renamed in any of the 4 target templates.
- `tests/test_agent_templates.py` no longer uses `importlib.resources` lookups.
- Any forbidden-surface edit would be required.
