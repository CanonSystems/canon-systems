# Scoper packet — E0-T1

- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T1
- workstream_id: wave-0a
- agent_name: scoper
- agent_run_id: 6e977ecb-101e-4ad3-b364-2811c19c4318
- phase: scoper
- phase_status: pass
- definition_of_ready: pass

## Scope summary

E0-T1 is a read-only audit-and-draft task for Canon Memory Platform v1 Wave 0.
The implementer must (1) identify the git repo, path, and deployment target
that currently backs `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, and
`MEMORY_ADAPTER_URL` (all three are consumed by `src/canon_systems/shared.py` +
`src/canon_systems/ask_hybrid.py`), (2) draft `docs/DEPRECATIONS.md` with a
keep|absorb|delete label + one-line justification for each of the six
sibling repos on this machine, and (3) draft `docs/OBSIDIAN-MIND-CATALOGUE.md`
enumerating every synthesis/summary/transform capability in
`/Users/edwardwalker/localwork/obsidian-mind` with source-file references so
Wave 5 can absorb useful logic. No service moves, no infra imports, no code
edits. Output is three markdown files committed to canon-systems.

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: (see above)

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E0-T1"
      workstream_id: "wave-0a"
      agent_name: "scoper"
      parent_wave: "Wave 0 / E0"
      prior_checkpoint: "none (first task in plan)"
      company_id: "IMC"
      repository_id: "innermost"
      repo_ref: "github.com/<owner>/canon-systems @ HEAD (main)"

    story:
      title: "Audit sibling repos and locate backend services"
      userValue: "Wave 0 downstream tasks need one authoritative answer for each in-use URL backing plus explicit keep|absorb|delete policy for all siblings."
      acceptanceCriteria:
        - "Report names the git repo + path + deployment target for each of the three URLs." # verbatim from backlog
        - "docs/DEPRECATIONS.md drafted with keep|absorb|delete label per sibling."           # verbatim from backlog
        - "docs/OBSIDIAN-MIND-CATALOGUE.md drafted listing obsidian-mind capabilities."       # verbatim from backlog
        - "The audit report is persisted at docs/WAVE-0-AUDIT.md and cites concrete artifacts per URL."
        - "docs/DEPRECATIONS.md contains an entry for ALL SIX sibling repos."
        - "docs/OBSIDIAN-MIND-CATALOGUE.md lists agents/, commands/, scripts/, skills/, and vault layout with source paths."
        - "No service moves, no infra imports, no non-markdown writes."
      done_signal:
        - "docs/DEPRECATIONS.md committed."
        - "docs/OBSIDIAN-MIND-CATALOGUE.md committed."
        - "docs/WAVE-0-AUDIT.md committed."

    repository:
      primaryLanguages: ["Python 3.12", "Markdown", "Terraform (HCL)", "Dockerfile"]
      testFramework: "pytest (canon-systems root tests/)"
      build_tool: "pip (pyproject.toml)"
      relevantFiles:
        - "src/canon_systems/shared.py"
        - "src/canon_systems/ask_hybrid.py"
        - "src/canon_systems/context_preload.py"
        - "src/canon_systems/capture_session.py"
        - "scripts/validate_memory_endpoints.py"
        - "examples/memory-layer.team.env.example"
        - "docs/MEMORY-PLATFORM-BACKLOG.md"
        - "docs/MEMORY-PLATFORM-PLAN.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md"
        - ".cursor/rules/memory-platform-build-discipline.mdc"
      sibling_repos_to_audit:
        - "/Users/edwardwalker/localwork/canon-platform"
        - "/Users/edwardwalker/localwork/canon-systems-v2  (authoritative host of the three services)"
        - "/Users/edwardwalker/localwork/mempalace         (MIT upstream dependency)"
        - "/Users/edwardwalker/localwork/obsidian-mind     (personal vault system — Wave 5 absorbs logic)"
        - "/Users/edwardwalker/localwork/temporal          (Go upstream fork)"
        - "/Users/edwardwalker/localwork/total_recall      (design-doc + one-off extractor)"
      files_to_read_for_url_backings:
        - "/Users/edwardwalker/localwork/canon-systems-v2/deploy/manifest.json"
        - "/Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-api"
        - "/Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-worker"
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/README.md"
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker/README.md"
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter/README.md"
        - "/Users/edwardwalker/localwork/canon-systems-v2/scripts/dev/run-memory-adapter.sh"
        - "/Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/main.tf"
        - "/Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/variables.tf"
        - "/Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/terraform.tfvars"
      files_to_read_for_deprecations:
        - "/Users/edwardwalker/localwork/canon-platform/README.md"
        - "/Users/edwardwalker/localwork/mempalace/README.md"
        - "/Users/edwardwalker/localwork/temporal/README.md"
        - "/Users/edwardwalker/localwork/total_recall/docs/*.md"
      files_to_read_for_obsidian_catalogue:
        - "/Users/edwardwalker/localwork/obsidian-mind/README.md"
        - "/Users/edwardwalker/localwork/obsidian-mind/.claude/agents/*.md"
        - "/Users/edwardwalker/localwork/obsidian-mind/.claude/commands/om-*.md"
        - "/Users/edwardwalker/localwork/obsidian-mind/.claude/scripts/*"
        - "/Users/edwardwalker/localwork/obsidian-mind/.claude/skills/*/SKILL.md"
        - "/Users/edwardwalker/localwork/obsidian-mind/vault-manifest.json"
      files_to_write:
        - path: "docs/WAVE-0-AUDIT.md"
          purpose: "One section per URL (KNOWLEDGE_API_URL, KNOWLEDGE_WORKER_URL, MEMORY_ADAPTER_URL) citing sibling repo path, source subpath, Dockerfile/entrypoint, deployment target (ECS service + cluster + ECR repo) or explicit 'not yet deployed via IaC'. Tail: gaps and open questions for E0-T3/E0-T4."
        - path: "docs/DEPRECATIONS.md"
          purpose: "One entry per sibling repo with repo name, absolute path, keep|absorb|delete label, one-line justification, recommended wave for action. Must cover all six."
        - path: "docs/OBSIDIAN-MIND-CATALOGUE.md"
          purpose: "Capability catalogue by source-relative path: agents, commands, scripts, skills, vault layout. Each row: path + one-line description for E5-T2 absorption planning."
      files_not_to_write:
        - "No files under src/**, backend/**, infra/** (beyond markdown docs), .github/**, .cursor/rules/**."
        - "No rewrites of docs/MEMORY-PLATFORM-PLAN.md, docs/MEMORY-PLATFORM-BACKLOG.md, docs/SYSTEM-WORKFLOW.md."

    constraints:
      dependencies:
        - "canon-systems client (src/canon_systems/shared.py + ask_hybrid.py) MUST still resolve URLs from env / .canon/memory-layer.*.env files as today."
        - "Sibling repos read-only — no git ops in them."
      mustNotBreak:
        - "Existing three-URL resolution in shared.py."
        - "Hard-lock rule markdown-only edit surface."
        - "docs/SYSTEM-WORKFLOW.md Section 3 packet-path contract."
      mode: "markdown-only; read-only scan across sibling repos."

    tests_to_write:
      - path: "tests/test_wave0_audit_docs.py"
        purpose: "Smoke test proving the three audit docs exist and DEPRECATIONS covers all six sibling repos."
        assertions:
          - "docs/WAVE-0-AUDIT.md, docs/DEPRECATIONS.md, docs/OBSIDIAN-MIND-CATALOGUE.md all exist and are non-empty."
          - "docs/DEPRECATIONS.md contains case-insensitive substring for every sibling: canon-platform, canon-systems-v2, mempalace, obsidian-mind, temporal, total_recall."
          - "docs/DEPRECATIONS.md contains at least one keep|absorb|delete token per sibling block."
          - "docs/WAVE-0-AUDIT.md contains KNOWLEDGE_API_URL, KNOWLEDGE_WORKER_URL, MEMORY_ADAPTER_URL."
        framework: "pytest"

    ac_traceability:
      - criterion: "Report names the git repo + path + deployment target for each of the three URLs."
        implementation_targets: ["docs/WAVE-0-AUDIT.md"]
        verification_tests: ["tests/test_wave0_audit_docs.py::test_audit_mentions_all_three_urls"]
      - criterion: "docs/DEPRECATIONS.md drafted with keep|absorb|delete label per sibling."
        implementation_targets: ["docs/DEPRECATIONS.md"]
        verification_tests: ["tests/test_wave0_audit_docs.py::test_deprecations_covers_all_six_siblings_with_label"]
      - criterion: "docs/OBSIDIAN-MIND-CATALOGUE.md drafted listing obsidian-mind capabilities."
        implementation_targets: ["docs/OBSIDIAN-MIND-CATALOGUE.md"]
        verification_tests: ["tests/test_wave0_audit_docs.py::test_obsidian_mind_catalogue_nonempty"]

    out_of_scope:
      - "Physical service moves into backend/<service>/ (E0-T3)."
      - "Infra imports (E0-T4)."
      - "Code deletions or git ops inside sibling repos."
      - "backend/ monorepo skeleton creation (E0-T2)."
      - "Modifications to src/canon_systems/shared.py URL resolution."
      - "canon capture/ask/dor-log end-to-end smoke (E0-T5)."

    preliminary_findings_for_implementer:
      knowledge_api_url_backing:
        repo: "canon-systems-v2"
        path: "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api"
        entrypoint: "services/knowledge-api/app/main.py (FastAPI, uvicorn, port 8080)"
        dockerfile: "canon-systems-v2/deploy/docker/Dockerfile.knowledge-api"
        ecr_repository: "canon/knowledge-api"
        deployment_target: "AWS ECS Fargate (canon-systems-v2-dev-cluster / canon-systems-v2-dev-baseline)"
      knowledge_worker_url_backing:
        repo: "canon-systems-v2"
        path: "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker"
        entrypoint: "knowledge_worker.main:app (FastAPI, uvicorn, port 8091)"
        dockerfile: "canon-systems-v2/deploy/docker/Dockerfile.knowledge-worker"
        ecr_repository: "canon/knowledge-worker"
        deployment_target: "Same ECS baseline; reconcile per-service task defs in E0-T4."
      memory_adapter_url_backing:
        repo: "canon-systems-v2 (+ sibling dep on /Users/edwardwalker/localwork/mempalace)"
        path: "/Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter"
        entrypoint: "memory_adapter.main:app (FastAPI, uvicorn, port 8090) via scripts/dev/run-memory-adapter.sh"
        dockerfile: "NONE dedicated (bundled inside Dockerfile.knowledge-worker but CMD only starts knowledge_worker)."
        ecr_repository: "NOT PRESENT in tfvars:ecr_repository_names or deploy/manifest.json"
        deployment_target: "AMBIGUOUS — likely dev-only today. Implementer MUST flag as Wave-0 open question (consistent with E1-T2 'Fix memory-adapter 404 path')."
      sibling_recommendations:
        - {repo: "canon-platform",   label: "absorb", reason: "Legacy Lambda/Amplify; none of its services back the three URLs; subset of Terraform may import into infra/ in E0-T4."}
        - {repo: "canon-systems-v2", label: "absorb", reason: "Authoritative home of the three services + libs; E0-T3 moves into backend/."}
        - {repo: "mempalace",        label: "keep",   reason: "Upstream MIT library consumed via MEMPALACE_PATH; vendor dep, not a Canon service."}
        - {repo: "obsidian-mind",    label: "absorb", reason: "Personal vault agent system; Wave 5 absorbs synthesis logic; repo can retire after."}
        - {repo: "temporal",         label: "keep",   reason: "Vendor upstream (temporalio/temporal); retain as external reference."}
        - {repo: "total_recall",     label: "delete", reason: "Design-doc + one-off extractor; no deployed service; candidate for removal in E7-T2."}
      obsidian_mind_capability_surfaces:
        - {group: "synthesis agents",  path_prefix: ".claude/agents/"}
        - {group: "summary commands",  path_prefix: ".claude/commands/"}
        - {group: "transform scripts", path_prefix: ".claude/scripts/"}
        - {group: "skills adapters",   path_prefix: ".claude/skills/"}
        - {group: "vault layout",      path_prefix: ""}

    risks_and_assumptions:
      assumptions:
        - "canon-systems-v2 is the only sibling containing any of the three in-use services."
        - "canon-platform is NOT on the current dependency path for the three URLs."
        - "obsidian-mind is reference only — absorption is code/doc-level not runtime."
        - "Hard-lock rule permits markdown-only writes + a single pytest smoke file without cursor-pilot/qa-gate/release packets; if qa-gate interprets the smoke test as non-markdown, route through the standard packet flow."
      openQuestions:
        - "Is MEMORY_ADAPTER_URL served by any production compute today? (Must surface in docs/WAVE-0-AUDIT.md as open question.)"
        - "Does canon-platform contain Terraform E0-T4 should import, or is it fully superseded by canon-systems-v2/infra?"
      not_open_questions:
        - "Identity of knowledge-api / knowledge-worker backings is resolved; implementer verifies only."

    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
      prior_work_discovery: "pass"
      markdown_only_scope: "pass"
      sibling_repos_exist: "pass (ls confirmed)"

    prior_work_references:
      - {id: "ctx_latest_20260422T132642Z", source: ".canon/memory/context-latest.md", relevance: "memory_adapter 404 status confirms adapter is not serving traffic today."}
      - {id: "backlog_E0_T1",                source: "docs/MEMORY-PLATFORM-BACKLOG.md (lines 162-173)", relevance: "Canonical E0-T1 spec."}
      - {id: "plan_build_discipline",        source: ".cursor/rules/memory-platform-build-discipline.mdc Section 2", relevance: "Authorises markdown-only edits."}
      - {id: "v2_deploy_manifest",           source: "/Users/edwardwalker/localwork/canon-systems-v2/deploy/manifest.json", relevance: "Absent memory-adapter confirms gap."}
      - {id: "v2_terraform_tfvars",          source: "/Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/terraform.tfvars", relevance: "ecr_repository_names shows 4 repos only."}
      - {id: "v2_dockerfile_knowledge_worker", source: "/Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-worker", relevance: "Bundles memory-adapter source but CMD only starts knowledge_worker."}
END_HANDOFF_TO_CURSOR_PILOT
```

**DEFINITION_OF_READY verdict: PASS.**

Justification: six sibling repos exist on disk and were scanned; the three URL backings are locatable from canon-systems-v2 service/Docker/Terraform artifacts; acceptance criteria verbatim from the backlog plus three scoper-added testable refinements; each AC has an implementation target and verification test; the hard-lock rule permits the markdown-only write surface; the single genuine ambiguity (memory-adapter production deployment) is itself an audit finding to surface, not a scoping blocker.
