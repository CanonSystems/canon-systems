HANDOFF_TO_QA
  handoff_id: "structured-resume-task-memory"
  plan_id: "structured-resume-task-memory"
  task_id: "SRTM-T1"
  workstream_id: "ws-main"
  acceptance_criteria_covered:
    - criterion: "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md explicitly defines Phase 1 deliverables and testable acceptance criteria for the documentation/schema-lock task."
      evidence_files:
        - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md:299-348"
      evidence_tests:
        - "rg -n \"Phase 1: Documentation and schema lock|Deliverables:|Acceptance criteria:\" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md (exit 0)"
    - criterion: "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md includes inline JSON schema drafts or equivalent structured field contracts for session_handoff, plan, epic, task, task_update, and decision, without requiring standalone JSON schema files."
      evidence_files:
        - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md:350-608"
      evidence_tests:
        - "rg -n \"session_handoff|task_update|decision|\\\"schema_version\\\"|\\\"required\\\"\" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md (exit 0)"
        - "manual::six fenced JSON schema draft blocks for session_handoff, plan, epic, task, task_update, and decision"
    - criterion: "docs/SYSTEM-WORKFLOW.md contains a concise section describing the structured task/session memory model, retrieval precedence, and relationship to the existing checkpoint/resume and canonical memory planes, with a link to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
      evidence_files:
        - "docs/SYSTEM-WORKFLOW.md:229-248"
      evidence_tests:
        - "rg -n \"structured task|session memory|STRUCTURED-RESUME-TASK-MEMORY-PLAN|session_handoff|task_update|retrieval precedence\" docs/SYSTEM-WORKFLOW.md (exit 0)"
    - criterion: "docs/ROADMAP.md remains linked to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
      evidence_files:
        - "docs/ROADMAP.md:15"
      evidence_tests:
        - "rg -n \"STRUCTURED-RESUME-TASK-MEMORY-PLAN.md\" docs/ROADMAP.md (exit 0)"
    - criterion: "The task changes only markdown documentation and packet artifacts; no Python, Terraform, JSON, generated memory files, or runtime implementation files are included."
      evidence_files:
        - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md:1-744"
        - "docs/ROADMAP.md:15"
        - "docs/SYSTEM-WORKFLOW.md:229-248"
        - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/scoper.md:1-123"
        - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/cursor-pilot.md:1-225"
      evidence_tests:
        - "git status --short confirmed SRTM-T1 target paths are markdown docs/packets; unrelated dirty files also exist outside scope."
        - "test \"$(git diff --name-only -- '*.json' | wc -l | tr -d ' ')\" = \"0\" failed only because unrelated .canon/memory/capture-latest.json was already dirty/outside scope."
        - "git diff --name-only allowlist check reports unrelated .canon/memory/capture-latest.json and infra/terraform/variables.tf outside SRTM-T1 scope."
  summary: "SRTM-T1 locked the structured resume/task memory Phase 1 documentation contract: the detailed plan now has explicit deliverables, acceptance criteria, and six inline schema drafts; SYSTEM-WORKFLOW documents the planned typed retrieval contract; ROADMAP links to the plan."
  decisions:
    - "Keep Phase 1 markdown-only and embed schema drafts inline instead of creating standalone JSON schema files."
    - "Describe typed task/session memory as planned behavior, not shipped runtime behavior."
    - "Keep Jira/Linear-style workflow integration as a later external-workflow phase; Canon remains the source of truth for agent execution memory and rationale."
  next_actions:
    - "Run qa-gate for SRTM-T1 against this aggregate handoff."
    - "If QA passes, run release-orchestrator for documentation-only release status."
    - "Future implementation should start Phase 2: typed artifact writer and reader MVP."
  open_questions:
    - "Whether typed artifacts should be represented as new knowledge API artifact_type values or via a task-specific facade remains deferred to Phase 2."
    - "Whether session_handoff creation should be manual-only or a rolling capture-hook draft remains deferred to Phase 3."
  notes:
    - "Retrieval degradation: graph, state, and AWS-backed canonical lookup degraded because AWS Secrets Manager credentials/state-api/AXON URL were unavailable; implementation was grounded in scoper packet and local markdown files."
    - "Workspace contains unrelated dirty files outside SRTM-T1: .canon/memory/capture-latest.json, infra/terraform/variables.tf, and scripts/clone_memory_layer_secret.py."
END_HANDOFF_TO_QA
