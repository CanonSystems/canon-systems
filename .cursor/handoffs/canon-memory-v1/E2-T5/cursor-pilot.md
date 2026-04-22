# E2-T5 Cursor-Pilot Packet

**Task:** Enforce checkpoint artifacts in flow-audit + qa-validate
**Wave branch:** `wave/2/canon-memory-v1` (tip f1525b6)
**Produced by:** parent orchestrator from E2-T5 scoper packet

---

```
CURSOR_PILOT_PROMPT

ROLE: Additive code + tests implementer for CLI gates. No backend/infra/templates/hooks edits. No checkpoint_cli.py changes. Stdlib-only.

TASK (E2-T5): Add a new shared helper and a new `--require-checkpoints` flag to BOTH `canon flow-audit` and `canon qa-validate`. When the flag is set, both CLIs fail unless `.cursor/handoffs/<handoff_id>/<task_id>/checkpoints/<phase>.json` exists for all five §B phases (scoper, cursor-pilot, implementer, qa-gate, release-orchestrator) and each file satisfies the field contract.

CONTEXT:
- Exit-code contracts preserved: flow-audit 0/1/2; qa-validate 0/1/2.
- §B phases (agent-name values) are the ONLY valid filename stems: {scoper, cursor-pilot, implementer, qa-gate, release-orchestrator}.
- Field contract per checkpoint JSON file (all required):
    * Top-level must be a JSON object.
    * schema_version == "1" (exact string).
    * phase == filename stem.
    * task_id == CLI --task-id.
    * handoff_id == CLI --handoff-id.
    * state_version is an integer >= 1.
- Existing test fixtures:
    tests/test_flow_audit.py::_write_task_artifacts, _write_memory_health_evidence, _write_dor_rejection_with_telemetry — reuse pattern for tmp_path.
    tests/test_qa_validate.py creates GATE_RESULTS blocks inline — mirror style.
- Env var CANON_SYSTEMS_REPO_ROOT relocates repo root for tests; use it as the two test modules do today.

REPOSITORY:
- Workdir: /Users/edwardwalker/localwork/canon-systems
- Branch: wave/2/canon-memory-v1
- Scope packet: .cursor/handoffs/canon-memory-v1/E2-T5/scoper.md

REASONING:
- Implement the shared helper in a NEW file `src/canon_systems/checkpoints.py`. It must export:
    REQUIRED_PHASES: tuple[str, ...] = ("scoper", "cursor-pilot", "implementer", "qa-gate", "release-orchestrator")
    def _collect_checkpoint_errors(*, root: Path, handoff_id: str, task_id: str) -> list[str]
  The helper iterates REQUIRED_PHASES; constructs `<root>/.cursor/handoffs/<handoff_id>/<task_id>/checkpoints/<phase>.json`; validates:
    - File exists → else "missing checkpoint artifact: <abs_path>"
    - Valid JSON → else "invalid JSON in checkpoint artifact: <path>"
    - Top-level object (dict) → else "checkpoint payload must be JSON object: <path>"
    - schema_version == "1" → else "checkpoint schema_version mismatch (got X, expected '1'): <path>"
    - phase == phase_stem → else "checkpoint phase mismatch (got X, expected '<stem>'): <path>"
    - task_id == task_id_arg → else "checkpoint task_id mismatch (got X, expected '<arg>'): <path>"
    - handoff_id == handoff_id_arg → else "checkpoint handoff_id mismatch (got X, expected '<arg>'): <path>"
    - state_version is int AND state_version >= 1 → else "checkpoint state_version invalid (got X, expected int >= 1): <path>"
  Returns the accumulated errors list (empty list means success).

- Edit `src/canon_systems/flow_audit.py`:
    * Add `from .checkpoints import _collect_checkpoint_errors` near the `from .shared import repo_root` line.
    * Add `parser.add_argument("--require-checkpoints", action="store_true")` near the other --require-* flags.
    * In `run()`, after the existing error-collection logic and BEFORE the "if errors: print FAILED" block, add:
        if args.require_checkpoints:
            errors.extend(_collect_checkpoint_errors(root=root, handoff_id=args.handoff_id, task_id=args.task_id))
    * Preserve all other logic verbatim.

- Edit `src/canon_systems/qa_validate.py`:
    * Add `from .checkpoints import _collect_checkpoint_errors` import near `from .shared import repo_root`.
    * Add `parser.add_argument("--require-checkpoints", action="store_true")` near `--require-dor-telemetry`.
    * In `run()`, after DoR telemetry collection and BEFORE the final `if errors: print FAILED`:
        if args.require_checkpoints:
            if not args.handoff_id or not args.task_id:
                print("qa-validate: --require-checkpoints requires --handoff-id and --task-id")
                return 2
            errors.extend(_collect_checkpoint_errors(root=root, handoff_id=args.handoff_id.strip(), task_id=args.task_id.strip()))

- Tests:
    tests/test_flow_audit.py — APPEND new tests at end of file (do not modify existing):
        def _write_checkpoint(root, *, handoff_id, task_id, phase, overrides=None):
            base = root / ".cursor" / "handoffs" / handoff_id / task_id / "checkpoints"
            base.mkdir(parents=True, exist_ok=True)
            body = {"schema_version": "1", "phase": phase, "task_id": task_id, "handoff_id": handoff_id, "state_version": 1}
            if overrides: body.update(overrides)
            (base / f"{phase}.json").write_text(json.dumps(body) + "\n", encoding="utf-8")
        Then the nine new test functions (exact names from scoper AC22..AC30). Use tmp_path + monkeypatch CANON_SYSTEMS_REPO_ROOT. Assert exit code and (where specified) capsys output fragments.

    tests/test_qa_validate.py — APPEND the four new test functions (AC31..AC34). Share a `_write_gate_packet(path, ...)` helper if helpful; or inline.

- Living-spec additive edits:
    CHANGELOG.md → prepend bullet at TOP of `[Unreleased] ### Added` (above E2-T4 bullet): "E2-T5: flow-audit + qa-validate enforce per-phase checkpoint artifacts — new --require-checkpoints flag on both CLIs; validates .cursor/handoffs/<handoff_id>/<task_id>/checkpoints/<phase>.json for all five §B phases."
    README.md → add ONE additive row (or line) mentioning --require-checkpoints for both gates; do not reflow the commands table.
    docs/SYSTEM-WORKFLOW.md §6 → add ONE additive bullet: agents writing checkpoint artifacts per phase; merge gate runs `canon flow-audit --require-checkpoints` and `canon qa-validate --require-checkpoints` to block integration when files are missing or malformed.

OUTPUT FORMAT:
- Emit HANDOFF_TO_QA mapping every scoper AC (22 in ac_traceability; 36 in acceptanceCriteria) to a covering test or file reference.
- Include `files_changed`.

STOP CONDITIONS:
- `pytest -q` exits 0 (target ≥237 passed).
- `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` exits 0.
- `git diff --name-only` intersects E2-T5 allowlist only:
    src/canon_systems/checkpoints.py (new)
    src/canon_systems/flow_audit.py (additive)
    src/canon_systems/qa_validate.py (additive)
    tests/test_flow_audit.py (append)
    tests/test_qa_validate.py (append)
    CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md
- No forbidden-surface edits.

DO NOT:
- Commit or push.
- Touch backend/**, infra/**, templates/**, hooks/**, scripts/**, pyproject.toml, pytest.ini, checkpoint_cli.py, .cursor/rules/**, .cursor/plans/**.
- Add third-party deps.
- Remove or reflow existing test bodies.

END_CURSOR_PILOT_PROMPT
```
