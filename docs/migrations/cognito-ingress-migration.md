# Cognito + Ingress Migration

This runbook migrates Canon memory traffic from raw IP endpoints + IAM keypair auth to a stable domain endpoint and Cognito-backed auth phases.

## Goals

- Route memory API calls through a stable hostname (`memory.canon-systems.com` or your chosen `canon-systems.com` subdomain).
- Use phased auth rollout: `prepare` -> `canary` -> `enforce`.
- Keep rollback available at every phase.

## Prerequisites

- ECS service healthy in target account.
- DNS and TLS ready for the canonical domain.
- Cognito pool/client configured for backend validation.
- AWS profile with `secretsmanager:GetSecretValue` and `PutSecretValue`.

## Phase Workflow

1. **Prepare**
   - Update repo env:
     - `canon auth-migration prepare --domain memory.canon-systems.com`
   - Update AWS secrets in dry-run first:
     - `python scripts/migrate_memory_secrets.py --profile <p> --phase prepare`
   - Validate secret endpoints:
     - `python scripts/validate_memory_endpoints.py --profile <p> --secret-id <id>`

2. **Canary**
   - Apply secret writes:
     - `python scripts/migrate_memory_secrets.py --profile <p> --phase canary --apply`
   - Flip selected repos/users to canary:
     - `canon auth-migration canary --domain memory.canon-systems.com`
   - Verify capture + ask success and latency.

3. **Enforce**
   - Require Cognito path:
     - `canon auth-migration enforce --domain memory.canon-systems.com`
   - Apply enforce secrets:
     - `python scripts/migrate_memory_secrets.py --profile <p> --phase enforce --apply`
   - Verify legacy keypair-only clients are rejected.

## Observability Gates

- Error rate no worse than baseline +5%.
- Timeout rate below 1%.
- Canary success rate above 99% for capture/ask.

Do not advance phases unless all gates are green for at least 30 minutes.

## CSC `canon-systems` stable dev URLs

For secret `canon-memory-dev/memory-layer__csc__canon-systems`, follow **`docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md` §1.2c**: apply/import optional ECS target-group attachment in `infra/terraform`, update the four HTTPS URL keys + optional `canon doctor --fix-cache`, validate with `scripts/validate_memory_endpoints.py` and `canon memory-health`. Rollback = previous secret version + cache clear.

## Rollback Trigger

Rollback immediately if:

- capture/ask failures exceed threshold
- auth failures spike after phase shift
- ingress endpoint becomes unreachable

Use `scripts/auth-migration/rollback.sh` and restore previous secrets version.
