# Auth Migration Rollback Runbook

Use this when migration phases cause elevated errors or degraded memory writes.

## Trigger Conditions

- Memory capture timeout or failure rate above agreed threshold.
- Unexpected auth rejection for known-good Cognito users.
- Ingress endpoint unreachable from operator network.

## Preconditions

- Confirm incident scope (single repo vs all repos).
- Confirm latest successful phase/time window.
- Identify affected secret IDs and repos.

## Rollback Steps

1. Roll back repo-local migration state:

```bash
scripts/auth-migration/rollback.sh --repo-root /path/to/repo
```

2. Restore Secrets Manager values:
   - Either re-run with known-good phase in dry-run first:

```bash
python scripts/migrate_memory_secrets.py --profile <profile> --phase prepare
```

   - Or restore prior secret version in AWS console/CLI if needed.

3. Re-check endpoint health:

```bash
python scripts/validate_memory_endpoints.py \
  --profile <profile> \
  --secret-id <secret-id>
```

4. Confirm capture path:

```bash
canon --repo-root /path/to/repo capture --summary "rollback probe" --user-text "probe" --assistant-text "probe"
```

## Verification Checklist

- `canon auth-migration status` shows `CANON_AUTH_PHASE=rollback`.
- Secret endpoints match known-good values.
- Capture no longer reports timeout/connection errors.
- Ask returns expected recent memory items.

## Aftercare

- Log incident timeline and root cause.
- Freeze phase progression until remediation is reviewed.
- Add regression test or alert for the triggering failure mode.
