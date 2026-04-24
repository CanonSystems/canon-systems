GATE_RESULTS
  handoff_id: "handoff_20260424T000000Z_stable_dev_memory_urls"
  verdict: PASS
  acceptance_criteria:
    - criterion: "The Terraform root and `infra/terraform/modules/ecs-fargate` can model stable ingress for the current dev `ecs_baseline` ECS stack without changing existing stack naming/import assumptions: configurable load-balancer/target-group/DNS inputs and outputs exist, and the ECS service can attach to a target group when ingress is enabled."
      status: PASS
      covering_tests:
        - "tests/test_infra_layout.py::test_ecs_fargate_module_declares_optional_ingress"
        - "tests/test_infra_layout.py::test_root_wires_ecs_ingress_variables_and_outputs"
        - "tests/test_infra_layout.py::test_infra_readme_stable_ingress_section"
      run_result: "pass; AC-covering ingress contract nodes passed in the fresh rerun."
    - criterion: "Repo-owned secret/default tooling and diagnostics treat stable HTTPS DNS as the canonical shape for `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and `CANON_STATE_API_URL`, while preserving the current shared-base behavior where `knowledge-api` mounts `POST /memory/search`."
      status: PASS
      covering_tests:
        - "tests/test_secrets_submit.py::test_template_outputs_structured_payload"
        - "tests/test_secrets_submit.py::test_coerce_state_api_url_defaults_from_knowledge_api"
        - "tests/test_auth_migration_assets.py::test_secret_migration_rewrites_to_canonical_domain"
        - "tests/test_auth_migration_assets.py::test_validate_script_connectivity_probe_and_ip_detection"
        - "tests/test_doctor.py::test_doctor_json_ok_when_wired_no_hits"
      run_result: "pass; stable-HTTPS/defaulting/tooling behavior passed, including the explicit shared-base defaulting regression test."
    - criterion: "Operator-facing docs explain the precise cutover and rollback path for `canon-memory-dev/memory-layer__csc__canon-systems`: apply/import infra, update the secret to stable DNS values, clear `~/.canon/memory-layer-aws-cache.json` or run `canon doctor --fix-cache`, validate endpoints/health, and restore the previous secret version if rollback is needed."
      status: PASS
      covering_tests:
        - "tests/test_auth_migration_assets.py::test_migration_and_rollback_docs_exist_with_expected_sections"
        - "tests/test_infra_layout.py::test_infra_readme_stable_ingress_section"
      run_result: "pass; docs assertions for cutover, cache clear, validation, and rollback all passed."
    - criterion: "Focused tests cover the new Terraform contract and any stable-DNS helper/diagnostic behavior added in this task, with no requirement for live AWS mutations in CI."
      status: PASS
      covering_tests:
        - "tests/test_infra_layout.py::test_no_tfstate_committed"
        - "tests/test_infra_layout.py::test_no_terraform_lock_committed"
        - "tests/test_infra_layout.py::test_no_terraform_cache_committed"
        - "tests/test_infra_layout.py::test_ecs_fargate_module_declares_optional_ingress"
        - "tests/test_doctor.py::test_doctor_json_ok_when_wired_no_hits"
        - "tests/test_auth_migration_assets.py::test_validate_script_connectivity_probe_and_ip_detection"
      run_result: "pass; broad regression sweep `python3 -m pytest tests/test_infra_layout.py tests/test_doctor.py tests/test_auth_migration_assets.py tests/test_secrets_submit.py -q --tb=short` passed with `38 passed in 0.40s`, and exact AC-covering nodes also passed (`12 passed in 0.07s`)."
  iterations: 0
  regression_checked: true
  remaining_gaps:
    - "None."
  notes: "The previously failing infra hygiene regression is resolved: `infra/axon-only` local Terraform artifacts are no longer tracked and ignore coverage is present. Graph/state retrieval remained degraded in this environment (checkpoint localhost transport refusal, graph SSL verification failure), so final verification relied on repo evidence plus fresh passing test runs."
END_GATE_RESULTS
