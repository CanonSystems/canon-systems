HANDOFF_TO_CURSOR_PILOT
  scope_summary: SRTM-T1 is a markdown-only schema and documentation lock for Phase 1 of the Structured Resume and Task Memory plan. The implementer should make the plan explicit enough for later code tasks by adding durable schema drafts, sharper Phase 1 deliverables/acceptance criteria, and a concise workflow-spec section that documents the structured task/session memory model and retrieval precedence without changing runtime behavior.
  scope_packet:
    identifiers:
      handoff_id: "structured-resume-task-memory"
      plan_id: "structured-resume-task-memory"
      task_id: "SRTM-T1"
      workstream_id: "ws-main"
      company_id: "CSC"
      repository_id: "canon-systems"
      repo_ref: "main@112884c53c5796ea88891cf1eb005b8a7a0c58c8"
      packet_persistence_path: ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/scoper.md"
    story:
      title: "Schema lock for structured resume and task memory"
      userValue: "Canon operators and future agent phases get a durable, reviewable documentation contract for structured resume and task memory before any implementation code is written."
      acceptanceCriteria:
        - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md explicitly defines Phase 1 deliverables and testable acceptance criteria for the documentation/schema-lock task."
        - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md includes inline JSON schema drafts or equivalent structured field contracts for session_handoff, plan, epic, task, task_update, and decision, without requiring standalone JSON schema files."
        - "docs/SYSTEM-WORKFLOW.md contains a concise section describing the structured task/session memory model, retrieval precedence, and relationship to the existing checkpoint/resume and canonical memory planes, with a link to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
        - "docs/ROADMAP.md remains linked to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
        - "The task changes only markdown documentation and packet artifacts; no Python, Terraform, JSON, generated memory files, or runtime implementation files are included."
    repository:
      primaryLanguages: ["Python", "Markdown", "Terraform", "Shell"]
      testFramework: "pytest for code tasks; SRTM-T1 verification is markdown review plus simple repository checks"
      relevantFiles:
        - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/ROADMAP.md"
        - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/scoper.md"
        - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/cursor-pilot.md"
    constraints:
      dependencies:
        - "Existing Canon agent-chain discipline: scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator."
        - "No non-markdown implementation files may be modified before scoper and cursor-pilot packets exist."
        - "Use docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md as the detailed plan source and docs/SYSTEM-WORKFLOW.md as the living workflow contract."
      mustNotBreak:
        - "Do not modify runtime behavior, CLI commands, backend services, Terraform, tests, or generated memory artifacts in this task."
        - "Do not include unrelated dirty files from parent start: .canon/memory/capture-latest.json, infra/terraform/variables.tf, scripts/clone_memory_layer_secret.py."
        - "Preserve the docs/ROADMAP.md link to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
        - "Keep external Jira/Linear-style workflow integration explicitly out of Phase 1 implementation scope."
      outOfScope:
        - "Implementing typed artifact writers/readers."
        - "Adding canon handoff, canon task, or canon plan CLI commands."
        - "Changing preflight, canon ask, checkpoint, resume, graph, or memory backend behavior."
        - "Creating standalone JSON schema files unless cursor-pilot determines markdown-only inline schemas are insufficient, which is not expected."
        - "Editing unrelated dirty files or committing changes."
    dor_checklist:
      repo_ref_verification: "pass: git branch main, remote git@github.com:CanonSystems/canon-systems.git, sha 112884c53c5796ea88891cf1eb005b8a7a0c58c8"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md explicitly defines Phase 1 deliverables and testable acceptance criteria for the documentation/schema-lock task."
        implementation_targets: ["docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"]
        verification_tests:
          - "rg -n \"Phase 1: Documentation and schema lock|Deliverables:|Acceptance criteria:\" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
          - "Manual docs review confirms Phase 1 ACs are specific, testable, and limited to documentation/schema lock."
      - criterion: "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md includes inline JSON schema drafts or equivalent structured field contracts for session_handoff, plan, epic, task, task_update, and decision, without requiring standalone JSON schema files."
        implementation_targets: ["docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"]
        verification_tests:
          - "rg -n \"session_handoff|task_update|decision|\\\"schema_version\\\"|\\\"required\\\"\" docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
          - "test \"$(git diff --name-only -- '*.json' | wc -l | tr -d ' ')\" = \"0\""
      - criterion: "docs/SYSTEM-WORKFLOW.md contains a concise section describing the structured task/session memory model, retrieval precedence, and relationship to the existing checkpoint/resume and canonical memory planes, with a link to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
        implementation_targets: ["docs/SYSTEM-WORKFLOW.md"]
        verification_tests:
          - "rg -n \"structured task|session memory|STRUCTURED-RESUME-TASK-MEMORY-PLAN|session_handoff|task_update|retrieval precedence\" docs/SYSTEM-WORKFLOW.md"
          - "Manual docs review confirms the section is concise and does not claim shipped runtime behavior."
      - criterion: "docs/ROADMAP.md remains linked to docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md."
        implementation_targets: ["docs/ROADMAP.md"]
        verification_tests:
          - "rg -n \"STRUCTURED-RESUME-TASK-MEMORY-PLAN.md\" docs/ROADMAP.md"
      - criterion: "The task changes only markdown documentation and packet artifacts; no Python, Terraform, JSON, generated memory files, or runtime implementation files are included."
        implementation_targets:
          - "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
          - "docs/SYSTEM-WORKFLOW.md"
          - "docs/ROADMAP.md"
          - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/scoper.md"
          - ".cursor/handoffs/structured-resume-task-memory/SRTM-T1/cursor-pilot.md"
        verification_tests:
          - "git diff --name-only -- docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md docs/SYSTEM-WORKFLOW.md docs/ROADMAP.md .cursor/handoffs/structured-resume-task-memory/SRTM-T1/scoper.md .cursor/handoffs/structured-resume-task-memory/SRTM-T1/cursor-pilot.md"
          - "git diff --name-only | rg -v '^(docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md|docs/SYSTEM-WORKFLOW.md|docs/ROADMAP.md|\\.cursor/handoffs/structured-resume-task-memory/SRTM-T1/(scoper|cursor-pilot)\\.md)$' || true"
    risks_and_assumptions:
      assumptions:
        - "Inline markdown schema drafts are sufficient for SRTM-T1; standalone JSON schema files belong to a later implementation task unless cursor-pilot identifies a documentation-only need."
        - "The current roadmap link is already present and should be preserved rather than rewritten broadly."
        - "The SYSTEM-WORKFLOW addition should describe the target structured memory contract as planned behavior, not as already shipped runtime behavior."
      openQuestions: []
    retrieval_notes:
      graph: "Degraded. canon graph query attempted for this scope but AWS Secrets Manager lookup failed with 'Unable to locate credentials' and AXON_SERVICE_URL/base URL was missing."
      state: "Degraded. canon checkpoint read for structured-resume-task-memory/SRTM-T1/ws-main returned transport connection refused at localhost:8080."
      canonical: "Partially degraded. canon ask reported AWS Secrets Manager lookup failure but returned one mempalace hit not directly specific to this task."
      context_file: ".canon/memory/context-latest.md appeared scoped to IMC/innermost and query 'status check', so it was not treated as authoritative prior work for this repo task."
      parent_reported_degradation: "Parent shell previously observed 'AWS Secrets Manager fetch failed: Unable to locate credentials'; secrets wizard was launched once and stopped while waiting for interactive input."
    prior_work_references:
      - artifact_id: "docs/STRUCTURED-RESUME-TASK-MEMORY-PLAN.md"
        source: "canonical"
        relevance: "Detailed local plan already defines target objects, retrieval rules, implementation phases, and Phase 1 as documentation/schema lock."
      - artifact_id: "docs/ROADMAP.md"
        source: "canonical"
        relevance: "Roadmap already links the structured resume and task memory plan and frames it as Canon-owned agent execution memory with later workflow integration."
      - artifact_id: "docs/FINAL_STANDUP_CHECKLIST.md"
        source: "mempalace"
        relevance: "Only available canon ask hit; weakly relevant because it reinforces that historical recall should use the memory-adapter boundary rather than placeholder stubs."
    implementation_guidance:
      - "Keep the edit set small and markdown-only."
      - "In the plan, convert the current brief Phase 1 bullets into explicit deliverables, acceptance criteria, and review checks."
      - "Add inline schema drafts for the six target artifact types using stable fields already named in the plan, including tenant scope and source/evidence references where applicable."
      - "In SYSTEM-WORKFLOW, add a concise forward-looking section near the memory/runtime or forward-plan areas that explains object-type-first retrieval precedence: explicit identifiers, resume intent, task status intent, rationale intent, then existing snippet fallback."
      - "Avoid describing Phase 2+ behavior as implemented."
END_HANDOFF_TO_CURSOR_PILOT
