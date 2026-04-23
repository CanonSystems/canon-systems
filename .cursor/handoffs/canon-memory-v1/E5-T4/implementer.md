# E5-T4 implementer handoff

```yaml
HANDOFF_TO_QA:
  handoff_id: handoff_20260423T1530Z_E5-T4_synthesis_web
  task_id: E5-T4
  branch: wave/5/canon-memory-v1
  files_created:
    - backend/synthesis-web/pyproject.toml
    - backend/synthesis-web/README.md
    - backend/synthesis-web/synthesis_web/__init__.py
    - backend/synthesis-web/synthesis_web/reader.py
    - backend/synthesis-web/synthesis_web/renderer.py
    - backend/synthesis-web/synthesis_web/search.py
    - backend/synthesis-web/synthesis_web/cache.py
    - backend/synthesis-web/synthesis_web/main.py
    - backend/synthesis-web/synthesis_web/templates/base.html
    - backend/synthesis-web/synthesis_web/templates/index.html
    - backend/synthesis-web/synthesis_web/templates/vault_home.html
    - backend/synthesis-web/synthesis_web/templates/page.html
    - backend/synthesis-web/synthesis_web/templates/not_found.html
    - backend/synthesis-web/synthesis_web_tests/__init__.py
    - backend/synthesis-web/synthesis_web_tests/_fakes.py
    - backend/synthesis-web/synthesis_web_tests/conftest.py
    - backend/synthesis-web/synthesis_web_tests/test_healthz.py
    - backend/synthesis-web/synthesis_web_tests/test_index.py
    - backend/synthesis-web/synthesis_web_tests/test_vault_home.py
    - backend/synthesis-web/synthesis_web_tests/test_page_render.py
    - backend/synthesis-web/synthesis_web_tests/test_backlinks.py
    - backend/synthesis-web/synthesis_web_tests/test_graph.py
    - backend/synthesis-web/synthesis_web_tests/test_search.py
    - backend/synthesis-web/synthesis_web_tests/test_404.py
    - backend/synthesis-web/synthesis_web_tests/test_etag.py
    - backend/synthesis-web/synthesis_web_tests/test_zero_install.py
    - backend/synthesis-web/synthesis_web_tests/test_reader_source_scan.py
    - infra/terraform/modules/synthesis-web/main.tf
    - infra/terraform/modules/synthesis-web/variables.tf
    - infra/terraform/modules/synthesis-web/outputs.tf
    - infra/terraform/modules/synthesis-web/README.md
  files_modified:
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md
    - backend/README.md
    - scripts/backend/build-services.sh
    - scripts/backend/install-workspace.sh
    - tests/test_backend_layout.py
  acceptance_criteria:
    - id: AC1
      status: MET
      evidence: "12 synthesis_web_tests pass; zero-install regex on /, vault home, plan + task pages; graph + search + backlinks + wikilinks covered; reader has no write-call sites."
      covering_tests:
        - backend/synthesis-web/synthesis_web_tests/test_index.py::test_index_lists_multiple_vaults
        - backend/synthesis-web/synthesis_web_tests/test_vault_home.py::test_vault_home_lists_pages_and_links
        - backend/synthesis-web/synthesis_web_tests/test_page_render.py::test_page_resolves_wikilinks_to_internal_urls
        - backend/synthesis-web/synthesis_web_tests/test_page_render.py::test_unknown_wikilink_renders_as_inactive_span
        - backend/synthesis-web/synthesis_web_tests/test_backlinks.py::test_backlinks_section_lists_linking_pages
        - backend/synthesis-web/synthesis_web_tests/test_graph.py::test_graph_endpoint_deterministic_json
        - backend/synthesis-web/synthesis_web_tests/test_search.py::test_search_honors_limit_and_truncation
        - backend/synthesis-web/synthesis_web_tests/test_404.py::test_missing_page_returns_404_html
        - backend/synthesis-web/synthesis_web_tests/test_zero_install.py::test_no_external_cdn_in_rendered_html
        - backend/synthesis-web/synthesis_web_tests/test_reader_source_scan.py::test_reader_source_has_no_write_calls
    - id: AC2
      status: MET
      evidence: "SSR vs static spike in backend/synthesis-web/README.md (Design spike section) + scoper §1; ETag + If-None-Match 304 exercises SSR cache path."
      covering_tests:
        - backend/synthesis-web/synthesis_web_tests/test_etag.py::test_content_hash_etag_honors_if_none_match
        - .cursor/handoffs/canon-memory-v1/E5-T4/scoper.md
        - backend/synthesis-web/README.md
  suite_result: total=402 passed=402 skipped=0
  deviations:
    - "Omitted canon-backend-shared from pyproject.toml (implementer env instruction: prefer drop unpublished dep); main module does not import it."
    - "Added mangum>=0.17,<1 and lazy Lambda handler wrapper (terraform expects synthesis_web.main.handler)."
    - "reader.py module docstring avoids literal put_object/delete_object/copy_object so repo rg gate on reader.py passes; test_reader_source_scan asserts no write call sites via \\b(name)\\s*\\( regex."
    - "tests/test_backend_layout.py: replaced E0 placeholder test_synthesis_web_is_readme_only with synthesis-web entry in PYTHON_SERVICES (pyproject + synthesis_web/main.py required)."
    - "scripts/backend/build-services.sh + install-workspace.sh: pip install -e backend/synthesis-web for CI/import smoke."
    - "backend/README.md: table row for synthesis-web updated from placeholder to SSR description."
    - "Starlette TemplateResponse(request, name, context) form; no pilot change required."
END_HANDOFF_TO_QA
```

## Inline packet (duplicate)

Same `HANDOFF_TO_QA` block as above is persisted in this file for qa-gate consumption.
