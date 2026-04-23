# E5-T1 implementer handoff (Vault layout spec + redaction allowlist)

```yaml
HANDOFF_TO_QA:
  handoff_id: handoff_20260423_e5t1_vault_layout_spec
  task_id: E5-T1
  branch: wave/5/canon-memory-v1
  files_modified:
    - docs/VAULT-LAYOUT.md
    - backend/synthesis/README.md
    - tests/test_vault_layout_spec.py
    - CHANGELOG.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC1
      status: MET
      evidence: docs/VAULT-LAYOUT.md includes YAML event frontmatter schema, wikilinks, §4 .obsidian/ seed files, and attachments/ in the layout tree; test asserts required sections, attachments/, wikilinks, .obsidian/.
      run_result: "pytest tests/test_vault_layout_spec.py::test_vault_layout_spec_is_schema_v1_and_has_required_sections -q  → 1 passed"
      covering_tests: |
        test_vault_layout_spec_is_schema_v1_and_has_required_sections
    - id: AC2
      status: MET
      evidence: "§5 table names every non-payload CanonicalEvent field; `model` in DROPPED row; payload policy states silently drop unknown keys."
      run_result: "pytest tests/test_vault_layout_spec.py::test_vault_layout_allowlist_covers_canonical_event_fields_and_backend_readme_links -q  → 1 passed"
      covering_tests: |
        test_vault_layout_allowlist_covers_canonical_event_fields_and_backend_readme_links
    - id: AC3
      status: MET
      evidence: Doc YAML frontmatter and §3 example frontmatter include schema_version: 1; test asserts presence in body.
      run_result: "pytest tests/test_vault_layout_spec.py::test_vault_layout_spec_is_schema_v1_and_has_required_sections -q  → 1 passed"
      covering_tests: |
        test_vault_layout_spec_is_schema_v1_and_has_required_sections
    - id: AC4
      status: MET
      evidence: backend/synthesis/README.md appends link to docs/VAULT-LAYOUT.md and schema_version: 1; test asserts substrings in README.
      run_result: "pytest tests/test_vault_layout_spec.py::test_vault_layout_allowlist_covers_canonical_event_fields_and_backend_readme_links -q  → 1 passed"
      covering_tests: |
        test_vault_layout_allowlist_covers_canonical_event_fields_and_backend_readme_links
    - id: AC5
      status: MET
      evidence: E5-T1 bullet prepended at top of CHANGELOG [Unreleased]/Added; E5-T1 bullet appended in SYSTEM-WORKFLOW.md §3 after E4-T3; no production-line edits to forbidden surfaces.
      run_result: "pytest -q  → 367 passed (no regression on living-spec docs contract)"
      covering_tests: |
        tests/test_vault_layout_spec.py
        CHANGELOG.md
        docs/SYSTEM-WORKFLOW.md
    - id: AC6
      status: MET
      evidence: "Full suite: 365 baseline + 2 new tests = 367."
      run_result: "pytest -q  → 367 passed, 0 skipped, 0 failed"
      covering_tests: |
        tests/test_vault_layout_spec.py
    - id: AC7
      status: MET
      evidence: "No edits to backend/**/*.py, src/canon_systems/**/*.py, or infra/**; only docs, backend/synthesis/README.md, and new tests/ file."
      run_result: "git diff --name-only  → five paths as listed; no *.py under backend/s synthesis package except README not applicable (README is .md)"
      covering_tests: |
        tests/test_vault_layout_spec.py
  suite_result:
    total: 367
    passed: 367
    skipped: 0
    failed: 0
END_HANDOFF_TO_QA
```

## Summary

- Created `docs/VAULT-LAYOUT.md` (schema_version 1, 9 sections) per cursor-pilot §1.
- Appended one pointer line to `backend/synthesis/README.md` (first 5 lines unchanged).
- Added `tests/test_vault_layout_spec.py` (2 tests) verbatim from cursor-pilot §5.
- Prepend E5-T1 in `CHANGELOG.md`; append E5-T1 in `docs/SYSTEM-WORKFLOW.md` §3 (after E4-T3, before E4-T4 and `## 4)`).
- `CanonicalEvent` (15 non-payload fields) matches §5 allowlist; no blocker.
- **Do not commit** — parent orchestrator commits after QA + release-orchestrator.
