#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-canon-systems-v2-dev-cluster}"
ECS_SERVICE="${ECS_SERVICE:-canon-systems-v2-dev-baseline}"
ECR_REPO="${ECR_REPO:-canon/cursor-sdk-poc}"
TASK_FAMILY="${TASK_FAMILY:-canon-cursor-sdk-poc}"
LOG_GROUP="${LOG_GROUP:-/ecs/canon-systems-v2-dev}"
LOG_PREFIX="${LOG_PREFIX:-cursor-sdk-poc}"
ECS_ASSIGN_PUBLIC_IP="${ECS_ASSIGN_PUBLIC_IP:-DISABLED}"
CURSOR_POC_REPO_URL="${CURSOR_POC_REPO_URL:-https://github.com/CanonSystems/canon-systems}"
CURSOR_POC_STARTING_REF="${CURSOR_POC_STARTING_REF:-main}"
CURSOR_POC_MODEL="${CURSOR_POC_MODEL:-composer-2}"
CURSOR_POC_RUNTIME="${CURSOR_POC_RUNTIME:-cloud}"
CURSOR_POC_PROMPT="${CURSOR_POC_PROMPT:-Summarize what this repository does, identify one low-risk improvement area, and stop without changing any files.}"
CURSOR_POC_AUTO_CREATE_PR="${CURSOR_POC_AUTO_CREATE_PR:-0}"

if [[ -z "${CURSOR_API_KEY_SECRET_ARN:-}" ]]; then
  echo "CURSOR_API_KEY_SECRET_ARN is required. Store the Cursor API key in Secrets Manager and pass its ARN." >&2
  exit 2
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text --region "$AWS_REGION")"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"

aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION" >/dev/null

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com" >/dev/null

docker build --platform linux/amd64 -t "$IMAGE_URI" "$ROOT_DIR"
docker push "$IMAGE_URI" >/dev/null

BASE_TASK_DEF_ARN="$(aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION" \
  --query 'services[0].taskDefinition' \
  --output text)"

EXECUTION_ROLE_ARN="$(aws ecs describe-task-definition \
  --task-definition "$BASE_TASK_DEF_ARN" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.executionRoleArn' \
  --output text)"

TASK_ROLE_ARN="$(aws ecs describe-task-definition \
  --task-definition "$BASE_TASK_DEF_ARN" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.taskRoleArn' \
  --output text)"

SUBNETS="$(aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION" \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
  --output text | tr '\t' ',')"

SECURITY_GROUPS="$(aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION" \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups' \
  --output text | tr '\t' ',')"

TASK_DEF_ARN="$(aws ecs register-task-definition \
  --region "$AWS_REGION" \
  --family "$TASK_FAMILY" \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn "$EXECUTION_ROLE_ARN" \
  --task-role-arn "$TASK_ROLE_ARN" \
  --container-definitions "[{\"name\":\"cursor-sdk-poc\",\"image\":\"$IMAGE_URI\",\"essential\":true,\"secrets\":[{\"name\":\"CURSOR_API_KEY\",\"valueFrom\":\"$CURSOR_API_KEY_SECRET_ARN\"}],\"environment\":[{\"name\":\"CURSOR_POC_RUNTIME\",\"value\":\"$CURSOR_POC_RUNTIME\"},{\"name\":\"CURSOR_POC_REPO_URL\",\"value\":\"$CURSOR_POC_REPO_URL\"},{\"name\":\"CURSOR_POC_STARTING_REF\",\"value\":\"$CURSOR_POC_STARTING_REF\"},{\"name\":\"CURSOR_POC_MODEL\",\"value\":\"$CURSOR_POC_MODEL\"},{\"name\":\"CURSOR_POC_PROMPT\",\"value\":\"$CURSOR_POC_PROMPT\"},{\"name\":\"CURSOR_POC_AUTO_CREATE_PR\",\"value\":\"$CURSOR_POC_AUTO_CREATE_PR\"}],\"logConfiguration\":{\"logDriver\":\"awslogs\",\"options\":{\"awslogs-group\":\"$LOG_GROUP\",\"awslogs-region\":\"$AWS_REGION\",\"awslogs-stream-prefix\":\"$LOG_PREFIX\"}}}]" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"

TASK_ARN="$(aws ecs run-task \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --launch-type FARGATE \
  --task-definition "$TASK_DEF_ARN" \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUPS],assignPublicIp=$ECS_ASSIGN_PUBLIC_IP}" \
  --query 'tasks[0].taskArn' \
  --output text)"

echo "Started ECS task: $TASK_ARN"
aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN"

aws ecs describe-tasks \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --tasks "$TASK_ARN" \
  --query 'tasks[0].{lastStatus:lastStatus,stopCode:stopCode,stoppedReason:stoppedReason,containers:containers[].{name:name,lastStatus:lastStatus,exitCode:exitCode,reason:reason}}' \
  --output json

TASK_ID="${TASK_ARN##*/}"
LOG_STREAM="$(aws logs describe-log-streams \
  --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name-prefix "$LOG_PREFIX/cursor-sdk-poc/$TASK_ID" \
  --query 'logStreams[0].logStreamName' \
  --output text)"

echo "CloudWatch log stream: $LOG_STREAM"
if [[ "$LOG_STREAM" == "None" || -z "$LOG_STREAM" ]]; then
  echo "No CloudWatch log stream was created for task $TASK_ARN" >&2
  exit 3
fi
aws logs get-log-events \
  --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name "$LOG_STREAM" \
  --query 'events[].message' \
  --output text
