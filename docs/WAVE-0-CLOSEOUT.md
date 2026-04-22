# Wave 0 closeout — Canon Memory Platform v1 (consolidation)

## Wave summary

- **Branch:** `wave/0/canon-memory-v1`
- **Final tip (post–E0-T5 commit):** TBD (this document updated at E0-T5; replace when the E0-T5 commit SHA exists)
- **Scope:** E0-T1 through E0-T5 — repository consolidation, backend layout, Terraform root import, and consolidation smoke harness

## Per-task commits

| Task  | Commit   | Short description / QA |
|-------|----------|-------------------------|
| E0-T1 | `7eba576` | (per wave history) |
| E0-T2 | `da02e41` | (per wave history) |
| E0-T3 | `35df118` | (per wave history) |
| E0-T4 | `30a3b59` | (per wave history) |
| E0-T5 | TBD       | Wave 0 closeout smoke harness — this task |

## Green-signal definition

Wave 0 is **green** when:

- `bash scripts/smoke-test.sh` exits 0 from a clean shell at the repo root (build → `pytest -q` → `terraform` init/validate, or documented skip for terraform only via `SMOKE_SKIP_TERRAFORM=1` when the binary is unavailable).
- GitHub Actions workflow **Canon Smoke Test** (`.github/workflows/ci.yml`) passes on `pull_request` and on `push` to `main` and `wave/**`.
- Root `pytest -q` passes (including `tests/test_consolidation_smoke.py`).

## Deferred follow-ups

- **OQ-E0-T4-01:** `terraform plan` shows no changes against production — **operator post-merge** (reconcile remote state; Wave 0 does not require a green plan in CI).
- **OQ-E0-T5-01:** `canon capture` → `ask` → `dor-log` exercised against the live three URLs — **operator post-merge or Wave 1** (no canon CLI or live URL hits in the E0-T5 smoke harness).

Other open questions from scoping (non-blocking for Wave 0): Python version matrix, pip caching in CI, ruff/format in smoke, and replacing `template-policy-guard.yml` are explicitly **out of scope** for this closeout; they remain backlog items if needed.

## Explicit acceptance

**Wave 0 is complete under: consolidation complete, reconciliation pending.**

Consolidation (backend sources, Terraform root, smoke harness) is in-repo and verifiable without AWS credentials. Full production reconciliation (remote Terraform state, live API behavior) is deferred to operator follow-up and later waves, as captured in the OQ items above.
