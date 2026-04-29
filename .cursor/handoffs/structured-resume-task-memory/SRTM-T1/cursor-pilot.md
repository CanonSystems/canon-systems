CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Schema lock for structured resume and task memory: make the Phase 1 documentation contract durable and reviewable so later Canon implementation tasks can build structured resume and task memory without changing runtime behavior in this task.
</TASK>

<ACCEPTANCE_CRITERIA>
- docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md explicitly defines Phase 1 deliverables and testable acceptance criteria for the documentation/schema-lock task.
- docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md includes inline JSON schema drafts or equivalent structured field contracts for session_handoff, plan, epic, task, task_update, and decision, without requiring standalone JSON schema files.
- docs/SYSTEM-WORKFLOW.md contains a concise section describing the structured task/session memory model, retrieval precedence, and relationship to the existing checkpoint/resume and canonical memory planes, with a link to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md.
- docs/ROADMAP.md remains linked to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md.
- The task changes only markdown documentation and packet artifacts; no Python, Terraform, JSON, generated memory files, or runtime implementation files are included.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: CSC
- repository_id: canon-systems
- handoff_id: structured-resume-task-memory
- plan_id: structured-resume-task-memory
- task_id: SRTM-T1
- workstream_id: ws-main
- cursor_pilot_packet_expected_path: .cursor/handoffs/structured-resume-task-memory/SRTM-T1/cursor-pilot.md
- prior_work_references:
  - docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md: Detailed local plan already defines target objects, retrieval rules, implementation phases, and Phase 1 as documentation/schema lock.
  - docs/ROADMAP.md: Roadmap already links the structured resume and task memory plan and frames it as Canon-owned agent execution memory with later workflow integration.
  - docs/FINAL_STANDUP_CHECKLIST.md: Weakly relevant memory hit reinforcing that historical recall should use the memory-adapter boundary rather than placeholder stubs.
- retrieval_degradation_notes:
  - Graph retrieval degraded: `canon graph query` and `canon graph impact` failed because AWS Secrets Manager credentials were unavailable and AXON_SERVICE_URL/base URL was missing.
  - State retrieval degraded: `canon checkpoint read` for structured-resume-task-memory/SRTM-T1/ws-main returned transport connection refused at localhost:8080.
  - Canonical AWS-backed memory lookup degraded: `canon ask` reported AWS Secrets Manager credentials unavailable, though it returned one weak MemPalace hit.
  - Parent reported the secrets wizard was started and stopped while waiting for interactive input.
</CONTEXT>

<REPOSITORY>
- primaryLanguages: ["Python", "Markdown", "Terraform", "Shell"]
- testFramework: pytest for code tasks; SRTM-T1 verification is markdown review plus simple repository checks
- relevantFiles:
  - docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md
  - docs/SYSTEM-WORKFLOW.md
  - docs/ROADMAP.md
  - .cursor/handoffs/structured-resume-task-memory/SRTM-T1/scoper.md
  - .cursor/handoffs/structured-resume-task-memory/SRTM-T1/cursor-pilot.md
- mustNotBreak:
  - Do not modify runtime behavior, CLI commands, backend services, Terraform, tests, or generated memory artifacts in this task.
  - Do not include unrelated dirty files from parent start: .canon/memory/capture-latest.json, infra/terraform/variables.tf, scripts/clone_memory_layer_secret.py.
  - Preserve the docs/ROADMAP.md link to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md.
  - Keep external Jira/Linear-style workflow integration explicitly out of Phase 1 implementation scope.
- graphImpact:
  - unavailable due retrieval degradation above; treat the blast radius as docs-only and verify with git diff path checks.
</REPOSITORY>

<REASONING>
Implement this as a narrow markdown-only documentation lock. In `docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md`, sharpen the existing Phase 1 section from broad bullets into explicit deliverables, testable acceptance criteria, and review checks. Also add inline schema drafts or structured field contracts for exactly these six typed artifacts: `session_handoff`, `plan`, `epic`, `task`, `task_update`, and `decision`. Prefer fenced JSON examples or schema-like markdown tables embedded in the plan; do not create standalone `.json` schema files.

In `docs/SYSTEM-WORKFLOW.md`, add a concise forward-looking section near the memory/runtime, retrieval policy, or forward-plan area. It should describe the target structured task/session memory model, object-type-first retrieval precedence, and how this layer relates to existing checkpoint/resume, canonical memory, graph, and snippet fallback planes. Be explicit that this is a planned/contracted model for later tasks, not shipped runtime behavior.

For `docs/ROADMAP.md`, preserve the existing link to `docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md`. Only edit it if necessary to keep the link accurate; avoid broad roadmap rewriting.

AC traceability:
- AC1 maps to `docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md` Phase 1 deliverables, acceptance criteria, and review checks.
- AC2 maps to inline structured contracts for `session_handoff`, `plan`, `epic`, `task`, `task_update`, and `decision` in `docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md`.
- AC3 maps to a concise `docs/SYSTEM-WORKFLOW.md` section with retrieval precedence and relationship to checkpoint/resume plus canonical memory.
- AC4 maps to preserving the `docs/ROADMAP.md` link.
- AC5 maps to final git diff verification proving only markdown docs and handoff packets changed.

Verification commands to run after edits:
- `rg -n "Phase 1: Documentation and schema lock|Deliverables:|Acceptance criteria:" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md`
- `rg -n "session_handoff|task_update|decision|\"schema_version\"|\"required\"" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md`
- `rg -n "structured task|session memory|STRUCTURED-RESUME-TASK-MEMORY-PLAN|session_handoff|task_update|retrieval precedence" docs/SYSTEM-WORKFLOW.md`
- `rg -n "STRUCTURED-RESUME-TASK-MEMORY-PLAN.md" docs/ROADMAP.md`
- `test "$(git diff --name-only -- '*.json' | wc -l | tr -d ' ')" = "0"`
- `git diff --name-only | rg -v '^(docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md|docs/SYSTEM-WORKFLOW.md|docs/ROADMAP.md|\.cursor/handoffs/structured-resume-task-memory/SRTM-T1/(scoper|cursor-pilot)\.md)$' || true`

Risks and assumptions:
- Inline markdown schema drafts are sufficient for SRTM-T1; standalone JSON schema files are out of scope.
- The workflow spec addition must not imply Phase 2+ runtime behavior already exists.
- Existing dirty files outside the markdown scope must be left untouched and unstaged.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Lock Phase 1 plan schema documentation"
    acceptance_criteria:
      - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md explicitly defines Phase 1 deliverables and testable acceptance criteria for the documentation/schema-lock task."
      - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md includes inline JSON schema drafts or equivalent structured field contracts for session_handoff, plan, epic, task, task_update, and decision, without requiring standalone JSON schema files."
    implementation_targets:
      - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
    verification_tests:
      - "rg -n \"Phase 1: Documentation and schema lock|Deliverables:|Acceptance criteria:\" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
      - "rg -n \"session_handoff|task_update|decision|\\\"schema_version\\\"|\\\"required\\\"\" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
      - "manual review: six target artifact contracts are present and markdown-only"
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Document workflow retrieval model"
    acceptance_criteria:
      - "docs/SYSTEM-WORKFLOW.md contains a concise section describing the structured task/session memory model, retrieval precedence, and relationship to the existing checkpoint/resume and canonical memory planes, with a link to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
    implementation_targets:
      - "docs/SYSTEM-WORKFLOW.md"
    verification_tests:
      - "rg -n \"structured task|session memory|STRUCTURED-RESUME-TASK-MEMORY-PLAN|session_handoff|task_update|retrieval precedence\" docs/SYSTEM-WORKFLOW.md"
      - "manual review: section is forward-looking and does not claim shipped runtime behavior"
    depends_on: []
    can_run_parallel: true
  - id: "ws3"
    goal: "Preserve roadmap link"
    acceptance_criteria:
      - "docs/ROADMAP.md remains linked to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
    implementation_targets:
      - "docs/ROADMAP.md"
    verification_tests:
      - "rg -n \"STRUCTURED-RESUME-TASK-MEMORY-PLAN.md\" docs/ROADMAP.md"
    depends_on: []
    can_run_parallel: true
  - id: "ws4"
    goal: "Verify markdown-only scope"
    acceptance_criteria:
      - "The task changes only markdown documentation and packet artifacts; no Python, Terraform, JSON, generated memory files, or runtime implementation files are included."
    implementation_targets:
      - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
      - "docs/SYSTEM-WORKFLOW.md"
      - "docs/ROADMAP.md"
      - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/scoper.md"
      - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/cursor-pilot.md"
    verification_tests:
      - "test \"$(git diff --name-only -- '*.json' | wc -l | tr -d ' ')\" = \"0\""
      - "git diff --name-only | rg -v '^(docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md|docs/SYSTEM-WORKFLOW.md|docs/ROADMAP.md|\\.cursor/handoffs/structured-resume-task-memory/SRTM-T1/(scoper|cursor-pilot)\\.md)$' || true"
      - "manual review: unrelated dirty files are untouched"
    depends_on: ["ws1", "ws2", "ws3"]
    can_run_parallel: false
- parent_orchestration:
  - "Launch one `implementer` subagent per workstream marked can_run_parallel=true in a single parallel subagent call."
  - "Pin each coding subagent to `composer-2-fast`."
  - "For dependent streams, execute only after required upstream streams complete."
  - "After all workstreams finish, merge shard outputs into one HANDOFF_TO_QA block for qa-gate."
- execution_waves_example:
  - wave: 1
    stream_ids: ["ws1", "ws2", "ws3"]
  - wave: 2
    stream_ids: ["ws4"]
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the markdown documentation changes needed to satisfy all acceptance criteria, plus the required handoff output. Do not refactor unrelated docs. Do not modify runtime code, tests, Terraform, JSON files, generated memory artifacts, or the unrelated dirty files named in this prompt.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
When running a single implementation stream, emit this block verbatim (filled
in):

HANDOFF_TO_QA
  handoff_id: "structured-resume-task-memory"
  acceptance_criteria_covered:
    - criterion: "<exact AC text>"
      evidence_files:
        - "path/to/impl.ext:<line range>"
      evidence_tests:
        - "path/to/test.ext::<test name or command>"
  summary: "<1-2 sentences on what changed>"
  decisions:
    - "<notable design decision made during implementation>"
  next_actions:
    - "<follow-up work explicitly deferred>"
  open_questions:
    - "<anything still unclear that QA should verify>"
  notes:
    - "Retrieval degradation: graph, state, and AWS-backed canonical lookup degraded because AWS Secrets Manager credentials/state-api/AXON URL were unavailable; implementation was grounded in scoper packet and local markdown files."
END_HANDOFF_TO_QA

When running multiple parallel streams, each implementer must emit:

HANDOFF_TO_QA_SHARD
  handoff_id: "structured-resume-task-memory"
  shard_id: "<workstream id>"
  acceptance_criteria_covered:
    - criterion: "<exact AC text>"
      evidence_files:
        - "path/to/impl.ext:<line range>"
      evidence_tests:
        - "path/to/test.ext::<test name or command>"
  summary: "<1 sentence on this shard's changes>"
END_HANDOFF_TO_QA_SHARD

Parent must aggregate all shard outputs into one final `HANDOFF_TO_QA` before
invoking `qa-gate`.

Do not declare the task complete without the required handoff block(s).
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
