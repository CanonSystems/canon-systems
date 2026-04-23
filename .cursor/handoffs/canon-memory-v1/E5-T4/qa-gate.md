# E5-T4 qa-gate verdict

```yaml
GATE_RESULTS:
  task_id: E5-T4
  handoff_id: handoff_20260423T1530Z_E5-T4_synthesis_web
  verdict: PASS
  ac_results:
    - id: AC1
      status: PASS
      evidence: |
        Zero-install / read-only SSR browser over S3 vault proven by:
          - backend/synthesis-web/synthesis_web_tests/test_index.py::test_index_lists_multiple_vaults
          - backend/synthesis-web/synthesis_web_tests/test_vault_home.py::test_vault_home_lists_pages_and_links
          - backend/synthesis-web/synthesis_web_tests/test_page_render.py::test_page_resolves_wikilinks_to_internal_urls
          - backend/synthesis-web/synthesis_web_tests/test_page_render.py::test_unknown_wikilink_renders_as_inactive_span (augmented to assert no <a and no href in unresolved span fragment)
          - backend/synthesis-web/synthesis_web_tests/test_backlinks.py::test_backlinks_section_lists_linking_pages
          - backend/synthesis-web/synthesis_web_tests/test_graph.py::test_graph_endpoint_deterministic_json
          - backend/synthesis-web/synthesis_web_tests/test_search.py::test_search_honors_limit_and_truncation
          - backend/synthesis-web/synthesis_web_tests/test_404.py::test_missing_page_returns_404_html
          - backend/synthesis-web/synthesis_web_tests/test_zero_install.py::test_no_external_cdn_in_rendered_html (covers /, vault home, plan page, task page)
          - backend/synthesis-web/synthesis_web_tests/test_reader_source_scan.py::test_reader_source_has_no_write_calls (augmented to cover 21 S3 write methods including upload_*, create_multipart_upload, put_object_acl, etc.)
          - backend/synthesis-web/synthesis_web_tests/test_reader_source_scan.py::test_reader_source_scan_regex_detects_sample_writes (self-check)
    - id: AC2
      status: PASS
      evidence: |
        SSR-vs-static spike recorded:
          - .cursor/handoffs/canon-memory-v1/E5-T4/scoper.md §1 (table + rationale; Option A CHOSEN, Option B REJECTED)
          - backend/synthesis-web/README.md "Design spike: SSR over rebuild-on-publish" section
        SSR cache-path behavior proven by:
          - backend/synthesis-web/synthesis_web_tests/test_etag.py::test_content_hash_etag_honors_if_none_match (200 + quoted 64-hex ETag → 304 on If-None-Match)
          - backend/synthesis-web/synthesis_web_tests/test_etag.py::test_changing_content_busts_etag (new: mutating content-hash metadata returns fresh 200 with different ETag; stale 304 proven on the new ETag)
  deviations_reviewed:
    - deviation: "canon-backend-shared dropped from backend/synthesis-web/pyproject.toml"
      disposition: accepted
      justification: |
        synthesis_web/{main,reader,renderer,search,cache}.py have zero imports of canon_backend_shared.
        Repo-level test_canon_backend_shared_listed_in_moved_service_pyprojects only enforces the dep for
        knowledge-api / knowledge-worker / memory-adapter, so synthesis-web's omission is consistent with
        E5-T2 (synthesis also omits it). No functional coupling lost.
    - deviation: "Added mangum>=0.17,<1 and a lazy Lambda handler (synthesis_web.main.handler)"
      disposition: accepted
      justification: |
        The unwired infra/terraform/modules/synthesis-web Lambda reference expects a handler entry point;
        the implementation imports mangum lazily inside handler() so tests never load it (confirmed by
        passing TestClient-based suite with no mangum import at module scope). No external CDN or write
        path added. Scope is consistent with the unwired-terraform waiver in scoper §5.
    - deviation: "reader.py module docstring softened to avoid the repo-wide rg scan catching literal method names"
      disposition: accepted
      justification: |
        The read-only claim is behaviorally guarded by test_reader_source_scan.py, which now scans 21
        known S3 write-method names using a \b(name)\s*\( call-site regex. The self-check test
        test_reader_source_scan_regex_detects_sample_writes proves the regex detects real call sites.
        The softened docstring is purely cosmetic — the contract is enforced by behavior, not by text.
    - deviation: "tests/test_backend_layout.py placeholder test_synthesis_web_is_readme_only removed; synthesis-web added to PYTHON_SERVICES"
      disposition: accepted
      justification: |
        The E0-T2 placeholder was explicitly a 'deferred until E5-T4' stub (it asserted that
        backend/synthesis-web contained only README.md + .gitkeep). E5-T4 delivers the full service,
        so the placeholder invariant is obsolete. The new PYTHON_SERVICES entry reuses the existing
        parametrized test to require pyproject.toml + synthesis_web/main.py + module-level `app`.
    - deviation: "scripts/backend/build-services.sh + install-workspace.sh: pip install -e backend/synthesis-web added to the service loop"
      disposition: accepted
      justification: |
        Two-line additive edits that only append 'synthesis-web' to the existing service list and map
        'synthesis-web → synthesis_web' for the import smoke test. No other behavior changed.
    - deviation: "backend/README.md synthesis-web row updated from placeholder to SSR description"
      disposition: accepted
      justification: |
        Living-spec edit explicitly permitted by scoper §6 (README 'Backend monorepo' row additive).
  tests_added_or_augmented:
    - path: backend/synthesis-web/synthesis_web_tests/test_reader_source_scan.py
      rationale: |
        Parent qa-gate hard requirement: "MUST have zero S3 write call sites (put_object, delete_object,
        copy_object, upload_*, create_multipart_upload, etc.) — augment test if coverage is too narrow."
        Expanded the forbidden set from 3 to 21 boto3 S3 write methods (including upload_file,
        upload_fileobj, upload_part, upload_part_copy, create_multipart_upload,
        complete_multipart_upload, abort_multipart_upload, put_object_acl, put_object_tagging,
        put_object_retention, put_object_legal_hold, put_bucket_policy, put_bucket_acl, delete_objects,
        delete_object_tagging, restore_object, write_get_object_response, copy). Added a self-check test
        proving the regex catches a synthetic call site for every forbidden name.
    - path: backend/synthesis-web/synthesis_web_tests/test_etag.py
      rationale: |
        Parent qa-gate hard requirement: "changing content busts the ETag." Added
        test_changing_content_busts_etag: mutates the underlying fake S3 object body +
        x-amz-meta-content-hash; asserts (1) stale If-None-Match no longer returns 304, (2) new 200
        response carries a different ETag, (3) new page body reflects the content change, (4) the new
        ETag does honor If-None-Match → 304. Proves the cache key is content-addressed, not path-addressed.
    - path: backend/synthesis-web/synthesis_web_tests/test_page_render.py
      rationale: |
        Parent qa-gate hard requirement: "unknown wikilinks render as inactive spans (no broken links,
        no href=\"#\" that 200s)." Tightened test_unknown_wikilink_renders_as_inactive_span to locate the
        specific <span class="wikilink-unresolved"> fragment containing 'does-not-exist' and assert
        neither <a nor any href= attribute appears inside it.
  suite_result: total=404 passed=404 failed=0 skipped=0
  synthesis_web_suite_result: total=14 passed=14 failed=0 skipped=0
  iterations: 1
  regression_checked: true
  blocking_issues: []
  notes: |
    Implementer delivered 402 tests green; qa-gate augmented 2 existing tests and 1 new test to make
    the AC1 read-only + AC1 ETag-bust + AC1 inactive-wikilink guarantees behaviorally enforced rather
    than textual. Full repo suite now 404 passed / 0 failed. synthesis-web suite now 14 passed.
    No scope-creep changes; all edits confined to E5-T4 paths. Branch wave/5/canon-memory-v1 clean.
END_GATE_RESULTS
```
