# Cursor SDK AWS validation (May 1, 2026)

## Objective

Validate whether Canon can run from AWS and use Cursor SDK as a remote execution layer against `https://github.com/CanonSystems/canon-systems`.

## Current result

The local Cursor SDK cloud path has been validated with a real Cursor API key:

- created a Cursor SDK cloud agent
- targeted `github.com/CanonSystems/canon-systems`
- streamed tool and assistant events
- returned `status: finished`
- returned structured `agentId`, `runId`, result text, model, duration, and repo metadata

The AWS deployment path has also been validated from ECS:

- `AWS_PROFILE=canon-systems-v2`
- secret id: `canon/cursor-sdk-poc/cursor-api-key`
- secret value confirmed non-empty (`SecretString` length 69)
- Docker build/push completed
- ECS task started through `projects/cursor-sdk-poc/scripts/aws-build-push-run.sh`
- read-only AWS run completed with `status: finished`
- write-path AWS run created a branch and PR

The earlier AWS failure was caused by local profile mismatch: `~/.canon/canon-systems.env` points at `AWS_PROFILE=canon-systems`, but `~/.aws/credentials` did not contain a `[canon-systems]` stanza. The working profile in this environment is `canon-systems-v2`.

## Roadmap implication

This validation upgrades the Cursor SDK path from strategic hypothesis to proven execution substrate.

Canon can now treat Cursor SDK cloud execution as the first reference `remote_worker` adapter:

- Canon-controlled AWS infrastructure can launch the run.
- Cursor SDK can operate against the target GitHub repository.
- Cursor SDK can stream runtime events back to Canon-observable logs.
- Cursor SDK can produce branch/commit/PR output.
- Canon can wrap that output in policy, evidence, checkpoint, QA, and release semantics.

The next product milestone is therefore **not** "can Canon run Cursor remotely?" That is now answered. The next milestone is:

- create a Canon evidence envelope for Cursor SDK runs
- archive the envelope and relevant phase packets/evidence to S3, then write
  DynamoDB run-ledger records connecting Cursor `agentId` / `runId`, branch,
  commit, PR, packet URIs, validation outcomes, and release status
- persist Cursor `agentId`, `runId`, ECS task ARN, GitHub branch/commit/PR, prompt hash, model, duration, and event summary
- add negative tests for missing evidence, failed runs, timeout, skipped QA, and unauthorized merge
- add cleanup/rotation tooling for Cursor API keys, ECR images, ECS task definitions, CloudWatch logs, and IAM policy attachments
- define whether customer-owned Cursor credentials are accepted, required, or avoided in the managed product

## Added harness

The validation harness lives under `projects/cursor-sdk-poc/`.

It now includes:

- `probe.mjs` — Cursor SDK runner with structured evidence output
- `Dockerfile` — container for ECS execution
- `scripts/aws-build-push-run.sh` — build, push, register, run, wait, and fetch CloudWatch logs
- `README.md` — local, cloud, and AWS usage

## Verified locally

Commands run successfully:

```bash
cd projects/cursor-sdk-poc
npm run check
npm ls @cursor/sdk
```

Confirmed SDK package:

```text
@cursor/sdk@1.0.11
```

Container build succeeded:

```bash
docker build -t canon-cursor-sdk-poc:local projects/cursor-sdk-poc
```

Container runtime produced the expected structured missing-secret failure:

```json
{"phase":"error","error":{"message":"Missing required environment variable: CURSOR_API_KEY"}}
```

## AWS credential note

If `aws` fails with:

```text
Unable to locate credentials. You can configure credentials by running "aws configure".
```

check whether `AWS_PROFILE` points at a profile that exists in `~/.aws/credentials`.

In this environment, use:

```bash
export AWS_PROFILE=canon-systems-v2
```

Longer-term options:

- align `~/.canon/canon-systems.env` with an existing profile
- or define `[canon-systems]` in `~/.aws/credentials` and `~/.aws/config`

## AWS execution command

After configuring AWS credentials and storing the Cursor API key in Secrets Manager:

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

Expected success evidence:

- ECR image push succeeds
- ECS task starts on `canon-systems-v2-dev-cluster`
- CloudWatch logs include `create_agent`
- CloudWatch logs include `run_started`
- CloudWatch logs include one or more `cursor_event` rows
- CloudWatch logs include `run_complete` with `status: finished`

## Completed AWS read-only run

Read-only ECS task:

```text
arn:aws:ecs:us-east-1:222274634742:task/canon-systems-v2-dev-cluster/d85e78b268624cc6b4d219f485562c42
```

Cursor SDK metadata:

```text
cursorAgentId: bc-094d7156-22c2-46c8-9251-113474757d8e
cursorRunId:   run-f84a6a41-2a39-4e1b-84bf-c3705253125b
status:        finished
durationMs:    20506
eventCount:    278
```

The run targeted `https://github.com/CanonSystems/canon-systems`, read repo files, returned a repository summary, and made no changes.

## Completed AWS write-path run

Write-path ECS task:

```text
arn:aws:ecs:us-east-1:222274634742:task/canon-systems-v2-dev-cluster/d656966b2378412bb8ac9dfdb97f4ec8
```

Cursor SDK metadata:

```text
cursorAgentId: bc-bb3c8998-3336-4822-b3bd-1bef697d647e
cursorRunId:   run-875e4e93-1f6b-4991-8d45-4fe0c650d239
status:        finished
durationMs:    24777
eventCount:    84
```

GitHub evidence:

```text
branch: cursor/cursor-sdk-write-path-smoke-647e
commit: 8d47e7c0f0a592fd1ab08039526a9f04cb89700f
PR:     https://github.com/CanonSystems/canon-systems/pull/9
state:  OPEN
diff:   docs/CURSOR-SDK-WRITE-PATH-SMOKE.md (+1/-0)
```

The Cursor SDK cloud agent, launched from ECS, created exactly one docs file:

```text
docs/CURSOR-SDK-WRITE-PATH-SMOKE.md
```

with the content:

```text
Cursor SDK AWS write-path smoke test.
```

## ECS networking note

The first ECS task reached `STOPPED` before container startup because it could not retrieve the Cursor API key from Secrets Manager:

```text
ResourceInitializationError: unable to pull secrets or registry auth: unable to retrieve secret from asm
```

The task was launched with `assignPublicIp=DISABLED` and landed in a subnet without working egress to Secrets Manager for this use case. For the validation run, set:

```bash
export ECS_ASSIGN_PUBLIC_IP=ENABLED
```

## Container platform note

Fargate expects `linux/amd64` for this task definition. The harness builds with:

```bash
docker build --platform linux/amd64 ...
```

## Next validation after AWS execution

1. Wrap the Cursor result in a first-class Canon evidence artifact rather than relying on CloudWatch logs alone.
2. Store that artifact through the durable packet/evidence archive and connect it to the task through the DynamoDB run ledger.
3. Add a controlled cleanup path for PoC ECR/task-definition/IAM artifacts.
4. Decide whether PR #9 should remain open as evidence or be closed after review.
5. Add a merge/release negative test proving a Cursor SDK-created PR without Canon evidence cannot pass Canon policy.
