# Cursor-pilot packet — E0-T1

- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T1
- workstream_id: wave-0a
- agent_name: cursor-pilot
- agent_run_id: 5c8bb043-659b-4a7a-aa83-3779ccf96766
- phase: cursor-pilot
- phase_status: pass
- definition_of_ready: pass (scoper DoR already PASS; pilot is precision translation)

## CURSOR_PILOT_PROMPT

```
CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor on the
canon-systems repo. This prompt MUST be executed by that subagent (default
model: `composer-2-fast`), not by the parent planner agent. You operate under
the Canon Memory Platform v1 build hard-lock rule
(`.cursor/rules/memory-platform-build-discipline.mdc` §2): for task E0-T1 the
permitted edit surface is markdown files under `docs/**` plus a single pytest
smoke file `tests/test_wave0_audit_docs.py`. Nothing else.
</ROLE>

<TASK>
E0-T1 (wave-0a, handoff canon-memory-v1): audit the three backend URLs
consumed by canon-systems (`KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`,
`MEMORY_ADAPTER_URL`), draft `docs/WAVE-0-AUDIT.md` naming the git repo +
source path + deployment target for each, draft `docs/DEPRECATIONS.md`
labeling all six sibling repos on this machine as keep|absorb|delete with
one-line justifications, and draft `docs/OBSIDIAN-MIND-CATALOGUE.md`
enumerating every synthesis/summary/transform capability surface in
`/Users/edwardwalker/localwork/obsidian-mind` so Wave 5 can plan absorption.
No service moves, no infra imports, no code edits. Output is three markdown
docs plus one pytest smoke file.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: Report names the git repo + path + deployment target for each of the three URLs.
- AC2: docs/DEPRECATIONS.md drafted with keep|absorb|delete label per sibling.
- AC3: docs/OBSIDIAN-MIND-CATALOGUE.md drafted listing obsidian-mind capabilities.
- AC4: The audit report is persisted at docs/WAVE-0-AUDIT.md and cites concrete artifacts per URL.
- AC5: docs/DEPRECATIONS.md contains an entry for ALL SIX sibling repos.
- AC6: docs/OBSIDIAN-MIND-CATALOGUE.md lists agents/, commands/, scripts/, skills/, and vault layout with source paths.
- AC7: No service moves, no infra imports, no non-markdown writes (the pytest smoke file is the one explicit exception granted by §2 of the discipline rule).
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T1
- workstream_id: wave-0a
- company_id: IMC
- repository_id: innermost
- repo_ref: github.com/<owner>/canon-systems @ HEAD (main)
- prior_work_references:
  - ctx_latest_20260422T132642Z — .canon/memory/context-latest.md — memory_adapter 404 status confirms adapter is not serving traffic today.
  - backlog_E0_T1 — docs/MEMORY-PLATFORM-BACKLOG.md — canonical E0-T1 spec.
  - plan_build_discipline — .cursor/rules/memory-platform-build-discipline.mdc §2 — markdown-only + single pytest smoke file permitted.
  - v2_deploy_manifest — /Users/edwardwalker/localwork/canon-systems-v2/deploy/manifest.json — absent memory-adapter entry.
  - v2_terraform_tfvars — /Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/terraform.tfvars — 4 ECR repos only.
  - v2_dockerfile_knowledge_worker — /Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-worker — bundles memory-adapter source but CMD only starts knowledge_worker.
- parent_wave: Wave 0 / E0
- prior_checkpoint: none (first task in plan)
</CONTEXT>

<REPOSITORY>
- primaryLanguages: Python 3.12, Markdown, Terraform (HCL), Dockerfile
- testFramework: pytest (run from canon-systems root; tests live in tests/)
- build_tool: pip (pyproject.toml)
- relevantFiles (read-only reference; do NOT modify):
  - src/canon_systems/shared.py, ask_hybrid.py, context_preload.py, capture_session.py
  - scripts/validate_memory_endpoints.py
  - examples/memory-layer.team.env.example
  - docs/MEMORY-PLATFORM-BACKLOG.md, MEMORY-PLATFORM-PLAN.md, SYSTEM-WORKFLOW.md
  - .cursor/plans/canon_memory_platform_build_d21073e1.plan.md
  - .cursor/rules/memory-platform-build-discipline.mdc
- sibling_repos_to_audit (read-only; NO git ops, NO edits):
  - /Users/edwardwalker/localwork/canon-platform
  - /Users/edwardwalker/localwork/canon-systems-v2
  - /Users/edwardwalker/localwork/mempalace
  - /Users/edwardwalker/localwork/obsidian-mind
  - /Users/edwardwalker/localwork/temporal
  - /Users/edwardwalker/localwork/total_recall
- files_to_read_for_url_backings:
  - /Users/edwardwalker/localwork/canon-systems-v2/deploy/manifest.json
  - /Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-api
  - /Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-worker
  - /Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/README.md
  - /Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker/README.md
  - /Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter/README.md
  - /Users/edwardwalker/localwork/canon-systems-v2/scripts/dev/run-memory-adapter.sh
  - /Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/main.tf, variables.tf, terraform.tfvars
- files_to_read_for_deprecations:
  - /Users/edwardwalker/localwork/canon-platform/README.md
  - /Users/edwardwalker/localwork/mempalace/README.md
  - /Users/edwardwalker/localwork/temporal/README.md
  - /Users/edwardwalker/localwork/total_recall/docs/*.md
- files_to_read_for_obsidian_catalogue:
  - /Users/edwardwalker/localwork/obsidian-mind/README.md
  - /Users/edwardwalker/localwork/obsidian-mind/.claude/agents/*.md
  - /Users/edwardwalker/localwork/obsidian-mind/.claude/commands/om-*.md
  - /Users/edwardwalker/localwork/obsidian-mind/.claude/scripts/*
  - /Users/edwardwalker/localwork/obsidian-mind/.claude/skills/*/SKILL.md
  - /Users/edwardwalker/localwork/obsidian-mind/vault-manifest.json
- files_to_write (EXACTLY these four paths, nothing else):
  - docs/WAVE-0-AUDIT.md
  - docs/DEPRECATIONS.md
  - docs/OBSIDIAN-MIND-CATALOGUE.md
  - tests/test_wave0_audit_docs.py
- files_NOT_to_write (hard prohibition):
  - NO files under src/**, backend/**, infra/**, .github/**, .cursor/rules/**, scripts/**, examples/**.
  - NO edits to existing .md outside the three new docs.
  - NO writes/commits/git ops inside any sibling repo.
  - NO additional pytest files beyond tests/test_wave0_audit_docs.py.
- mustNotBreak:
  - Existing three-URL resolution in src/canon_systems/shared.py.
  - Hard-lock markdown-only edit surface.
  - docs/SYSTEM-WORKFLOW.md §3 packet-path contract.
</REPOSITORY>

<REASONING>
Approach (single workstream; do in this order):

1. Independently VERIFY the scoper's preliminary findings against the cited
   files. Do NOT copy the scoper's claims blindly.

2. Write docs/WAVE-0-AUDIT.md with one section per URL citing sibling repo
   path, source subpath, Dockerfile/entrypoint, deployment target or explicit
   "not yet deployed via IaC". End with `## Open questions for Wave 0`
   section capturing memory-adapter ambiguity and canon-platform Terraform
   question. DO NOT fabricate a deployment target for memory-adapter.

3. Write docs/DEPRECATIONS.md with one section per sibling repo (all six),
   each containing repo name, absolute path, literal token keep|absorb|delete,
   one-line justification, recommended wave.

4. Write docs/OBSIDIAN-MIND-CATALOGUE.md grouped under agents/, commands/,
   scripts/, skills/, vault layout. Each row: source-relative path + one-line
   description.

5. Write tests/test_wave0_audit_docs.py with three functions (names must match):
   - test_audit_mentions_all_three_urls
   - test_deprecations_covers_all_six_siblings_with_label
   - test_obsidian_mind_catalogue_nonempty
   Resolve paths relative to repo root via pathlib.

6. Run `pytest tests/test_wave0_audit_docs.py -q` from repo root. MUST pass
   before emitting HANDOFF_TO_QA. Capture the one-line summary.

AC traceability preserved verbatim from scoper for qa-gate matching.
</REASONING>

<PARALLELIZATION_PLAN>
strategy: single-stream
rationale: coherent markdown audit; shared inputs; audit findings feed DEPRECATIONS labels.
workstreams:
  - id: ws1
    depends_on: []
    can_run_parallel: false
    implementation_targets: ["docs/WAVE-0-AUDIT.md", "docs/DEPRECATIONS.md", "docs/OBSIDIAN-MIND-CATALOGUE.md", "tests/test_wave0_audit_docs.py"]
parent_orchestration: launch exactly one implementer; pin composer-2-fast; do not shard.
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce exactly the four new files. No edits to existing files. No other new
files. Citations must be verifiable absolute paths.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
Halt and report (do NOT emit HANDOFF_TO_QA) if:
- pytest fails after reasonable fix attempts on doc content.
- You would need to write outside the four permitted paths.
- You would need to modify any sibling repo.
- Scoper's URL-backing findings are materially wrong.

Flag-and-continue:
- memory-adapter deployment target ambiguity — record in Open questions section.

On success, emit HANDOFF_TO_QA with handoff_id canon-memory-v1, task_id E0-T1,
evidence paths for all four files, pytest one-line summary, AC traceability
preserved.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
```
