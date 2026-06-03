#!/usr/bin/env bash
# Create Canon Memory Platform DynamoDB tables (idempotent) for dev plane.
# Matches infra/terraform/modules/dynamodb-canon-state/main.tf naming.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
PREFIX="${1:-canon-systems-v2-dev}"

create_pk_sk_table() {
  local name="$1"
  local purpose="$2"
  if aws dynamodb describe-table --table-name "$name" --region "$REGION" >/dev/null 2>&1; then
    echo "exists: $name"
    return 0
  fi
  echo "creating: $name"
  aws dynamodb create-table \
    --table-name "$name" \
    --region "$REGION" \
    --billing-mode PAY_PER_REQUEST \
    --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S \
    --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE \
    --sse-specification Enabled=true \
    --tags "Key=Purpose,Value=${purpose}"
  aws dynamodb update-continuous-backups \
    --table-name "$name" \
    --region "$REGION" \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true 2>/dev/null || true
  aws dynamodb wait table-exists --table-name "$name" --region "$REGION"
}

create_pk_sk_table "${PREFIX}-canon-state" "canon-state"
aws dynamodb update-time-to-live \
  --table-name "${PREFIX}-canon-state" \
  --region "$REGION" \
  --time-to-live-specification "Enabled=true,AttributeName=lease_expires_at" 2>/dev/null || true

create_pk_sk_table "${PREFIX}-canon-run-ledger" "canon-run-ledger"
create_pk_sk_table "${PREFIX}-canon-tasks" "canon-tasks"

echo "done: ${PREFIX}-canon-{state,run-ledger,tasks}"
