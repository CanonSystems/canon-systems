# Cursor SDK PoC

Small proof-of-concept for validating whether a Canon-controlled service can invoke Cursor SDK runs using a provided `CURSOR_API_KEY`.

## What this validates

- a backend process can create a Cursor agent with `@cursor/sdk`
- the process can start a run and stream events
- the process can wait for the final result
- Canon could, in principle, wrap governance and evidence around the execution layer

## Install

```bash
cd projects/cursor-sdk-poc
npm install
```

## Local runtime probe

```bash
export CURSOR_API_KEY=...
export CURSOR_POC_RUNTIME=local
export CURSOR_POC_CWD=/absolute/path/to/repo
npm run probe
```

## Cloud runtime probe

```bash
export CURSOR_API_KEY=...
export CURSOR_POC_RUNTIME=cloud
export CURSOR_POC_REPO_URL=https://github.com/<owner>/<repo>
export CURSOR_POC_STARTING_REF=main
npm run probe
```

## AWS ECS validation

Store the Cursor API key in AWS Secrets Manager first. The ECS task injects it
as a secret and never prints it.

```bash
cd /Users/edwardwalker/localwork/canon-systems
export AWS_PROFILE=canon-systems-v2
export AWS_REGION=us-east-1
export ECS_ASSIGN_PUBLIC_IP=ENABLED
export CURSOR_API_KEY_SECRET_ARN="$(aws secretsmanager describe-secret \
  --secret-id canon/cursor-sdk-poc/cursor-api-key \
  --query ARN --output text)"
projects/cursor-sdk-poc/scripts/aws-build-push-run.sh
```

Defaults used by the script:

- `ECS_CLUSTER=canon-systems-v2-dev-cluster`
- `ECS_SERVICE=canon-systems-v2-dev-baseline`
- `ECS_ASSIGN_PUBLIC_IP=DISABLED` unless overridden
- `ECR_REPO=canon/cursor-sdk-poc`
- `CURSOR_POC_RUNTIME=cloud`
- `CURSOR_POC_REPO_URL=https://github.com/CanonSystems/canon-systems`
- `CURSOR_POC_STARTING_REF=main`
- `CURSOR_POC_MODEL=composer-2`

Optional environment variables:

- `CURSOR_POC_MODEL` — default `composer-2`
- `CURSOR_POC_PROMPT` — default safe read-only repository summary prompt
- `CURSOR_POC_AUTO_CREATE_PR=1` — enable PR creation for cloud runs

## Success criteria

The probe is considered successful when it can:

1. create an agent
2. start a run
3. stream at least one event or complete cleanly
4. return final result metadata

## Notes

- This is a technical validation only. It does **not** confirm commercial terms, pricing, or long-term auth suitability for Canon.
- The default prompt avoids code changes so the first run can be used as a low-risk connectivity test.
