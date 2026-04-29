# Structured Resume and Task Memory Plan

This plan captures the product work needed to make Canon useful for both
crash-safe agent execution and human-friendly "pick up where we left off"
continuity across new Cursor chats.

It is intentionally separate from the completed Canon Memory Platform v1
backlog. The v1 platform already provides the core substrate: canonical
artifacts, per-phase checkpoints, leases, handoff packets, graph retrieval,
reports, and vault synthesis. This plan adds typed product surfaces on top of
that substrate so memory retrieval can answer task and resume questions
directly instead of relying on ranked transcript snippets.

## Problem

The current memory layer stores per-turn `memory_capture` artifacts. Those
captures can include prompt text, assistant output, decisions, next actions,
open questions, and a `conversation_id`.

That is useful raw material, but it does not reliably reconstruct a working
context in a new chat because:

- `canon ask` retrieves ranked snippets, not a complete session narrative.
- Preflight context lists current artifacts and MemPalace hits, but does not
  hydrate a structured handoff for the active topic.
- Plans and tasks are mostly represented as markdown or execution packets, not
  first-class retrievable product objects.
- A vague query like "where did we leave off" can collide with unrelated
  same-day captures.
- Conversation memory and execution recovery are currently adjacent but not
  unified in the operator experience.

The desired behavior is:

- If an agent or machine crashes during task execution, Canon can tell the next
  agent exactly which `(task_id, phase)` to resume.
- If a human starts a new chat later, Canon can surface the durable rationale,
  decisions, open questions, and next action for the topic.
- If someone asks about a task later, Canon can return the task definition,
  status history, implementation evidence, QA result, and unresolved follow-up.

## Design Principle

Keep agent execution context inside Canon first. Do not start by building an
internal Jira.

Canon should own:

- task and plan memory used by agents,
- crash recovery and phase checkpoints,
- rationale, decisions, and handoffs,
- retrieval behavior for new chats,
- evidence linking code, packets, QA, and release state.

Jira-like tooling should come later only for portfolio workflow concerns:

- human ownership,
- sprint and status reporting,
- approvals,
- dates and commitments,
- dashboards,
- cross-team prioritization.

If external workflow tooling is needed later, integrate it with Canon instead
of replacing Canon as the agent execution memory system.

## Target Memory Objects

Add typed artifacts to the canonical memory layer. These can be stored using
the existing artifact/event infrastructure, but retrieval must understand their
types and relationships.

### `session_handoff`

Purpose: Resume a human conversation or investigation in a new chat.

Core fields:

- `handoff_id`
- `company_id`
- `repository_id`
- `conversation_id`
- `topic`
- `summary`
- `where_we_left_off`
- `rationale`
- `decisions`
- `next_actions`
- `open_questions`
- `blockers`
- `important_files`
- `important_commands`
- `artifact_refs`
- `task_refs`
- `created_from_capture_ids`
- `updated_at`
- `confidence`

Retrieval use:

- Preferred for prompts like "continue this", "pick this up", "where did we
  leave off", "resume yesterday's CST thread", and similar phrasing.
- Should be returned as a coherent packet, not as snippets.

### `plan`

Purpose: Store an initiative-level plan as a durable, queryable object.

Core fields:

- `plan_id`
- `title`
- `objective`
- `scope`
- `non_goals`
- `assumptions`
- `epic_ids`
- `task_ids`
- `decision_ids`
- `status`
- `source_docs`
- `created_at`
- `updated_at`

Retrieval use:

- Preferred for prompts like "what is the plan for X", "show the roadmap for
  this initiative", or "what did we decide to build".

### `epic`

Purpose: Group tasks into value-oriented phases.

Core fields:

- `epic_id`
- `plan_id`
- `title`
- `user_value`
- `success_criteria`
- `task_ids`
- `depends_on`
- `status`
- `open_questions`

Retrieval use:

- Preferred for wave or epic-level progress questions.

### `task`

Purpose: Make task lookup deterministic by `task_id`.

Core fields:

- `task_id`
- `plan_id`
- `epic_id`
- `title`
- `goal`
- `acceptance_criteria`
- `depends_on`
- `can_run_parallel`
- `parallel_group`
- `done_signal`
- `status`
- `current_phase`
- `handoff_paths`
- `checkpoint_ref`
- `decision_ids`
- `task_update_ids`
- `qa_refs`
- `release_refs`

Retrieval use:

- Preferred for prompts like "what was E4-T2", "what did task X do", "what is
  left on task X", or "resume task X".

### `task_update`

Purpose: Store status transitions and evidence over time without mutating away
history.

Core fields:

- `task_update_id`
- `task_id`
- `plan_id`
- `phase`
- `status`
- `summary`
- `evidence_refs`
- `packet_paths`
- `test_results`
- `decisions`
- `open_questions`
- `created_at`
- `actor_id`
- `agent_run_id`

Retrieval use:

- Preferred for "what was done" and "why did this task move to blocked/pass".

### `decision`

Purpose: Preserve rationale independently from transcript prose.

Core fields:

- `decision_id`
- `title`
- `decision`
- `rationale`
- `alternatives_considered`
- `consequences`
- `scope_refs`
- `task_refs`
- `source_refs`
- `created_at`
- `actor_id`

Retrieval use:

- Preferred for "why did we choose X" and "what alternatives did we reject".

## Retrieval Rules

Retrieval should select the object type before ranking text.

Recommended precedence:

1. Explicit identifiers:
   - `task_id`, `plan_id`, `epic_id`, `handoff_id`, or `decision_id`.
   - Return the matching typed object first.
2. Resume intent:
   - Queries containing "resume", "continue", "pick up", "where did we leave
     off", or "what were we doing".
   - Return matching `session_handoff` objects first, then active `task`
     objects, then raw captures.
3. Task status intent:
   - Queries about "status", "done", "blocked", "what changed", or "what was
     implemented".
   - Return `task` plus latest `task_update` chain.
4. Rationale intent:
   - Queries starting with "why", "what did we decide", or "what was the
     rationale".
   - Return `decision` objects before transcript snippets.
5. Fallback:
   - Use existing canonical and MemPalace snippet retrieval.

Preflight should use the same classifier. When the user starts a turn that
looks like resume intent, `.canon/memory/context-latest.md` should include a
full `session_handoff` packet or task packet, not just artifact titles.

## CLI Surface

MVP commands:

```shell
canon handoff create --from-conversation-id <id> --topic "<topic>"
canon handoff resume "<query>"
canon task show <task_id> --plan-id <plan_id>
canon task update --task-id <task_id> --phase <phase> --status <status> --summary "<summary>"
canon plan import --file <path>
```

Later commands:

```shell
canon workflow sync --provider jira|linear --plan-id <plan_id>
canon workflow link --task-id <task_id> --external-id <key>
canon workflow status --plan-id <plan_id>
```

## Crash Recovery Behavior

Crash recovery for structured agent execution should continue to rely on the
existing operational-state plane:

1. Run `canon stall-watchdog scan`.
2. Run `canon resume`.
3. Reinvoke the returned `(task_id, phase)`.
4. Use persisted packets and checkpoint state as the source of truth.

The new task memory layer should mirror and explain that state for humans:

- `task.current_phase` tracks the latest checkpoint phase.
- `task_update` records each transition and evidence reference.
- `session_handoff` explains the human context around the work.

The operational-state plane remains authoritative for concurrency and resume.
The task memory layer is authoritative for human-readable task meaning and
history.

## Implementation Phases

### Phase 1: Documentation and schema lock

**Goal:** Make Phase 1 a reviewable contract: explicit deliverables, testable
acceptance criteria, and inline JSON Schema-style field contracts for the six
core artifact types. Phase 1 does **not** ship runtime behavior, CLI changes,
or standalone `*.json` schema files in the repository.

**Deliverables:**

1. This plan document with the Phase 1 sections below complete.
2. Inline JSON Schema draft fragments (embedded only in this markdown file) for
   `session_handoff`, `plan`, `epic`, `task`, `task_update`, and `decision`,
   each including `schema_version`, `type`, `required`, and `properties` as
   specified under [Phase 1 inline JSON Schema draft contracts](#phase-1-inline-json-schema-draft-contracts).
3. Retrieval precedence documented in `docs/SYSTEM-WORKFLOW.md` (coordinated
   with the broader SRTM documentation workstream).
4. Roadmap linked to this plan (`docs/ROADMAP.md`).
5. Explicit documentation of the boundary: Canon-owned execution memory vs.
   later Jira-like workflow integration (see [External Workflow Boundary](#external-workflow-boundary)).

**Acceptance criteria:**

1. **Taxonomy:** The object taxonomy for `session_handoff`, `plan`, `epic`,
   `task`, `task_update`, and `decision` is explicit in this document (see
   [Target Memory Objects](#target-memory-objects) and the inline schemas
   below).
2. **Workflow boundary:** The split between Canon-owned execution memory and
   out-of-scope Phase 1 external workflow tooling is documented (this plan plus
   roadmap cross-links); Phase 1 does not require Jira/Linear implementation.
3. **Contracts:** Each of the six artifact types has an inline schema draft in
   this file with a non-empty `required` array and a documented `schema_version`
   integer (see contracts below).
4. **No runtime change:** No Phase 1 task changes application code, tests,
   Terraform, or generated artifact pipelines; documentation and handoff packets
   only.
5. **Verification (automated spot-checks):** The following patterns are
   discoverable in this file for CI or local review:
   - Headings and labels: `Phase 1: Documentation and schema lock`, `Deliverables:`,
     `Acceptance criteria:` (exact substrings for `rg`).
   - Contracts: `session_handoff`, `task_update`, `decision`, `"schema_version"`,
     and `"required"` appear in the inline schema fences below.

**Review checks (human):**

- [ ] All six inline schema drafts parse as single JSON objects inside their
  fences (no trailing commas, valid JSON).
- [ ] Required fields match the intent described in [Target Memory
  Objects](#target-memory-objects).
- [ ] Operators can trace retrieval rules in [Retrieval Rules](#retrieval-rules)
  without assuming Phase 2+ behavior is implemented.

#### Phase 1 inline JSON Schema draft contracts

The fragments below are **draft** contracts for later storage and validation.
They are not separate schema files; embed and evolve them here until a later
phase promotes them to a canonical schema registry or tool-generated artifacts.

##### `session_handoff`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_version": 1,
  "title": "session_handoff",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "handoff_id",
    "company_id",
    "repository_id",
    "conversation_id",
    "topic",
    "summary",
    "where_we_left_off",
    "updated_at"
  ],
  "properties": {
    "handoff_id": { "type": "string", "minLength": 1 },
    "company_id": { "type": "string", "minLength": 1 },
    "repository_id": { "type": "string", "minLength": 1 },
    "conversation_id": { "type": "string" },
    "topic": { "type": "string", "minLength": 1 },
    "summary": { "type": "string" },
    "where_we_left_off": { "type": "string" },
    "rationale": { "type": ["string", "null"] },
    "decisions": { "type": "array", "items": { "type": "string" } },
    "next_actions": { "type": "array", "items": { "type": "string" } },
    "open_questions": { "type": "array", "items": { "type": "string" } },
    "blockers": { "type": "array", "items": { "type": "string" } },
    "important_files": { "type": "array", "items": { "type": "string" } },
    "important_commands": { "type": "array", "items": { "type": "string" } },
    "artifact_refs": { "type": "array", "items": { "type": "string" } },
    "task_refs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["plan_id", "task_id"],
        "properties": {
          "plan_id": { "type": "string" },
          "task_id": { "type": "string" }
        },
        "additionalProperties": true
      }
    },
    "created_from_capture_ids": { "type": "array", "items": { "type": "string" } },
    "updated_at": { "type": "string", "format": "date-time" },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

##### `plan`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_version": 1,
  "title": "plan",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "plan_id",
    "title",
    "objective",
    "status",
    "created_at",
    "updated_at"
  ],
  "properties": {
    "plan_id": { "type": "string", "minLength": 1 },
    "title": { "type": "string", "minLength": 1 },
    "objective": { "type": "string" },
    "scope": { "type": "string" },
    "non_goals": { "type": "array", "items": { "type": "string" } },
    "assumptions": { "type": "array", "items": { "type": "string" } },
    "epic_ids": { "type": "array", "items": { "type": "string" } },
    "task_ids": { "type": "array", "items": { "type": "string" } },
    "decision_ids": { "type": "array", "items": { "type": "string" } },
    "status": { "type": "string", "enum": ["draft", "active", "completed", "archived"] },
    "source_docs": { "type": "array", "items": { "type": "string" } },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" }
  }
}
```

##### `epic`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_version": 1,
  "title": "epic",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "epic_id",
    "plan_id",
    "title",
    "status"
  ],
  "properties": {
    "epic_id": { "type": "string", "minLength": 1 },
    "plan_id": { "type": "string", "minLength": 1 },
    "title": { "type": "string", "minLength": 1 },
    "user_value": { "type": "string" },
    "success_criteria": { "type": "array", "items": { "type": "string" } },
    "task_ids": { "type": "array", "items": { "type": "string" } },
    "depends_on": { "type": "array", "items": { "type": "string" } },
    "status": { "type": "string", "enum": ["draft", "active", "done", "blocked"] },
    "open_questions": { "type": "array", "items": { "type": "string" } }
  }
}
```

##### `task`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_version": 1,
  "title": "task",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "task_id",
    "plan_id",
    "title",
    "status",
    "current_phase"
  ],
  "properties": {
    "task_id": { "type": "string", "minLength": 1 },
    "plan_id": { "type": "string", "minLength": 1 },
    "epic_id": { "type": ["string", "null"] },
    "title": { "type": "string", "minLength": 1 },
    "goal": { "type": "string" },
    "acceptance_criteria": { "type": "array", "items": { "type": "string" } },
    "depends_on": { "type": "array", "items": { "type": "string" } },
    "can_run_parallel": { "type": "boolean" },
    "parallel_group": { "type": ["string", "null"] },
    "done_signal": { "type": "string" },
    "status": { "type": "string", "enum": ["todo", "in_progress", "blocked", "done", "cancelled"] },
    "current_phase": {
      "type": "string",
      "enum": [
        "scoper",
        "cursor-pilot",
        "implementer",
        "qa-gate",
        "release-orchestrator"
      ]
    },
    "handoff_paths": { "type": "array", "items": { "type": "string" } },
    "checkpoint_ref": { "type": ["string", "null"] },
    "decision_ids": { "type": "array", "items": { "type": "string" } },
    "task_update_ids": { "type": "array", "items": { "type": "string" } },
    "qa_refs": { "type": "array", "items": { "type": "string" } },
    "release_refs": { "type": "array", "items": { "type": "string" } }
  }
}
```

##### `task_update`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_version": 1,
  "title": "task_update",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "task_update_id",
    "task_id",
    "plan_id",
    "phase",
    "status",
    "summary",
    "created_at"
  ],
  "properties": {
    "task_update_id": { "type": "string", "minLength": 1 },
    "task_id": { "type": "string", "minLength": 1 },
    "plan_id": { "type": "string", "minLength": 1 },
    "phase": {
      "type": "string",
      "enum": [
        "scoper",
        "cursor-pilot",
        "implementer",
        "qa-gate",
        "release-orchestrator"
      ]
    },
    "status": { "type": "string" },
    "summary": { "type": "string" },
    "evidence_refs": { "type": "array", "items": { "type": "string" } },
    "packet_paths": { "type": "array", "items": { "type": "string" } },
    "test_results": { "type": "object", "additionalProperties": true },
    "decisions": { "type": "array", "items": { "type": "string" } },
    "open_questions": { "type": "array", "items": { "type": "string" } },
    "created_at": { "type": "string", "format": "date-time" },
    "actor_id": { "type": ["string", "null"] },
    "agent_run_id": { "type": ["string", "null"] }
  }
}
```

##### `decision`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_version": 1,
  "title": "decision",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "decision_id",
    "title",
    "decision",
    "created_at"
  ],
  "properties": {
    "decision_id": { "type": "string", "minLength": 1 },
    "title": { "type": "string", "minLength": 1 },
    "decision": { "type": "string" },
    "rationale": { "type": "string" },
    "alternatives_considered": { "type": "array", "items": { "type": "string" } },
    "consequences": { "type": "string" },
    "scope_refs": { "type": "array", "items": { "type": "string" } },
    "task_refs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["plan_id", "task_id"],
        "properties": {
          "plan_id": { "type": "string" },
          "task_id": { "type": "string" }
        },
        "additionalProperties": true
      }
    },
    "source_refs": { "type": "array", "items": { "type": "string" } },
    "created_at": { "type": "string", "format": "date-time" },
    "actor_id": { "type": ["string", "null"] }
  }
}
```

### Phase 2: Typed artifact writer and reader MVP

Deliverables:

- Canon CLI can write/read typed artifacts through the existing canonical
  artifact infrastructure.
- `canon plan import` can ingest an existing markdown/PROJECT_EXECUTION_PLAN
  document into `plan`, `epic`, and `task` objects.
- `canon task show` returns a complete task packet by id.

Acceptance criteria:

- Looking up a task by id does not require fuzzy transcript search.
- Imported plans are idempotent.
- Typed artifacts preserve tenant scope.

### Phase 3: Session handoff synthesis

Deliverables:

- `canon handoff create` groups captures by `conversation_id` and writes a
  `session_handoff`.
- Manual mode supports explicit summary, rationale, decisions, next actions,
  blockers, and open questions.
- Optional synthesis mode can summarize recent captures into a handoff packet.

Acceptance criteria:

- A new chat can resume from one `session_handoff` without needing the full
  transcript.
- Handoff packets link back to source capture ids.
- The handoff format distinguishes facts from assumptions.

### Phase 4: Retrieval and preflight integration

Deliverables:

- `canon ask` and preflight classify query intent.
- Resume-intent prompts hydrate `session_handoff` first.
- Explicit task-id prompts hydrate typed `task` plus latest updates.
- Snippet retrieval remains as fallback.

Acceptance criteria:

- "Where did we leave off on CST?" returns the CST handoff before unrelated
  same-day captures.
- "What was E4-T2?" returns the task object and update chain.
- Preflight context is useful enough to continue a new chat without manual doc
  pasting when a handoff exists.

### Phase 5: Agent-chain integration

Deliverables:

- Project planner emits typed `plan`, `epic`, and `task` artifacts.
- Scoper/cursor-pilot/implementer/qa-gate/release-orchestrator emit
  `task_update` and `decision` objects at phase boundaries.
- Release gates can validate that task memory exists for completed tasks.

Acceptance criteria:

- Every task has a durable human-readable history alongside checkpoints and
  handoff packets.
- `canon resume` remains operational-state based, but its output can include
  links to task memory.

### Phase 6: Jira-like workflow integration

Deliverables:

- Provider abstraction for Jira/Linear-style systems.
- Mapping between Canon tasks and external issues.
- Sync rules for status, owner, labels, due dates, and external URLs.
- Conflict policy defining which fields Canon owns and which fields the
  workflow system owns.

Acceptance criteria:

- Canon remains source of truth for agent rationale and execution evidence.
- External workflow tool remains source of truth for human PM fields.
- Sync is idempotent and does not overwrite rationale or evidence.

## External Workflow Boundary

Do not copy every Canon detail into Jira-like tools.

Canonical ownership:

- acceptance criteria,
- rationale,
- decisions,
- agent phase history,
- packet paths,
- QA/release evidence,
- session handoffs,
- retrieval metadata.

External workflow ownership:

- assignee,
- sprint or milestone,
- due date,
- priority,
- stakeholder approval,
- dashboard/status rollups,
- human-facing workflow state.

Shared fields:

- title,
- short description,
- labels,
- status summary,
- links between Canon `task_id` and external issue key.

## Open Questions

- Should typed artifacts be represented as new `artifact_type` values in the
  existing knowledge API, or should a task-specific API facade sit in front of
  the same store?
- Should `session_handoff` creation be manual-only at first, or should the
  capture hook opportunistically maintain a rolling draft?
- How much transcript body should be available behind a handoff for audit
  without overloading preflight context?
- Should task memory be published into the synthesis vault as operator-facing
  markdown pages by default?
- Which external workflow system should be integrated first, if any: Jira,
  Linear, GitHub Issues, or a small internal UI over Canon artifacts?

## Recommended Next Step

Start with Phase 1 and Phase 2 inside Canon. That gives durable task lookup and
explicit handoffs without creating another system of truth. Defer external
workflow integration until typed Canon task memory is working and the remaining
need is clearly human project management rather than agent continuity.
